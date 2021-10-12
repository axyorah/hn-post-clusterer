import os
import numpy as np
from collections import defaultdict

import errno
from smart_open import open  # for transparently opening remote files
from itertools import cycle, tee

from sklearn.manifold import TSNE
import pandas as pd


def copy_and_measure_generator(generator, num_copies=1):
    """
    makes a specified number of generator copies
    and measures the number of elements in generator
    and the number of items in element;
    assumes that each generator's element is an iterable (list, array)
    and that all elements have the same number of items
    INPUTS:
        generator: generator to be copied and measured (will be consumed)
        num_copies: number of generator copies that need to be returned
    OUTPUTS:
        (list_of_generator_copies, (#elements in generator, #items in element))
    """
    gs = tee(generator, max(1,num_copies)+1)
    rows, sample = 0, []
    for sample in gs[0]:
        rows += 1
    return gs[1:], (rows, len(sample) if hasattr(sample, '__iter__') else 1)

def copy_and_measure_batch_generator(generator, num_copies=1):
    """
    makes a specified number of generator copies
    and measures the number of elements/batches in generator,
    the number of samples in all the batches,
    and the number of items in elements;
    assumes that each generator's element is an batch of iterables 
    (list of lists, list of arrays),
    each element/batch has different number of samples,
    but all samples have the same number of items
    INPUTS:
        generator: generator to be copied and measured (will be consumed)
        num_copies: number of generator copies that need to be returned
    OUTPUTS:
        (list_of_generator_copies, (#batches in generator, #samples in all batches, #items in sample))
    """
    gs = tee(generator, max(1,num_copies)+1)
    num_batches, num_items, item = 0, 0, []
    for batch in gs[0]:
        num_batches += 1
        num_items += len(batch)
    return gs[1:], (num_batches, num_items, len(item) if hasattr(item, '__iter__') else 1)

class SerialReader:
    def __init__(self, fname, blacklist=set()):
        self.fname = fname
        self.blacklist = blacklist

    def __iter__(self):
        for line in open(self.fname):
            # assume there's one document per line, tokens separated by whitespace
            yield [word for word in line.lower().split(' ') if word not in self.blacklist]

class GeneratorNormalizer:
    def __init__(self):
        self.min_sample = None
        self.max_sample = None

    def _set_minmax(self, generator, sample_sz):
        min_sample, max_sample = [np.Inf] * sample_sz, [0] * sample_sz
        for sample in generator:
            min_sample = [min(a,b) for a,b in zip(min_sample, sample)]
            max_sample = [max(a,b) for a,b in zip(max_sample, sample)]

        self.min_sample = np.array(min_sample)
        self.max_sample = np.array(max_sample)

    def _normalize_sample(self, sample):
        sample = np.array(sample).ravel()
        return (sample - self.min_sample) / (self.max_sample - self.min_sample)

    def _normalize_generator(self, generator):
        return (
            self._normalize_sample(sample) for sample in generator
        )

    def fit_transform(self, generator):
        (s1, s2), (_, sample_sz) = copy_and_measure_generator(generator, 2)
        
        # get min and max
        self._set_minmax(s1, sample_sz)
        
        # create new normalized generator
        normalized = self._normalize_generator(s2)

        return normalized 

    def transform_generator(self, generator):
        return self._normalize_generator(generator)

    def transform_sample(self, sample):
        return self._normalize_sample(sample)

class GeneratorStandardizer:
    def __init__(self):
        self.gen = None
        self.mean = None
        self.var = None
        
    def get_mean(self):
        (g1,g2) = tee(self.gen)
        
        sm = None
        for i,sample in enumerate(g1):
            if not i:
                sm = np.zeros(sample.shape)
            sm += sample
            
        self.gen = g2
        self.mean = sm / (i + 1)
        
        return self.mean
        
    def get_var(self):
        (g1,g2) = tee(self.gen)
        
        sm = None
        for i,sample in enumerate(g1):
            if not i:
                sm = np.zeros(sample.shape)
            sm += (sample - self.mean)**2
            
        self.var = np.sqrt(sm / (i + 1)) if i else 0
        self.gen = g2
        return self.var
    
    def fit(self, gen):
        self.gen = gen        
        mean = self.get_mean()
        var = self.get_var()
        
        return True
        
    def transform(self, gen):
        def helper(gen):
            for sample in gen:
                yield (sample - self.mean) / self.var
                
        return helper(gen)
    
    def fit_transform(self, gen):
        self.fit(gen)
        return self.transform(self.gen)

