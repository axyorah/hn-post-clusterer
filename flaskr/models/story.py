from typing import Any, Dict, List, Tuple, Set, Optional, Generator, Union

from flaskr.utils.db_utils import DBHelper

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