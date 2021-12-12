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