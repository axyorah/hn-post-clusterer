from typing import Any, Dict, List, Tuple, Set, Optional, Generator, Union

from flaskr.utils.db_utils import DBHelper
from flaskr.models.story import Story

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
