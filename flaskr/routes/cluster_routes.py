import os

from flask import (
    current_app as app,
    request,
)
from flask.json import jsonify

from flaskr.utils.form_utils import RequestParser as rqparser
from flaskr.utils.general_utils import BatchedPipeliner
from flaskr.utils.nlp_utils import ClusterFrequencyCounter
from flaskr.utils.cluster_utils import TSNEer

# set globals
CORPUS_DIR = 'data'
DF_FNAME = os.path.join(CORPUS_DIR, 'df.csv')
DFT_FNAME = os.path.join(CORPUS_DIR, 'df_tsne.csv')
PCA_FNAME = os.path.join(CORPUS_DIR, 'pca.txt')


# cluster routes
@app.route("/cluster/new", methods=["POST"])
def cluster_posts_and_serialize_results():
    """
    runs preprocessing and clustering pipeline and serializes results on disk;
    request body should be:
    {
        "sender": "clusterer",
        "show-ts-begin-range": <min item timestamp in seconds>, 
        "show-ts-end-range": <max item timestamp in seconds>,
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
            "ok": True
        })
    except Exception as e:
        print(f'[ERR: /cluster/new] {e}')
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
            "ok": True
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
            "ok": True
        })
            
    except Exception as e:
        print(f'[ERR: /cluster/visuals/tsne] {e}')
        return jsonify({
            "errors": e.args[0],
        }), 500
