import json
import numpy as np
import lxml
import bs4 as bs
import sys
import re
from collections import defaultdict

#from sklearn.decomposition import PCA
from sentence_transformers import SentenceTransformer
#import faiss

import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, LancasterStemmer

nltk.download('stopwords')
stop_words = stopwords.words('english')
stop_words = set(stop_words)

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

class StoryEmbedder:
    def __init__(self, model_name='sentence-transformers/all-distilroberta-v1'):
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

class Tokenizer:
    def __init__(self):
        self.porter = PorterStemmer()
        self.punct_pattern = re.compile('[\W_]+', re.UNICODE)
        self.space_pattern = re.compile(' +', re.UNICODE)
        self.frequencies = defaultdict(int)
        self.stop_words = set(stopwords.words('english'))
        self.trivial_words = set([
            'use', 'go', 'thing', 'would','year', 'day', 'look', 'way',
            'with', 'without', 'take', 'need', 'stuff', 'also', 'much',
            'yup', 'nope', 'get', 'even', 'ye', 'want', 'happen',
            'week', 'could', 'see', 'oh', 'man', 'lol', 'tell', 'lot', 
            'few', 'time', 'went', 'yet', 'make', 'like', 'people',
            'one', 'two', 'three', 'work', 'use'
        ])
        self.blacklist = self.stop_words.union(self.trivial_words)
        
    def remove_punctuation(self, txt):
        txt =  self.punct_pattern.sub(' ', txt)
        return self.space_pattern.sub(' ', txt)
    
    def get_stems(self, txt):
        if isinstance(txt, str):            
            txt = txt.split(' ')
            
        return [
            self.porter.stem(word) for word in txt 
            if word not in self.blacklist
        ]
    
    def tokenize(self, txt: str):
        txt = self.remove_punctuation(txt.lower())
        return self.get_stems(txt)

# def get_story_embeddings(data: list, model_name='sentence-transformers/all-distilroberta-v1'):
#     """
#     INPUTS:
#        data: list: each element is a story dict with keys:
#            story_id, author, unix_time, score, title, url, num_comments, children
#            e.g.:
#            [
#                {story_id: ..., author: ..., unix_time: ..., title: ..., ...},
#                {storY_id, ..., author: ..., unix_time: ..., title: ..., ...},
#            ]
#         model_name: str: name of the sentence transformer from list https://www.sbert.net/docs/pretrained_models.html
#     OUTPUTS:
#         list: each element is a BERT embedding based on story comments
#         [
#             ndarray of floats with shape (768,), or (384,)
#             ...
#         ]
#     """
#     embedder = StoryEmbedder(model_name=model_name)

#     return [
#         embedder.embed_and_average_sentences(
#             html2sentences(story['children'])
#         ) for story in data
#     ]

# def cluster_stories_with_faiss(embeds, nclusters=15):
#     d = embeds.shape[1]
#     verbose = False
#     niter = 20

#     kmeans = faiss.Kmeans(d, nclusters, niter=niter, verbose=verbose)
#     kmeans.train(embeds)
#     _, lbls = kmeans.assign(embeds)

#     return lbls

# def project_embeddings(embeds, n=2):
#     # TODO: fit with centroids
#     # TODO: make class that would cluster and project...
#     pca = PCA(n_components=n)
#     return pca.fit_transform(embeds)