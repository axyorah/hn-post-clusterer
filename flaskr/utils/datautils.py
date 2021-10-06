import os
import json
import numpy as np
import bs4 as bs
from gensim.parsing.preprocessing import preprocess_documents

def create_file(fname):
    with open(fname, 'w') as f:
        f.write('')

def parse_raw_html_document(document):
    soup = bs.BeautifulSoup(document, 'lxml')
    return soup.get_text(separator=' ')

def append_raw_document_to_file(fname, document):
    """
    fname: string: name of the file to append document to
    document: string: preprocessed document = list of tokens
    """
    append_write = 'a' if os.path.exists(fname) else 'w'
    with open(fname, append_write) as f:
        f.write(f'{document}\n')

def append_preprocessed_document_to_file(fname, document):
    """
    fname: string: name of the file to append document to
    document: List[string]: preprocessed document = list of tokens
    """
    append_write = 'a' if os.path.exists(fname) else 'w'
    with open(fname, append_write) as f:
        f.write(f'{" ".join(document)}\n')

def serialize_vectors_to_disc(fname, vectors):
    for vector in vectors:
        append_raw_document_to_file(
            fname, ' '.join(str(val) for val in vector)
        )

    return True

def serialize_raw_documents_to_disc(fname, documents):
    for document in documents:
        append_raw_document_to_file(fname, document)

    return True

def serialize_tokenized_documents_to_disc(fname, documents):
    """
    fname: string: name of the file to append document to
    documents: List[string]: documents = list of raw story comments with html markup
        each list element corresponds to all comments of a single story
    """
    # parse documents (remove html markup)
    parsed_documents = [
        parse_raw_html_document(document) for document in documents
    ]

    # preprocess documents
    preprocessed_documents = preprocess_documents(parsed_documents)

    # append documents separated by '/n' to file
    for document in preprocessed_documents:
        append_preprocessed_document_to_file(fname, document)
    
    return True

def serialize_dict_keys(dict_iterator, keys=[], key2fname=dict()):

    for dct in dict_iterator:
        for key in keys or dct.keys():
            fname = key2fname.get(key) or f'{key}.txt'
            if key == 'children':
                serialize_tokenized_documents_to_disc(fname, [dct[key]])
            else:
                serialize_raw_documents_to_disc(fname, [dct[key]])

    return True

def serialize_dict_of_dicts(dct, fname='./data/dict.csv'):

    fields = []
    for i,key in enumerate(dct.keys()):
        # add heading
        if not i:
            fields = list(dct[key].keys())
            with open(fname, 'w') as f:
                f.write('\t'.join(fields) + '\n')

        # append row
        with open(fname, 'a') as f:
            f.write('\t'.join(
                ','.join(str(val) for val in dct[key][field])
                    if field == 'embedding'
                    else str(dct[key].get(field) or '') 
                for field in fields
            ) + '\n')

    return True