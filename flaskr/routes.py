import os, json
from smart_open import open

from flask import current_app as app
from flask import Flask, render_template, redirect, url_for
from flask import request, make_response, Response

from flaskr.utils.formutils import RequestParser
from flaskr.utils.dbutils import DBHelper
from flaskr.utils.generalutils import BatchedPipeliner
from flaskr.utils.nlputils import ClusterFrequencyCounter
from flaskr.utils.clusterutils import TSNEer


# get request parser
rqparser = RequestParser() 

# set globals
CORPUS_DIR = 'data'
DF_FNAME = os.path.join(CORPUS_DIR, 'df.csv')

# main page
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/db/add", methods=["POST"])
def seed_db():
    if request.method == "POST":
        form_request = rqparser.parse(request)
        dbhelper = DBHelper()

        dbhelper.query_api_and_add_result_to_db(form_request)

    return {"ok": True}

@app.route("/db/get", methods=["POST"])
def query_db():
    if request.method == "POST":
        form_request = rqparser.parse(request)
        dbhelper = DBHelper()
            
        if request.form.get('sender') == 'show':
            story_dict = dbhelper.get_stories_with_children_from_id_range(form_request)
        elif request.form.get('sender') == 'kmeans-show':
            story_dict = dbhelper.get_stories_with_children_from_id_list(form_request)
        else:
            story_dict = {}
            
        return json.dumps(story_dict)

@app.route("/file/read", methods=["POST"])
def file_reader():
    if request.method == "POST":
        form_request = rqparser.parse(request)
        with open(form_request["fname"], "r") as f:
            lines = f.read().splitlines()
        return {"contents": lines, "ok": True}
    
    return {"ok": False}

@app.route("/file/readcsv", methods=["POST"])
def csv_reader():
    if request.method == "POST":
        form_request = rqparser.parse(request)
        with open(form_request["fname"], "r") as f:
            lines = f.read().splitlines()
        
        idx2field = {i:name for i,name in enumerate(lines[0].split("\t"))}
        contents = {field: [] for field in idx2field.values()}
        for line in lines[1:]:
            for i,val in enumerate(line.split("\t")):
                contents[idx2field[i]].append(val)
        
        return { "contents": contents, "ok": True } 

    return {"ok": False}

@app.route("/semanticcluster", methods=["POST"])
def semantic_cluster():
    if request.method == "POST":

        pipe = BatchedPipeliner(request)
        stories = pipe.get_story_batches()
        embeddings = pipe.get_embedding_batches(stories)
        embeddings = pipe.standardize_embedding_batches(embeddings)
        embeddings = pipe.reduce_embedding_dimensionality(embeddings, n_dims=100)
        pipe.cluster_story_batches(embeddings)
        pipe.serialize_result(fname=DF_FNAME)

        # FROM CLIENT: plot cluster histogram and embeddings (PCA or tSNE)
        
        return {"ok": True}

    return {"ok": False}

@app.route("/wordcloud", methods=["GET", "POST"])
def serialize_data_for_wordcloud():

    counter = ClusterFrequencyCounter()
    counter.count_serialized_cluster_frequencies(DF_FNAME)
    counter.serialize_cluster_frequencies(data_dir='data', min_freq=2)

    return {"ok": True}

@app.route("/tsne", methods=["GET", "POST"])
def embeddings2tsne():

    print('hello tsne!')

    tsneer = TSNEer(random_state=42, n_components=2)
    embeddings = tsneer.read_embedding_from_csv(DF_FNAME)
    tsneer.reduce_embedding_dimensions(embeddings)
    tsneer.serialize_results('data/df_tsne.csv')

    return {"ok": True}


