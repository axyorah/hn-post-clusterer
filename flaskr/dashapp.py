import os
import numpy as np
import pandas as pd
import dash
from dash.dependencies import Input, Output
import dash_table
import dash_html_components as html
import dash_core_components as dcc
import plotly.express as px

# set globals
CORPUS_DIR = 'data'
CORPUS_FNAME = os.path.join(CORPUS_DIR, 'corpus.txt')
ID_FNAME = os.path.join(CORPUS_DIR, 'ids.txt')
LABEL_FNAME = os.path.join(CORPUS_DIR, 'labels.txt')

STYLE = {
    'background_color': 'rgba(255,255,255,0.1)',
    'paper_color': 'rgb(76, 73, 82)',
    'text_color': 'white'
}

def create_dataframe():
    with open(ID_FNAME, 'r') as f:
        ids = f.read().splitlines()

    with open(LABEL_FNAME, 'r') as f:
        labels = f.read().splitlines()

    return pd.DataFrame(data={
        'id': ids,
        'label': labels
    })

def get_barplot(df):
    # Custom HTML layout
    fig = px.bar(
        x=np.unique(df['label']),
        y=[
            sum(1 for lbl in df['label'] if lbl == tar) 
            for tar in np.unique(df['label'])
        ]
    )

    fig.update_xaxes(title='Cluster Indices')
    fig.update_yaxes(title='Number of Posts')
    fig.update_layout(
        transition_duration=500,
        plot_bgcolor=STYLE['background_color'],
        paper_bgcolor=STYLE['paper_color'],
        font_color=STYLE['text_color']
    )

    return fig
    
    

def init_dashboard(server):
    """Create a Plotly Dash dashboard."""
    dash_app = dash.Dash(
        server=server,
        routes_pathname_prefix='/dashapp/',
        external_stylesheets=[
            '../static/css/style.css', 
            '../static/css/figures.css',
        ]
    )

    dash_app.layout = html.Div(
        children=[
            dcc.Graph(
                id='bar-chart',
                className='graph',
                figure=get_barplot(pd.DataFrame(data={'id':[], 'label':[]}))
            ),
            html.Button('Update', id='bar-chart-update-btn', className='graph-btn', n_clicks=0),
        ],
        id='dash-container',
    )

    @dash_app.callback(
        Output(component_id='bar-chart', component_property='figure'),
        Input(component_id='bar-chart-update-btn', component_property='n_clicks')
    )
    def update(n_clicks):
        df = create_dataframe()
        return get_barplot(df)

    return dash_app.server