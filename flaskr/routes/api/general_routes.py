from flask import (
    current_app as app,
    request,
)
from flask.json import jsonify

from flaskr.models.story import (
    Story,
    StoryList,
)
from flaskr.models.comment import (
    Comment,
    CommentList,
)

def validate(item, schema, item_type='item', optional={}):
    for field in schema:
        if field not in item and field not in optional:
            raise NameError(f"{item_type} is missing `{field}` field")
        if field in item and type(item[field]) not in schema[field]:
            raise TypeError(
                f"{item_type} field `{field}` is expected to be of {schema[field]} type, "
                f"got {type(item[field])}"
            )

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