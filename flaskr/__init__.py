import os
from flask import Flask
from . import db

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )
    
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance dir exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # create data dir if not present
    os.makedirs('data', exist_ok=True)

    # register db with the app
    db.init_app(app)

    with app.app_context():
        from flaskr.routes import (
            page_routes,
            io_routes,
            cluster_routes
        )
        from flaskr.routes.api import (
            general_routes,
            story_routes,
            comment_routes,
            item_routes
        )
        from flaskr.dashapp import init_dashboard
        app = init_dashboard(app)
        return app
