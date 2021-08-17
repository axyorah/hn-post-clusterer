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
    # get relevant data
    df_bar = {
        'Cluster#': np.unique(df['label']),
        'Number of Posts': [
            sum(1 for lbl in df['label'] if lbl == tar) 
            for tar in np.unique(df['label'])
        ]
    }

    fig = px.bar(
        df_bar,
        x='Cluster#',
        y='Number of Posts'
    )

    # update style to match the rest of the flask app style
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

    dash_app.layout = html.Div([
        dcc.Location(id='url', refresh=False),
        html.Div(id='page-content')
    ])

    # --- Simple Clustering ---
    # bar plot
    simple_cluster_bar_plot = html.Div(
        children=[
            dcc.Graph(
                id='bar-plot',
                className='graph',
                figure=get_barplot(pd.DataFrame(data={'id':[], 'label':[]}))
            ),
            html.Button('Update', id='bar-plot-update-btn', className='graph-btn', n_clicks=0),
        ],
        id='dash-container',
    )

    @dash_app.callback(
        Output(component_id='bar-plot', component_property='figure'),
        Input(component_id='bar-plot-update-btn', component_property='n_clicks')
    )
    def update(n_clicks):
        df = create_dataframe()
        return get_barplot(df)

    # --- Put Everything Together ---
    # NOTE ON CALLBACKS:
    # since in the callbacks we're refering to elements that are not added to layout 
    # Dash will show a warning in console;
    # these warnings can be ignored, since we are actually adding these elements indirectly in `display_page(.)`
    # (e.g., div with id='bar-plot' is not added to layout directly, 
    # it belongs to `simple_cluster_bar_plot` html.Div object, which we return in the callback below;
    # see: https://dash.plotly.com/urls)
    @dash_app.callback(
        Output('page-content', 'children'),
        Input('url', 'pathname')
    )
    def display_page(pathname):
        if pathname == '/dashapp/simple-cluster-bar-plot':
            return simple_cluster_bar_plot
        else:
            return #TODO: error page

    return dash_app.server