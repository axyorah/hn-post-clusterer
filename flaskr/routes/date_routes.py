import os

from flask import (
    current_app as app,
    request,
)
from flask.json import jsonify

from flaskr.utils.form_utils import RequestParser as rqparser
from flaskr.utils.date_utils import get_first_id_on_day

# time and date routes
@app.route("/time/first_id_on")
def get_first_hn_it_on_date():
    """
    use as "/time/first_id_on?year=2021&month=12&day=31
    both month and day use 1-based indexing:
      jan -> 1, feb -> 2, ... dec -> 12
    """
    try:
        date = {
            "year": int(request.args.get("year")) or 2021,
            "month": int(request.args.get("month")) or 10,
            "day": int(request.args.get("day")) or 17
        }
    except Exception as e:
        return jsonify({
            "message": (
                "couldn't parse the query string, should be " +
                "`/time/first_id_on?year=2021&month=12&day=31`"
            ),
            "errors": e.args[0],
        }), 400

    try:
        first_id = get_first_id_on_day(**date)
        return jsonify({
            "data": {"id": first_id},
            "ok": True
        })
    except ValueError as e:
        return jsonify({
            "message": "date out of range",
            "errors": e.args[0]
        }), 400
    except Exception as e:
        return jsonify({
            "message": f"couldn't fetch anything from {date}",
            "errors": e.args[0]
        }), 500