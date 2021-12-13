from types import FunctionType, prepare_class
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

from flaskr.utils.cluster_utils import (
    copy_and_measure_generator,
    copy_and_measure_batch_generator,
    BatchedGeneratorStandardizer
)

from flaskr.utils.db_utils import DBHelper as dbh
from flaskr.models.story import Story

class Pipeliner:
    def __init__(self):
        self.pipe = []

    def add(self, fun: FunctionType, params: Optional[Dict]=None):
        self.pipe.append((fun, params or {}))

    def run(self, inpt):
        x = inpt
        for fun, params in self.pipe:
            x = fun(x, **params)
        return x


class Batcher:
    @classmethod
    def rebatch_generator(cls, batches: Generator, min_batch_size: int):
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

class ClustererBuilder:
    def __init__(self, clusterer: 'Clusterer'):
        self.clusterer = clusterer

    def n_clusters(self, val: int) -> 'ClustererBuilder':
        self.clusterer._n_clusters = val
        return self

    def n_pca_dims(self, val: int) -> 'ClustererBuilder':
        self.clusterer._n_pca_dims = val
        return self

    def min_batch_size(self, val: int) -> 'ClustererBuilder':
        self.clusterer._min_batch_size = val
        return self

    def begin_timestep(self, val: int) -> 'ClustererBuilder':
        self.clusterer._begin_ts = val
        return self

    def end_timestep(self, val: int) -> 'ClustererBuilder':
        self.clusterer._end_ts = val
        return self

    def begin_comments(self, val: int) -> 'ClustererBuilder':
        self.clusterer._begin_comm = val
        return self

    def end_comments(self, val: int) -> 'ClustererBuilder':
        self.clusterer._end_comm = val
        return self

    def begin_score(self, val: int) -> 'ClustererBuilder':
        self.clusterer._begin_score = val
        return self

    def end_score(self, val: int) -> 'ClustererBuilder':
        self.clusterer._end_score = val
        return self

    def build(self):
        return self.clusterer


