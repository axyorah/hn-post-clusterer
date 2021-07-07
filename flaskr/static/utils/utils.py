from flaskr.db import get_db
import requests as rq
import datetime
import json

from ...db import get_db

def parse_form(request):
    req = request.form
    form = dict()

    names = [
        ('begin_ts', 'begin-date-range'),
        ('end_ts', 'end-date-range'),
        ('begin_id', 'begin-id-range'),
        ('end_id', 'end-id-range')
    ]

    for form_name, html_name in names:
        try:
            form[form_name] = int(req.get(html_name))
        except:
            raise NameError(f'Error accessing element with id "{html_name}"')
        
    return form

def update_display_record(display, form):
    begin_date = datetime.datetime.fromtimestamp(form.get('begin_ts') // 1000)
    end_date = datetime.datetime.fromtimestamp(form.get('end_ts') // 1000)

    display.begin_date = f'{begin_date.year}/{begin_date.month}/{begin_date.day}'
    display.end_date = f'{end_date.year}/{end_date.month}/{end_date.day}'

    display.begin_id = form.get('begin_id')
    display.end_id = form.get('end_id')

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
        '(story_id, deleted, author, unix_time, body, dead, url, score, title, descendants) ' + \
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            story.get('id'),
            story.get('deleted'),
            story.get('by'), 
            story.get('time'), 
            story.get('text'), 
            story.get('dead'), 
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
           deleted = ?, author = ?, unix_time = ?, body = ?, dead = ?, url = ?, score = ?, title = ?, descendants = ?
           WHERE story_id = ?''',
        (
            story.get('deleted'),
            story.get('by'), 
            story.get('time'), 
            story.get('text'), 
            story.get('dead'), 
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
        '(comment_id, deleted, author, unix_time, body, dead, story_id) ' + \
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        (
            comment.get('id'),
            comment.get('deleted'),
            comment.get('by'), 
            comment.get('time'), 
            comment.get('text'), 
            comment.get('dead'), 
            comment.get('story_id'),
        )
    )    
    db.commit()

def add_item_to_db(db, item):
    if item.get('type', None) == 'story':
        add_story_to_db(db, item)
    elif item.get('type', None) == 'comment':
        add_comment_to_db(db, item)

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

    # add/update item if not empty
    if item is None:
        print('got empty...')
        return
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
    """use story_ids and comment_ids"""
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