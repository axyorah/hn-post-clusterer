from flask import (
    current_app as app,
    request,
)
from flask.json import jsonify

from flaskr.utils.form_utils import RequestParser as rqparser
from flaskr.utils.db_utils import (
    Story,
    Comment,
    StoryList,
    CommentList    
)
from flaskr.utils.hn_utils import (
    query_api,
    translate_response_api2schema,
    query_hn_and_add_result_to_db
)

# general db stuff
@app.route("/db/stats")
def get_db_stats():
    """
    returns basic stats about stories and comments in db under `data` field:
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
            "data": {
                "stories": StoryList.stats(),
                "comments": CommentList.stats()
            },
            "ok": True
        })
    except Exception as e:
        return jsonify({
            "message": "couldn't get basic stats on stories and comments",
            "errors": e.args[0]
        }), 500

# db routes for single story
@app.route("/db/story/<string:id>")
def get_story(id):
    """
    gets story with specified id from db, returns under json's `data` field
    """
    story = Story.find_by_id(id)        
    if story:
        return jsonify({
            "message": "got story from db",
            "data": story.json(),
            "ok": True
        })
    else: 
        return jsonify({
            "message": f"item `{id}` not found",
        }), 404

@app.route("/db/story/<string:id>", methods=["POST"])
def post_story(id):
    """
    fetches story with specified if from hn and posts it in db
    """
    story = Story.find_by_id(id)        
    if story:
        return jsonify({
            "message": "story is already in a database",
        }), 400
    else:
        try:
            item = query_api(id)
            if item is None:
                return jsonify({
                    "message": f"couldn't fetch item with id `{id}` from hn"
                }), 400
            if item.get("type") != "story":
                return jsonify({
                    "message": f"item `{id}` is not hn story"
                }), 400
            item = translate_response_api2schema(item)
            story = Story(**item)
            story.add()
            return jsonify({
                "message": f"item {id} added to db",
                "ok": True
            })
        except Exception as e:
            return jsonify({
                "message": f"couldn't fetch item {id} from hn and add it to db",
                "errors": e.args[0]
            }), 500

@app.route("/db/story/<string:id>", methods=["DELETE"])
def delete_story(id):
    try:
        story = Story.find_by_id(id)
        comment = Comment.find_by_id(id)
        if story or (not story and not comment):
            story.delete()
            return jsonify({
                "message": f"item {id} deleted",
                "ok": True
            })
        elif comment:
            return jsonify({
                "message": f"item {id} is a comment"
            }), 400
    except Exception as e:
        return jsonify({
            "message": f"couldn't delete item {id}",
            "errors": e.args[0]
        })


@app.route("/db/story/<string:id>", methods=["PUT"])
def update_story(id):
    try:
        story = Story.find_by_id(id)
        item = query_api(id)
        if item.get("type") != "story":
            return jsonify({
                "message": f"item {id} is not a story"
            }), 400
        item = translate_response_api2schema(item)    
        if story:        
            story = Story(**item)
            story.update()
            return jsonify({
                "message": f"story {id} updated",
                "data": story.json(),
                "ok": True
            })
        else:
            story = Story(**item)
            story.add()
            return jsonify({
                "message": f"story {id} added",
                "data": story.json(),
                "ok": True
            })
    except Exception as e:
        return jsonify({
            "message": f"couldn't add/update story {id}",
            "errors": e.args[0]
        }), 500

## db routes for single comment
@app.route("/db/comment/<string:id>")
def get_comment(id):
    """
    gets comment with specified is from db, returns under json's `data` field
    """
    comment = Comment.find_by_id(id)
        
    if comment:
        return jsonify({
            "message": "got comment from db",
            "data": comment.json(),
            "ok": True
        })
    else: 
        return jsonify({
            "message": f"item `{id}` not found",
    }), 404

# db routes for multiple stories
@app.route("/db/stories")
def get_stories_with_children():
    """
    fetches stories with specified ids from db;
    stories are returned in json's `data` field;
    stories contain additional field `children` with all comments in a single html;
    use as `/db/stories?ids=1,2,3`
    """
    # TODO: should be parsed properly
    if request.args.get("ids") is None:
        return jsonify({
            "message": "could not understand the request; should be `/db/stories?ids=1,2,3`",
        }), 400

    id_list = [int(i) for i in request.args.get("ids").split(",") if i.isnumeric()]

    if id_list:
        try:
            stories = StoryList.find_by_ids_with_children(id_list)
            # if no stories found - empty list returned but no error is raised
            return jsonify({
                "message": "got stories from db",
                "data": [story.json() for story in stories],
                "ok": True
            })
        except Exception as e:
            return jsonify({
                "message": "couldn't get stories from db",
                "errors": e.args[0],
            }), 500

    else:
        return jsonify({
            "message": "stories with speicifed ids not found",
        }), 404

# db routes for multiple items (stories + comments)
@app.route("/db/items", methods=["POST"])
def post_items():
    """
    fetches items (stories and comments) within spcified id range from hn
    and adds them to db;
    request body should be:
    {
        "sender": "db-seeder",
        "seed-id-begin-range": <min item id>,
        "seed-id-end-range": <max item id>
    }
    """
    try:
        form_request = rqparser.parse(request)
    
        query_hn_and_add_result_to_db(form_request)

        return jsonify({
            "message": "updated database with new entries",
            "ok": True
        })
    except (KeyError, ValueError) as e:
        return jsonify({
            "message": "couldn't get items from hn and add them to database",
            "errors": e.args[0]
        }), 400
    except Exception as e:
        print(e.args)
        return jsonify({
            "message": "couldn't get items from hn and add them to database",
            "errors": e.args[0],
        }), 500

@app.route("/db/items", methods=["DELETE"])
def delete_items():
    return jsonify({
        "message": f"this route is currently unavailable",
    }), 500

@app.route("/db/items", methods=["PUT"])
def update_items():
    return jsonify({
        "message": f"this route is currently unavailable",
    }), 500