from flask import (
    current_app as app,
    request,
)
from flask.json import jsonify

from flaskr.utils.form_utils import RequestParser as rqparser

from flaskr.models.item import (
    Item,
    ItemList,
)

from flaskr.routes.api.general_routes import validate


def validate_item(item):
    schema = {
        "item_id": {int},
        "type": {str},
    }

    validate(item, schema, item_type='item')

@app.route("/api/items/<string:id>/", strict_slashes=False)
def get_item_by_id(id):
    """
    gets item with specified id from db, returns under json's `data` field
    """
    try:
        item = Item.find_by_id(id)
        
        if item:
            print(f"got item {id} from db")
            return jsonify({
                "message": f"got item `{id}` from db",
                "data": item.json(),
            }), 200
        else:
            print(f"item `{id}` not found")
            return jsonify({
                "message": f"item `{id}` not found",
        }), 404
    except Exception as e:
        print(e.args[0])
        return jsonify({
            "messsage": f"couldn't get item `{id}`",
            "errors": e.args[0]
        }), 500

@app.route("/api/items", strict_slashes=False)
def get_items_by_id():
    """
    gets items with specified id from db, returns under json's `data` field
    """
    if request.args.get("ids") is None:
        print("could not understand the request; ")
        return jsonify({
            "message": (
                "could not understand the request; "
                "should be `/api/items?ids=1,2,3`"
            ),
        }), 400

    id_list = [int(i) for i in request.args.get("ids").split(",") if i.isnumeric()]

    if id_list:
        try:
            items = ItemList.find_by_ids(id_list)
            # if no items found - empty list returned but no error is raised
            print(f"got {len(items)} items from db")
            return jsonify({
                "message": f"got {len(items)} items from db",
                "data": [item.json() for item in items],
            }), 200
        except Exception as e:
            print(e.args[0])
            return jsonify({
                "message": "couldn't get items from db",
                "errors": e.args[0],
            }), 500
    else:
        msg = (
            "items with speicifed ids not found "
            "(should be `/api/items?ids=1,2,3`)"
        )
        return jsonify({
            "message": msg,
            "errors": msg
        }), 404
