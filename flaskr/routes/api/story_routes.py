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

from flaskr.routes.api.general_routes import validate


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
    optional = {"url"}

    validate(item, schema, item_type='story', optional=optional)



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
        "url": ...[OPTIONAL],
        "score": ...,
        "title": ...,
        "num_comments": ...,
        "deleted": ...[OPTIONAL],
        "dead": ...[OPTIONAL],
    }
    """
    try:
        item = request.get_json()
    except Exception as e:
        return jsonify({
            "message": "couldn't parse request",
            "errors": e.args[0]
        }), 400

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
        }), 201
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
        print(item)
    except Exception as e:
        print(e.args[0])
        return jsonify({
            "message": "couldn't parse request",
            "errors": e.args[0]
        }), 400

    try:
        validate_story(item)
    except Exception as e:
        print(e.args[0])
        return jsonify({
            "message": e.args[0],
            "errors": e.args[0]
        }), 400

    if int(id) != item['story_id']:
        return jsonify({
            "message": f"updating story with wrong id: {id} != {item['story_id']}",
            "error": f"updating story with wrong id: {id} != {item['story_id']}"
        }), 400

    # update db
    try:
        story = Story(**item)
        story.update()

        return jsonify({
            "message": f"item {id} updated",
            "data": story.json()
        }), 200
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
            }), 200
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
        }), 200
    except Exception as e:
        return jsonify({
            "message": "couldn't get stories from db",
            "errors": e.args[0],
        }), 500

