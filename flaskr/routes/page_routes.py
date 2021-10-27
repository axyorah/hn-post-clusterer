from flask import (
    current_app as app,
    render_template,
)

# main page
@app.route("/", methods=["GET"])
def index():
    """renders index page"""
    return render_template("index.html")