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
        (story_id, author, unix_time, body, url, score, title, num_comments)
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
        author = ?, unix_time = ?, body = ?, url = ?, score = ?, title = ?, num_comments = ?
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
        'num_comments': number of comments
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
                s.title
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
            s.num_comments,
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
        'num_comments': number of comments
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
                s.title
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
            s.num_comments,
            (
                SELECT COALESCE(GROUP_CONCAT(body, "<br><br>"), " ")
                FROM tab
                WHERE root_id = s.story_id
                GROUP BY root_id
            ) AS children            
        FROM story AS s
        WHERE 
            s.story_id BETWEEN ? AND ? AND
            s.num_comments BETWEEN ? AND ? AND
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

def get_id_list_from_sqlite_rows(rows) -> 'List[str]':
    """
    Extract post 'id's from HN posts;
    Returns a list of ids
    """
    return [str(row.__getitem__("story_id")) for row in rows]

def get_document_list_from_sqlite_rows(rows) -> 'List[str]':
    """
    Extract 'texts' from HN posts - SQLite Row objects corresponding to HN stories
    with an extra field 'children' corresponding to all comments 
    concatenated into a single string;
    These concatenated comments constitute corpus documents - 
    single document contains all comments parented by the same HN story;
    Returns a list of comments 
    """
    return [row.__getitem__("children") for row in rows]

def get_document_dict_from_sqlite_rows(rows, aslist=False) -> 'dict':
    """
    Extract 'texts' from HN posts - SQLite Row objects corresponding to HN stories
    with an extra field 'children' corresponding to all comments 
    concatenated into a single string;
    These concatenated comments constitute corpus documents - 
    single document contains all comments parented by the same HN story;
    Returns:
    if `aslist=False` (default): dict with keys = story ids and 
        values = story dicts (parsed sql row objs)
    else: list of story dicts (parsed sql row objs)
    """
    fields = [
        'story_id', 'author', 'unix_time', 'score', 
        'title', 'url', 'num_comments', 'children'
    ]

    if aslist:
        return [
            {field: row.__getitem__(field) for field in fields} 
            for row in rows
        ]
    else:
        return {
            row.__getitem__('story_id'): {
                field: row.__getitem__(field) for field in fields
            } for row in rows
        }
        

def get_stories_from_db(form_request, delta_id=10000):
    """
    generator - returns stories from the id range specified in form_request;
    each story is given as a python dict with keys:
        story_id
        author
        unix_time
        score
        title
        url
        num_comments
        children <- all comments corresponding to a given story
    Under the hood uses `get_stories_with_children_from_id_range(.)`,
    but never loads all the data from the entire queried range to mem    
    """
    begin_id = int(form_request["begin_id"])
    end_id = int(form_request["end_id"])
    for b_id in range(begin_id, end_id, delta_id):
        # get current(!) begin_id and end_id range (b_id and e_id)
        e_id = min(b_id + delta_id - 1, end_id)
        form_request["begin_id"] = b_id
        form_request["end_id"] = e_id
        print(f"fetching posts from {b_id} to {e_id}")

        # query db for a portion of data and... 
        story_rows = get_stories_with_children_from_id_range(form_request)
        
        # ... yield intividual posts as dicts
        for row in story_rows:
            dct = get_document_dict_from_sqlite_rows([row])
            for key, val in dct.items():
                yield val

class DBHelper:
    def __init__(self):
        self.db = get_db()
        self.story_pattern_without_where = """
        WITH RECURSIVE tab(id, parent_id, root_id, level, title, body) AS (
            SELECT 
                s.story_id, 
                s.story_id,
                s.story_id,
                1,
                s.title,
                s.title
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
            s.num_comments,
            (
                SELECT COALESCE(GROUP_CONCAT(body, "<br><br>"), " ")
                FROM tab
                WHERE root_id = s.story_id
                GROUP BY root_id
            ) AS children            
        FROM story AS s
        """

    def get_story_with_children_by_id(self, story_id):

        fields = [
            'story_id', 'author', 'unix_time', 'score', 
            'title', 'url', 'num_comments', 'children'
        ]

        row = self.db.execute(        
            f'''
            {self.story_pattern_without_where}
            WHERE s.story_id = ?;
            ''', 
            (story_id,)
        ).fetchone()

        return {
            field: row.__getitem__(field)
            for field in fields
        }
