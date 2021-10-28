"""
use as:
$ python3 -m pytest tests/
or 
$ pytest
(the latter requires `__init__.py` file to be present in `tests`)
"""
import os, json

def test_index_ok(client):
    rv = client.get('/')
    assert rv.status_code == 200 and b'HN POST CLUSTERER' in rv.data

def test_empty_db(client):
    """Start with a blank database."""

    rv = client.get('/db/stories/stats')
    res = rv.json
    assert rv.status_code == 200 and res.get('data') and not res.get('data').get('num')

def test_post_to_db_ok(client):
    # fetch items from hn and post them to db
    rv = client.post('/db/items', 
        headers={'Content-Type': 'application/json'},
        data=json.dumps({
            'sender': 'db-seeder',
            'seed-id-begin-range': 27700200,
            'seed-id-end-range': 27700210
    }))
    assert rv.status_code == 200

    # there should be 3 new storeis
    rv = client.get('/db/stories/stats')
    res = rv.json
    assert rv.status_code == 200 and res.get('data') and res.get('data').get('num') == 3

    # there should be 8 new comments
    rv = client.get('/db/comments/stats')
    res = rv.json
    assert rv.status_code == 200 and res.get('data') and res.get('data').get('num') == 8

def test_post_to_db_fail(client):    
    # sender not specified
    params = {
            'seed-id-begin-range': 27700200,
            'seed-id-end-range': 27700210
    }
    rv = client.post('/db/items', 
        headers={'Content-Type': 'application/json'},
        data=json.dumps(params))
    assert rv.status_code == 400

    # sender not recognised
    params = {
            'sender': 'abc',
            'seed-id-begin-range': 27700200,
            'seed-id-end-range': 27700210
    }
    rv = client.post('/db/items', 
        headers={'Content-Type': 'application/json'},
        data=json.dumps(params))
    assert rv.status_code == 400

    # one of the ids is not numeric
    params = {
            'sender': 'db-seeder',
            'seed-id-begin-range': "abc",
            'seed-id-end-range': 27700210
    }
    rv = client.post('/db/items', 
        headers={'Content-Type': 'application/json'},
        data=json.dumps(params))
    assert rv.status_code == 400

    # min id > max id
    params = {
            'sender': 'db-seeder',
            'seed-id-begin-range': 27700210,
            'seed-id-end-range': 27700200
    }
    rv = client.post('/db/items', 
        headers={'Content-Type': 'application/json'},
        data=json.dumps(params))
    assert rv.status_code == 400

def test_get_stories_ok(client):
    rv = client.get('/db/stories?ids=27700200,27700210')
    res = rv.json
    assert rv.status_code == 200 and len(res.get('data')) == 2 and \
        res.get('data')[0].get('story_id') == 27700200 and res.get('data')[0].get('unix_time') == 1625153690 and \
        res.get('data')[1].get('story_id') == 27700210 and res.get('data')[1].get('unix_time') == 1625153743

def test_get_stories_fail(client):
    # query string is badly formatted 1
    rv = client.get('/db/stories?id=27700200,27700210')
    assert rv.status_code == 400

    # query string is badly formatted 1
    rv = client.get('/db/stories?ids=27700200;27700210')
    assert rv.status_code == 404

    # ids correspond to comments
    rv = client.get('/db/stories?ids=27700201,27700211')
    assert rv.status_code == 200 and not len(rv.json.get('data'))

    # ids are not numeric
    rv = client.get('/db/stories?ids=abc,def')
    assert rv.status_code == 404

def test_first_id_on_date_ok(client):
    url = '/time/first_id_on?year={}&month={}&day={}'
    rv = client.get(url.format(2021, 7, 1))
    res = rv.json
    assert rv.status_code == 200 and res.get('data') and res.get('data').get('id') == 27693892

