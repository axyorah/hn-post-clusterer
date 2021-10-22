import os, re, json
import numpy as np
from itertools import accumulate
import pandas as pd
import dash
from dash.dependencies import Input, Output
from dash import dash_table
from dash import html
from dash import dcc
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator

from flaskr.utils.dash_utils import (
    DataHelper as data,
    FigureHelper as figs
)

def get_interactive_html_graph(graph_id, init_figure):
    return html.Div(
        children=[
            dcc.Graph(
                id=graph_id,
                className='graph',
                figure=init_figure
            ),
            html.Button('Update', id=f'{graph_id}-update-btn', className='graph-btn', n_clicks=0),
        ],
        id=f'{graph_id}-container',
    )
        
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

    # --- Figures ---
    # cluster count bar plot
    cluster_bar_plot = get_interactive_html_graph(
        'cluster-bar-plot', 
        figs.get_cluster_barplot(pd.DataFrame(data={'Cluster':[], 'Number of Posts':[]}))
    )

    @dash_app.callback(
        Output(component_id='cluster-bar-plot', component_property='figure'),
        Input(component_id='cluster-bar-plot-update-btn', component_property='n_clicks')
    )
    def update_cluster_bar_plot(n_clicks):
        df = data.get_cluster_barplot_df()
        return figs.get_cluster_barplot(df, continuous=False)

    # daily cluster count bar plot
    daily_bar_plot = get_interactive_html_graph(
        'daily-bar-plot',
        figs.get_daily_barplot(pd.DataFrame(data={'Cluster': [], 'Number of Posts': [], 'Date': []}))
    )

    @dash_app.callback(
        Output(component_id='daily-bar-plot', component_property='figure'),
        Input(component_id='daily-bar-plot-update-btn', component_property='n_clicks')
    )
    def update_daily_bar_plot(n_clicks):
        df = data.get_daily_barplot_df()
        return figs.get_daily_barplot(df, continuous=False)

    # 2d cluster scatter plot
    pca_cluster_scatter_plot = get_interactive_html_graph(
        'pca-cluster-2d',
        figs.get_scatterplot(
            pd.DataFrame(data={'Id': [], 'Label': [], 'Title':[], 'Axis-A': [], 'Axis-B': []})
        )
    )

    @dash_app.callback(
        Output(component_id='pca-cluster-2d', component_property='figure'),
        Input(component_id='pca-cluster-2d-update-btn', component_property='n_clicks')
    )
    def update_pca_scatter_plot(n_clicks):
        df = data.get_pca_embedding_df()
        return figs.get_scatterplot(df, continuous=True)

    # explained pca variance
    pca_explained_variance_plot = get_interactive_html_graph(
        'pca-explained-variance',
        figs.get_pca_explained_variance_plot(pd.DataFrame({'Variance': [], 'Cummulative': []}))
    )

    @dash_app.callback(
        Output(component_id='pca-explained-variance', component_property='figure'),
        Input(component_id='pca-explained-variance-update-btn', component_property='n_clicks')
    )
    def update_semantic_scatter_plot(n_clicks):
        df = data.get_pca_explained_variance()
        return figs.get_pca_explained_variance_plot(df)

    # tsne
    tsne_cluster_scatter_plot = get_interactive_html_graph(
        'tsne-cluster-2d',
        figs.get_scatterplot(
            pd.DataFrame(data={'Id': [], 'Label': [], 'Title':[], 'Axis-A': [], 'Axis-B': []})
        )
    )

    @dash_app.callback(
        Output(component_id='tsne-cluster-2d', component_property='figure'),
        Input(component_id='tsne-cluster-2d-update-btn', component_property='n_clicks')
    )
    def update_tsne_scatter_plot(n_clicks):
        df = data.get_tsne_embedding_df()
        return figs.get_scatterplot(df, continuous=True)

    # wordcloud subplots
    def get_wordcloud_dccgraph(freqs):
        return dcc.Graph(
            id='wordcloud',
            className='graph',
            figure=figs.get_wordclouds(freqs),
            style={'height': f'{100 + 200 * int(np.ceil(len(freqs.keys()) / 2))}px'}
        )

    def get_wordcloud_button():
        return html.Button(
            'Update', 
            id='wordcloud-plot-update-btn', 
            className='graph-btn', 
            n_clicks=0
        )

    wordcloud_container = html.Div(
        id='wordcloud-container',
        children = [ 'Generating WordClouds...', get_wordcloud_button() ],
    )

    @dash_app.callback(
        Output(component_id='wordcloud-container', component_property='children'),
        Input(component_id='wordcloud-plot-update-btn', component_property='n_clicks')
    )
    def update_wordcloud_style(n_clicks):
        freqs = data.get_cluster_frequencies()
        return [
            get_wordcloud_dccgraph(freqs),
            get_wordcloud_button()
        ]


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
        if pathname == '/dashapp/cluster-bar-plot':
            return cluster_bar_plot
        elif pathname == '/dashapp/daily-bar-plot':
            return daily_bar_plot
        elif pathname == '/dashapp/embeddings-pca-scatter-plot':
            return pca_cluster_scatter_plot
        elif pathname == '/dashapp/embeddings-tsne-scatter-plot':
            return tsne_cluster_scatter_plot
        elif pathname == '/dashapp/pca-explained-variance-plot':
            return pca_explained_variance_plot
        elif pathname == '/dashapp/wordcloud-plot':
            return wordcloud_container
        else:
            return #TODO: error page

    return dash_app.server