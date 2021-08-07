import os, json, datetime

from flask import Flask, render_template, redirect, url_for
from flask import request, make_response, Response

from flaskr.utils.formutils import (
    RequestParser,
    get_document_list_from_sqlite_rows,
    get_document_dict_from_sqlite_rows,
    update_display_record
)
from flaskr.utils.dbutils import (
    query_api_and_add_result_to_db,
    get_stories_with_children_from_id_range,
    get_stories_with_children_from_id_list
)
from flaskr.utils.clusterutils import (    
    serialized2kmeanslabels
)
from . import db

from flaskr.utils.datautils import (
    create_file,
    serialize_raw_documents_to_disc,
    get_stories_from_db_and_serialize_ids_and_comments
)

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )
    CORPUS_DIR = 'data'
    CORPUS_FNAME = os.path.join(CORPUS_DIR, 'corpus.txt')
    ID_FNAME = os.path.join(CORPUS_DIR, 'ids.txt')
    LABEL_FNAME = os.path.join(CORPUS_DIR, 'labels.txt')

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

    # get request parser
    rqparser = RequestParser() 

    # main page
    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")

    @app.route("/seed", methods=["POST"])
    def seed_db():
        if request.method == "POST":
            form_request = rqparser.parse(request)
            query_api_and_add_result_to_db(form_request)

        return {"ok": True}

    @app.route("/db", methods=["POST"])
    def query_db():
        if request.method == "POST":
            form_request = rqparser.parse(request)
            
            if request.form.get('sender') == 'show':
                story_rows = get_stories_with_children_from_id_range(form_request)
            elif request.form.get('sender') == 'kmeans-show':
                story_rows = get_stories_with_children_from_id_list(form_request)
            else:
                story_rows = []
            
            story_dict = get_document_dict_from_sqlite_rows(story_rows)
            
            return json.dumps(story_dict)

    @app.route("/serialize", methods=["POST"])    
    def serialize_corpus():
        if request.method == "POST":
            form_request = rqparser.parse(request)
            get_stories_from_db_and_serialize_ids_and_comments(CORPUS_DIR, form_request)
            return {"ok": True}

        return {"ok": False}

    @app.route("/simplecluster", methods=["POST"])
    def simple_cluster():
        if request.method == "POST":
            form_request = rqparser.parse(request)
            labels = serialized2kmeanslabels(
                CORPUS_FNAME, form_request["num_topics"], form_request["n_clusters"]
            )
            create_file(LABEL_FNAME)
            serialize_raw_documents_to_disc(LABEL_FNAME, labels)

            return {"ok": True}
        return {"ok": False}

    @app.route("/readfile", methods=["POST"])
    def file_reader():
        if request.method == "POST":
            form_request = rqparser.parse(request)
            with open(form_request["fname"], "r") as f:
                lines = f.read().splitlines()
            return {"contents": lines, "ok": True}

    return app
