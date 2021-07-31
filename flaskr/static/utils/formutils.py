from flaskr.db import get_db
import requests as rq
import datetime
import json

def parse_form(request, form_type='show'):
    # form_type is either `seed` or `show`, depending on the type of form
    req = request.form
    form = dict()

    names = [
        #('begin_date', f'{form_type}-date-begin-range'),
        #('end_date', f'{form_type}-date-end-range'),
        ('begin_id', f'{form_type}-id-begin-range'),
        ('end_id', f'{form_type}-id-end-range'),
    ]

    show_names = [
        ('begin_comm', 'show-comm-begin-range'),
        ('end_comm', 'show-comm-end-range'),
        ('begin_score', 'show-score-begin-range'),
        ('end_score', 'show-score-end-range'),
        ('num_topics', 'show-lsi-topics-num'),
        ('n_clusters', 'show-kmeans-clusters-num')
    ]

    if form_type == 'show':
        names.extend(show_names)

    for form_name, html_name in names:
        try:
            form[form_name] = int(req.get(html_name))
        except:
            print(req)
            raise NameError(f'Error accessing element with id "{html_name}"')
        
    return form

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
            'author': row.__getitem__('author'),
            'unix_time': row.__getitem__('unix_time'),
            'score': row.__getitem__('score'),
            'title': row.__getitem__('title'),
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

