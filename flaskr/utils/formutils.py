from logging import raiseExceptions
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
            'story_ids': 'story_ids',
            'fname': 'fname',
            'fnames': 'fnames',
            'num-clusters': 'n_clusters',
            'model-name': 'model_name',
            'perplexity': 'perplexity',
            'dims': 'dims',
        }
        # specify the list of html eles for each sender type
        self.sender2html = {
            'db-seeder': ['seed-id-begin-range', 'seed-id-end-range'],
            'db-lister': ['story_ids'],
            'reader': ['fname'],
            'deleter': ['fnames'],
            'clusterer': [
                'show-id-begin-range', 'show-id-end-range', 
                'show-comm-begin-range', 'show-comm-end-range', 
                'show-score-begin-range', 'show-score-end-range',
                'num-clusters', 'model-name'
            ],
            'tsneer': ['perplexity', 'dims']
        }
        # specify how each key should be parsed
        self.key2type = {
            **{key: 'int' for key in [
                'begin_id', 'end_id', 
                'begin_comm', 'end_comm', 
                'begin_score', 'end_score', 
                'num_topics', 'n_clusters',
                'perplexity', 'dims'
            ]},
            'fname': 'str',
            'fnames': 'list[str]',
            'model_name': 'str',
            'story_ids': 'list[str]',
        }

    def _parse_field(self, key, field):
        keytype = self.key2type[key]
        if keytype == 'int':
            try:
                return int(field)
            except:
                print(f'{field} received non-{keytype}!')
                return

        if keytype == 'str':
            try:
                return field
            except:
                print(f'{field} received non-{keytype}!')
                return

        elif keytype == 'list[str]':
            try:
                return [item for item in field.split(',')]
            except:
                print(f'{field} received non-{keytype}!')
                return
        return field

    def _parse_request(self, request, htmls):
        form = request.form
        parsed = dict()
        for html in htmls:
            key = self.html2key.get(html)
            if form.get(html) is None and form.get(key) is None:
                raise NameError(f'Error accessing element with id "{html}" ({key})')

            parsed[key] = self._parse_field(key, form.get(html) or form.get(key)) # can be None
                
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

def update_display_record(display, form):
    begin_date = datetime.datetime.fromtimestamp(form.get('begin_date') // 1000)
    end_date = datetime.datetime.fromtimestamp(form.get('end_date') // 1000)

    display.begin_date = f'{begin_date.year}/{begin_date.month}/{begin_date.day}'
    display.end_date = f'{end_date.year}/{end_date.month}/{end_date.day}'

    display.begin_id = form.get('begin_id')
    display.end_id = form.get('end_id')

