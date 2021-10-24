import os, json, glob
from smart_open import open

from flask import (
    current_app as app,
    render_template,
    request,
)
from flask.json import jsonify

from flaskr.utils.form_utils import RequestParser as rqparser
from flaskr.utils.db_utils import (
    DBHelper as dbh,
    query_hn_and_add_result_to_db
)
from flaskr.utils.general_utils import BatchedPipeliner
from flaskr.utils.nlp_utils import ClusterFrequencyCounter
from flaskr.utils.cluster_utils import TSNEer
from flaskr.utils.date_utils import get_first_id_on_day

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
            "message": "got story from db",
            "data": dbh.rows2dicts(story_rows)[0],
        })
    else: 
        return jsonify({
            "message": f"item {id} not found",
        }), 404

@app.route("/db/story/<string:id>", methods=["POST"])
def post_story():
    return jsonify({
        "message": f"this route is currently unavailable",
    }), 500

@app.route("/db/story/<string:id>", methods=["DELETE"])
def delete_story(id):
    return jsonify({
        "message": f"this route is currently unavailable",
    }), 500

@app.route("/db/story/<string:id>", methods=["PUT"])
def update_story(id):
    return jsonify({
        "message": f"this route is currently unavailable",
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
            "message": "got comment from db",
            "data": dbh.rows2dicts(comment_rows)[0],
        })
    else: 
        return jsonify({
            "message": f"item {id} not found",
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
    if request.args.get("ids") is None:
        return jsonify({
            "message": "could not understand the request; should be `/db/stories?ids=1,2,3`",
        }), 400

    id_list = [int(i) for i in request.args.get("ids").split(",") if i.isnumeric()]

    if id_list:
        try:
            query = f"""
                {dbh.STORY_PATTERN_WITHOUT_WHERE}
                WHERE s.story_id IN ({", ".join("?" for _ in id_list)});
            """
            story_rows = dbh.get_query(query, id_list)
            return jsonify({
                "message": "got stories from db",
                "data": dbh.rows2dicts(story_rows),
            })
        except Exception as e:
            return jsonify({
                "message": "couldn't get stories from db",
                "errors": e.args[0],
            }), 500

    else:
        return jsonify({
            "message": "stories with speicifed ids not found",
        }), 404
        

@app.route("/db/stories/stats")
def get_stories_stats():
    """
    returns basic stats about stories in db under `data` field:
    {
        "num": <number of stories in db>,
        "min": <min story id>,
        "max": <max story id>
    }
    """
    num_query = "SELECT COUNT(*) as num FROM story;"
    min_query = "SELECT MIN(story_id) as min FROM story;"
    max_query = "SELECT MAX(story_id) as max FROM story;"
    
    try:
        result = {
            "num": dbh.get_query(num_query, [])[0].__getitem__("num"),
            "min": dbh.get_query(min_query, [])[0].__getitem__("min"),
            "max": dbh.get_query(max_query, [])[0].__getitem__("max")
        }
    except Exception as e:
        return jsonify({
            "message": "couldn't get story stats",
            "errors": e.args[0],
        })

    return jsonify({
        "data": result,
    })

@app.route("/db/comments/stats")
def get_comments_stats():
    """
    returns basic stats about comments in db under `data` field:
    {
        "num": <number of comments in db>,
        "min": <min comment id>,
        "max": <max comment id>
    }
    """
    num_query = "SELECT COUNT(*) as num FROM comment;"
    min_query = "SELECT MIN(comment_id) as min FROM comment;"
    max_query = "SELECT MAX(comment_id) as max FROM comment;"
    
    try:
        result = {
            "num": dbh.get_query(num_query, [])[0].__getitem__("num"),
            "min": dbh.get_query(min_query, [])[0].__getitem__("min"),
            "max": dbh.get_query(max_query, [])[0].__getitem__("max")
        }
    except Exception as e:
        return jsonify({
            "message": "couldn't get comment stats",
            "errors": e.args[0],
        }), 500

    return jsonify({
        "data": result,
    })

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
            "message": "updated database with new entries",
        })
    except Exception as e:
        return jsonify({
            "message": "couldn't get items from hn and add them to database",
            "errors": e.args[0],
        }), 500

@app.route("/db/items", methods=["DELETE"])
def delete_items():
    return jsonify({
        "message": f"this route is currently unavailable",
    }), 500

@app.route("/db/items", methods=["PUT"])
def update_items():
    return jsonify({
        "message": f"this route is currently unavailable",
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
            "message": f"file {fname} not found",
        }), 404

    # checks ext
    ext = fname.split(".")[-1]
    if ext not in ["txt", "csv", "json"]:
        return jsonify({
            "message": f"file extension should be one of: txt, csv or json",
        }), 400

    # reads as txt, csv (with header) or json depending on ext
    try:    
        if ext == "txt":
            with open(fname, "r") as f:
                lines = f.read().splitlines()
                return jsonify({
                    "message": f"read {fname} as txt",
                    "data": lines,
                })
        elif ext == "json":
            with open(fname, "f") as f:
                return jsonify({
                    "message": f"read {fname} as json",
                    "data": json.load(f),
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
                "message": f"read {fname} as dataframe",
                "data": contents,
            })
    except Exception as e:
        print(f'[ERR: /file] {e}')
        return jsonify({
            "errors": e.args[0],
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
            "message": f"specify file to be deleted at `fname` key",
        }), 400

    # checks ext
    ext = fname_pattern.split(".")[-1]
    if ext not in ["txt", "csv", "json"]:
        return jsonify({
            "message": f"file extension should be one of: txt, csv or json",
        }), 400

    # check location
    subdir = fname_pattern.split("/")[0]
    if subdir != "data":
        return jsonify({
            "message": f"only files located in `data` subdir can be deleted",
        }), 400

    # delete all files that match pattern
    try:
        fnames = glob.glob(fname_pattern)
        for fname in fnames:
            print(fname, end=", ")
            os.remove(fname)
        print("")
        
        return jsonify({
            "message": f"deleted files: {','.join(fnames)}",
        })

    except Exception as e:
        print(f'[ERR: /file] {e}')
        return jsonify({
            "errors": e.args[0],
        }), 500

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
    })

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
            "message": f"ran clustering pipeline and serialized results",
        })
    except Exception as e:
        print(f'[ERR: /cluster/run] {e}')
        return jsonify({
            "errors": e.args[0],
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
            "message": f"calculated token frequencies required for wordcloud and serialized result",
            "data": {"num_clusters": len(counter.frequencies.keys())},
        })

    except Exception as e:
        print(f'[ERR: /cluster/visuals/wordcloud] {e}')
        return jsonify({
            "errors": e.args[0],
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
            "message": f"calculated 2D embedding visualization with t-SNE and serialized results",
        })
            
    except Exception as e:
        print(f'[ERR: /cluster/visuals/tsne] {e}')
        return jsonify({
            "errors": e.args[0],
        }), 500
