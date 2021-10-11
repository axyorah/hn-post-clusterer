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

# set globals
CORPUS_DIR = 'data'
DF_FNAME = os.path.join(CORPUS_DIR, 'df.csv')

STYLE = {
    'background_color': 'rgba(255,255,255,0.1)',
    'paper_color': 'rgb(76, 73, 82)',
    'text_color': 'white'
}

def update_fig_layout(fig):
    # update style to match the rest of the flask app style
    fig.update_layout(
        transition_duration=500,
        plot_bgcolor=STYLE['background_color'],
        paper_bgcolor=STYLE['paper_color'],
        font_color=STYLE['text_color']
    )

    return fig

def read_semantic_df():
    df = pd.read_csv(DF_FNAME, sep='\t')
    df['ax-0'] = df['embedding'].map(lambda row: float(row.split(',')[0]))
    df['ax-1'] = df['embedding'].map(lambda row: float(row.split(',')[1]))
    return df

def read_tsne_df():
    df = pd.read_csv('data/df_tsne.csv', sep='\t')
    df['ax-0'] = df['embedding_tsne'].map(lambda row: float(row.split(',')[0]))
    df['ax-1'] = df['embedding_tsne'].map(lambda row: float(row.split(',')[1]))
    return df

def read_cluster_frequencies():
    fnames = [
        os.path.join('data', fname) 
        for fname in os.listdir('data') if 'freq' in fname
    ]

    frequencies = dict()
    for fname in fnames:
        res = re.search('freq_(?P<lbl>[0-9])+', fname)
        lbl = res['lbl']
        with open(fname, 'r') as f:
            frequencies[lbl] = json.load(f)

    return frequencies

def read_pca_explained_variance():
    if not os.path.isfile('data/pca.txt'):
        return pd.DataFrame({'Variance': [], 'Cummulative': []})

    with open('data/pca.txt') as f:
        variance = [float(val) for val in f.read().splitlines()]

    cummulative = list(accumulate(variance))
    return pd.DataFrame({'Variance': variance, 'Cummulative': cummulative})

def get_barplot(df):
    df_bar = df.groupby('label').count()
    df_bar['Cluster#'] = df_bar.index
    df_bar['Number of Posts'] = df_bar['id']

    fig = px.bar(
        df_bar,
        x='Cluster#',
        y='Number of Posts',
        color='Cluster#'
    )

    update_fig_layout(fig)

    return fig

def get_scatterplot(df):
    df_scat = {
        'Axis-A': df['ax-0'],
        'Axis-B': df['ax-1'],
        'id': df['id'],
        'Cluster#': df['label'],
        'title': df['title']
    }
    fig = px.scatter(
        df_scat, 
        x='Axis-A', 
        y='Axis-B', 
        color='Cluster#', 
        opacity=0.5,
        hover_data=['id', 'title']
    )

    update_fig_layout(fig)

    return fig

def get_pca_explained_variance_plot(df):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df.index.map(lambda val: val + 1),
            y=df['Cummulative'].map(lambda val: int(val * 100)),
            mode='lines',
            hovertemplate='#Dimensions: %{x}<br>Explained Variance: %{y}%',
    ))    

    fig.update_layout(
        xaxis_title='Number of PCA vectors',
        yaxis_title='% Variance Explained'
    )

    update_fig_layout(fig)

    return fig
  
def get_wordclouds(frequencies):
    wcloud = WordCloud()

    fig = make_subplots(
        rows=int(np.ceil(len(frequencies.keys())/2))+1, 
        cols=2,
        subplot_titles=[f'Cluster {i}' for i in range(len(frequencies.keys()))],
        horizontal_spacing=0.01,
        vertical_spacing=0.03
    )
    for lbl in range(len(frequencies.keys())):
        row, col = lbl // 2 + 1, lbl % 2 + 1
        cloud = wcloud.generate_from_frequencies(frequencies[str(lbl)])
        fig.add_trace(
            go.Image(
                z=cloud.to_array(), 
                hovertemplate=f'Cluster {lbl}',                
            ), 
            row=row, col=col,           
        )

    update_fig_layout(fig)
    fig.update_xaxes(visible=False) 
    fig.update_yaxes(visible=False)

    return fig

def get_wordcloud(freq):
    wcloud = WordCloud()
    cloud = wcloud.generate_from_frequencies(freq)
    return update_fig_layout(px.imshow(cloud.to_array()))

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

    # --- Semantic Clustering ---
    # bar plot
    semantic_cluster_bar_plot = get_interactive_html_graph(
        'semantic-bar-plot', 
        get_barplot(pd.DataFrame(data={'id':[], 'label':[]}))
    )

    @dash_app.callback(
        Output(component_id='semantic-bar-plot', component_property='figure'),
        Input(component_id='semantic-bar-plot-update-btn', component_property='n_clicks')
    )
    def update_semantic_bar_plot(n_clicks):
        df = pd.read_csv(DF_FNAME, sep='\t')
        return get_barplot(df)

    # 2d cluster scatter plot
    semantic_cluster_scatter_plot = get_interactive_html_graph(
        'semantic-cluster-2d',
        get_scatterplot(
            pd.DataFrame(data={'id': [], 'label': [], 'ax-0': [], 'ax-1': [], 'title': []})
        )
    )

    @dash_app.callback(
        Output(component_id='semantic-cluster-2d', component_property='figure'),
        Input(component_id='semantic-cluster-2d-update-btn', component_property='n_clicks')
    )
    def update_semantic_scatter_plot(n_clicks):
        df = read_semantic_df()
        return get_scatterplot(df)

    # explained pca variance
    pca_explained_variance_plot = get_interactive_html_graph(
        'pca-explained-variance',
        get_pca_explained_variance_plot(pd.DataFrame({'Variance': [], 'Cummulative': []}))
    )

    @dash_app.callback(
        Output(component_id='pca-explained-variance', component_property='figure'),
        Input(component_id='pca-explained-variance-update-btn', component_property='n_clicks')
    )
    def update_semantic_scatter_plot(n_clicks):
        df = read_pca_explained_variance()
        return get_pca_explained_variance_plot(df)

    # tsne
    tsne_cluster_scatter_plot = get_interactive_html_graph(
        'tsne-cluster-2d',
        get_scatterplot(
            pd.DataFrame(data={'id': [], 'label': [], 'ax-0': [], 'ax-1': [], 'title': []})
        )
    )

    @dash_app.callback(
        Output(component_id='tsne-cluster-2d', component_property='figure'),
        Input(component_id='tsne-cluster-2d-update-btn', component_property='n_clicks')
    )
    def update_tsne_scatter_plot(n_clicks):
        df = read_tsne_df()
        return get_scatterplot(df)

    # wordcloud subplots
    def get_wordcloud_dccgraph(freqs):
        return dcc.Graph(
            id='wordcloud',
            className='graph',
            figure=get_wordclouds(freqs),
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
        freqs = read_cluster_frequencies()
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
        if pathname == '/dashapp/semantic-cluster-bar-plot':
            return semantic_cluster_bar_plot
        elif pathname == '/dashapp/semantic-cluster-scatter-plot':
            return semantic_cluster_scatter_plot
        elif pathname == '/dashapp/tsne-cluster-scatter-plot':
            return tsne_cluster_scatter_plot
        elif pathname == '/dashapp/pca-explained-variance-plot':
            return pca_explained_variance_plot
        elif pathname == '/dashapp/wordcloud-plot':
            return wordcloud_container
        else:
            return #TODO: error page

    return dash_app.server