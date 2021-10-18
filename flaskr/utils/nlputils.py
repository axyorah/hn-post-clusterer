from typing import Any, Dict, List, Set, Optional, Generator

import os
import json
import numpy as np
import lxml
import bs4 as bs
import re
from collections import defaultdict
from sentence_transformers import SentenceTransformer

from smart_open import open

import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, LancasterStemmer

from flaskr.utils.dbutils import DBHelper

nltk.download('stopwords')
stop_words = stopwords.words('english')
stop_words = set(stop_words)

def html2text(html: str) -> str:
    soup = bs.BeautifulSoup(html, 'lxml')
    return soup.get_text(separator=' ')

def html2paragraphs(html: str) -> str:
    soup = bs.BeautifulSoup(html, 'lxml')    
    return [
        sp.get_text(separator=' ') 
        for sp in soup.find_all('p')
    ]

def html2sentences(html: str) -> List[str]:
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

class RareWordFinder:
    def __init__(self, minfreq: int):
        self.minfreq = max(minfreq, 2)
        self.counter = defaultdict(int)
        self.rare = set()

    def count_tokens(self, tokens: List[str]) -> None:
        """
        count frequencies of each token and store it in `self.counter` dict
        """
        for token in tokens:
            self.counter[token] += 1
            if self.counter[token] < self.minfreq:
                self.rare.add(token)
            elif token in self.rare:
                self.rare.remove(token)

    def get_rare_words(self) -> Set:
        """
        returns the set of tokens whose frequency is lower than `self.minfreq`
        """
        return self.rare

class StoryEmbedder:
    def __init__(self, model_name: str = 'sentence-transformers/all-distilroberta-v1'):
        self.model = SentenceTransformer(model_name)

    def embed_sentences(self, sentences: List[str]) -> List[np.ndarray]:
        return self.model.encode(sentences)

    def embed_and_average_sentences(self, sentences: List[str]) -> np.ndarray:
        return self.model.encode(sentences).mean(axis=0)



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
            'one', 'two', 'three', 'http', 'https', 'www', 'com',
            'work', 'use', 
        ])
        self.blacklist = self.stop_words.union(self.trivial_words)
        
    def remove_punctuation(self, txt: str) -> str:
        txt =  self.punct_pattern.sub(' ', txt)
        return self.space_pattern.sub(' ', txt)
    
    def get_stems(self, txt: str) -> List[str]:
        if isinstance(txt, str):            
            txt = txt.split(' ')
            
        return [
            self.porter.stem(word) for word in txt 
            if word not in self.blacklist
        ]
    
    def tokenize(self, txt: str) -> List[str]:
        txt = self.remove_punctuation(txt.lower())
        return self.get_stems(txt)

class ClusterFrequencyCounter:
    def __init__(self):
        self.dbhelper = DBHelper()
        self.tokenizer = Tokenizer()
        self.frequencies = dict()

    def update_cluster_frequencies(self, label: int, tokens: List[str]) -> None:
        for token in tokens:
            if not token:
                continue
            if label not in self.frequencies.keys():
                self.frequencies[label] = defaultdict(int)
            self.frequencies[label][token] += 1

    def count_serialized_cluster_frequencies(self, fname: str) -> Dict:
        for i,line in enumerate(open(fname)):
            if not i:
                field2idx = {field:idx for idx,field in enumerate(line.split('\t'))}
                continue

            vals = line.split('\t')
            story_id = vals[field2idx['id']]
            label = vals[field2idx['label']]

            story = self.dbhelper.get_story_with_children_by_id(story_id)
            comments = html2text(story['children'])
            tokens = self.tokenizer.tokenize(comments)

            self.update_cluster_frequencies(label, tokens)

        return self.frequencies

    def serialize_cluster_frequencies(self, data_dir: str = '.', min_freq: int = 2) -> bool:
        for label in self.frequencies.keys():
            fname = os.path.join(data_dir, f'freq_{label}.json')
            with open(fname, 'w') as f:
                json.dump({
                    key:val for key,val in self.frequencies[label].items()
                    if val >= min_freq
                }, f)

        return True