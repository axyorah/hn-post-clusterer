import json
import numpy as np
import lxml
import bs4 as bs
import sys

from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sentence_transformers import SentenceTransformer
import faiss

class StoryEmbedder:
    def __init__(self, model_name='bert-base-nli-mean-tokens'):
        self.model = SentenceTransformer(model_name)

    def embed_sentences(self, sentences: 'List[str]'):
        return self.model.encode(sentences)

    def embed_and_average_sentences(self, sentences: 'List[str]'):
        return self.model.encode(sentences).mean(axis=0)

def html2text(html):
    soup = bs.BeautifulSoup(html, 'lxml')
    return soup.get_text(separator=' ')

def html2paragraphs(html):
    soup = bs.BeautifulSoup(html, 'lxml')    
    return [
        sp.get_text(separator=' ') 
        for sp in soup.find_all('p')
    ]

def html2sentences(html):
    # get dict to remove punctuation
    tr = {
        i: '' for i in 
        list(range(33, 46)) + 
        list(range(58,64)) + 
        list(range(91,97)) +
        list(range(123,127))
    }
    # get html-free text
    txt = html2text(html)
    # split into sentences
    return [
        sentence.strip().lower().translate(tr)
        for sentence in txt.split('.')
    ]

def get_story_embeddings(data: dict):
    """
    INPUTS:
       data: dict: maps story ids to dict characterizing story with keys: 
           story_id, author, unix_time, score, title, url, num_comments, children
           e.g.:
           {
               123: {story_id: ..., author: ..., unix_time: ..., title: ..., ...},
               456: {storY_id, ..., author: ..., unix_time: ..., title: ..., ...},
               ...
           }
    OUTPUTS:
        dict: maps each story id to BERT embedding based on story comments
        {
            123: ndarray of floats with shape (768,), 
            456: ...,
        }
    """
    id2embed = dict()
    embedder = StoryEmbedder()
    for story_id in data.keys():
        html = data[story_id]['children']
        sentences = html2sentences(html)
        embed = embedder.embed_and_average_sentences(sentences)
        id2embed[story_id] = embed

    return list(id2embed.keys()), np.stack(id2embed.values())

def cluster_stories_with_faiss(embeds, nclusters=15):
    d = embeds.shape[1]
    verbose = False
    niter = 20

    kmeans = faiss.Kmeans(d, nclusters, niter=niter, verbose=verbose)
    kmeans.train(embeds)
    _, lbls = kmeans.assign(embeds)

    return lbls

def project_embeddings(embeds, n=2):
    # TODO: fit with centroids
    # TODO: make class that would cluster and project...
    pca = PCA(n_components=n)
    return pca.fit_transform(embeds)
    

    

