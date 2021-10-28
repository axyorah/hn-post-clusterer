# set env vars
export FLASK_APP=flaskr
export FLASK_ENV=development

# activate python venv if venv directory exists
if [[ -d venv ]]
    then source venv/bin/activate
fi

# run app
flask init-db
flask run