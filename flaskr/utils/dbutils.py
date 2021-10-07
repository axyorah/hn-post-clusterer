from flaskr.db import get_db
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
    'num_comments': 'descentants',
    'kids': 'kids', # not in schema but we need it...
    'type': 'type' # not in schema
}

comment_api2schema = {
    'comment_id': 'id',
    'author': 'by',
    'unix_time': 'time',
    'body': 'text',
    'parent_id': 'parent',
    'type': 'type' # not in schema...
}

def query_api(item_id):
    # TODO: rename api fields to schema fields
    url = f'https://hacker-news.firebaseio.com/v0/item/{item_id}.json?print=pretty'
    res = rq.get(url)
    return json.loads(res.text)

def translate_response_api2schema( res: dict ):
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
            s.comment_embedding,
            (
                SELECT COALESCE(GROUP_CONCAT(body, "<br><br>"), " ")
                FROM tab
                WHERE root_id = s.story_id
                GROUP BY root_id
            ) AS children            
        FROM story AS s
        """

    def is_story_id_in_db(self, item_id):
        if self.db.execute(
            'SELECT 1 FROM story WHERE story_id = ?', (item_id,)
        ).fetchone() is not None:
            return True
        else:
            return False
    
    def is_comment_id_in_db(self, item_id):
        if self.db.execute(
            'SELECT 1 FROM comment WHERE comment_id = ?', (item_id,)
        ).fetchone() is not None:
            return True
        else:
            return False

    def add_story_to_db(self, story, commit=True):
        # add to `story` table
        self.db.execute(
            '''
            INSERT INTO story
            (story_id, author, unix_time, body, url, score, title, num_comments, comment_embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                story.get('story_id'),
                story.get('author'), 
                story.get('unix_time'), 
                story.get('body'),
                story.get('url'), 
                story.get('score'), 
                story.get('title'), 
                story.get('num_comments'),
                story.get('comment_embedding')
            )
        )

        # add to `parent` table
        self.db.execute(
            '''
            INSERT INTO parent
            (parent_id, parent_type)
            VALUES (?, ?)
            ''',
            ( story.get('story_id'), 'story')
        )

        if commit:
            self.db.commit()

    def add_comment_to_db(self, comment, commit=True):
        # add to `comment` table
        self.db.execute(
            '''
            INSERT INTO comment
            (comment_id, author, unix_time, body, parent_id)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                comment.get('comment_id'),
                comment.get('author'), 
                comment.get('unix_time'), 
                comment.get('body'), 
                comment.get('parent_id'),
            )
        ) 

        # add to `parent` table
        self.db.execute(
            '''
            INSERT INTO parent
            (parent_id, parent_type)
            VALUES (?, ?)
            ''',
            (comment.get('commen_id'),'comment')
        )

        if commit:
            self.db.commit()

    def update_story_in_db(self, story, commit=True):
        self.db.execute(
            '''
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
            ''',
            (
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
        ) 

        if commit:
            self.db.commit()

    def add_item_to_db(self, item, commit=True):
        if item.get('type', None) == 'story':
            self.add_story_to_db(item, commit=commit)
        elif item.get('type', None) == 'comment':
            self.add_comment_to_db(item, commit=commit)

    def delete_item_by_id_from_db_if_present(self, item_id, commit=True):
        if self.db.execute(
            'SELECT 1 FROM parent WHERE parent_id = ?', (item_id,)
        ).fetchone() is not None:
            self.db.execute(
                'DELETE FROM parent WHERE parent_id = ?', (item_id, )
            )
        if commit:
            self.db.commit()

    def fetch_and_add_item_by_id(self, item_id, commit=True):
        print(f'[INFO] getting {item_id}...', end=' ')

        # skip if item already in db
        if self.is_story_id_in_db(item_id) or self.is_comment_id_in_db(item_id):
            print('already in db, skipping...')
            return

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
        self.add_item_to_db(item, commit=commit)

        return item

    def query_api_and_add_result_to_db(self, form_request, delta_commit=100):
        """
        collect all the stories in the requested range and 
        all thhe comments parented by these stories + 
        all the comments in the requested range

        TODO: deal with deleted and dead items
        """
        extra_comment_ids = []
    
        # add/update all items in the requested range
        print(f'<<< REQUESTING ITEMS FROM {form_request["begin_id"]} TO {form_request["end_id"]} >>>')
        for item_id in range(form_request['begin_id'], form_request['end_id']+1):
            item = self.fetch_and_add_item_by_id(item_id, commit=False)

            # for stories only: record comments (kids) outside requested range
            if item is not None and item.get('kids', None) is not None:
                extra_comment_ids.extend([
                    comment_id for comment_id in item['kids']
                    if comment_id > form_request["end_id"]
                ])

            # commit db every `delta_commit`
            if not (item_id - form_request['begin_id']) % delta_commit:
                self.db.commit()
    
        # add comments outside the requested range
        # if they are parented by the stories withing the requested range
        print('<<< REQUESTING MORE ITEMS! >>>')
        for i,item_id in enumerate(extra_comment_ids):
            self.fetch_and_add_item_by_id(item_id, commit=False)
            
            # commit db every `delta_commit`
            if not (i % delta_commit):
                self.db.commit()

        # final db commit
        self.db.commit()

    
    def get_story_with_children_by_id(self, story_id):
        # TODO: embeds
        fields = [
            'story_id', 'author', 'unix_time', 'score', 
            'title', 'url', 'num_comments', 'children',
            'comment_embedding', 
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

    def get_story_rows_with_children_from_id_range(self, form_request):

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
            'comment_embedding'
            'children'    : all comments related to the same story (html markup)
        """
        return self.db.execute(
            f'''
            {self.story_pattern_without_where}
                WHERE 
                s.story_id BETWEEN ? AND ? AND
                s.num_comments BETWEEN ? AND ? AND
                s.score BETWEEN ? AND ?
            ;
            ''', 
            (
                form_request['begin_id'], form_request['end_id'],
                form_request['begin_comm'], form_request['end_comm'],
                form_request['begin_score'], form_request['end_score']
            )
        ).fetchall()

    def get_story_rows_with_children_from_id_list(self, form_request):
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
            'comment_embedding'
        """
        return self.db.execute(
            f'''
            {self.story_pattern_without_where}
                WHERE 
                s.story_id IN ({", ".join("?" for _ in form_request["story_ids"])})
            ;
            ''', 
            tuple(form_request['story_ids'])
        ).fetchall()

    def story_rows_to_dicts(self, rows, aslist=False):
        """
        convert sql row objects corresponding to stories
        into dicts with fields
            story_id, author, unix_time, score, title, url, num_comments, children
        return dictionary is aslist=False (default),
        where keys are story ids and values are story dicts
        or lists of story dicts in aslist=True
        """
        fields = [
            'story_id', 'author', 'unix_time', 'score', 
            'title', 'url', 'num_comments', 'children',
            'comment_embedding'
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

    def get_stories_with_children_from_id_range(self, form_request, aslist=False):
        """
        return story dicts from a range specified in `form_request`;
        return either a dict (aslist=False) where keys are story ids 
        and values are story dicts,
        or a list of story dicts (aslist=True);
        form_request should have fields `begin_id` and `end_id`;
        internal dicts correspond to stories with fields:
            story_id, author, unix_time, score, title, url, num_comments, children
        """
        rows = self.get_story_rows_with_children_from_id_range(form_request)
        return self.story_rows_to_dicts(rows, aslist=aslist)

    def get_stories_with_children_from_id_list(self, form_request, aslist=False):
        """
        return story dicts from an id list specified in `form_request`;
        return either a dict (aslist=False) where keys are story ids 
        and values are story dicts,
        or a list of story dicts (aslist=True);
        form_request should have field `story_ids`;
        internal dicts correspond to stories with fields:
            story_id, author, unix_time, score, title, url, num_comments, children
        """
        rows = self.get_story_rows_with_children_from_id_list(form_request)
        return self.story_rows_to_dicts(rows, aslist=aslist)

    def yield_story_from_id_range(self, form_request, delta_id=10000):
        begin_id = int(form_request["begin_id"])
        end_id = int(form_request["end_id"])
        for b_id in range(begin_id, end_id, delta_id):
            # get current(!) begin_id and end_id range (b_id and e_id)
            e_id = min(b_id + delta_id - 1, end_id)
            form_request["begin_id"] = b_id
            form_request["end_id"] = e_id
            print(f"fetching posts from {b_id} to {e_id}")

            # query db for a portion of data and... 
            story_dicts = self.get_stories_with_children_from_id_range(form_request, aslist=True)
        
            # ... yield intividual posts as dicts
            for dct in story_dicts:
                for _, val in dct.items():
                    yield val    
