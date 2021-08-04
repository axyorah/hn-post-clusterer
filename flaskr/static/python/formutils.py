from flaskr.db import get_db
import requests as rq
import datetime
import json

#TODO: key2html should be a dict    

def parse_request(request, key2html):
    req = request.form
    form = dict()
    for form_name, html_name in key2html:
        try:
            form[form_name] = int(req.get(html_name))
        except:
            raise NameError(f'Error accessing element with id "{html_name}"')
        
    return form

def parse_show_request(request):
    key2html = [
        ('begin_id', 'show-id-begin-range'),
        ('end_id', 'show-id-end-range'),
        ('begin_comm', 'show-comm-begin-range'),
        ('end_comm', 'show-comm-end-range'),
        ('begin_score', 'show-score-begin-range'),
        ('end_score', 'show-score-end-range'),
    ]

    return parse_request(request, key2html)

def parse_seed_request(request):
    key2html = [
        ('begin_id', 'seed-id-begin-range'),
        ('end_id', 'seed-id-end-range'),
    ]

    return parse_request(request, key2html)

def parse_simple_cluster_request(request):
    key2html = [
        ('num_topics', 'show-lsi-topics-num'),
        ('n_clusters', 'show-kmeans-clusters-num')
    ]

    return parse_request(request, key2html)

def get_id_list_from_sqlite_rows(rows) -> 'List[str]':
    """
    Extract post 'id's from HN posts
    """
    return [str(row.__getitem__("story_id")) for row in rows]

def get_document_list_from_sqlite_rows(rows) -> 'List[str]':
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

def get_document_dict_from_sqlite_rows(rows) -> 'dict':
    """
    Extract 'texts' from HN posts - SQLite Row objects corresponding to HN stories
    with an extra field 'children' corresponding to all comments 
    concatenated into a single string;
    These concatenated comments constitute corpus documents - 
    single document contains all comments parented by the same HN story
    """
    documents = dict()
    for row in rows:
        documents[row.__getitem__('story_id')] = {
            'story_id': row.__getitem__('story_id'),
            'author': row.__getitem__('author'),
            'unix_time': row.__getitem__('unix_time'),
            'score': row.__getitem__('score'),
            'title': row.__getitem__('title'),
            'url': row.__getitem__('url'),
            'descendants': row.__getitem__('descendants'),
            'children': f'{row.__getitem__("title")}\t{row.__getitem__("children")}'
        }
        
    return documents

def update_display_record(display, form):
    begin_date = datetime.datetime.fromtimestamp(form.get('begin_date') // 1000)
    end_date = datetime.datetime.fromtimestamp(form.get('end_date') // 1000)

    display.begin_date = f'{begin_date.year}/{begin_date.month}/{begin_date.day}'
    display.end_date = f'{end_date.year}/{end_date.month}/{end_date.day}'

    display.begin_id = form.get('begin_id')
    display.end_id = form.get('end_id')

