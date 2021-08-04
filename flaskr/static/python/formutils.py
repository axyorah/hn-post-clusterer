from flaskr.db import get_db
import requests as rq
import datetime
import json

class RequestParser:
    def __init__(self):
        # map raw form field name (html ele id) to corresponding short name (key)
        self.html2key = {
            'seed-id-begin-range': 'begin_id',
            'seed-id-end-range': 'end_id',
            'show-id-begin-range': 'begin_id',
            'show-id-end-range': 'end_id',
            'show-comm-begin-range': 'begin_comm',
            'show-comm-end-range': 'end_comm',
            'show-score-begin-range': 'begin_score',
            'show-score-end-range': 'end_score',
            'show-lsi-topics-num': 'num_topics',
            'show-kmeans-clusters-num': 'n_clusters',
            'story_ids': 'story_ids'
        }
        # specify the list of html eles for each sender type
        self.sender2html = {
            'seed': ['seed-id-begin-range', 'seed-id-end-range'],
            'show': [
                'show-id-begin-range', 'show-id-end-range', 
                'show-comm-begin-range', 'show-comm-end-range', 
                'show-score-begin-range', 'show-score-end-range'
            ],
            'kmeans': ['show-lsi-topics-num', 'show-kmeans-clusters-num'],
        }
        # specify how each key should be parsed
        self.key2type = {
            **{key: 'int' for key in [
                'begin_id', 'end_id', 
                'begin_comm', 'end_comm', 
                'begin_score', 'end_score', 
                'num_topics', 'n_clusters'
            ]},
            'story_ids': 'list[str]'
        }

    def _parse_field(self, key, field):
        keytype = self.key2type[key]
        if keytype == 'int':
            return int(field)
        elif keytype == 'list[str]':
            return [item for item in field.split(',')]
        return field

    def _parse_request(self, request, htmls):
        form = request.form
        parsed = dict()
        for html in htmls:
            key = self.html2key.get(html)
            if form.get(html) is None and form.get(key) is None:
                raise NameError(f'Error accessing element with id "{html}" ({key})')

            parsed[key] = self._parse_field(key, form.get(html) or form.get(key))
                
        return parsed

    def parse(self, request):
        """
        parse form request
        request should have a field `sender` (`seed`, `show`, `kmeans`, ...)
        which will be used to correctly parse the request
        """
        sender = request.form.get('sender')

        if sender is None:
            raise(KeyError(f'Field "sender" is not speciefied! Got {request.form}'))

        if self.sender2html.get(sender) is None:
            raise(KeyError(
                f'"Sender" not recognized! '+\
                f'Should be one of {list(self.sender2html.keys())}.\n'+\
                f'Got {sender}\n'+\
                f'Received form: {request.form}\n'
            ))
            
        return self._parse_request(request, self.sender2html[sender])

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

