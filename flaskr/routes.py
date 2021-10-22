import os, json, glob
from smart_open import open

from flask import current_app as app
from flask import Flask, render_template, redirect, url_for
from flask import request, make_response, Response
from flask.json import jsonify

from flaskr.utils.form_utils import RequestParser as rqparser
from flaskr.utils.db_utils import (
    DBHelper as dbh,
    query_hn_and_add_result_to_db
)
from flaskr.utils.general_utils import BatchedPipeliner
from flaskr.utils.nlp_utils import ClusterFrequencyCounter
from flaskr.utils.cluster_utils import TSNEer

# set globals
CORPUS_DIR = 'data'
DF_FNAME = os.path.join(CORPUS_DIR, 'df.csv')
DFT_FNAME = os.path.join(CORPUS_DIR, 'df_tsne.csv')
PCA_FNAME = os.path.join(CORPUS_DIR, 'pca.txt')

# main page
@app.route("/", methods=["GET"])
def index():
    """renders index page"""
    return render_template("index.html")

# db routes for single story
@app.route("/db/story/<string:id>")
def get_story(id):
    """
    gets story with specified is from db, returns under json's `data` field
    """
    story_rows = dbh.get_query("SELECT * FROM story WHERE story_id = ?", [id])
        
    if story_rows:
        return jsonify({
            "code": 200,
            "ok": True,
            "message": "got story from db",
            "data": dbh.rows2dicts(story_rows)[0],
            "path": "/db/story/<id>"
        })
    else: 
        return jsonify({
            "code": 500,
            "ok": False,
            "message": f"item {id} not found",
            "path": "/db/story/<id>"
        }), 500

@app.route("/db/story/<string:id>", methods=["POST"])
def post_story():
    return jsonify({
        "code": 500,
        "ok": False,
        "message": f"this route is currently unavailable",
        "path": "/db/story/<id>"
    }), 500

@app.route("/db/story/<string:id>", methods=["DELETE"])
def delete_story(id):
    return jsonify({
        "code": 500,
        "ok": False,
        "message": f"this route is currently unavailable",
        "path": "/db/story/<id>"
    }), 500

@app.route("/db/story/<string:id>", methods=["PUT"])
def update_story(id):
    return jsonify({
        "code": 500,
        "ok": False,
        "message": f"this route is currently unavailable",
        "path": "/db/story/<id>"
    }), 500

## db routes for single comment
@app.route("/db/comment/<string:id>")
def get_comment(id):
    """
    gets comment with specified is from db, returns under json's `data` field
    """
    comment_rows = dbh.get_query("SELECT * FROM comment WHERE comment_id = ?", [id])
        
    if comment_rows:
        print(comment_rows)
        return jsonify({
            "code": 200,
            "ok": True,
            "message": "got comment from db",
            "data": dbh.rows2dicts(comment_rows)[0],
            "path": "/db/comment/<id>"
        })
    else: 
        return jsonify({
            "code": 404,
            "ok": False,
            "message": f"item {id} not found",
            "path": "/db/comment/<id>"
    }), 404

# db routes for multiple stories
@app.route("/db/stories")
def get_stories():
    """
    fetches stories with specified ids from db;
    stories are returned in json's `data` field;
    use as `/db/stories?ids=1,2,3`
    """
    # TODO: should be parsed properly
    id_list = [int(i) for i in request.args.get("ids").split(",") if i.isnumeric()]

    if id_list:
        try:
            query = f"""
                {dbh.STORY_PATTERN_WITHOUT_WHERE}
                WHERE s.story_id IN ({", ".join("?" for _ in id_list)});
            """
            story_rows = dbh.get_query(query, id_list)
            return jsonify({
                "code": 200,
                "ok": True,
                "message": "got stories from db",
                "data": dbh.rows2dicts(story_rows),
                "path": "/db/stories"
            })
        except Exception as e:
            return jsonify({
                "code": 500,
                "ok": True,
                "message": "couldn't get stories from db",
                "errors": e.args[0],
                "path": "/db/stories"
            }), 500

    else:
        return jsonify({
            "code": 400,
            "ok": False,
            "message": "could not understand the request; should be `/db/stories?ids=1,2,3`",
            "path": "/db/stories"
        }), 400

# db routes for multiple items (stories + comments)
@app.route("/db/items", methods=["POST"])
def post_items():
    """
    fetches items (stories and comments) within spcified id range from hn
    and adds them to db;
    request body should be:
    {
        "sender": "db-seeder",
        "seed-id-begin-range": <min item id>,
        "seed-id-end-range": <max item id>
    }
    """
    try:
        form_request = rqparser.parse(request)
    
        query_hn_and_add_result_to_db(form_request)

        return jsonify({
            "code": 200,
            "ok": True,
            "message": "added new entries to database",
            "path": "/db/items"
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "ok": False,
            "message": "couldn't get items from hn and add them to db",
            "errors": e.args[0],
            "path": "/db/items"
        }), 500

@app.route("/db/items", methods=["DELETE"])
def delete_items():
    return jsonify({
        "code": 500,
        "ok": False,
        "message": f"this route is currently unavailable",
        "path": "/db/items"
    }), 500

