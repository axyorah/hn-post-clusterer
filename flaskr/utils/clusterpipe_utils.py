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
from flaskr.utils.io_utils import Event, Observer, Observable
from flaskr.models.story import Story


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


class Pipeliner:
    def __init__(self):
        self.pipe = []

    def add(self, fun: FunctionType, params: Optional[Dict]=None):
        self.pipe.append((fun, params or {}))

    def run(self, inpt: Any) -> Any:
        x = inpt
        for fun, params in self.pipe:
            x = fun(x, **params)
        return x


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

    def build(self) -> 'Clusterer':
        return self.clusterer


class Clusterer(Observable):
    def __init__(self):
        super().__init__() # adds `change` attr of type `Event` (see io_utils)
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
    def set(self) -> ClustererBuilder:
        return ClustererBuilder(self)

    @property
    def stories(self):
        return self._stories

    @stories.setter
    def stories(self, val):
        self._stories = val
        self.change('stories', val)

    @property
    def embeddings(self):
        return self._stories

    @embeddings.setter
    def embeddings(self, val):
        self._embeddings = val
        self.change('embeddings', val)

    @property
    def lowdim_embeddings(self):
        return self._stories

    @lowdim_embeddings.setter
    def lowdim_embeddings(self, val):
        self._lowdim_embeddings = val
        self.change('lowdim_embeddings', val)

    @property
    def labels(self):
        return self._labels

    @labels.setter
    def labels(self, val):
        self._labels = val
        self.change('labels', val) 

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

    def _read_or_generate_story_embeddings(self, story_list: List[Dict]) -> List[np.ndarray]:
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
        gen = rebatch_generator(gen, self._min_batch_size)

        # copy genrator: save one copy, return another
        print('[INFO] copying story generator...')
        batches, (num_batches, num_items, _) = copy_and_measure_batch_generator(gen, num_copies=2)
        self._num_batches = num_batches
        self._num_stories = num_items
        self.stories = batches[0]

        return batches[1]

    def _get_embedding_batches(
        self, 
        story_batches: Optional[Generator] = None
    ) -> Generator:
        """
        each element of a batch is a (batch_size, embed_dim) numpy array
        (embed_dim is 768 for default bert transformers and 384 for minis)
        """
        if story_batches is None and self.stories is None:
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
        self.embeddings = batches[0]

        return batches[1]


    def _standardize_embedding_batches(
        self, 
        embedding_batches: Optional[Generator] = None
    ) -> Generator:

        if embedding_batches is None and self.embeddings is None:
            raise RuntimeError(
                'There is nothing to standardize! '+\
                'Consider running `get_embedding_batches()` first!'
            )
        
        print('[INFO] standardizing embeddings...')
        normalized = self.scaler.fit_transform(embedding_batches or self._embeddings)
        batches = tee(normalized, 2)
        self.embeddings = batches[0]

        return batches[1]

    def _reduce_embedding_dimensionality_by_batches(
        self, 
        embedding_batches: Optional[Generator] = None
    ) -> Generator:

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
            return embedding_batches or self.embeddings

        # copy high dim embeddings
        highdim_batches = tee(embedding_batches or self.embeddings, 2)

        # train pca
        print(f'[INFO] reducing embedding dimensionality to {self._n_pca_dims}...')
        self.pca = IncrementalPCA(n_components=self._n_pca_dims)
        for batch in highdim_batches[0]:
            self.pca.partial_fit(batch)
        
        # reduce
        def batch_generator(batches):
            for batch in batches:
                yield self.pca.transform(batch)

        lowdim_batches = tee(batch_generator(highdim_batches[1]), 3)
        self.embeddings = lowdim_batches[0]
        self.lowdim_embeddings = lowdim_batches[1]

        return lowdim_batches[2]

    def _cluster_embedding_batches(
        self, 
        embedding_batches: Optional[Generator] = None
    ) -> None:
        if embedding_batches is None and self.embeddings is None:
            raise RuntimeError(
                'There is nothing to cluster yet! ' +\
                'You must obtain and story embeddings first! ' +\
                'Consider running `get_embedding_batches()` or `set_embedding_batches()`'
            )

        print('[INFO] copying embeddings')
        batches = tee(embedding_batches or self.embeddings, 2)
        
        # train kmeans
        print(f'[INFO] clustering stories to {self._n_clusters} clusters...')
        for batch in batches[0]:
            self.kmeans.partial_fit(batch)

        self.centroids = self.kmeans.cluster_centers_

        # predict labels
        def cluster(batches):
            for batch in batches:
                yield self.kmeans.predict(batch)

        self.labels = cluster(batches[1])
        return self.labels

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