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
    def batch_generator(cls, query, params):
        pass

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


class Serializer:
    # observer
    pass


class ClustererBuilder:
    def __init__(self, clusterer):
        self.clusterer = clusterer

    def n_clusters(self, val):
        self.clusterer._n_clusters = val
        return self

    def n_pca_dims(self, val):
        self.clusterer._n_pca_dims = val
        return self

    def min_batch_size(self, val):
        self.clusterer._min_batch_size = val
        return self

    def begin_timestep(self, val):
        self.clusterer._begin_ts = val
        return self

    def end_timestep(self, val):
        self.clusterer._end_ts = val
        return self

    def begin_comments(self, val):
        self.clusterer._begin_comm = val
        return self

    def end_comments(self, val):
        self.clusterer._end_comm = val
        return self

    def begin_score(self, val):
        self.clusterer._begin_score = val
        return self

    def end_score(self, val):
        self.clusterer._end_score = val
        return self

    def build(self):
        return self.clusterer


class Clusterer:
    def __init__(self):
        self._n_clusters = 10
        self._model_name = 'sentence-transformers/all-distilroberta-v1'

        self._n_pca_dims = 100
        self._min_batch_size = 100

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

    def _get_story_batches(self):
        pass

    def _get_or_generate_story_embeddings(self):
        # single batch
        pass

    def _get_embedding_batches(self):
        pass

    def _standardize_embedding_batches(self):
        pass

    def _reduce_embedding_diimensionality(self):
        pass

    def _cluster_batches(self):
        pass

    def run(self):
        self.pipeliner.add(self._get_story_batches)
        self.pipeliner.add(self._get_embedding_batches)
        self.pipeliner.add(self._standardize_embedding_batches)
        self.pipeliner.add(self._reduce_embedding_diimensionality)
        self.pipeliner.add(self._cluster_batches)

        output = self.pipeliner.run()

    
