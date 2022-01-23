from flask import (
    current_app as app,
    request,
)
from flask.json import jsonify

from flaskr.utils.form_utils import RequestParser as rqparser

from flaskr.models.story import (
    Story,
    StoryList,
)
from flaskr.models.comment import (
    Comment,
    CommentList,
)

def validate(item, schema, item_type='item'):
    for field in schema:
        if field not in item:
            raise Exception(f"{item_type} is missing `{field}` field")
        if type(item[field]) not in schema[field]:
            raise Exception(
                    f"{item_type} field `{field}` is expected to be of {schema[field]} type, "
                    f"got {type(item[field])}"
                )

def validate_story(item):
    schema = {
        "story_id": {int},
        "author": {str},
        "unix_time": {int},
        "body": {str, type(None)},
        "url": {str, type(None)},
        "score": {int},
        "title": {str},
        "num_comments": {int},
    }

    validate(item, schema, 'story')

def validate_comment(item):
    schema = {
        "comment_id": {int},
        "author": {str},
        "unix_time": {int},
        "body": {str, type(None)},
        "parent_id": {int},
    }

    validate(item, schema, 'comment')


@app.route("/api/", strict_slashes=False)
def get_api_routes():
    """
    list of available routes
    """
    return jsonify([
        {"GET": "/api/meta/"},
        {"GET": "/api/stories?ids=<id1>,<id2>"},
        {"GET": "/api/stories/<id>/"},
        {"POST": "/api/stories/"},
        {"PUT": "/api/stories/<id>/"},
        {"DELETE": "/api/stories/<id>/"},
        {"GET": "/api/comments?ids=<id1>,<id2>"},
        {"GET": "/api/comments/<id>/"},
        {"POST": "/api/comments/"},
        {"PUT": "/api/comments/<id>/"},
        {"DELETE": "/api/comments/<id>/"},
    ])

@app.route("/api/meta/", strict_slashes=False)
def get_db_meta():
    """
    returns basic stats about stories and comments in db:
    {
        "stories": {
            "num": <number of stories in db>,
            "min": <min story id>,
            "max": <max story id>
        },
        "comments": {
            "num": <number of comments in db>,
            "min": <min commentid>,
            "max": <max commentid>
        }
    }
    """
    try:
        return jsonify({
            "stories": StoryList.stats(),
            "comments": CommentList.stats()
        })
    except Exception as e:
        return jsonify({
            "message": "couldn't get basic stats on stories and comments",
            "errors": e.args[0]
        }), 500


@app.route("/api/stories/<string:id>/", strict_slashes=False)
def get_story_by_id(id):
    """
    gets story with specified id from db, returns under json's `data` field
    """
    story = Story.find_by_id(id)        
    if story:
        return jsonify({
            "message": "got story from db",
            "data": story.json()
        })
    else: 
        return jsonify({
            "message": f"item `{id}` not found",
            "errors": f"item `{id}` not found"
        }), 404

@app.route("/api/stories/", methods=["POST"], strict_slashes=False)
def add_story_to_db():
    """
    adds story in db
    expects the following body:
    {
        "story_id": ...,
        "author": ...,
        "unix_time": ....,
        "body": ...,
        "url": ...,
        "score": ...,
        "title": ...,
        "num_comments": ...,
        "deleted": ...,
        "dead": ...,
    }
    """
    try:
        item = request.get_json()
    except Exception as e:
        return jsonify({
            "message": "couldn't parse request",
            "errors": e.args[0]
        })

    try:
        validate_story(item)
    except Exception as e:
        return jsonify({
            "message": e.args[0],
            "errors": e.args[0]
        }), 400

    # check if it's already in db
    story = Story.find_by_id(item['story_id'])
    if story:
        return jsonify({
            "message": f"story {item['story_id']} is already in database",
        }), 400

    # post to db
    try:
        story = Story(**item)
        story.add()

        return jsonify({
            "message": f"item {item['story_id']} added to db",
            "data": story.json()
        })
    except Exception as e:
        return jsonify({
            "message": f"couldn't add item {item['story_id']} to db",
            "errors": e.args[0]
        }), 500

@app.route("/api/stories/<string:id>/", methods=["PUT"], strict_slashes=False)
def update_story_in_db(id):
    """
    updates story in db
    expects the following body:
    {
        "story_id": ...,
        "author": ...,
        "unix_time": ....,
        "body": ...,
        "url": ...,
        "score": ...,
        "title": ...,
        "num_comments": ...,
        "deleted": ...,
        "dead": ...,
    }
    """
    try:
        item = request.get_json()
    except Exception as e:
        return jsonify({
            "message": "couldn't parse request",
            "errors": e.args[0]
        })

    try:
        validate_story(item)
    except Exception as e:
        return jsonify({
            "message": e.args[0],
            "errors": e.args[0]
        }), 400

    if int(id) != item['story_id']:
        return jsonify({
            "message": f"updating story with wrong id: {id} != {item['story_id']}",
            "error": f"updating story with wrong id: {id} != {item['story_id']}"
        })

    # update db
    try:
        story = Story(**item)
        story.update()

        return jsonify({
            "message": f"item {id} updated",
            "data": story.json()
        })
    except Exception as e:
        return jsonify({
            "message": f"couldn't add item {item['story_id']} to db",
            "errors": e.args[0]
        }), 500
    
    
