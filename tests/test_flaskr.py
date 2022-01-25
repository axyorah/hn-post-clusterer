"""
use as:
$ python3 -m pytest tests/
or 
$ pytest
(the latter requires `__init__.py` file to be present in `tests`)
"""
import os, json

def check_get(client, url, code):
    rv = client.get(url)
    assert rv.status_code == code 
    return rv

def check_post(client, url, data, code):
    rv = client.post(
        url, 
        headers={'Content-Type': 'application/json'},
        data=json.dumps(data)
    )
    assert rv.status_code == code
    return rv

def check_put(client, url, data, code):
    rv = client.put(
        url, 
        headers={'Content-Type': 'application/json'},
        data=json.dumps(data)
    )
    assert rv.status_code == code
    return rv

def check_del(client, url, code):
    rv = client.delete(url)
    assert rv.status_code == code
    return rv


# ----------------------------------
# ------------ GENERAL -------------
# ----------------------------------
def test_index_ok(client):
    rv = client.get('/')
    assert rv.status_code == 200 and b'HN POST CLUSTERER' in rv.data

def test_empty_db(client):
    """Start with a blank database"""
    rv = check_get(client, '/api/meta/', 200)
    assert rv.json.get("stories") and not rv.json.get("stories").get('num')

# ----------------------------------
# ------------- STORY --------------
# ----------------------------------
def test_post_story_to_db_ok(client):
    # post new story
    data = {
            "author": "cbushko",
            "body": None,
            "num_comments": 0,
            "score": 8,
            "story_id": 27812656,
            "title": "Dropbox Engineering Career Framework",
            "unix_time": 1626110314,
            "url": "https://dropbox.github.io/dbx-career-framework/"
    }
    check_post(client, '/api/stories/', data, 201)

    # one of the optional fields is missing
    data = {
        "author": "bqe",
        "body": None,
        "num_comments": 588,
        "score": 1041,
        "story_id": 27399581,
        "title": "LOL just got kicked out of  @ycombinator",
        "unix_time": 1622844115,
        #"url": "https://twitter.com/paulbiggar/status/1400904600421535744"
    }
    check_post(client, '/api/stories/', data, 201)

def test_post_story_to_db_fail(client):
    # story already in db
    data = {
        "author": "cbushko",
        "body": None,
        "num_comments": 0,
        "score": 8,
        "story_id": 27812656,
        "title": "Dropbox Engineering Career Framework",
        "unix_time": 1626110314,
        "url": "https://dropbox.github.io/dbx-career-framework/"
    }
    check_post(client, '/api/stories/', data, 400)

    # one of the required fields is missing
    data = {
        "author": "bqe",
        "body": None,
        "num_comments": 588,
        "score": 1041,
        "story_id": 27399581,
        "title": "LOL just got kicked out of  @ycombinator",
        #"unix_time": 1622844115,
        "url": "https://twitter.com/paulbiggar/status/1400904600421535744"
    }
    check_post(client, '/api/stories/', data, 400)

    # one of the required fields is wrong type
    data = {
        "author": "bqe",
        "body": None,
        "num_comments": 588,
        "score": 1041,
        "story_id": "abc",
        "title": "LOL just got kicked out of  @ycombinator",
        "unix_time": 1622844115,
        "url": "https://twitter.com/paulbiggar/status/1400904600421535744"
    }
    check_post(client, '/api/stories/', data, 400)

def test_get_story_from_db_ok(client):
    check_get(client, '/api/stories/27812656/', 200)

def test_get_story_from_db_fail(client):
    check_get(client, '/api/stories/27812657/', 404)

def test_get_stories_ok(client):
    rv = check_get(client, '/api/stories?ids=27812656', 200)
    assert rv.json.get('data', None) is not None
    assert isinstance(rv.json['data'], list)
    assert len(rv.json['data']) == 1

