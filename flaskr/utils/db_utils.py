from typing import Any, Dict, List, Tuple, Set, Optional, Generator, Union

import sqlite3
from flaskr.db import get_db, close_db
import requests as rq
import datetime
import json

story_api2schema = {
    'story_id': 'id',
    'author': 'by',
    'unix_time': 'time',
    'body': 'text',
    'url': 'url',
    'score': 'score',
    'title': 'title',
    'num_comments': 'descendants',
    'kids': 'kids', # not in schema but we need it...
    'type': 'type', # not in schema,
    'deleted': 'deleted',
    'dead': 'dead'
}

comment_api2schema = {
    'comment_id': 'id',
    'author': 'by',
    'unix_time': 'time',
    'body': 'text',
    'parent_id': 'parent',
    'type': 'type' # not in schema...
}

def query_api(item_id: Union[int, str]) -> str:
    # TODO: rename api fields to schema fields
    url = f'https://hacker-news.firebaseio.com/v0/item/{item_id}.json?print=pretty'
    res = rq.get(url)
    return json.loads(res.text)

def translate_response_api2schema(res: Dict) -> Dict:
    if res is None:
        return
    elif res.get('type') == 'story':
        return {
            field: res.get(story_api2schema[field]) 
            for field in story_api2schema.keys()
        }
    elif res.get('type') == 'comment':
        return {
            field: res.get(comment_api2schema[field]) 
            for field in comment_api2schema.keys()
        }

def fetch_and_add_item_by_id(item_id: Union[int, str], commit: str = True) -> Optional[Dict]:
    print(f'[INFO] getting {item_id}...', end=' ')

    # skip if comment and already in db
    # keep is story and already in db -> update it later
    story_needs_update = False
    if DBHelper.find_comment_by_id(item_id):
        print('')
        return
    if DBHelper.find_story_by_id(item_id):
        story_needs_update = True

    # get item
    item = query_api(item_id) # raw response
    item = translate_response_api2schema(item) # fields are now the same as in schema (+)
    
    # skip if empty/deleted/dead
    if item is None or item.get('deleted',False) or item.get('dead',False):
        print('got empty, deleted or dead...')
        return    
    
    # add to db if not empty
    print(
        f'got {item.get("type", "UNKNOWN")} ' +\
        f'from {str(datetime.datetime.fromtimestamp(int(item.get("unix_time") | 0))).split(" ")[0]}, ' +\
        f'adding to db...'
    )

    if story_needs_update:
        DBHelper.update_story_in_db(item, commit=commit)
    elif item.get('type') == 'story':
        DBHelper.add_story_to_db(item, commit=commit)
    elif item.get('type') == 'comment':
        DBHelper.add_comment_to_db(item, commit=commit)

    return item

def query_hn_and_add_result_to_db(form_request: Dict) -> None:
        """
        collect all the stories in the requested range and 
        all thhe comments parented by these stories + 
        all the comments in the requested range
        """
        extra_comment_ids = []
    
        # add/update all items in the requested range
        print(f'<<< REQUESTING ITEMS FROM {form_request["begin_id"]} TO {form_request["end_id"]} >>>')
        for item_id in range(form_request['begin_id'], form_request['end_id']+1):
            item = fetch_and_add_item_by_id(item_id, commit=True)

            # for stories only: record comments (kids) outside requested range
            if item is not None and item.get('kids', None) is not None:
                extra_comment_ids.extend([
                    comment_id for comment_id in item['kids']
                    if comment_id > form_request["end_id"]
                ])
    
        # add comments outside the requested range
        # if they are parented by the stories withing the requested range
        print('<<< REQUESTING MORE ITEMS! >>>')
        for i,item_id in enumerate(extra_comment_ids):
            fetch_and_add_item_by_id(item_id, commit=True)

