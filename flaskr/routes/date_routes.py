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
    """
    try:
        date = {
            "year": int(request.args.get("year")) or 2021,
            "month": int(request.args.get("month")) or 10,
            "day": int(request.args.get("day")) or 17
        }
    except Exception as e:
        return jsonify({
            "errors": e.args[0],
        }), 500

    return jsonify({
        "data": {"id": get_first_id_on_day(**date)},
        "ok": True
    })