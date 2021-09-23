from flask import current_app as app

import os, json, datetime
import requests as rq

from flask import Flask, render_template, redirect, url_for
from flask import request, make_response, Response

from flaskr.utils.formutils import (
    RequestParser,
    update_display_record
)
from flaskr.utils.dbutils import (
    query_api_and_add_result_to_db,
    get_stories_with_children_from_id_range,
    get_stories_with_children_from_id_list,
    get_document_list_from_sqlite_rows,
    get_document_dict_from_sqlite_rows,
    get_stories_from_db,
)
from flaskr.utils.clusterutils import (    
    serialized2kmeanslabels
)

from flaskr.utils.datautils import (
    create_file,
    serialize_raw_documents_to_disc,
    serialize_vectors_to_disc,
    serialize_dict_keys,
    serialize_dict_of_dicts,
    get_stories_from_db_and_serialize_ids_and_comments,
)

from flaskr.utils.semanticutils import (
    get_story_embeddings,
    #train_and_serialize_faiss_index,
    cluster_stories_with_faiss,
    project_embeddings,

)

# get request parser
rqparser = RequestParser() 

# set globals
CORPUS_DIR = 'data'
CORPUS_FNAME = os.path.join(CORPUS_DIR, 'corpus.txt')
ID_FNAME = os.path.join(CORPUS_DIR, 'ids.txt')
LABEL_FNAME = os.path.join(CORPUS_DIR, 'labels.txt')
LSI_FNAME = os.path.join(CORPUS_DIR, 'lsi.txt')

# main page
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/db/add", methods=["POST"])
def seed_db():
    if request.method == "POST":
        form_request = rqparser.parse(request)
        query_api_and_add_result_to_db(form_request)

    return {"ok": True}

@app.route("/db/get", methods=["POST"])
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

@app.route("/file/read", methods=["POST"])
def file_reader():
    if request.method == "POST":
        form_request = rqparser.parse(request)
        with open(form_request["fname"], "r") as f:
            lines = f.read().splitlines()
        return {"contents": lines, "ok": True}
    
    return {"ok": False}

@app.route("/file/write", methods=["POST"])    
def serialize_corpus():
    if request.method == "POST":
        form_request = rqparser.parse(request)
        #get_stories_from_db_and_serialize_ids_and_comments(CORPUS_DIR, form_request)
        
        stories = get_stories_from_db(form_request) # generator of story dicts

        create_file(ID_FNAME)
        create_file(CORPUS_FNAME)

        serialize_dict_keys(
            stories, keys=['story_id', 'children'], 
            key2fname={'story_id': ID_FNAME, 'children': CORPUS_FNAME}
        )
        return {"ok": True}

    return {"ok": False}

@app.route("/simplecluster", methods=["POST"])
def simple_cluster():
    if request.method == "POST":
        form_request = rqparser.parse(request)
        result = serialized2kmeanslabels(
            CORPUS_FNAME, form_request["num_topics"], form_request["n_clusters"]
        )

        create_file(LABEL_FNAME)
        create_file(LSI_FNAME)

        serialize_raw_documents_to_disc(LABEL_FNAME, result['labels'])
        serialize_vectors_to_disc(LSI_FNAME, result['lsi'])

        return {"ok": True}
    return {"ok": False}

@app.route("/semanticcluster", methods=["POST"])
def semantic_cluster():
    if request.method == "POST":
        # get stories data
        print('[INFO] Fetching Post Data from DB...')
        story_dict = rq.post('http://localhost:5000/db/get',data=request.form).json()

        # cluster stories
        print('[INFO] Generating Post Embeddings...')
        ids, embeds = get_story_embeddings(story_dict)
        print('[INFO] Clustering Posts...')
        lbls = cluster_stories_with_faiss(embeds, nclusters=15)

        # serialize result
        print('[INFO] Projecting Embeddings on 2D Plane...')
        embeds_nd = project_embeddings(embeds, n=2)
        print('[INFO] Serializing Data to Disk...')
        serialize_dict_of_dicts({
            ids[i]: {
                'id': ids[i],
                'title': story_dict[ids[i]]['title'],
                'url': story_dict[ids[i]]['url'],
                'label': lbls[i],
                'embedding': embeds_nd[i]
            } for i in range(len(ids))
        }, fname='./data/df.csv')

        # FROM CLIENT: plot cluster histogram and embeddings (PCA or tSNE)
        
        return {"ok": True}

    return {"ok": False}