import os, json, glob
from smart_open import open

from flask import (
    current_app as app,
    request,
)
from flask.json import jsonify

from flaskr.utils.form_utils import RequestParser as rqparser

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
                    "ok": True
                })
        elif ext == "json":
            with open(fname, "f") as f:
                return jsonify({
                    "message": f"read {fname} as json",
                    "data": json.load(f),
                    "ok": True
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
                "ok": True
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
            "ok": True
        })

    except Exception as e:
        print(f'[ERR: /file] {e}')
        return jsonify({
            "errors": e.args[0],
        }), 500