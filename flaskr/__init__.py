import os, json, datetime

from flask import Flask, render_template, redirect, url_for
from flask import request, make_response, Response

from flaskr.static.python.formutils import (
    parse_seed_request, 
    parse_show_request,
    parse_simple_cluster_request,
    get_document_list_from_sqlite_rows,
    get_document_dict_from_sqlite_rows,
    update_display_record
)
from flaskr.static.python.dbutils import (
    query_api_and_add_result_to_db,
    get_requested_stories_with_children
)
from flaskr.static.python.clusterutils import (    
    serialized2kmeanslabels
)
from . import db

from flaskr.static.python.datautils import (
    get_stories_from_db_and_serialize_comments
)

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
    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")

    @app.route("/seed", methods=["POST"])
    def seed_db():
        if request.method == "POST":
            form_request = parse_seed_request(request)
            query_api_and_add_result_to_db(form_request)

        return redirect("/")

    @app.route("/db", methods=["POST"])
    def query_db():
        if request.method == "POST":
            form_request = parse_show_request(request)
            story_rows = get_requested_stories_with_children(form_request)
            story_dict = get_document_dict_from_sqlite_rows(story_rows)
            return json.dumps(story_dict)

    @app.route("/serialize", methods=["POST"])    
    def serialize_corpus():
        fname = "data/corpus.txt"

        if request.method == "POST":
            form_request = parse_show_request(request)
            get_stories_from_db_and_serialize_comments(fname, form_request)
            return {"ok": True}

        return {"ok": False}

    @app.route("/simplecluster", methods=["POST"])
    def simple_cluster():
        fname = 'data/corpus.txt'
        if request.method == "POST":
            form_request = parse_simple_cluster_request(request)
            print(form_request)
            labels = serialized2kmeanslabels(
                fname, form_request["num_topics"], form_request["n_clusters"]
            )

            for _ in range(50):
                print(next(labels))

            return {"ok": True}
        return {"ok": False}

    return app
