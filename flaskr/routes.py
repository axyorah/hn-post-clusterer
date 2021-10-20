import os, json, glob
from smart_open import open

from flask import current_app as app
from flask import Flask, render_template, redirect, url_for
from flask import request, make_response, Response
from flask.json import jsonify

from flaskr.utils.formutils import RequestParser as rqparser
from flaskr.utils.dbutils import DBHelper
from flaskr.utils.generalutils import BatchedPipeliner
from flaskr.utils.nlputils import ClusterFrequencyCounter
from flaskr.utils.clusterutils import TSNEer

# set globals
CORPUS_DIR = 'data'
DF_FNAME = os.path.join(CORPUS_DIR, 'df.csv')
DFT_FNAME = os.path.join(CORPUS_DIR, 'df_tsne.csv')
PCA_FNAME = os.path.join(CORPUS_DIR, 'pca.txt')

# main page
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# RESTful db routes for single story
@app.route("/db/story/<string:id>")
def get_story(id):
    dbhelper = DBHelper()

    story_rows = dbhelper.query("SELECT * FROM story WHERE story_id = ?", [id])
        
    if story_rows is not None:
        return jsonify({
            "code": 200,
            "ok": True,
            "message": "got story from db",
            "data": dbhelper.story_rows_to_dicts(story_rows)[int(id)],
            "path": "/db/story"
        })
    else: 
        return jsonify({
            "code": 500,
            "ok": False,
            "message": f"item {id} not found",
            "path": "/db/story"
    })

@app.route("/db/story", methods=["POST"])
def post_story():
    pass

@app.route("/db/story/<string:id>", methods=["DELETE"])
def delete_story(id):
    pass

@app.route("/db/story/<string:id>", methods=["PUT"])
def update_story(id):
    pass

# RESTful db routes for multiple stories
@app.route("/db/stories")
def get_stories():

    # should be called as "/db/items?id=1,2,3"
    id_list = [int(i) for i in request.args.get("id").split(",")]

    if id_list:
        dbhelper = DBHelper()

        query = f"""
        {dbhelper.story_pattern_without_where}
        WHERE s.story_id IN ({", ".join("?" for _ in id_list)});
        """
        story_rows = dbhelper.query(query, id_list)
        return jsonify({
            "code": 200,
            "ok": True,
            "message": "got stories from db",
            "data": dbhelper.story_rows_to_dicts(story_rows),
            "path": "/db/stories"
        })

    else:
        return jsonify({
            "code": 500,
            "ok": False,
            "message": "could not understand the request; should be `/db/stories?id=1,2,3`",
            "path": "/db/stories"
        })


# RESTful db routes for multiple items (stories + comments)
@app.route("/db/items", methods=["POST"])
def post_items():
    form_request = rqparser.parse(request)
    
    dbhelper = DBHelper()
    dbhelper.query_api_and_add_result_to_db(form_request)

    return jsonify({
        "code": 200,
        "ok": True,
        "message": "added new entries to database",
        "path": "/db/items"
    })

@app.route("/db/items", methods=["DELETE"])
def delete_items():
    pass

@app.route("/db/items", methods=["PUT"])
def update_items():
    pass

# RESTful file routes
@app.route("/file/<string:fname>")
def read_file(fname):
    # checks if present
    # checks ext
    # reads as txt, csv (with header) or json depending on ext
    pass

@app.route("/file/<string:fname>", methods=["DELETE"])
def delete_file(fname):
    # checks if exists
    # check if data file (txt, csv, json)
    # deletes if data file
    pass



@app.route("/db/add", methods=["POST"])
def seed_db():
    if request.method == "POST":
        try:
            form_request = rqparser.parse(request)

            dbhelper = DBHelper()
            dbhelper.query_api_and_add_result_to_db(form_request)

            return jsonify({
                "code": 200,
                "ok": True,
                "message": "added new entries to database",
                "path": "/db/add"
            })
        except Exception as e:
            print(f'[ERR: /db/add] {e}')
            return jsonify({
                "errors": e.args[0],
                "code": 500,
                "path": "/db/add",
                "ok": False
            }), 500



@app.route("/db/get", methods=["POST"])
def query_db():
    if request.method == "POST":
        try:
            form_request = rqparser.parse(request)

            dbhelper = DBHelper()            
            if request.form.get('sender') == 'db-lister':
                story_dict = dbhelper.get_stories_with_children_from_id_list(form_request)
            else:
                story_dict = {}
            
            return jsonify({
                "code": 200,
                "ok": True,
                "message": f"fetched stories from db",
                "data": story_dict,
                "path": "/db/get"
            })
        except Exception as e:
            print(f'[ERR: /db/get] {e}')
            return jsonify({
                "errors": e.args[0],
                "code": 500,
                "path": "/db/get",
                "ok": False
            }), 500

@app.route("/file/readtxt", methods=["POST"])
def txt_reader():
    if request.method == "POST":
        try:
            form_request = rqparser.parse(request)
            with open(form_request["fname"], "r") as f:
                lines = f.read().splitlines()
            return jsonify({
                "code": 200,
                "ok": True,
                "message": f"read {form_request['fname']}",
                "data": lines,
                "path": "/file/readtxt"
            })
        except Exception as e:
            print(f'[ERR: /file/readtxt] {e}')
            return jsonify({
                "errors": e.args[0],
                "code": 500,
                "path": "/file/readtxt",
                "ok": False
            }), 500

