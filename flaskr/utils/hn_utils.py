from typing import Any, Dict, List, Tuple, Set, Optional, Generator, Union

import requests as rq
import datetime

from flaskr.utils.db_utils import (
    Story, 
    Comment
)

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