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


def validate_comment(item):
    schema = {
        "comment_id": {int},
        "author": {str},
        "unix_time": {int},
        "body": {str, type(None)},
        "parent_id": {int},
    }

    validate(item, schema, item_type='comment')

@app.route("/api/comments/<string:id>/", strict_slashes=False)
def get_comment_by_id(id):
    """
    gets comment with specified is from db, returns under json's `data` field
    """
    comment = Comment.find_by_id(id)
        
    if comment:
        print(f"got comment {id} from db")
        return jsonify({
            "message": f"got comment {id} from db",
            "data": comment.json(),
        }), 200
    else:
        print(f"item `{id}` not found")
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
        print(e.args[0])
        return jsonify({
            "message": "couldn't parse request",
            "errors": e.args[0]
        }), 400

    try:
        validate_comment(item)
    except Exception as e:
        print(e.args[0])
        return jsonify({
            "message": e.args[0],
            "errors": e.args[0]
        }), 400

    # check if it's already in db
    comment = Comment.find_by_id(item['comment_id'])
    if comment:
        print(f"comment {item['comment_id']} is already in database")
        return jsonify({
            "message": f"comment {item['comment_id']} is already in database",
        }), 400

    # post to db
    try:
        comment = Comment(**item)
        comment.add()
        print(f"item {item['comment_id']} added to db")
        return jsonify({
            "message": f"item {item['comment_id']} added to db",
            "data": comment.json()
        }), 201
    except Exception as e:
        print(e.args[0])
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
        print(e.args[0])
        return jsonify({
            "message": "couldn't parse request",
            "errors": e.args[0]
        }), 200

    try:
        validate_comment(item)
    except Exception as e:
        print(e.args[0])
        return jsonify({
            "message": e.args[0],
            "errors": e.args[0]
        }), 400

    if int(id) != item['comment_id']:
        print(f"updating comment with wrong id: {id} != {item['comment_id']}")
        return jsonify({
            "message": f"updating comment with wrong id: {id} != {item['comment_id']}",
            "error": f"updating comment with wrong id: {id} != {item['comment_id']}"
        }), 400

    # update db
    try:
        comment = Comment(**item)
        comment.update()

        print(f"item {id} updated")
        return jsonify({
            "message": f"item {id} updated",
            "data": comment.json()
        }), 200
    except Exception as e:
        print(e.args[0])
        return jsonify({
            "message": f"couldn't add item {item['comment_id']} to db",
            "errors": e.args[0]
        }), 500

@app.route("/api/comments/<string:id>/", methods=["DELETE"], strict_slashes=False)
def delete_comment_from_db(id):
    try:
        story = Story.find_by_id(id)
        comment = Comment.find_by_id(id)
        if comment:
            comment.delete()
            print(f"item {id} deleted")
            return jsonify({
                "message": f"item {id} deleted",
            }), 200
        elif story:
            print(f"item {id} is a story")
            return jsonify({
                "message": f"item {id} is a story",
            }), 400
        elif (not story) and (not comment):
            print(f"item {id} not in db")
            return jsonify({
                "message": f"item {id} not in db",
            }), 200
    except Exception as e:
        print(e.args[0])
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
        print("could not understand the request; ")
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
        print(f"got {len(comments)} comments from db")
        return jsonify({
            "message": f"got {len(comments)} comments from db",
            "data": [comment.json() for comment in comments],
        }), 200
    except Exception as e:
        print(e.args[0])
        return jsonify({
            "message": "couldn't get comments from db",
            "errors": e.args[0],
        }), 500