def test_get_stories_fail(client):
    # query string is badly formatted 1
    rv = client.get('/api/stories?id=27812656')
    assert rv.status_code == 400

    # query string is badly formatted 1
    rv = client.get('/api/stories?ids=27812656;27700210')
    assert rv.status_code == 404

    # ids correspond to comments/not added items
    rv = client.get('/api/stories?ids=27812657')
    assert rv.status_code == 200 and not len(rv.json.get('data'))

    # ids are not numeric
    rv = client.get('/api/stories?ids=abc,def')
    assert rv.status_code == 404

def test_put_story_to_db_ok(client):
    # put already existing story to db
    data = {
        "author": "cbushko",
        "body": None,
        "num_comments": 0,
        "score": 8,
        "story_id": 27812656,
        "title": "Dropbox Engineering Career Framework",
        "unix_time": 1626110314,
        "url": "https://dropbox.github.io/dbx-career-framework/"
    }
    check_put(client, '/api/stories/27812656/', data, 200)

    # one of the optional fields is missing
    data = {
        "author": "bqe",
        "body": None,
        "num_comments": 588,
        "score": 1041,
        "story_id": 27399581,
        "title": "LOL just got kicked out of  @ycombinator",
        "unix_time": 1622844115,
        #"url": "https://twitter.com/paulbiggar/status/1400904600421535744"
    }
    check_put(client, '/api/stories/27399581/', data, 200)

def test_put_story_to_db_fail(client):
    # one of the required fields is missing
    data = {
        "author": "bqe",
        "body": None,
        "num_comments": 588,
        "score": 1041,
        "story_id": 27399581,
        "title": "LOL just got kicked out of  @ycombinator",
        #"unix_time": 1622844115,
        "url": "https://twitter.com/paulbiggar/status/1400904600421535744"
    }
    check_put(client, '/api/stories/27399581/', data, 400)

    # one of the required fields is wrong type
    data = {
        "author": "bqe",
        "body": None,
        "num_comments": 588,
        "score": 1041,
        "story_id": "abc",
        "title": "LOL just got kicked out of  @ycombinator",
        "unix_time": 1622844115,
        "url": "https://twitter.com/paulbiggar/status/1400904600421535744"
    }
    check_put(client, '/api/stories/27399581/', data, 400)

    # updating wrong story
    data = {
        "author": "bqe",
        "body": None,
        "num_comments": 588,
        "score": 1041,
        "story_id": 27399581,
        "title": "LOL just got kicked out of  @ycombinator",
        "unix_time": 1622844115,
        "url": "https://twitter.com/paulbiggar/status/1400904600421535744"
    }
    check_put(client, '/api/stories/27812656/', data, 400)

def test_del_story_from_db_ok(client):
    # delete existing story
    check_get(client, '/api/stories/27812656/', 200)
    check_del(client, '/api/stories/27812656/', 200)

    # delete non-existing story
    print(dir(client))
    check_get(client, '/api/stories/27812656/', 404)
    check_del(client, '/api/stories/27812656/', 200)


# ----------------------------------
# ----------- COMMENT --------------
# ----------------------------------
def test_post_comment_to_db_ok(client):
    # fetch items from hn and post them to db
    data = {
        "author": "p4bl0",
        "body": (
            "There are other ways of having a distributed immutable ledger than a blockchain, "
            "if you don&#x27;t have the constraints of a decentralized adversarial context. "
            "You don&#x27;t have this context for diplomas.<p>"
            "Also, neither revocation nor security and privacy does seem like "
            "good examples of what a blockchain would allow "
            "that a non-blockchain based approach wouldn&#x27;t."
        ),
        "comment_id": 30063390,
        "parent_id": 30063265,
        "unix_time": 1643055409
    }
    check_post(client, '/api/comments/', data, 201)