class Clusterer:
    def __init__(self):
        self._model_name = 'sentence-transformers/all-distilroberta-v1'
        self._n_clusters = 10
        self._n_pca_dims = 100
        self._min_batch_size = 100
        self._begin_ts = None
        self._end_ts = None
        self._begin_comm = 3
        self._end_comm = 500
        self._begin_score = 0
        self._end_score = 500

        self._num_batches = 0
        self._num_stories = 0

        self._stories = None
        self._embeddings = None
        self._labels = None

        self.pipeliner = Pipeliner()
        self.embedder = StoryEmbedder(model_name=self._model_name)
        self.scaler = BatchedGeneratorStandardizer()
        self.kmeans = MiniBatchKMeans(n_clusters=self._n_clusters)
        self.pca = None
        self.centroids = None

    @property
    def set(self):
        return ClustererBuilder(self)

    def _story_batch_generator(self, delta_ts: int = 100000) -> Generator:
        get_query = f'''
            {Story.RECURSIVE_CTE_WITHOUT_WHERE}
            WHERE 
                s.unix_time BETWEEN ? AND ? AND
                s.num_comments BETWEEN ? AND ? AND
                s.score BETWEEN ? AND ?
            ;
        '''

        num = 0
        for b_ts in range(
            self._begin_ts, 
            self._end_ts, 
            delta_ts
        ):
            p = (
                b_ts, min(b_ts + delta_ts, self._end_ts),
                self._begin_comm, self._end_comm,
                self._begin_score, self._end_score
            )

            story_dicts = dbh.get_query(get_query, p)

            if len(story_dicts):
                num += len(story_dicts)
                yield story_dicts
        print(f'[INFO] got {num} stories!')

    def _read_or_generate_story_embeddings(self, story_list: List[Dict]):
        """
        returns the list of embeddings; each embedding corresponds
        to a story in `story_list` and is calculated
        by averaging all embeddings corresponding to story comments;
        read the embedding from db if already present 
        and writes it to db when calculated
        INPUTS:
           stories: list: each element is a story dict with keys:
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
        for story in story_list:
            # fetch embedding if roberta is selected and the embedding is already in db
            if self._model_name == 'sentence-transformers/all-distilroberta-v1' and\
                story.get('comment_embedding'):
                embedding = np.array([
                    float(val) for val in story['comment_embedding'].split(',')
                ])
            else:
                embedding = self.embedder.embed_and_average_sentences(
                    html2sentences(story['children'])
                )
                # write embedding to db (update story row) only if roberta was used
                if self._model_name == 'sentence-transformers/all-distilroberta-v1':
                    story['comment_embedding'] = ','.join(str(val) for val in embedding)

                    dbh.mod_query(
                        update_query, 
                        (story['comment_embedding'], story['story_id']), 
                        commit=True
                    )

            batch.append(embedding)

        return batch

    def _get_story_batches(self, delta_ts: int = 100000) -> Generator:
        """
        queries db based on form request,
        recursively collects all comments for each story,
        returns a generator, where each element 
        is a list ("batch") of story dicts with the following fields:
            'story_id', 'author', 'unix_time', 'score', 
            'title', 'url', 'num_comments', 'children'
        """
        print('[INFO] fetching data from db...')

        # get stories
        gen = self._story_batch_generator(delta_ts=delta_ts)

        # rebatch stories
        gen = Batcher.rebatch_generator(gen, self._min_batch_size)

        # copy genrator: save one copy, return another
        print('[INFO] copying story generator...')
        batches, (num_batches, num_items, _) = copy_and_measure_batch_generator(gen, num_copies=2)
        self._num_batches = num_batches
        self._num_stories = num_items
        self._stories = batches[0]

        return batches[1]

    def _get_embedding_batches(self, story_batches: Optional[Generator] = None) -> Generator:
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
                yield np.stack(self._read_or_generate_story_embeddings(batch))
            print(f'[INFO] got {num} embeddings!')
        
        # copy genrator: save one copy, return another
        gen = batch_generator(story_batches or self._stories)
        print('[INFO] copying embedding generator...')
        batches = tee(gen, 2)
        self._embeddings = batches[0]

        return batches[1]


    def _standardize_embedding_batches(self, embedding_batches: Optional[Generator] = None) -> Generator:
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

    def _reduce_embedding_dimensionality_by_batches(self, embedding_batches: Optional[Generator] = None) -> Generator:
        if embedding_batches is None and self._embeddings is None:
            raise RuntimeError(
                'There is nothing to reduce yet! ' +\
                'You must obtain and story embeddings first! ' +\
                'Consider running `get_embedding_batches()` or `set_embedding_batches()`'
            )

        if self._num_stories < self._n_pca_dims:
            warnings.warn(
                'Can not reduce the dimensionality of the embeddings!\n' +\
                'Dimensionality should be less or equal to the number of samples, ' +\
                f'got n_samples={self._num_stories} and n_dims={self._n_pca_dims}!\n' +\
                'Returning original embeddings without changes.'
            )
            return embedding_batches or self._embeddings

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

    def _cluster_embedding_batches(self, embedding_batches: Optional[Generator] = None) -> None:
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

    def run(self):
        # we need to create dummy fun,
        # because pipeliner requires an input for the pipe,
        # but `_get_story_batches` doesn't require any inputs (aside from one kwarg)
        dummy = lambda x, **params: self._get_story_batches(**params)

        self.pipeliner.add(dummy, {'delta_ts': 100000})
        self.pipeliner.add(self._get_embedding_batches)
        self.pipeliner.add(self._standardize_embedding_batches)
        self.pipeliner.add(self._reduce_embedding_dimensionality_by_batches)
        self.pipeliner.add(self._cluster_embedding_batches)

        self.pipeliner.run('dummy_input')

        return self

    
class Serializer:
    # TODO: make it an Observer
    def __init__(self, clusterer: 'Clusterer'):
        self.clusterer = clusterer

    def serialize_clustering_result(self, fname: str = './data/df.csv') -> bool:
        # check if all the necessary data is available
        if self.clusterer.kmeans is None or self.clusterer._embeddings is None:
            raise RuntimeError(
                'There is nothing to serialize yet. ' +\
                'You must obtain and cluster embeddings first!'
            )

        print('[INFO] copying stories...')
        story_batches, (l,_) = copy_and_measure_generator(self.clusterer._stories, num_copies=2)
        self.clusterer._stories = story_batches[0]
        if not l:
            raise RuntimeError(
                'Story generator is empty! ' +\
                'Consider rerunning .get_story_batches()'
            )
        
        print('[INFO] copying embeddings...')
        emb_batches, (l,_) = copy_and_measure_generator(self.clusterer._embeddings, num_copies=2)
        self.clusterer._embeddings = emb_batches[0]
        if not l:
            raise RuntimeError(
                'Embedding generator is empty! ' +\
                'Consider rerunning .get_embedding_batches()'
            )

        if not self.clusterer._labels:
            raise RuntimeError(
                'There are no labels to serialize! ' +\
                'Consider running .cluster_story_batches()'
            )     

        # --- project to low-dim space if it wasn't done already ---
        # embeds were not projected to low-dim space if num_stories < n_pca_dim
        if self.clusterer.pca is None:
            n_dims = min(
                self.clusterer._num_stories, 
                self.clusterer._n_pca_dims
            )
            self.clusterer.pca = PCA(n_components=n_dims)
            self.clusterer.pca.fit(self.kmeans.cluster_centers_)
            print(f'[INFO] pca dim set to {n_dims}')

        # --- serialize ---
        print(f'[INFO] serializing result to {fname}...')
        fields = ['id', 'title', 'url', 'unix_time', 'label', 'embedding']
        with open(fname, 'w') as f:
            f.write('\t'.join(fields) + '\n')

        for st_batch, emb_batch, lbl_batch in zip(
            story_batches[1], emb_batches[1], self.clusterer._labels
        ):
            # reduce dimensionality with pca if it hasn't already been done
            # otehrwise take n_dims first eigenvecs
            emb_proj = self.clusterer.pca.transform(emb_batch) \
                if emb_batch.shape[1] > self.clusterer._n_pca_dims \
                else emb_batch
            
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
        if self.clusterer.pca is None:
            return False
        
        with open(fname, 'w') as f:
            f.write('\n'.join(
                str(val) for val in self.clusterer.pca.explained_variance_ratio_
            ))

        return True