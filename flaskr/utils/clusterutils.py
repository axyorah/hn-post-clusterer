import os
import numpy as np
from collections import defaultdict

import gensim
from gensim import corpora, models
from gensim.parsing.preprocessing import preprocess_documents

# import sklearn
# from sklearn.cluster import KMeans
# from sklearn.metrics import silhouette_score

import errno
from smart_open import open  # for transparently opening remote files
from itertools import cycle, tee


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

class RareWordFinder:
    def __init__(self, minfreq):
        self.minfreq = max(minfreq, 2)
        self.counter = defaultdict(int)
        self.rare = set()

    def count_tokens(self, tokens):
        """
        count frequencies of each token and store it in `self.counter` dict
        """
        for token in tokens:
            self.counter[token] += 1
            if self.counter[token] < self.minfreq:
                self.rare.add(token)
            elif token in self.rare:
                self.rare.remove(token)

    def get_rare_words(self):
        """
        returns the set of tokens whose frequency is lower than `self.minfreq`
        """
        return self.rare

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

def get_rare_words_in_serialized_corpus(fname, min_freq=2):
    rwf = RareWordFinder(min_freq)
    reader = SerialReader(fname)

    for document in reader:
        rwf.count_tokens(document)

    return rwf.get_rare_words()

def serialized2filtered(fname):
    """
    reads serialized documents from specified file 
    and filters the rare words;
    file should contain already tokenized documents: 
    documents should be separated by a new line, 
    tokens corresponding to a single document should be separated by space;
    returns the generator that yields one filtered document at a time
    (list of all tokens corresponding to the original document,
    except for stopwords ['a', 'the', 'in'...] and rare words)
    """
    # read the serialized corpus once to find the rare words 
    # that should be filtered during the actual analysis
    min_freq = 2
    rare_words = get_rare_words_in_serialized_corpus(fname, min_freq=min_freq)

    # get filtered tokenized documents 
    return SerialReader(fname, blacklist=rare_words) # generator!

def filtered2bow(documents):
    (documents1, documents2), (_,_) = copy_and_measure_generator(documents, 2)
    dictionary = corpora.Dictionary(documents1)
    return (dictionary.doc2bow(document) for document in documents2) # generator!

def bow2tfidx(bow_corpus):
    (bow_corpus1, bow_corpus2), (_,_) = copy_and_measure_generator(bow_corpus, 2)
    tfidf_model = models.TfidfModel(bow_corpus1)
    return tfidf_model[bow_corpus2]

def tfidf2lsi(tfidf_corpus, dictionary, num_topics):
    (tfidf_corpus1, tfidf_corpus2),(_,_) = copy_and_measure_generator(tfidf_corpus, 2)
    lsi_model = models.LsiModel(
        tfidf_corpus1, 
        id2word=dictionary, 
        num_topics=num_topics
    )
    return lsi_model[tfidf_corpus2]
        
def vectorize_lsi_corpus(lsi_corpus):
    return (        
        np.array([tpl[1] for tpl in document]) for document in lsi_corpus
    )

def serialized2kmeanslabels(fname, num_topics, n_clusters):
    if not os.path.exists(fname):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),fname)
    
    filtered = serialized2filtered(fname)
    (filtered1, filtered2), (_,_) = copy_and_measure_generator(filtered, 2)
    
    bow_corpus = filtered2bow(filtered1)
    tfidf_corpus = bow2tfidx(bow_corpus)

    dictionary = corpora.Dictionary(filtered2)
    lsi_corpus = tfidf2lsi(tfidf_corpus, dictionary, num_topics)
    lsi_vectorized = vectorize_lsi_corpus(lsi_corpus)
    (lsi_vectorized1, lsi_vectorized2), (_,_) = copy_and_measure_generator(lsi_vectorized, 2)

    normalizer = GeneratorNormalizer()
    normalized_corpus = normalizer.fit_transform(lsi_vectorized1)
    (samples1, samples2), (_,_) = copy_and_measure_generator(normalized_corpus, 2)

    kmeans = KMeansForGenerator(n_clusters=n_clusters)
    kmeans.fit(samples1)
    labels = kmeans.predict(samples2)

    return {
        'labels': labels,
        'lsi': lsi_vectorized2
    }