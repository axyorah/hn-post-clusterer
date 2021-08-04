import os
import json
import bs4 as bs
from gensim.parsing.preprocessing import preprocess_documents

from flaskr.static.python.formutils import (
    get_id_list_from_sqlite_rows,
    get_document_list_from_sqlite_rows,
)
from flaskr.static.python.dbutils import (
    get_requested_stories_with_children
)

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

def serialize_raw_documents_to_disc(fname, documents):
    _ = [
        append_raw_document_to_file(fname, document) 
        for document in documents
    ]

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
    _ = [
        append_preprocessed_document_to_file(fname, document) 
        for document in preprocessed_documents
    ]
    
    return True

def get_stories_from_db_and_serialize_ids_and_comments(corpus_dir, form_request, delta_id=10000):
    """
    query db in portions(!) to get stories with all child comments,
    tokenize comments and serialize them on disk:
    all child comments corresponding to the same story are serialized 
    as a single line of ' '-separated tokens in specified file;
    
    corpus_dir: string: name of a directory to store comment and id files
    form_request: dict[]: parsed form request
    delta_id: int: id range processed in a single db query
    """
    # create new files for storing story ids and comments
    fname_ids = os.path.join(corpus_dir, 'ids.txt')
    fname_comments = os.path.join(corpus_dir, 'corpus.txt')

    os.makedirs(corpus_dir, exist_ok=True) 
    create_file(fname_ids)
    create_file(fname_comments)

    # query db in portions - `delta_id` entries at a time
    begin_id = int(form_request["begin_id"])
    end_id = int(form_request["end_id"])              
    for b_id in range(begin_id, end_id, delta_id):
        # get current(!) begin_id and end_id range (b_id and e_id)
        e_id = min(b_id + delta_id - 1, end_id)
        form_request["begin_id"] = b_id
        form_request["end_id"] = e_id
        print(f"serializing from {b_id} to {e_id}")

        # query db for a portion of data and... 
        story_rows = get_requested_stories_with_children(form_request)        
        ids = get_id_list_from_sqlite_rows(story_rows)
        comments = get_document_list_from_sqlite_rows(story_rows)
        
        # ... store all ids and comments in specified files
        serialize_raw_documents_to_disc(fname_ids, ids)
        serialize_tokenized_documents_to_disc(fname_comments, comments)