def test_post_comment_to_db_fail(client):
    # comment already in db
    data = {
        "author": "p4bl0",
        "body": (
            "There are other ways of having a distributed immutable ledger than a blockchain, "
            "if you don&#x27;t have the constraints of a decentralized adversarial context. "
            "You don&#x27;t have this context for diplomas.<p>"
            "Also, neither revocation nor security and privacy does seem like "
            "good examples of what a blockchain would allow "
            "that a non-blockchain based approach wouldn&#x27;t."
        ),
        "comment_id": 30063390,
        "parent_id": 30063265,
        "unix_time": 1643055409
    }
    check_post(client, '/api/comments/', data, 400)

    # one of the required fields is missing
    data = {
        "author": "p4bl0",
        "comment_id": 30063390,
        "parent_id": 30063265,
        "unix_time": 1643055409
    }
    check_post(client, '/api/comments/', data, 400)

    # one of the required fields is wrong type
    data = {
        "author": "p4bl0",
        "body": None,
        "comment_id": 30063390,
        "parent_id": 30063265,
        "unix_time": 1643055409
    }
    check_post(client, '/api/comments/', data, 400)

def test_get_comment_from_db_ok(client):
    check_get(client, '/api/comments/30063390/', 200)

def test_get_comment_from_db_fail(client):
    check_get(client, '/api/comments/27812656/', 404)

def test_get_comments_ok(client):
    rv = check_get(client, '/api/comments?ids=30063390', 200)
    assert rv.json.get('data', None) is not None
    assert isinstance(rv.json['data'], list)
    assert len(rv.json['data']) == 1

def test_get_comments_fail(client):
    # query string is badly formatted 1
    rv = client.get('/api/comments?id=30063390')
    assert rv.status_code == 400

    # query string is badly formatted 1
    rv = client.get('/api/comments?ids=30063390;30063390')
    assert rv.status_code == 404

    # ids correspond to comments/not added items
    rv = client.get('/api/comments?ids=27812656')
    assert rv.status_code == 200 and not len(rv.json.get('data'))

    # ids are not numeric
    rv = client.get('/api/comments?ids=abc,def')
    assert rv.status_code == 404

def test_put_comment_to_db_ok(client):
    # put already existing comment to db
    data = {
        "author": "p4bl0",
        "body": (
            "There are other ways of having a distributed immutable ledger than a blockchain, "
            "if you don&#x27;t have the constraints of a decentralized adversarial context. "
            "You don&#x27;t have this context for diplomas.<p>"
            "Also, neither revocation nor security and privacy does seem like "
            "good examples of what a blockchain would allow "
            "that a non-blockchain based approach wouldn&#x27;t."
        ),
        "comment_id": 30063390,
        "parent_id": 30063265,
        "unix_time": 1643055409
    }
    check_put(client, '/api/comments/30063390/', data, 200)

def test_put_comment_to_db_fail(client):
    # one of the required fields is missing
    data = {
        "author": "p4bl0",
        "comment_id": 30063390,
        "parent_id": 30063265,
        "unix_time": 1643055409
    }
    check_put(client, '/api/comments/30063390/', data, 400)

    # one of the required fields is wrong type
    data = {
        "author": "p4bl0",
        "body": None,
        "comment_id": 30063390,
        "parent_id": 30063265,
        "unix_time": 1643055409
    }
    check_post(client, '/api/comments/', data, 400)

    # updating wrong comment
    data = {
        "author": "p4bl0",
        "body": None,
        "comment_id": 30063390,
        "parent_id": 30063265,
        "unix_time": 1643055409
    }
    check_put(client, '/api/comments/30063391', data, 400)

def test_del_comment_from_db_ok(client):
    # delete existing comment
    check_get(client, '/api/comments/30063390/', 200)
    check_del(client, '/api/comments/30063390/', 200)

    # delete non-existing comment
    check_get(client, '/api/comments/30063390/', 404)
    check_del(client, '/api/comments/30063390/', 200)
    

# ----------------------------------
# -------------- IO ----------------
# ----------------------------------
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
