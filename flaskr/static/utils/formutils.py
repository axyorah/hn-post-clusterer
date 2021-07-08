from flaskr.db import get_db
import requests as rq
import datetime
import json

def parse_form(request):
    req = request.form
    form = dict()

    names = [
        ('begin_ts', 'begin-date-range'),
        ('end_ts', 'end-date-range'),
        ('begin_id', 'begin-id-range'),
        ('end_id', 'end-id-range')
    ]

    for form_name, html_name in names:
        try:
            form[form_name] = int(req.get(html_name))
        except:
            raise NameError(f'Error accessing element with id "{html_name}"')
        
    return form

def update_display_record(display, form):
    begin_date = datetime.datetime.fromtimestamp(form.get('begin_ts') // 1000)
    end_date = datetime.datetime.fromtimestamp(form.get('end_ts') // 1000)

    display.begin_date = f'{begin_date.year}/{begin_date.month}/{begin_date.day}'
    display.end_date = f'{end_date.year}/{end_date.month}/{end_date.day}'

    display.begin_id = form.get('begin_id')
    display.end_id = form.get('end_id')

