from typing import Any, Dict, List, Optional, Generator

import os
import sys
import warnings
from itertools import tee
import requests as rq
import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import PCA, IncrementalPCA
from sklearn.manifold import TSNE

from flaskr.utils.nlp_utils import (
    StoryEmbedder,
    html2sentences,
)

from flaskr.utils.db_utils import (
    DBHelper as dbh,
    Story, 
    StoryList
)

from flaskr.utils.cluster_utils import (
    copy_and_measure_generator,
    copy_and_measure_batch_generator,
    BatchedGeneratorStandardizer
)

def rebatch_generator(batches: Generator, min_batch_size: int):
    """
    resamples generator of batches so that 
    new batches have atleast `min_batch_size` elements
    """
    prev, curr = [], []
    for batch in batches:
        curr += batch
        if len(curr) >= min_batch_size:
            if prev:
                yield prev
            prev = curr.copy()
            curr = []

    # last batch
    yield prev + curr

class BatchedPipeliner:
    def __init__(self, request_form: Dict):
        self.request_form = request_form

        self._n_clusters = self.request_form['n_clusters']
        self._model_name = self.request_form['model_name']

        self._n_pca_dims = 100
        self._min_batch_size = 100
        self._num_batches = 0
        self._num_stories = 0

        self._stories = None
        self._embeddings = None
        self._labels = None

        self.embedder = StoryEmbedder(model_name=self._model_name)
        self.scaler = BatchedGeneratorStandardizer()
        self.kmeans = MiniBatchKMeans(n_clusters=self._n_clusters)
        self.pca = None
        self.centroids = None
        """
        pipe:
        - get stories from db
        - get story embeddings (requires removing markup and splitting into sentences)
        - standardize/normalize embeddings
        - cluster stories with batched kmeans        
        - serialize result
        """

    def get_story_batches(self, delta_ts: int = 100000) -> Generator:
        """
        queries db based on form request,
        recursively collects all comments for each story,
        returns a generator, where each element 
        is a list ("batch") of story dicts with the following fields:
            'story_id', 'author', 'unix_time', 'score', 
            'title', 'url', 'num_comments', 'children'
        """
        print('[INFO] fetching data from db...')

        get_query = f'''
            {Story.RECURSIVE_CTE_WITHOUT_WHERE}
            WHERE 
                s.unix_time BETWEEN ? AND ? AND
                s.num_comments BETWEEN ? AND ? AND
                s.score BETWEEN ? AND ?
            ;
        '''

        begin_ts = int(self.request_form["begin_ts"])
        end_ts = int(self.request_form["end_ts"])

        def batch_generator(begin_ts: int, end_ts: int, delta_ts: int) -> List:
            num = 0
            for b_ts in range(begin_ts, end_ts, delta_ts):                
                params = (
                    b_ts, min(b_ts + delta_ts, end_ts),
                    self.request_form['begin_comm'], self.request_form['end_comm'],
                    self.request_form['begin_score'], self.request_form['end_score']
                )

                story_dicts = dbh.get_query(get_query, params)

                if len(story_dicts):
                    num += len(story_dicts)
                    yield story_dicts
            print(f'[INFO] got {num} stories!')
        
        # get stories
        gen = batch_generator(begin_ts, end_ts, delta_ts)

        # rebatch stories
        gen = rebatch_generator(gen, self._min_batch_size)

        # copy genrator: save one copy, return another
        print('[INFO] copying story generator...')
        batches, (num_batches, num_items, _) = copy_and_measure_batch_generator(gen, num_copies=2)
        self._num_batches = num_batches
        self._num_stories = num_items
        self._stories = batches[0]

        return batches[1]

    def get_story_embeddings(self, data: List[Dict]) -> List[np.ndarray]:
        """
        INPUTS:
           data: list: each element is a story dict with keys:
               story_id, author, unix_time, score, title, url, num_comments, children
               e.g.:
               [
                   {story_id: ..., author: ..., unix_time: ..., title: ..., ...},
                   {storY_id, ..., author: ..., unix_time: ..., title: ..., ...},
               ]
        OUTPUTS:
            list: each element is a BERT embedding based on story comments
            [
                ndarray of floats with shape (768,), or (384,)
                ...
            ]
        """
        return [
            self.embedder.embed_and_average_sentences(
                html2sentences(story['children'])
            ) for story in data
        ]
    
    def fetch_or_generate_story_embeddings(self, data: List[Dict]) -> List[np.ndarray]:
        """
        the same as `get_story_embeddings(.)` but instead of always 
        calculating the embedding on the fly 
        it fetches the embedding from db if present 
        and writes it to db when calculated
        INPUTS:
           data: list: each element is a story dict with keys:
               story_id, author, unix_time, score, title, url, num_comments, children
               e.g.:
               [
                   {story_id: ..., author: ..., unix_time: ..., title: ..., ...},
                   {storY_id, ..., author: ..., unix_time: ..., title: ..., ...},
               ]
        OUTPUTS:
            list: each element is a BERT embedding based on story comments
            [
                ndarray of floats with shape (768,), or (384,)
                ...
            ]
        """
        update_query = '''
            UPDATE story
            SET comment_embedding = ?
            WHERE story_id = ?        
        '''

        batch = []
        for story in data:
            # fetch embedding if roberta is selected and the embedding is already in db
            if self.request_form['model_name'] == 'sentence-transformers/all-distilroberta-v1' and\
                story.get('comment_embedding'):
                embedding = np.array([
                    float(val) for val in story['comment_embedding'].split(',')
                ])
            else:
                embedding = self.embedder.embed_and_average_sentences(
                    html2sentences(story['children'])
                )
                # write embedding to db (update story row) only if roberta was used
                if self.request_form['model_name'] == 'sentence-transformers/all-distilroberta-v1':
                    story['comment_embedding'] = ','.join(str(val) for val in embedding)

                    dbh.mod_query(
                        update_query, 
                        (story['comment_embedding'], story['story_id']), 
                        commit=True
                    )

            batch.append(embedding)

        return batch

    def get_embedding_batches(self, story_batches: Optional[Generator] = None) -> Generator:
        """
        each element of a batch is a (batch_size, embed_dim) numpy array
        (embed_dim is 768 for default bert transformers and 384 for minis)
        """
        if story_batches is None and self._stories is None:
            raise RuntimeError(
                'There is nothing to embed! '+\
                'Consider running `get_story_batches()` first!'
            )

        print('[INFO] generating embeddings...')
        def batch_generator(story_batches):
            num = 0
            for batch in story_batches:
                num += len(batch)
                #yield np.stack(self.get_story_embeddings(batch))
                yield np.stack(self.fetch_or_generate_story_embeddings(batch))
            print(f'[INFO] got {num} embeddings!')
        
        # copy genrator: save one copy, return another
        gen = batch_generator(story_batches or self._stories)
        print('[INFO] copying embedding generator...')
        batches = tee(gen, 2)
        self._embeddings = batches[0]

        return batches[1]

    def standardize_embedding_batches(self, embedding_batches: Optional[Generator] = None) -> Generator:
        if embedding_batches is None and self._embeddings is None:
            raise RuntimeError(
                'There is nothing to standardize! '+\
                'Consider running `get_embedding_batches()` first!'
            )
        
        print('[INFO] standardizing embeddings...')
        normalized = self.scaler.fit_transform(embedding_batches or self._embeddings)
        batches = tee(normalized, 2)
        self._embeddings = batches[0]

        return batches[1]

    def reduce_embedding_dimensionality(self, embedding_batches: Optional[Generator] = None, n_dims: int = 100) -> Generator:
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

        # adjust _n_pca_dims if needed
        self._n_pca_dims = n_dims

        # copy high dim embeddings
        highdim_batches = tee(embedding_batches or self._embeddings, 2)

        # train pca
        print(f'[INFO] reducing embedding dimensionality to {self._n_pca_dims}...')
        self.pca = IncrementalPCA(n_components=self._n_pca_dims)
        for batch in highdim_batches[0]:
            self.pca.partial_fit(batch)
        
        # reduce
        def batch_generator(batches):
            for batch in batches:
                yield self.pca.transform(batch)

        lowdim_batches = tee(batch_generator(highdim_batches[1]), 2)
        self._embeddings = lowdim_batches[0]
        return lowdim_batches[1]
    
    def cluster_story_batches(self, embedding_batches: Optional[Generator] = None) -> None:
        if embedding_batches is None and self._embeddings is None:
            raise RuntimeError(
                'There is nothing to cluster yet! ' +\
                'You must obtain and story embeddings first! ' +\
                'Consider running `get_embedding_batches()` or `set_embedding_batches()`'
            )

        # TODO: n_clusters should be accessed from form request
        print('[INFO] copying embeddings')
        batches = tee(embedding_batches or self._embeddings, 2)
        
        print(f'[INFO] clustering stories to {self._n_clusters} clusters...')
        #self.kmeans = MiniBatchKMeans(n_clusters=n_clusters)
        # train kmeans
        for batch in batches[0]:
            self.kmeans.partial_fit(batch)

        self.centroids = self.kmeans.cluster_centers_

        # predict labels
        def cluster(batches):
            for batch in batches:
                yield self.kmeans.predict(batch)

        self._labels = cluster(batches[1])
    
    def serialize_result(self, fname: str = './data/df.csv') -> bool:
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

        # --- project to low-dim space if it wasn't done already ---
        # embeds were not projected to low-dim space if num_stories < n_pca_dim
        if self.pca is None:
            n_dims = min(self._num_stories, self._n_pca_dims)
            self.pca = PCA(n_components=n_dims)
            self.pca.fit(self.kmeans.cluster_centers_)
            print(f'[INFO] pca dim set to {n_dims}')

        # --- serialize ---
        print(f'[INFO] serializing result to {fname}...')
        fields = ['id', 'title', 'url', 'unix_time', 'label', 'embedding']
        with open(fname, 'w') as f:
            f.write('\t'.join(fields) + '\n')

        for st_batch, emb_batch, lbl_batch in zip(story_batches[1], emb_batches[1], self._labels):
            # reduce dimensionality with pca if it hasn't already been done
            # otehrwise take n_dims first eigenvecs
            emb_proj = self.pca.transform(emb_batch) if emb_batch.shape[1] > self._n_pca_dims else emb_batch
            for st, emb, lbl in zip(st_batch, emb_proj, lbl_batch):
                with open(fname, 'a') as f:
                    f.write(
                        '\t'.join([
                            str(st.get('story_id')),
                            st.get('title') or '',
                            st.get('url') or '', # nullable
                            str(st.get('unix_time')),
                            str(lbl),
                            ','.join(str(val) for val in emb)
                        ]) + '\n'
                    )

        return True

    def serialize_pca_explained_variance(self, fname: int = 'data/pca.txt') -> bool:
        if self.pca is None:
            return False
        
        with open(fname, 'w') as f:
            f.write('\n'.join(
                str(val) for val in self.pca.explained_variance_ratio_
            ))

        return True