class DBHelper:
    STORY_FIELDS = [
        'story_id', 
        'author', 
        'unix_time', 
        'body', 
        'url', 
        'score', 
        'title', 
        'num_comments', 
        'comment_embedding'
    ]

    COMMENT_FIELDS = [
        'comment_id',
        'author',
        'unix_time',
        'body',
        'parent_id'
    ]

    STORY_PATTERN_WITHOUT_WHERE = """
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
            s.comment_embedding,
            (
                SELECT COALESCE(GROUP_CONCAT(body, "<br><br>"), " ")
                FROM tab
                WHERE root_id = s.story_id
                GROUP BY root_id
            ) AS children
        FROM story AS s
        """

    @classmethod
    def get_connection(cls) -> sqlite3.Cursor:
        return get_db()

    @classmethod
    def close_connection(cls) -> bool:
        close_db()
        return True

    @classmethod
    def row2dict(cls, row: sqlite3.Row) -> Dict:
        fields = row.keys()
        return {
            field: row.__getitem__(field)
            for field in fields
        }

    @classmethod
    def rows2dicts(cls, rows: List[sqlite3.Row]) -> List[Dict]:
        return [
            {
                field: row.__getitem__(field) 
                for field in row.keys()
            } for row in rows
        ]
    
    @classmethod
    def find_story_by_id(cls, story_id: Union[str, int]) -> Optional[Dict]:
        db = cls.get_connection()
        get_query = """
            SELECT * FROM story WHERE story_id = ?;
        """
        row = db.execute(get_query, (story_id,)).fetchone()
        cls.close_connection()
        return cls.row2dict(row) if row is not None else None

    @classmethod
    def find_comment_by_id(cls, comment_id: Union[str, int]) -> Optional[Dict]:
        db = cls.get_connection()
        get_query = """
            SELECT * FROM comment WHERE comment_id = ?;
        """
        row = db.execute(get_query, (comment_id,)).fetchone()
        cls.close_connection()
        return cls.row2dict(row) if row is not None else None

    @classmethod
    def add_story_to_db(cls, story: Dict, commit: bool = True) -> None:
        db = cls.get_connection()

        # add to `story` table
        add_story_query = """
            INSERT INTO story
            (story_id, author, unix_time, body, url, score, title, num_comments, comment_embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        story_params = tuple([story.get(field) for field in cls.STORY_FIELDS])
        db.execute(add_story_query, story_params)

        # add to `parent` table
        add_parent_query = """
            INSERT INTO parent
            (parent_id, parent_type)
            VALUES (?, ?)
        """
        parent_params = ( story.get('story_id'), 'story')
        db.execute(add_parent_query, parent_params)

        if commit:
            db.commit()
        cls.close_connection()

    @classmethod
    def add_comment_to_db(cls, comment: Dict, commit: bool = True) -> None:
        db = cls.get_connection()

        # add to `comment` table
        add_comment_query = """
            INSERT INTO comment
            (comment_id, author, unix_time, body, parent_id)
            VALUES (?, ?, ?, ?, ?)
        """
        comment_params = tuple([comment.get(field) for field in cls.COMMENT_FIELDS])
        db.execute(add_comment_query, comment_params) 

        # add to `parent` table
        parent_query = """
            INSERT INTO parent
            (parent_id, parent_type)
            VALUES (?, ?)
        """
        parent_params = (comment.get('commen_id'),'comment')
        db.execute(parent_query, parent_params)

        if commit:
            db.commit()
        cls.close_connection()

    @classmethod
    def update_story_in_db(cls, story: Dict, commit: bool = True) -> None:
        db = cls.get_connection()

        update_story_query = """
            UPDATE story
            SET 
                author = ?, 
                unix_time = ?, 
                body = ?, 
                url = ?, 
                score = ?, 
                title = ?, 
                num_comments = ?,
                comment_embedding = ?
            WHERE story_id = ?
        """

        update_story_params = (
            story.get('author'), 
            story.get('unix_time'), 
            story.get('body'),
            story.get('url'), 
            story.get('score'), 
            story.get('title'), 
            story.get('num_comments'),
            story.get('comment_embedding'),
            story.get('story_id'),
        )

        db.execute(update_story_query, update_story_params) 

        if commit:
            db.commit()
        cls.close_connection()        

    @classmethod
    def get_query(cls, query_pattern: str, params: Union[List,Tuple]) -> List[Optional[sqlite3.Row]]:
        db = cls.get_connection()
        rows = db.execute(query_pattern, tuple(params)).fetchall()
        cls.close_connection()
        return cls.rows2dicts(rows) if rows is not None else []

    @classmethod
    def mod_query(cls, query_pattern: str, params: Union[List,Tuple], commit: bool = True) -> List[Optional[sqlite3.Row]]:
        db = cls.get_connection()
        db.execute(query_pattern, tuple(params))
        if commit:
            db.commit()
        cls.close_connection()
        return True