def test_first_id_on_date_fail(client):
    url = '/time/first_id_on?year={}&month={}&day={}'

    # date does not exist 1
    rv = client.get(url.format(2021, 2, 31))
    assert rv.status_code == 400

    # date does not exist 2
    rv = client.get(url.format(2021, 13, 31))
    assert rv.status_code == 400

    # date is in the future
    rv = client.get(url.format(3021, 7, 1))
    assert rv.status_code == 400
    
    # date is not numeric
    rv = client.get(url.format("abc", 7, 1))
    assert rv.status_code == 400

    # query string is wrongly formatted
    rv = client.get('/time/first_id_on?y=2021&m=7&d=1')
    assert rv.status_code == 400

def test_read_file_ok(client):
    # make temp dummy data files
    with open('data/test.txt', 'w') as f:
        f.write('1\n2\n3')
    with open('data/test.csv', 'w') as f:
        f.write('f1\tf2\tf3\n1\t2\t3\n4\t5\t6')
    with open('data/test.json', 'w') as f:
        json.dump({'f1': 1, 'f2': 2, 'f3': 3}, f)
    
    try:
        rv = client.get('/file?fname=data/test.txt')
        assert rv.status_code == 200 and rv.json.get('data') == ['1', '2', '3']

        rv = client.get('/file?fname=data/test.csv')
        assert rv.status_code == 200  and isinstance(rv.json.get('data'), dict) and \
            rv.json.get('data').get('f1') == ['1','4']

        rv = client.get('/file?fname=data/test.json')
        assert rv.status_code == 200 and isinstance(rv.json.get('data'), dict) and \
            rv.json.get('data').get('f1') == 1
    
    # cleanup
    finally:
        os.remove('data/test.txt')
        os.remove('data/test.csv')
        os.remove('data/test.json')

def test_read_file_fail(client):
    # file does not exist
    rv = client.get('/file?fname=data/this-file-does-not-exist.txt')
    assert rv.status_code == 404

    # file is not data file
    rv = client.get('/file?fname=run.sh')
    assert rv.status_code == 400

def test_delete_file_ok(client):
    # make temp dummy data files
    fnames = [
        'data/test.txt', 'data/test.json', 'data/test.csv', 
        'data/test_1.txt', 'data/test_2.txt', 'data/test_3.txt'
    ]
    for fname in fnames:
        with open(fname, 'w') as f:
            f.write('')
    
    try:
        for fname in [
                'data/this-file-does-not-exist.txt',
                'data/test.txt', 'data/test.json', 'data/test.csv', 
                'data/test_*.txt'
            ]:
            rv = client.delete('/file', 
                headers={'Content-Type': 'application/json'},
                data=json.dumps({'sender': 'deleter', 'fname': fname})
            )
            if not '*' in fname:
                assert rv.status_code == 200 and not os.path.isfile(fname)
            else:
                assert rv.status_code == 200 and \
                    all(not os.path.isfile(name) for name in fnames[3:])
    # cleanup
    finally:
        for fname in fnames:
            if os.path.isfile(fname):
                os.remove(fname)

def test_delete_file_fail(client):
    # post request is badly formatted 1
    rv = client.delete('/file', 
        headers={'Content-Type': 'application/json'},
        data=json.dumps({'fname': 'data/test.txt'})
    )
    assert rv.status_code == 400

    # post request is badly formatted 2
    rv = client.delete('/file', 
        headers={'Content-Type': 'application/json'},
        data=json.dumps({'sender': '', 'fname': 'data/test.txt'})
    )
    assert rv.status_code == 400

    # post request is badly formatted 3
    rv = client.delete('/file', 
        headers={'Content-Type': 'application/json'},
        data=json.dumps({'sender': 'deleter', 'file': 'data/test.txt'})
    )
    assert rv.status_code == 400

    # post request is badly formatted 4
    rv = client.delete('/file', 
        data=json.dumps({'sender': 'deleter', 'fname': 'data/test.txt'})
    )
    assert rv.status_code == 400

    # not a data file
    rv = client.delete('/file', 
        headers={'Content-Type': 'application/json'},
        data=json.dumps({'sender': 'deleter', 'fname': 'data/test.py'})
    )
    assert rv.status_code == 400

    # file is outside `data` dir
    rv = client.delete('/file', 
        headers={'Content-Type': 'application/json'},
        data=json.dumps({'sender': 'deleter', 'fname': 'test.py'})
    )
    assert rv.status_code == 400
