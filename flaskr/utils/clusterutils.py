import os
import errno
import numpy as np
from collections import defaultdict

from numpy.lib.function_base import copy
import gensim
from gensim import corpora, models
from gensim.parsing.preprocessing import preprocess_documents
import sklearn
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from smart_open import open  # for transparently opening remote files
from itertools import cycle, tee

#TODO: implement streaming to avoid too much memory use:
# https://radimrehurek.com/gensim/auto_examples/core/run_corpora_and_vector_spaces.html#sphx-glr-auto-examples-core-run-corpora-and-vector-spaces-py

def copy_and_measure_generator(generator, num_copies=1):
    # assumes that generator contains same-sized elements
    # returns: ((copies of orig generator), (#samples, len(sample)))
    # consumes original generator in the process
    gs = tee(generator, max(1,num_copies)+1)
    rows = 0
    for sample in gs[0]:
        rows += 1
    return gs[1:], (rows, len(sample))

class RareWordFinder:
    def __init__(self, minfreq):
        self.minfreq = max(minfreq, 2)
        self.counter = defaultdict(int)
        self.rare = set()

    def count_tokens(self, tokens):
        for token in tokens:
            self.counter[token] += 1
            if self.counter[token] < self.minfreq:
                self.rare.add(token)
            elif token in self.rare:
                self.rare.remove(token)

    def get_rare_words(self):
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

def kmeans_for_generator(samples, n_clusters=10, iters=300):
    """
    samples should be normalized!
    """
    (s1, s2), (num_samples, sample_sz) = copy_and_measure_generator(samples, 2)
    cycled_samples = cycle(s1)
    clusters = np.random.rand(n_clusters, sample_sz)
    
    for _ in range(iters):
        cluster_sum = np.zeros((n_clusters, sample_sz))
        cluster_cnt = np.zeros((n_clusters, 1))
        for _ in range(num_samples):
            # assign cluster to sample
            sample = next(cycled_samples) # should be 1d np.array
            dists = np.zeros((n_clusters,))
            for c in range(n_clusters):
                dists[c] = np.linalg.norm(sample - clusters[c])
            idx = np.argmin(dists)
            cluster_sum[idx, :] += sample
            cluster_cnt[idx, 0] += 1

        # update clusters
        clusters = cluster_sum / cluster_cnt

    return clusters

def assign_cluster_to_sample(sample, clusters):
    n_clusters, _ = clusters.shape
    dists = np.zeros((n_clusters,))
    for c in range(n_clusters):
        dists[c] = np.linalg.norm(sample - clusters[c])
    return np.argmin(dists)

def assign_clusters_to_samples(samples, clusters):
    return (
        assign_cluster_to_sample(sample, clusters)
        for sample in samples
    )

def vectorize_lsi_corpus(lsi_corpus):
    return (        
        np.array([tpl[1] for tpl in document]) for document in lsi_corpus
    )

def serialized2kmeanslabels(fname, num_topics, n_clusters):
    if not os.path.exists(fname):
        raise(FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),fname))
    
    filtered = serialized2filtered(fname)
    (filtered1, filtered2), (_,_) = copy_and_measure_generator(filtered, 2)
    
    bow_corpus = filtered2bow(filtered1)
    tfidf_corpus = bow2tfidx(bow_corpus)

    dictionary = corpora.Dictionary(filtered2)
    lsi_corpus = tfidf2lsi(tfidf_corpus, dictionary, num_topics)
    lsi_vectorized = vectorize_lsi_corpus(lsi_corpus)

    normalizer = GeneratorNormalizer()
    normalized_corpus = normalizer.fit_transform(lsi_vectorized)
    (samples1, samples2), (_,_) = copy_and_measure_generator(normalized_corpus, 2)

    clusters = kmeans_for_generator(samples1, n_clusters=n_clusters)
    labels = assign_clusters_to_samples(samples2, clusters)

    return labels