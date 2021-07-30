import numpy as np
from collections import defaultdict
import gensim
from gensim import corpora, models
from gensim.parsing.preprocessing import preprocess_documents
import sklearn
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

#TODO: implement streaming to avoid too much memory use:
# https://radimrehurek.com/gensim/auto_examples/core/run_corpora_and_vector_spaces.html#sphx-glr-auto-examples-core-run-corpora-and-vector-spaces-py

def get_documents_from_sqlite_rows(rows) -> 'List[str]':
    """
    Extract 'texts' from HN posts - SQLite Row objects corresponding to HN stories
    with an extra field 'children' corresponding to all comments 
    concatenated into a single string;
    These concatenated comments constitute corpus documents - 
    single document contains all comments parented by the same HN story
    """
    documents = []
    for row in rows:
        documents.append(
            f'{row.__getitem__("title")}\t{row.__getitem__("children")}'
        )
    return documents

def remove_rare_words_from_documents(documents: 'List[int]', min_freq=2) -> 'List[int]':
    count = defaultdict(int)

    for document in documents:
        for word in document:
            count[word] += 1

    return [
        [word for word in document if count[word] >= min_freq] 
        for document in documents
    ]

def preprocess_raw_documents(documents: 'List[str]'):
    """
    remove stopwords, punctuation, replace word variations by the root
    """
    preprocessed_documents = preprocess_documents(documents)
    filtered_documents = remove_rare_words_from_documents(preprocessed_documents)
    return filtered_documents

def get_lsi_corpus(documents, num_topics):
    """documents = preprocessed and filtered documents"""
    dictionary = corpora.Dictionary(documents)
    corpus = [dictionary.doc2bow(documents) for documents in documents]

    tfidf_model = models.TfidfModel(corpus)
    tfidf_corpus = tfidf_model[corpus]

    lsi_model = models.LsiModel(tfidf_corpus, id2word=dictionary, num_topics=num_topics)
    lsi_corpus = lsi_model[tfidf_corpus]

    return lsi_corpus

def cluster_documents(documents, num_topics, n_clusters):
    # preprocessing
    preprocessed_documents = preprocess_raw_documents(documents)
    
    # embedding
    lsi_corpus = get_lsi_corpus(preprocessed_documents, num_topics)
    data = np.array([[t[1] for t in doc] for doc in lsi_corpus])

    # clustering
    kmeans = KMeans(n_clusters=n_clusters)
    kmeans.fit(data)

    return kmeans.labels_
