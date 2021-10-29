from typing import Any, Dict, List, Tuple, Set, Optional, Generator, Union

import sqlite3
from flaskr.db import get_db, close_db
import requests as rq
import datetime

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
    url = f'https://hacker-news.firebaseio.com/v0/item/{item_id}.json?print=pretty'
    res = rq.get(url)
    return res.json()

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
    if Comment.find_by_id(item_id):
        print('already in db, skipping...')
        return 
    if Story.find_by_id(item_id):
        story_needs_update = True

    # get item
    item = query_api(item_id) # raw re  sponse
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
        story = Story(**item)
        story.update()
    elif item.get('type') == 'story':
        story = Story(**item)
        story.add()
    elif item.get('type') == 'comment':
        comment = Comment(**item)
        comment.add()

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

class Story:
    SCHEMA = [
        "story_id", 
        "author", 
        "unix_time", 
        "body", 
        "url", 
        "score", 
        "title", 
        "num_comments", 
        "comment_embedding"
    ]

    RECURSIVE_CTE_WITHOUT_WHERE = """
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

    def __init__(self, 
        story_id=None, author=None, unix_time=None, 
        title=None, score=None, num_comments=None,
        body=None, url=None, comment_embedding=None, children=None,
        **kwargs # non-schema api kwargs, e.g., `deleled`, `type`, ...
    ):
        self.story_id = story_id
        self.author = author
        self.unix_time = unix_time
        self.title = title
        self.score = score
        self.num_comments = num_comments
        self.body = body
        self.url = url
        self.comment_embedding = comment_embedding
        self.children = children

    def json(self) -> Dict:
        return {
            "story_id": self.story_id,
            "author": self.author,
            "unix_time": self.unix_time,
            "title": self.title,
            "score": self.score,
            "num_comments": self.num_comments,
            "body": self.body,
            "url": self.url,
            "comment_embedding": self.comment_embedding,
            "children": self.children
        }

    @classmethod
    def find_by_id(cls, story_id: int) -> Optional['Story']:
        get_query = """
            SELECT * FROM story WHERE story_id = ?
        """
        rows = DBHelper.get_query(get_query, [story_id])
        if rows:
            return  cls(**DBHelper.rows2dicts(rows)[0])

    @classmethod
    def find_by_id_with_children(cls, story_id: int) -> Optional['Story']:
        get_query = f"""
            {cls.RECURSIVE_CTE_WITHOUT_WHERE}
            WHERE s.story_id = ?
        """
        rows = DBHelper.get_query(get_query, [story_id])
        if rows:
            return cls(**DBHelper.rows2dicts(rows)[0])

    def add(self) -> None:
        # add to story table
        add_story_query = f"""
            INSERT INTO story
            ({', '.join(self.SCHEMA)})
            VALUES ({', '.join(['?' for _ in self.SCHEMA])});
        """
        story_params = [getattr(self, field) for field in self.SCHEMA]
        DBHelper.mod_query(add_story_query, story_params)

        # add to parent table
        add_parent_query = """
            INSERT INTO parent
            (parent_id, parent_type)
            VALUES (?, ?)
        """
        parent_params = (self.story_id, 'story')
        DBHelper.mod_query(add_parent_query, parent_params)

    def update(self) -> None:
        update_query = f"""
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
            WHERE story_id = ?;
        """
        params = [
            self.author,
            self.unix_time,
            self.body,
            self.url,
            self.score,
            self.title,
            self.num_comments,
            self.comment_embedding,
            self.story_id
        ]
        DBHelper.mod_query(update_query, params)

    def delete(self) -> None:
        delete_query = """
            DELETE FROM story WHERE story_id = ?
        """
        DBHelper.mod_query(delete_query, [self.story_id])

class Comment:
    SCHEMA = [
        "comment_id",
        "author",
        "unix_time",
        "body",
        "parent_id"
    ]
    
    def __init__(self, 
        comment_id=None, author=None, unix_time=None, body=None, parent_id=None, 
        **kwargs # non-schema api kwargs, e.g., `deleled`, `type`, ...
    ):
        self.comment_id = comment_id
        self.author = author
        self.unix_time = unix_time
        self.body = body
        self.parent_id = parent_id

    def json(self) -> Dict:
        return {
            "comment_id": self.comment_id,
            "author": self.author,
            "unix_time": self.unix_time,
            "body": self.body,
            "parent_id": self.parent_id
        }

    @classmethod
    def find_by_id(cls, comment_id: int) -> Optional['Comment']:
        get_query = """
            SELECT * FROM comment WHERE comment_id = ?
        """
        rows = DBHelper.get_query(get_query, [comment_id])
        if rows:
            return cls(**DBHelper.rows2dicts(rows)[0])

    def add(self) -> None:
        # add to comment table
        add_query = f"""
            INSERT INTO comment
            ({', '.join(self.SCHEMA)})
            VALUES ({', '.join(['?' for _ in self.SCHEMA])});
        """
        params = [getattr(self, field) for field in self.SCHEMA]
        DBHelper.mod_query(add_query, params)

        # add to parent table
        add_parent_query = """
            INSERT INTO parent
            (parent_id, parent_type)
            VALUES (?, ?)
        """
        parent_params = (self.comment_id, 'comment')
        DBHelper.mod_query(add_parent_query, parent_params)

    def update(self) -> None:
        update_query = f"""
            UPDATE comment
            SET 
                author = ?, 
                unix_time = ?, 
                body = ?, 
                parent_id = ?
            WHERE comment_id = ?;
        """
        params = [
            self.author,
            self.unix_time,
            self.body,
            self.comment_id
        ]
        # TODO: update parent table???
        DBHelper.mod_query(update_query, params)

    def delete(self) -> None:
        delete_query = """
            DELETE FROM comment WHERE comment_id = ?
        """
        DBHelper.mod_query(delete_query, [self.comment_id])

class StoryList:
    @classmethod
    def stats(cls) -> Dict:
        num_query = "SELECT COUNT(*) as num FROM story;"
        min_query = "SELECT MIN(story_id) as min FROM story;"
        max_query = "SELECT MAX(story_id) as max FROM story;"

        return {
            "num": DBHelper.get_query(num_query, [])[0].__getitem__("num"),
            "min": DBHelper.get_query(min_query, [])[0].__getitem__("min"),
            "max": DBHelper.get_query(max_query, [])[0].__getitem__("max")
        }

    @classmethod
    def find_by_ids(cls, id_list: List[int]) -> List[Story]:
        get_query = f"""
            SELECT * FROM story 
            WHERE story_id IN ({', '.join('?' for _ in id_list)})
        """
        rows = DBHelper.get_query(get_query, id_list)
        stories = DBHelper.rows2dicts(rows)
        return [Story(**story) for story in stories]

    @classmethod
    def find_by_ids_with_children(cls, id_list: List[int]) -> List[Story]:
        get_query = f"""
            {Story.RECURSIVE_CTE_WITHOUT_WHERE} 
            WHERE story_id IN ({', '.join('?' for _ in id_list)})
        """
        rows = DBHelper.get_query(get_query, id_list)
        stories = DBHelper.rows2dicts(rows)
        return [Story(**story) for story in stories]

class CommentList:
    @classmethod
    def stats(cls) -> Dict:
        num_query = "SELECT COUNT(*) as num FROM comment;"
        min_query = "SELECT MIN(comment_id) as min FROM comment;"
        max_query = "SELECT MAX(comment_id) as max FROM comment;"

        return {
            "num": DBHelper.get_query(num_query, [])[0].__getitem__("num"),
            "min": DBHelper.get_query(min_query, [])[0].__getitem__("min"),
            "max": DBHelper.get_query(max_query, [])[0].__getitem__("max")
        }

    @classmethod
    def find_by_ids(cls, id_list: List[int]) -> List[Comment]:
        get_query = f"""
            SELECT * FROM comment 
            WHERE comment_id IN ({', '.join('?' for _ in id_list)})
        """
        rows = DBHelper.get_query(get_query, id_list)
        comments = DBHelper.rows2dicts(rows)
        return [Comment(**comment) for comment in comments]