@app.route("/api/stories/<string:id>/", methods=["DELETE"], strict_slashes=False)
def delete_story_from_db(id):
    try:
        story = Story.find_by_id(id)
        comment = Comment.find_by_id(id)
        if story or (not story and not comment):
            story.delete()
            return jsonify({
                "message": f"item {id} deleted",
            })
        elif comment:
            return jsonify({
                "message": f"item {id} is a comment",
            }), 400
    except Exception as e:
        return jsonify({
            "message": f"couldn't delete item {id}",
            "errors": e.args[0]
        }), 500

@app.route("/api/stories", strict_slashes=False)
def get_stories_by_id():
    """
    fetches stories with specified ids from db;
    stories are returned in json's `data` field;
    stories contain additional field `children` with all comments in a single html;
    use as `/db/stories?ids=1,2,3`
    """
    if request.args.get("ids") is None:
        return jsonify({
            "message": (
                "could not understand the request; "
                "should be `/api/stories?ids=1,2,3`"
            ),
        }), 400

    id_list = [int(i) for i in request.args.get("ids").split(",") if i.isnumeric()]

    try:
        stories = StoryList.find_by_ids_with_children(id_list)
        # if no stories found - empty list returned but no error is raised
        return jsonify({
            "message": f"got {len(stories)} stories from db",
            "data": [story.json() for story in stories],
        })
    except Exception as e:
        return jsonify({
            "message": "couldn't get stories from db",
            "errors": e.args[0],
        }), 500

@app.route("/api/comments/<string:id>/", strict_slashes=False)
def get_comment_by_id(id):
    """
    gets comment with specified is from db, returns under json's `data` field
    """
    comment = Comment.find_by_id(id)
        
    if comment:
        return jsonify({
            "message": f"got comment {id} from db",
            "data": comment.json(),
        })
    else: 
        return jsonify({
            "message": f"item `{id}` not found",
    }), 404

@app.route("/api/comments/", methods=["POST"], strict_slashes=False)
def add_comment_to_db():
    """
    adds comment in db
    expects the following body:
    {
        "comment_id": ...,
        "author": ...,
        "unix_time": ....,
        "body": ...,
        "parent_id": ...,
    }
    """
    try:
        item = request.get_json()
    except Exception as e:
        return jsonify({
            "message": "couldn't parse request",
            "errors": e.args[0]
        })

    try:
        validate_comment(item)
    except Exception as e:
        return jsonify({
            "message": e.args[0],
            "errors": e.args[0]
        }), 400

    # check if it's already in db
    comment = Comment.find_by_id(item['comment_id'])
    if comment:
        return jsonify({
            "message": f"comment {item['comment_id']} is already in database",
        }), 400

    # post to db
    try:
        comment = Comment(**item)
        comment.add()

        return jsonify({
            "message": f"item {item['comment_id']} added to db",
            "data": comment.json()
        })
    except Exception as e:
        return jsonify({
            "message": f"couldn't add item {item['comment_id']} to db",
            "errors": e.args[0]
        }), 500

@app.route("/api/comments/<string:id>/", methods=["PUT"], strict_slashes=False)
def update_comment_in_db(id):
    """
    updates comment in db
    expects the following body:
    {
        "comment_id": ...,
        "author": ...,
        "unix_time": ....,
        "body": ...,
        "parent_id": ...,
    }
    """
    try:
        item = request.get_json()
    except Exception as e:
        return jsonify({
            "message": "couldn't parse request",
            "errors": e.args[0]
        })

    try:
        validate_comment(item)
    except Exception as e:
        return jsonify({
            "message": e.args[0],
            "errors": e.args[0]
        }), 400

    if int(id) != item['comment_id']:
        return jsonify({
            "message": f"updating comment with wrong id: {id} != {item['comment_id']}",
            "error": f"updating comment with wrong id: {id} != {item['comment_id']}"
        })

    # update db
    try:
        comment = Comment(**item)
        comment.update()

        return jsonify({
            "message": f"item {id} updated",
            "data": comment.json()
        })
    except Exception as e:
        return jsonify({
            "message": f"couldn't add item {item['comment_id']} to db",
            "errors": e.args[0]
        }), 500

@app.route("/api/comments/<string:id>/", methods=["DELETE"], strict_slashes=False)
def delete_comment_from_db(id):
    try:
        story = Story.find_by_id(id)
        comment = Comment.find_by_id(id)
        if comment or (not story and not comment):
            comment.delete()
            return jsonify({
                "message": f"item {id} deleted",
            })
        elif story:
            return jsonify({
                "message": f"item {id} is a story",
            }), 400
    except Exception as e:
        return jsonify({
            "message": f"couldn't delete item {id}",
            "errors": e.args[0]
        }), 500

@app.route("/api/comments", strict_slashes=False)
def get_comments_by_id():
    """
    fetches comments with specified ids from db;
    comments are returned in json's `data` field;
    use as `/db/comments?ids=1,2,3`
    """
    if request.args.get("ids") is None:
        return jsonify({
            "message": (
                "could not understand the request; "
                "should be `/api/comments?ids=1,2,3`"
            ),
        }), 400

    id_list = [int(i) for i in request.args.get("ids").split(",") if i.isnumeric()]

    try:
        comments = CommentList.find_by_ids(id_list)
        # if no comments found - empty list returned but no error is raised
        return jsonify({
            "message": f"got {len(comments)} comments from db",
            "data": [comment.json() for comment in comments],
        })
    except Exception as e:
        return jsonify({
            "message": "couldn't get comments from db",
            "errors": e.args[0],
        }), 500
