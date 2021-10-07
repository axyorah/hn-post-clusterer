from flask import current_app as app

import os, json, datetime
from collections import defaultdict
import bs4 as bs
import requests as rq
from smart_open import open

from flask import Flask, render_template, redirect, url_for
from flask import request, make_response, Response

from flaskr.utils.formutils import RequestParser
from flaskr.utils.dbutils import DBHelper
from flaskr.utils.nlputils import Tokenizer
from flaskr.utils.generalutils import BatchedPipeliner

from flaskr.utils.ioutils import (
    create_file,
    serialize_dict_keys,
)


# get request parser
rqparser = RequestParser() 

# set globals
CORPUS_DIR = 'data'
CORPUS_FNAME = os.path.join(CORPUS_DIR, 'corpus.txt')
ID_FNAME = os.path.join(CORPUS_DIR, 'ids.txt')
LABEL_FNAME = os.path.join(CORPUS_DIR, 'labels.txt')
LSI_FNAME = os.path.join(CORPUS_DIR, 'lsi.txt')
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

@app.route("/file/write", methods=["POST"])    
def serialize_corpus():
    if request.method == "POST":
        form_request = rqparser.parse(request)
        dbhelper = DBHelper()
        
        stories = dbhelper.yield_story_from_id_range(form_request)# generator of story dicts

        create_file(ID_FNAME)
        create_file(CORPUS_FNAME)

        serialize_dict_keys(
            stories, keys=['story_id', 'children'], 
            key2fname={'story_id': ID_FNAME, 'children': CORPUS_FNAME}
        )
        return {"ok": True}

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
def generate_wordcloud():
    if True:
        print('hello wordcloud!!!')

        dbhelper = DBHelper()
        tokenizer = Tokenizer()
        frequencies = dict()

        # read records line by line
        # and calculate token frequencies for story comments of each label
        for i,line in enumerate(open(DF_FNAME)):
            if not i:
                field2idx = {field:idx for idx,field in enumerate(line.split('\t'))}
                continue

            vals = line.split('\t')
            story_id = vals[field2idx['id']]
            label = vals[field2idx['label']]

            story = dbhelper.get_story_with_children_by_id(story_id)
            comments = bs.BeautifulSoup(story['children'], 'lxml').get_text(separator=' ')
            tokens = tokenizer.tokenize(comments)

            for token in tokens:
                if not tokens:
                    continue
                if label not in frequencies.keys():
                    frequencies[label] = defaultdict(int)
                frequencies[label][token] += 1

        # write frequencies for each label
        print(frequencies.keys())
        for lbl in frequencies.keys():
            with open(f'data/freq_{lbl}.json', 'w') as f:
                json.dump({ 
                    key:val for key,val in frequencies[lbl].items()
                    if val > 1
                }, f)

        return {"ok": True}