@app.route("/db/items", methods=["PUT"])
def update_items():
    return jsonify({
        "code": 500,
        "ok": False,
        "message": f"this route is currently unavailable",
        "path": "/db/items"
    }), 500

# file routes
@app.route("/file")
def read_file():
    """ 
    reads file with specified fname and returns contents in json's `data` field;
    use as: /file?fname=<fname> 
    """
    fname = request.args.get("fname")

    # checks if present   
    if not os.path.isfile(fname):
        return jsonify({
            "code": 404,
            "ok": False,
            "message": f"file {fname} not found",
            "path": "/file"
        }), 404

    # checks ext
    ext = fname.split(".")[-1]
    if ext not in ["txt", "csv", "json"]:
        return jsonify({
            "code": 400,
            "ok": False,
            "message": f"file extension should be one of: txt, csv or json",
            "path": "/file"
        }), 400

    # reads as txt, csv (with header) or json depending on ext
    try:    
        if ext == "txt":
            with open(fname, "r") as f:
                lines = f.read().splitlines()
                return jsonify({
                    "code": 200,
                    "ok": True,
                    "message": f"read {fname} as txt",
                    "data": lines,
                    "path": "/file"
                })
        elif ext == "json":
            with open(fname, "f") as f:
                return jsonify({
                    "code": 200,
                    "ok": True,
                    "message": f"read {fname} as json",
                    "data": json.load(f),
                    "path": "/file"
                })
        elif ext == "csv":
            with open(fname, "r") as f:
                lines = f.read().splitlines()

            idx2field = {i:name for i,name in enumerate(lines[0].split("\t"))}
            contents = {field: [] for field in idx2field.values()}
            for line in lines[1:]:
                for i,val in enumerate(line.split("\t")):
                    contents[idx2field[i]].append(val)
        
            return jsonify({
                "code": 200,
                "ok": True,
                "message": f"read {fname} as dataframe",
                "data": contents,
                "path": "/file"
            })
    except Exception as e:
        print(f'[ERR: /file] {e}')
        return jsonify({
            "errors": e.args[0],
            "code": 500,
            "path": "/file",
            "ok": False
        }), 500

@app.route("/file", methods=["DELETE"])
def delete_file():
    """
    deletes all {txt, csv, json} files from `data` subdir that match specified pattern;
    request body should be:
    {
        "sender": "deleter",
        "fname": <fname pattern>
    }
    `fname` can be a pattern, e.g., `data/*.txt`
    """
    fname_pattern = request.get_json().get("fname")
    if fname_pattern is None:
        return jsonify({
            "code": 400,
            "ok": False,
            "message": f"specify file to be deleted at `fname` key",
            "path": "/file"
        }), 400

    # checks ext
    ext = fname_pattern.split(".")[-1]
    if ext not in ["txt", "csv", "json"]:
        return jsonify({
            "code": 400,
            "ok": False,
            "message": f"file extension should be one of: txt, csv or json",
            "path": "/file"
        }), 400

    # check location
    subdir = fname_pattern.split("/")[0]
    if subdir != "data":
        return jsonify({
            "code": 400,
            "ok": False,
            "message": f"only files located in `data` subdir can be deleted",
            "path": "/file"
        }), 400

    # delete all files that match pattern
    try:
        fnames = glob.glob(fname_pattern)
        for fname in fnames:
            print(fname, end=", ")
            os.remove(fname)
        print("")
        
        return jsonify({
            "code": 200,
            "ok": True,
            "message": f"deleted files: {','.join(fnames)}",
            "path": "/file"
        })

    except Exception as e:
        print(f'[ERR: /file] {e}')
        return jsonify({
            "errors": e.args[0],
            "code": 500,
            "path": "/file",
            "ok": False
        }), 500

# cluster routes
@app.route("/cluster/run", methods=["POST"])
def cluster_posts_and_serialize_results():
    """
    runs preprocessing and clustering pipeline and serializes results on disk;
    request body should be:
    {
        "sender": "clusterer",
        "show-id-begin-range": <min item id>, 
        "show-id-end-range": <max item id>,
        "show-comm-begin-range": <min number of comments>,
        "show-comm-end-range": <max number of comment>,
        "show-score-begin-range": <min score>,
        "show-score-end-range": <max score>,
        "num-clusters": <number of clusters>
    }
    """
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
    """
    requires `data/df.csv` to be present - it is used to read story labels;
    collects all comments or all stories for each cluster,
    calculates token frequencies for each cluster 
    and serializes result to disk
    so that it can be used by dashapp;
    """
    try:
        counter = ClusterFrequencyCounter()
        counter.count_serialized_cluster_frequencies(DF_FNAME)
        counter.serialize_cluster_frequencies(data_dir=CORPUS_DIR, min_freq=2)

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
    """
    requires `data/df.csv` to be present - it is used to read pca embeddings;
    reads pca embeddings, calculates tsne embeddings 
    and serializes them to disk (`data/df_tsne.csv`);
    request body shoud be:
    {
        "sender": "tsneer",
        "perplexity": <tsne perplexity>,
        "dims": <number of pca vectors to use as input>
    }
    """
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
