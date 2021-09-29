import os
import sys
import warnings
from itertools import tee
from gensim.parsing.preprocessing import RE_NONALPHA
import requests as rq
import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import PCA, IncrementalPCA
from sklearn.manifold import TSNE

from flaskr.utils.formutils import (
    RequestParser,
)

from flaskr.utils.semanticutils import (
    get_story_embeddings,

)

from flaskr.utils.dbutils import (
    get_stories_with_children_from_id_range,
    get_document_dict_from_sqlite_rows
)

from flaskr.utils.clusterutils import (
    copy_and_measure_generator,
    copy_and_measure_batch_generator
)

# TODO: use `cycle` instead of `tee` for copying generators...
# TODO: make 'measure' in 'copy_and_measure_generator' optional

class BatchedPipeliner:
    def __init__(self, request):
        self.rqparser = RequestParser()
        self.request_raw = request
        self.request_form = self.rqparser.parse(request)
        
        self._num_batches = 0
        self._num_stories = 0

        self._stories = None
        self._embeddings = None
        self._labels = None

        self.kmeans = None
        self.centroids = None
        """
        pipe:
        - get stories from db
        - get story embeddings (requires removing markup and splitting into sentences)
        - cluster stories with batched kmeans        
        - serialize result
        """

    def get_story_batches(self, delta_id=10000):
        """
        returns a generator, where each element 
        is a list ("batch") of story dicts with the following fields:
            'story_id', 'author', 'unix_time', 'score', 
            'title', 'url', 'num_comments', 'children'
        """
        print('[INFO] fetching data from db...')
        begin_id = int(self.request_form["begin_id"])
        end_id = int(self.request_form["end_id"])

        def batch_generator(begin_id, end_id, delta_id):
            num = 0
            for b_id in range(begin_id, end_id, delta_id):
                request_form = self.request_form
                request_form['begin_id'] = b_id
                request_form['end_id'] = min(b_id + delta_id, end_id)

                story_rows = get_stories_with_children_from_id_range(request_form) # list of sql rows
                story_dicts = get_document_dict_from_sqlite_rows(story_rows, aslist=True) # list of dicts

                # TODO: make it a list of dicts and adjust helpers in semanticutils.py
                if len(story_dicts):
                    num += len(story_dicts)
                    yield story_dicts
            print(f'[INFO] got {num} stories!')
        
        # copy genrator: save one copy, return another
        gen = batch_generator(begin_id, end_id, delta_id)
        print('[INFO] copying story generator...')
        batches, (num_batches, num_items, _) = copy_and_measure_batch_generator(gen, num_copies=2)
        self._num_batches = num_batches
        self._num_stories = num_items
        self._stories = batches[0]

        return batches[1]
    
    def get_embedding_batches(self, story_batches):
        print('[INFO] generating embeddings...')
        def batch_generator(story_batches):
            num = 0
            for batch in story_batches:
                num += len(batch)
                yield get_story_embeddings(batch)
            print(f'[INFO] got {num} embeddings!')
        
        # copy genrator: save one copy, return another
        gen = batch_generator(story_batches)
        print('[INFO] copying embedding generator...')
        batches = tee(gen, 2)
        self._embeddings = batches[0]

        return batches[1]

    def reduce_embedding_dimensionality(self, embedding_batches=None, n_dims=100):
        if embedding_batches is None and self._embeddings is None:
            raise RuntimeError(
                'There is nothing to reduce yet! ' +\
                'You must obtain and story embeddings first! ' +\
                'Consider running `get_embedding_batches()` or `set_embedding_batches()`'
            )

        if self._num_stories < n_dims:
            warnings.warn(
                'Can not reduce the dimensionality of the embeddings!\n' +\
                'Dimensionality should be less or equal to the number of samples, ' +\
                f'got n_samples={self._num_stories} and n_dims={n_dims}!\n' +\
                'Returning original embeddings without changes.'
            )
            return embedding_batches or self._embeddings

        # copy high dim embeddings
        highdim_batches = tee(embedding_batches or self._embeddings)

        # train pca
        print(f'[INFO] reducing embedding dimensionality to {n_dims}...')
        pca = IncrementalPCA(n_components=n_dims)
        for batch in highdim_batches[0]:
            pca.partial_fit(batch)
        
        # reduce
        def batch_generator(batches):
            for batch in batches:
                yield pca.transform(batch)

        lowdim_batches = tee(batch_generator(highdim_batches[1]), 2)
        self._embeddings = lowdim_batches[0]
        return lowdim_batches[1]
    
    def cluster_story_batches(self, embedding_batches=None, n_clusters=10):
        if embedding_batches is None and self._embeddings is None:
            raise RuntimeError(
                'There is nothing to cluster yet! ' +\
                'You must obtain and story embeddings first! ' +\
                'Consider running `get_embedding_batches()` or `set_embedding_batches()`'
            )

        # TODO: n_clusters should be accessed from form request
        print('[INFO] copying embeddings')
        batches = tee(embedding_batches or self._embeddings, 2)
        
        print(f'[INFO] clustering stories to {n_clusters} clusters...')
        self.kmeans = MiniBatchKMeans(n_clusters=n_clusters)        
        # train kmeans
        for batch in batches[0]:
            self.kmeans.partial_fit(batch)

        self.centroids = self.kmeans.cluster_centers_

        # predict labels
        def cluster(batches):
            for batch in batches:
                yield self.kmeans.predict(batch)

        self._labels = cluster(batches[1])
    
    def serialize_result(self, fname='./data/df.csv'):
        # check if all the necessary data is available
        if self.kmeans is None or self._embeddings is None:
            raise RuntimeError(
                'There is nothing to serialize yet. ' +\
                'You must obtain and cluster embeddings first!'
            )

        print('[INFO] copying stories...')
        story_batches, (l,_) = copy_and_measure_generator(self._stories, num_copies=2)
        self._stories = story_batches[0]
        if not l:
            raise RuntimeError(
                'Story generator is empty! ' +\
                'Consider rerunning .get_story_batches()'
            )
        
        print('[INFO] copying embeddings...')
        emb_batches, (l,_) = copy_and_measure_generator(self._embeddings, num_copies=2)
        self._embeddings = emb_batches[0]
        if not l:
            raise RuntimeError(
                'Embedding generator is empty! ' +\
                'Consider rerunning .get_embedding_batches()'
            )

        if not self._labels:
            raise RuntimeError(
                'There are no labels to serialize! ' +\
                'Consider running .cluster_story_batches()'
            )     

        # --- project to low-dim space ---
        n_dims = min(10, len(self.kmeans.cluster_centers_)) # num dimensions to project embeddings onto 
        print(f'[INFO] projecting embeddings to {n_dims}-dim space...')
        pca = PCA(n_components=n_dims)
        pca.fit(self.kmeans.cluster_centers_)

        # --- serialize ---
        print(f'[INFO] serializing result to {fname}...')
        fields = ['id', 'title', 'url','label', 'embedding']
        with open(fname, 'w') as f:
            f.write('\t'.join(fields) + '\n')

        for st_batch, emb_batch, lbl_batch in zip(story_batches[1], emb_batches[1], self._labels):
            # reduce dimensionality with pca if it hasn't already been done
            # otehrwise take n_dims first eigenvecs
            emb_proj = pca.transform(emb_batch) if emb_batch.shape[1] == 768 else emb_batch[:,:n_dims]
            for st, emb, lbl in zip(st_batch, emb_proj, lbl_batch):
                with open(fname, 'a') as f:
                    f.write(
                        '\t'.join([
                            str(st.get('story_id')),
                            st.get('title') or '',
                            st.get('url') or '', # nullable
                            str(lbl),
                            ','.join(str(val) for val in emb)
                        ]) + '\n'
                    )

        return True