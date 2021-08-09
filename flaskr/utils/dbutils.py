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
    # add to `story` table
    db.execute(
        '''
        INSERT INTO story
        (story_id, author, unix_time, body, url, score, title, descendants)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
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
    # add to `parent` table
    db.execute(
        '''
        INSERT INTO parent
        (parent_id, parent_type)
        VALUES (?, ?)
        ''',
        (
            story.get('id'),
            'story'
        )
    )
    db.commit()

def update_story_in_db(db, story):
    db.execute(
        '''
        UPDATE story
        SET 
        author = ?, unix_time = ?, body = ?, url = ?, score = ?, title = ?, descendants = ?
        WHERE story_id = ?
        ''',
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
    # add to `comment` table
    db.execute(
        '''
        INSERT INTO comment
        (comment_id, author, unix_time, body, parent_id)
        VALUES (?, ?, ?, ?, ?)
        ''',
        (
            comment.get('id'),
            comment.get('by'), 
            comment.get('time'), 
            comment.get('text'), 
            comment.get('parent'),
        )
    ) 
    # add to `parent` table
    db.execute(
        '''
        INSERT INTO parent
        (parent_id, parent_type)
        VALUES (?, ?)
        ''',
        (
            comment.get('id'),
            'comment'
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
        'SELECT 1 FROM parent WHERE parent_id = ?', (item_id,)
    ).fetchone() is not None:
        db.execute(
            'DELETE FROM parent WHERE parent_id = ?', (item_id, )
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
    print(f'<<< REQUESTING ITEMS FROM {form_request["begin_id"]} TO {form_request["end_id"]} >>>')
    for item_id in range(form_request['begin_id'], form_request['end_id']+1):
        item = add_or_update_item_by_id(db, item_id)

        # for stories only: record comments (kids) outside requested range
        if item is not None and item.get('kids', None) is not None:
            extra_comment_ids.extend(item['kids'])
    
    # add comments outside the requested range
    # if they are parented by the stories withing the requested range
    print('<<< REQUESTING MORE ITEMS! >>>')
    for item_id in extra_comment_ids:
        add_or_update_item_by_id(db, item_id)

def get_stories_with_children_from_id_list(form_request):
    """
    fetches the stories with specified id list;
    form_request: dict: should contain the following fields:
        'story_ids'   : list of story ids
    returns a list of sql Row objects with the following fields:
        'story_id'
        'author'
        'unix_time'
        'score'
        'title'
        'url'
        'descendants' : number of comments
        'children'    : all comments related to the same story (html markup)
    """
    db = get_db()
    
    return  db.execute(        
        f'''
        WITH RECURSIVE tab(id, parent_id, root_id, level, title, body) AS (
            SELECT 
                s.story_id, 
                s.story_id,
                s.story_id,
                1,
                s.title,
                s.url
            FROM story AS s
            
            UNION

            SELECT
                c.comment_id, 
                c.parent_id,
                tab.root_id,
                tab.level + 1,
                c.author,
                c.body
            FROM tab, comment as c WHERE c.parent_id = tab.id
        ) 

        SELECT 
            s.story_id,
            s.author, 
            s.unix_time,
            s.score,
            s.title, 
            s.url,
            s.descendants,
            (
                SELECT COALESCE(GROUP_CONCAT(body, "<br><br>"), " ")
                FROM tab
                WHERE root_id = s.story_id
                GROUP BY root_id
            ) AS children            
        FROM story AS s
        WHERE 
            s.story_id IN ({", ".join("?" for _ in form_request["story_ids"])})
        ;
        ''', 
        tuple(form_request['story_ids'])
    ).fetchall()
    #", ".join("?" for _ in form_request["story_ids"])
    #"?, " * len(form_request["story_ids"])

def get_stories_with_children_from_id_range(form_request):
    """
    filters the stories by the id range, #comments and score;
    form_request: dict: should contain the following fields:
        'begin_id'   : lower bound for story id
        'end_id'     : higher bound for story id
        'begin_comm' : lower bound for the number of comments
        'end_comm'   : height bound ...
        'begin_score': lower bound for score
        'end_score'  : higher bound ...
    returns a list of sql Row objects with the following fields:
        'story_id'
        'author'
        'unix_time'
        'score'
        'title'
        'url'
        'descendants' : number of comments
        'children'    : all comments related to the same story (html markup)
    """
    db = get_db()

    return  db.execute(        
        '''
        WITH RECURSIVE tab(id, parent_id, root_id, level, title, body) AS (
            SELECT 
                s.story_id, 
                s.story_id,
                s.story_id,
                1,
                s.title,
                s.url
            FROM story AS s
            -- WHERE s.story_id BETWEEN ? AND ?

            UNION

            SELECT
                c.comment_id, 
                c.parent_id,
                tab.root_id,
                tab.level + 1,
                c.author,
                c.body
            FROM tab, comment as c WHERE c.parent_id = tab.id
        ) 

        SELECT 
            s.story_id,
            s.author, 
            s.unix_time,
            s.score,
            s.title, 
            s.url,
            s.descendants,
            (
                SELECT COALESCE(GROUP_CONCAT(body, "<br><br>"), " ")
                FROM tab
                WHERE root_id = s.story_id
                GROUP BY root_id
            ) AS children            
        FROM story AS s
        WHERE 
            s.story_id BETWEEN ? AND ? AND
            s.descendants BETWEEN ? AND ? AND
            s.score BETWEEN ? AND ?
        ;
        ''', 
        (
            #form_request['begin_id'], form_request['end_id'], 
            form_request['begin_id'], form_request['end_id'],
            form_request['begin_comm'], form_request['end_comm'],
            form_request['begin_score'], form_request['end_score']
        )
    ).fetchall()