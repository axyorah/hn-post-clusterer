import os, json, datetime

from flask import Flask, render_template, redirect, url_for
from flask import request, make_response, Response

from flaskr.static.utils.formutils import (
    parse_form, 
    update_display_record
)
from flaskr.static.utils.dbutils import (
    query_api_and_add_result_to_db,
    get_requested_stories_with_children
)
from . import db

class RecordDisplay:
    pass

display = RecordDisplay()

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # register db with the app
    db.init_app(app)

    # main page
    @app.route('/', methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            form_request = parse_form(request)
            update_display_record(display, form_request)
            query_api_and_add_result_to_db(form_request)

            stories = get_requested_stories_with_children(form_request)
            print(len(stories))
        else:
            stories = None
        return render_template('index.html', stories=stories)

    return app