@app.route("/file/readcsv", methods=["POST"])
def csv_reader():
    if request.method == "POST":
        try:
            form_request = rqparser.parse(request)
            with open(form_request["fname"], "r") as f:
                lines = f.read().splitlines()
        
            idx2field = {i:name for i,name in enumerate(lines[0].split("\t"))}
            contents = {field: [] for field in idx2field.values()}
            for line in lines[1:]:
                for i,val in enumerate(line.split("\t")):
                    contents[idx2field[i]].append(val)
        
            return jsonify({
                "code": 200,
                "ok": True,
                "message": f"read {form_request['fname']} as dataframe",
                "data": contents,
                "path": "/file/readcsv"
            })
        except Exception as e:
            print(f'[ERR: /file/readcsv] {e}')
            return jsonify({
                "errors": e.args[0],
                "code": 500,
                "path": "/file/readcsv",
                "ok": False
            }), 500

@app.route("/file/delete", methods=["POST"])
def delete_serialized():
    if request.method == "POST":
        try:
            form_request = rqparser.parse(request)
        
            print(f"[INFO] deleting...", end=" ")        
            for pattern in form_request["fnames"]:
                # only data-files can be deleted!
                ext = pattern.split('.')[-1]
                if ext not in ["txt", "csv", "json"]:
                    continue
                fnames = glob.glob(pattern)
                for fname in fnames:
                    print(fname, end=", ")
                    os.remove(fname)
            print("")                
        
            return jsonify({
                "code": 200,
                "ok": True,
                "message": f"deleted files: {form_request['fnames']}",
                "path": "/file/delete"
            })
        except Exception as e:
            print(f'[ERR: /file/delete] {e}')
            return jsonify({
                "errors": e.args[0],
                "code": 500,
                "path": "/file/delete",
                "ok": False
            }), 500

@app.route("/cluster/run", methods=["POST"])
def cluster_posts_and_serialize_results():
    if request.method == "POST":
        try:
            request_form = rqparser.parse(request)

            pipe = BatchedPipeliner(request_form)
            stories = pipe.get_story_batches()
            embeddings = pipe.get_embedding_batches(stories)
            embeddings = pipe.standardize_embedding_batches(embeddings)
            embeddings = pipe.reduce_embedding_dimensionality(embeddings, n_dims=100)
            pipe.cluster_story_batches(embeddings)
            pipe.serialize_result(fname=DF_FNAME)
            pipe.serialize_pca_explained_variance(fname=PCA_FNAME)

            # FROM CLIENT: plot cluster histogram and embeddings (PCA or tSNE)
        
            return jsonify({
                "code": 200,
                "ok": True,
                "message": f"ran clustering pipeline and serialized results",
                "path": "/cluster/run"
            })
        except Exception as e:
            print(f'[ERR: /cluster/run] {e}')
            return jsonify({
                "errors": e.args[0],
                "code": 500,
                "path": "/cluster/run",
                "ok": False
            }), 500

@app.route("/cluster/visuals/wordcloud", methods=["POST"])
def serialize_data_for_wordcloud():

    if request.method == "POST":

        try:
            counter = ClusterFrequencyCounter()
            counter.count_serialized_cluster_frequencies(DF_FNAME)
            counter.serialize_cluster_frequencies(data_dir='data', min_freq=2)

            return jsonify({
                "code": 200,
                "ok": True,
                "message": f"calculated token frequencies required for wordcloud and serialized result",
                "data": {"num_clusters": len(counter.frequencies.keys())},
                "path": "/cluster/visuals/wordcloud"
            })

        except Exception as e:
            print(f'[ERR: /cluster/visuals/wordcloud] {e}')
            return jsonify({
                "errors": e.args[0],
                "code": 500,
                "path": "/cluster/visuals/wordcloud",
                "ok": False
            }), 500

@app.route("/cluster/visuals/tsne", methods=["POST"])
def serialize_data_for_tsne():
    if request.method == "POST":
        try:    
            form_request = rqparser.parse(request)
            perplexity = min(max(form_request['perplexity'], 5), 50)
            dims = min(max(form_request['dims'], 2), 100)

            tsneer = TSNEer(
                random_state=42, 
                n_components=2, 
                perplexity=perplexity
            )
            embeddings = tsneer.read_embedding_from_csv(
                DF_FNAME, 
                dims=dims
            )
            tsneer.reduce_embedding_dimensions(embeddings)
            tsneer.serialize_results(DFT_FNAME)

            return jsonify({
                "code": 200,
                "ok": True,
                "message": f"calculated 2D embedding visualization with t-SNE",
                "path": "/cluster/visuals/tsne"
            })
            
        except Exception as e:
            print(f'[ERR: /cluster/visuals/tsne] {e}')
            return jsonify({
                "errors": e.args[0],
                "code": 500,
                "path": "/cluster/visuals/tsne",
                "ok": False
            }), 500