class BatchedGeneratorStandardizer:
    def __init__(self):
        """
        assumes that each batch in a 2d numpy array
        """
        self.gen = None
        self.mean = None
        self.var = None
        
    def get_mean(self):
        (g1,g2) = tee(self.gen)
        
        sm,num = None,0
        for i,batch in enumerate(g1):
            if not i:
                sm = np.zeros(batch[0].shape)
            sm += batch.sum(axis=0)
            num += batch.shape[0]
            
        self.gen = g2
        self.mean = sm / num
        
        return self.mean
        
    def get_var(self):
        # check if self.gen is not None
        (g1,g2) = tee(self.gen)
        
        sm, num = None, 0
        for i,batch in enumerate(g1):
            if not i:
                sm = np.zeros(batch[0].shape)
            for sample in batch:
                sm += (sample - self.mean)**2
            num += batch.shape[0]
            
        self.var = np.sqrt(sm / num) if num else np.zeros(sample.shape)
        self.gen = g2

        return self.var
    
    def fit(self, gen):
        self.gen = gen        
        self.get_mean()
        self.get_var()
        
        return True
        
    def transform(self, gen):
        def helper(gen):
            mean = self.mean.reshape(1,-1)
            var = self.var.reshape(1,-1)
            for batch in gen:
                yield (batch - mean) / var
                
        return helper(gen)
    
    def fit_transform(self, gen):
        self.fit(gen)
        return self.transform(self.gen)
        
class KMeansForGenerator:
    def __init__(self, n_clusters, iters=300, tol=1e-5):
        self.n_clusters = n_clusters
        self.iters = iters
        self.tol = tol
        self.centroids = None
        
    def fit(self, X_generator):
        """
        finds centroids, consumes input generator
        """
        (g1,), (num_samples, sample_sz) = copy_and_measure_generator(X_generator, 1)
        cycled_samples = cycle(g1)
        self.centroids = np.random.rand(self.n_clusters, sample_sz)
    
        for _ in range(self.iters):
            cluster_sum = np.zeros((self.n_clusters, sample_sz))
            cluster_cnt = np.zeros((self.n_clusters, 1))
            for _ in range(num_samples):
                # assign cluster to sample
                sample = next(cycled_samples) # should be 1d np.array
                sq_dists = np.zeros((self.n_clusters,)) # square distances for speed
                for c in range(self.n_clusters):
                    sq_dists[c] = np.dot(
                        sample - self.centroids[c], 
                        sample - self.centroids[c]
                    )
                idx = np.argmin(sq_dists)
                cluster_sum[idx, :] += sample
                cluster_cnt[idx, 0] += 1

            # update clusters
            centroids = cluster_sum / cluster_cnt
            if max([np.abs(pt1 - pt2) 
                    for c1,c2 in zip(centroids, self.centroids)
                    for pt1, pt2 in zip(c1,c2)
                   ]) < self.tol:
                self.centroids = centroids
                break
            self.centroids = centroids

        return self.centroids
    
    def transform(self, X_generator):
        """
        assigns each sample of the input generator to the closest centroid;
        returns euclidean distances from each sample to the closest centroid;
        consumes input generator
        """
        if self.centroids is None:
            raise RuntimeError(
                'KMeans centroids are not defined! Run `fit` method first.'
            )
            
        return (
            np.array([
                np.linalg.norm(sample - self.centroids[c])
                for c in range(self.n_clusters)
            ])
            for sample in X_generator            
        )
    def predict(self, X_generator):
        """
        assigns each sample of the input generator to the closest centroid;
        returns generator of class predictions for each sample;
        consumes input generator
        """
        if self.centroids is None:
            raise RuntimeError(
                'KMeans centroids are not defined! Run `fit` method first.'
            )
            
        return (
            np.argmin([
                np.dot(sample - self.centroids[c],sample - self.centroids[c])
                for c in range(self.n_clusters)
            ])
            for sample in X_generator
        )

class TSNEer:
    def __init__(self, **kwargs):
        self.tsne = TSNE(**kwargs)
        self.reduced = None

    def read_embedding_from_csv(self, fname, colname='embedding', sep='\t', dims=768):
        print('tsne dims:', dims)
        self.df = pd.read_csv(fname, sep=sep)
        return np.stack(
            self.df[colname].map(
                lambda line: [
                    float(val) for i,val in enumerate(line.split(','))
                    if i < dims
                ]
            ).to_numpy()
        )

    def reduce_embedding_dimensions(self, embeddings):
        self.reduced = self.tsne.fit_transform(embeddings)
        print(self.reduced.shape)
        return self.reduced

    def serialize_results(self, fname):
        self.df['embedding_tsne'] = [
            ','.join([str(val) for val in arr])
            for arr in self.reduced            
        ]

        self.df.to_csv(fname, sep='\t')