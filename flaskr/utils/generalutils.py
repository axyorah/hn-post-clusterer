import os
import sys
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
    cluster_stories_with_faiss,
    project_embeddings,

)

from flaskr.utils.dbutils import (
    get_stories_with_children_from_id_range,
    get_id_list_from_sqlite_rows,
    get_document_list_from_sqlite_rows,
    get_document_dict_from_sqlite_rows
)

from flaskr.utils.clusterutils import (
    copy_and_measure_generator
)

# TODO: use `cycle` instead of `tee` for copying generators...

class BatchedPipeliner:
    def __init__(self, request):
        self.rqparser = RequestParser()
        self.request_raw = request
        self.request_form = self.rqparser.parse(request)

        self._stories = None
        self._embeddings = None

        self.ids = []
        self.labels = []
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
            for b_id in range(begin_id, end_id, delta_id):
                request_form = self.request_form
                request_form['begin_id'] = b_id
                request_form['end_id'] = min(b_id + delta_id, end_id)

                story_rows = get_stories_with_children_from_id_range(request_form) # list of sql rows
                story_dicts = get_document_dict_from_sqlite_rows(story_rows) # dict of dicts

                # TODO: make it a list of dicts and adjust helpers in semanticutils.py
                if len(story_dicts):
                    yield story_dicts
        
        # copy genrator: save one copy, return another
        gen = batch_generator(begin_id, end_id, delta_id)
        print('[INFO] copying story generator...')
        batches, (_,_) = copy_and_measure_generator(gen, num_copies=2)
        self._stories = batches[0]

        return batches[1]

    def get_embedding_batches(self, story_batches):
        print('[INFO] generating embeddings...')
        def batch_generator(story_batches):
            for batch in story_batches:
                ids, embeds = get_story_embeddings(batch)
                self.ids.append(ids)
                yield embeds    
        
        # copy genrator: save one copy, return another
        gen = batch_generator(story_batches)
        print('[INFO] copying embedding generator...')
        batches, (_,_) = copy_and_measure_generator(gen, num_copies=2)
        self._embeddings = batches[0]

        return batches[1]

    def cluster_story_batches(self, embedding_batches, n_clusters=10):
        print(f'[INFO] clustering stories to {n_clusters} clusters...')
        # TODO: n_clusters should be accessed from form request
        batches, (_,_) = copy_and_measure_generator(embedding_batches, num_copies=2)
        
        self.kmeans = MiniBatchKMeans(n_clusters=n_clusters)        
        # train kmeans
        for batch in batches[0]:
            self.kmeans.partial_fit(batch)

        # predict labels
        for batch in batches[1]:
            lbls = self.kmeans.predict(batch)
            self.labels.append(lbls)

        self.centroids = self.kmeans.cluster_centers_

        return self.labels

    def serialize_result(self, fname='./data/df.csv'):
        # check if all the necessary data is available
        if self.kmeans is None or self._embeddings is None:
            raise RuntimeError(
                'There is nothing to serialize yet. ' +\
                'You must obtain and cluster embeddings first!'
            )

        story_batches, (l,_) = copy_and_measure_generator(self._stories, num_copies=2)
        self._stories = story_batches[0]
        if not l:
            raise RuntimeError(
                'Story generator is empty! ' +\
                'Consider rerunning .get_story_batches()'
            )

        emb_batches, (l,_) = copy_and_measure_generator(self._embeddings, num_copies=3)
        self._embeddings = emb_batches[0]
        if not l:
            raise RuntimeError(
                'Embedding generator is empty! ' +\
                'Consider rerunning .get_embedding_batches()'
            )

        if not self.labels:
            raise RuntimeError(
                'There are no labels to serialize! ' +\
                'Consider running .cluster_story_batches()'
            )     

        # --- project to low-dim space ---
        n_dims = 10 # num dimensions to project embeddings onto 
        # if there are are more clusters that n_dims we can "cheat"
        # and use centroids to find projection axes (PCA);
        # otherwise use partial PCA
        print(f'[INFO] projecting embeddings to {n_dims}-dim space...')
        if len(self.kmeans.cluster_centers_) > n_dims:
            pca = PCA(n_components=n_dims)
            pca.fit(self.kmeans.cluster_centers_)
        else:
            pca = IncrementalPCA(n_components=n_dims)
            for emb_batch in emb_batches[1]:
                pca.partial_fit(emb_batch)

        # --- serialize ---
        print(f'[INFO] serializing result to {fname}...')
        fields = ['id', 'title', 'url','label', 'embedding']
        with open(fname, 'w') as f:
            f.write('\t'.join(fields) + '\n')

        for id_batch, st_batch, emb_batch, lbl_batch in zip(self.ids, story_batches[1], emb_batches[2], self.labels):
            emb_proj = pca.transform(emb_batch)
            for sid, emb, lbl in zip(id_batch, emb_proj, lbl_batch):
                with open(fname, 'a') as f:
                    f.write(
                        '\t'.join([
                            str(sid),
                            st_batch[sid].get('title') or '',
                            st_batch[sid].get('url') or '', # nullable
                            str(lbl),
                            ','.join(str(val) for val in emb)
                        ]) + '\n'
                    )

        return True