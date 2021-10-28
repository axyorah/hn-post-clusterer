from typing import Any, Dict, List, Optional
from werkzeug.wrappers import Request, Response

class RequestParser:
    # map raw form field name (html ele id) to corresponding short name (key)
    _html2key = {
        'seed-id-begin-range': 'begin_id',
        'seed-id-end-range': 'end_id',
        'show-id-begin-range': 'begin_id',
        'show-id-end-range': 'end_id',
        'show-ts-begin-range': 'begin_ts',
        'show-ts-end-range': 'end_ts',
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
    _sender2html = {
        'db-seeder': ['seed-id-begin-range', 'seed-id-end-range'],
        'db-lister': ['story_ids'],
        'reader': ['fname'],
        'deleter': ['fname'],
        'clusterer': [
            'show-ts-begin-range', 'show-ts-end-range', 
            'show-comm-begin-range', 'show-comm-end-range', 
            'show-score-begin-range', 'show-score-end-range',
            'num-clusters', 'model-name'
        ],
        'tsneer': ['perplexity', 'dims']
    }
    # specify how each key should be parsed
    _key2type = {
        **{key: 'int' for key in [
            'begin_id', 'end_id', 
            'begin_ts', 'end_ts', 
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
    # provide description of each key (should be useful when printing errors)
    _key2description = {
        'begin_id': 'minimal post id',
        'end_id': 'maximal post id',
        'begin_ts': 'minimal post timestamp',
        'end_ts': 'maximal post timestamp',
        'begin_comm': 'minimal number of comments',
        'end_comm': 'maximal number of comments',
        'begin_score': 'minimal score',
        'end_score': 'maximal score',
        'n_clusters': 'number of clusters',
        'perplexity': 'perplexity',
        'dims': 'number of PCA input vectors',
        'fname': 'file name',
        'fnames': 'file names',
        'model_name': 'name of the transformer',
        'story_ids': 'list of post ids'
    }
    _key2bounds = {
        'begin_id': [1, 99999999],
        'end_id': [2, 100000000],
        'begin_ts': [1160418111, 2000000000],
        'end_ts': [1160418112, 1999999999],
        'begin_comm': [5, 299],
        'end_comm': [6, 300],
        'begin_score': [0, 299],
        'end_score': [1, 300],
        'n_clusters': [2, 50],
        'perplexity': [5, 50],
        'dims': [5, 50]
    }

    @classmethod
    def _parse_field(cls, key: str, field: str) -> Any:
        keytype = cls._key2type[key]
        if keytype == 'int':            
            try:
                return int(field)
            except TypeError as err:
                raise TypeError(f'{cls._key2description.get(key) or key} should be an integer, received {field}!\n')

        if keytype == 'str':
            try:
                return field
            except TypeError as err:
                raise TypeError(f'{cls._key2description.get(key) or key} should be a string, received {field}!\n')

        elif keytype == 'list[str]':
            try:
                return [item for item in field.split(',')]
            except TypeError as err:
                raise TypeError(f'{cls._key2description.get(key) or key} should be a list of strings, received {field}!\n')
        else:
            raise TypeError(f'[ERR] {cls._key2description.get(key) or key} is of unrecognized type!\n')
        
    @classmethod
    def _parse_request(cls, request: Request, htmls: List[str]) -> Dict:
        form = request.form or request.get_json()
        parsed = dict()
        for html in htmls:
            key = cls._html2key.get(html)
            if form.get(html) is None and form.get(key) is None:
                raise NameError(f'Error accessing element with id "{html}" ({key})\n')
            
            parsed[key] = cls._parse_field(key, form.get(html) or form.get(key)) 
                            
        return parsed

    @classmethod
    def _fit_parsed_request_within_bounds(cls, parsed: Dict) -> None:
        """
        modifies input dict: fits all int-type entries within their specified bounds
        """
        for key in parsed.keys():
            if cls._key2type.get(key) != 'int':
                continue
            if cls._key2bounds.get(key) is not None and parsed[key] < cls._key2bounds[key][0]:
                parsed[key] = cls._key2bounds[key][0]
            if cls._key2bounds.get(key) is not None and parsed[key] > cls._key2bounds[key][1]:
                parsed[key] = cls._key2bounds[key][1]
            
    @classmethod
    def _check_if_ranges_are_valid(cls, parsed: Dict) -> None:
        """
        for all `begin_X` - `end_X` paires check if `begin_X` is lower or equal than `end_X`;        
        otherwise raises value error
        """
        for key in parsed.keys():
            if 'begin' in key:
                name = key.split('_')[1]
                paired_key = f'end_{name}'
                if parsed[key] >= parsed[paired_key]:
                    raise ValueError(
                        f'Value of `{cls._key2description[key]}` is higher or equal than ' + \
                        f'value of `{cls._key2description[paired_key]}`: ' + \
                        f'{parsed[key]} >= {parsed[paired_key]}'
                    )

    @classmethod
    def parse(cls, request: Request) -> Dict:
        """
        parse form request
        request should have a field `sender` (`db-seeder`, `clusterer`, `tsneer`, ...)
        which will be used to correctly parse the request
        """
        form = request.form or request.get_json()
        if form is None:
            raise ValueError('Request body is not form or json')

        sender = form.get('sender')
        if sender is None:
            raise(KeyError(f'Field "sender" is not specified! Got {form}\n'))

        if cls._sender2html.get(sender) is None:
            raise(KeyError(
                f'"Sender" not recognized! '+\
                f'Should be one of {list(cls._sender2html.keys())}.\n'+\
                f'Got {sender}\n'+\
                f'Received form: {request.form}\n'
            ))

        parsed = cls._parse_request(request, cls._sender2html[sender])
        cls._fit_parsed_request_within_bounds(parsed) # modifies input
        cls._check_if_ranges_are_valid(parsed) # doesn't return anything or raises error
        return parsed