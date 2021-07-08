from flaskr.db import get_db
import requests as rq
import datetime
import json

def is_item_id_in_db(db, item_id):
    if db.execute(
        'SELECT * FROM story WHERE story_id = ?', (item_id,)
    ).fetchone() is not None:
        # stories might need to be updated (score, num of descendants)
        return 'story', True
    elif db.execute(
        'SELECT * FROM comment WHERE comment_id = ?', (item_id,)
    ).fetchone() is not None:
        return 'comment', True
    else:
        return 'unknown', False

def add_story_to_db(db, story):
    db.execute(
        'INSERT INTO story ' +\
        '(story_id, author, unix_time, body, url, score, title, descendants) ' + \
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (
            story.get('id'),
            story.get('by'), 
            story.get('time'), 
            story.get('text'),
            story.get('url'), 
            story.get('score'), 
            story.get('title'), 
            story.get('descendants')
        )
    )    
    db.commit()

def update_story_in_db(db, story):
    db.execute(
        '''UPDATE story
           SET 
           author = ?, unix_time = ?, body = ?, url = ?, score = ?, title = ?, descendants = ?
           WHERE story_id = ?''',
        (
            story.get('by'), 
            story.get('time'), 
            story.get('text'),
            story.get('url'), 
            story.get('score'), 
            story.get('title'), 
            story.get('descendants'),
            story.get('id'),
        )
    )    
    db.commit()

def add_comment_to_db(db, comment):
    db.execute(
        'INSERT INTO comment ' +\
        '(comment_id, author, unix_time, body, story_id) ' + \
        'VALUES (?, ?, ?, ?, ?)',
        (
            comment.get('id'),
            comment.get('by'), 
            comment.get('time'), 
            comment.get('text'), 
            comment.get('story_id'),
        )
    )    
    db.commit()

def add_item_to_db(db, item):
    if item.get('type', None) == 'story':
        add_story_to_db(db, item)
    elif item.get('type', None) == 'comment':
        add_comment_to_db(db, item)

def delete_item_by_id_from_db_if_present(db, item_id):
    if db.execute(
        'SELECT * FROM story WHERE story_id = ?', (item_id,)
    ).fetchone() is not None:
        db.execute(
            'DELETE FROM story WHERE story_id = ?', (item_id,)
        )
    elif db.execute(
        'SELECT * FROM comment WHERE comment_id = ?', (item_id,)
    ).fetchone() is not None:
        db.execute(
            'DELETE FROM comment WHERE comment_id = ?', (item_id,)
        )
    db.commit()

def query_api(item_id):
    url = f'https://hacker-news.firebaseio.com/v0/item/{item_id}.json?print=pretty'
    res = rq.get(url)
    return json.loads(res.text)

def add_or_update_item_by_id(db, item_id):
    print(f'[INFO] getting {item_id}...', end=' ')

    # skip if item already in db and not story 
    #(stories might need to be updated)
    item_type, in_db = is_item_id_in_db(db, item_id)
    if in_db and item_type != 'story':
        print('already in db, skipping...')
        return
        
    # get item
    item = query_api(item_id)

    # delete item from db if empty/deleted/dead and still in db
    if item is None or item.get('deleted',False) or item.get('dead',False):
        print('got empty, deleted or dead...')
        delete_item_by_id_from_db_if_present(db, item_id)
        return

    # add/update item if not empty
    print(
        f'got {item.get("type", "UNKNOWN")} ' +\
        f'from {str(datetime.datetime.fromtimestamp(int(item.get("time") | 0))).split(" ")[0]}, ' +\
        f'adding to db...'
    )

    if not in_db:
        add_item_to_db(db, item)
    elif item_type == 'story':
        update_story_in_db(db, item)

    return item


def query_api_and_add_result_to_db(form_request):
    """
    collect all the stories in the requested range and 
    all thhe comments parented by these stories + 
    all the comments in the requested range

    TODO: deal with deleted and dead items
    """
    db = get_db()
    extra_comment_ids = []

    # add/update all items in the requested range
    for item_id in range(form_request['begin_id'], form_request['end_id']+1):
        item = add_or_update_item_by_id(db, item_id)

        # for stories only: record comments (kids) outside requested range
        if item is not None and item.get('kids', None) is not None:
            extra_comment_ids.extend([
                c for c in item['kids'] if c > form_request['end_id']
            ])

    # add comments outside the requested range
    # if they are parented by the stories withing the requested range
    for item_id in extra_comment_ids:
        add_or_update_item_by_id(db, item_id)

def get_requested_items(form_request):
    """
    use story_ids and comment_ids
    TODO: this shouldn't make new queries...
    """
    db = get_db()
    stories, comments = [], []

    for item_id in range(form_request['begin_id'], form_request['end_id']+1):
        maybe_story = db.execute(
            'SELECT * FROM story WHERE story_id = ?', (item_id, )
        ).fetchone()
        maybe_comment = db.execute(
            'SELECT * FROM comment WHERE comment_id = ?', (item_id,)
        ).fetchone()
        if maybe_story is not None:
            stories.append(maybe_story)
        elif maybe_comment is not None:
            comments.append(maybe_comment)

    return {'stories': stories, 'comments': comments}

def get_requested_stories_with_children(form_request):
    db = get_db()

    return db.execute(
        '''
        SELECT 
            s.story_id,
            s.title,
            s.author,
            s.unix_time,
            s.url,
            s.score,
            s.descendants,
            GROUP_CONCAT(c.body, "\n") AS children
        FROM story AS s
        LEFT JOIN comment AS c
        ON s.story_id = c.story_id 
        WHERE s.story_id > ? AND s.story_id < ?
        GROUP BY s.story_id , s.title, s.author, s.unix_time, s.url, s.score, s.descendants
        ''', (form_request['begin_id'], form_request['end_id']+1)
    ).fetchall()