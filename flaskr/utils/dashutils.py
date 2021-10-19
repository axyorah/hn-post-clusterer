import os, json, re, datetime
import numpy as np
import pandas as pd
from itertools import accumulate

import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator

def update_fig_layout(fig):
    STYLE = {
        'background_color': 'rgba(255,255,255,0.1)',
        'paper_color': 'rgb(76, 73, 82)',
        'text_color': 'white'
    }

    # update style to match the rest of the flask app style
    fig.update_layout(
        transition_duration=500,
        plot_bgcolor=STYLE['background_color'],
        paper_bgcolor=STYLE['paper_color'],
        font_color=STYLE['text_color']
    )

    return fig

class DataHelper:
    @classmethod
    def get_cluster_barplot_df(cls):
        fname = 'data/df.csv'

        if not os.path.isfile(fname):
            print(f'{fname} not found!')
            return pd.DataFrame({'Cluster#': [], 'Number of Posts': []})

        df = pd.read_csv(fname, sep='\t')
        # return df
        df_bar = df.groupby('label').count()
        df_bar['Cluster#'] = df_bar.index
        df_bar['Number of Posts'] = df_bar['id']
        
        return df_bar

    @classmethod
    def get_daily_barplot_df(cls):
        fname = 'data/df.csv'

        df = pd.read_csv(fname, sep='\t')
        df['unix_time'] = df['unix_time'].map(
            lambda ts: datetime.datetime.utcfromtimestamp(int(ts)).date()
        )

        df_bar = df.groupby(['unix_time', 'label']).count()
        df_bar['Date'] = df_bar.index.map(lambda t: str(t[0]))
        df_bar['Cluster#'] = df_bar.index.map(lambda t: t[1])
        df_bar['Number of Posts'] = df_bar['id']

        return df_bar[['Date', 'Cluster#', 'Number of Posts']]

    @classmethod
    def get_pca_embedding_df(cls):
        fname = 'data/df.csv'

        if not os.path.isfile(fname):
            print('`data/df.csv` not found!')
            return pd.DataFrame({'ax-0': [], 'ax-1': []})

        df = pd.read_csv(fname, sep='\t')
        df['ax-0'] = df['embedding'].map(lambda row: float(row.split(',')[0]))
        df['ax-1'] = df['embedding'].map(lambda row: float(row.split(',')[1]))
        return df

    @classmethod
    def get_tsne_embedding_df(cls):
        fname = 'data/df_tsne.csv'

        if not os.path.isfile(fname):
            print('`data/df_tsne.csv` not found!')
            return pd.DataFrame({'ax-0': [], 'ax-1': []})

        df = pd.read_csv(fname, sep='\t')
        df['ax-0'] = df['embedding_tsne'].map(lambda row: float(row.split(',')[0]))
        df['ax-1'] = df['embedding_tsne'].map(lambda row: float(row.split(',')[1]))
        return df

    @classmethod
    def get_cluster_frequencies(cls):
        fnames = [
            os.path.join('data', fname) 
            for fname in os.listdir('data') if 'freq' in fname
        ]

        if not fnames:
            print('frequency files not found!')
            return dict()

        frequencies = dict()
        for fname in fnames:
            res = re.search('freq_(?P<lbl>[0-9])+', fname)
            lbl = res['lbl']
            with open(fname, 'r') as f:
                frequencies[lbl] = json.load(f)

        return frequencies

    @classmethod
    def get_pca_explained_variance(cls):
        fname = 'data/pca.txt'

        if not os.path.isfile(fname):
            return pd.DataFrame({'Variance': [], 'Cummulative': []})

        with open('data/pca.txt') as f:
            variance = [float(val) for val in f.read().splitlines()]

        cummulative = list(accumulate(variance))
        return pd.DataFrame({'Variance': variance, 'Cummulative': cummulative})

    
class FigureHelper:
    @classmethod
    def get_cluster_barplot(cls, df):
    
        fig = px.bar(
            df,
            x='Cluster#',
            y='Number of Posts',
            color='Cluster#'
        )

        update_fig_layout(fig)

        return fig

    @classmethod
    def get_daily_barplot(cls, df):

        #df['Cluster#'] = df['Cluster#'].map(str) # str vals -> discrete color scheme

        fig = px.bar(
            df,
            x='Date',
            y='Number of Posts',
            color='Cluster#',
        )

        update_fig_layout(fig)

        return fig

    @classmethod
    def get_scatterplot(cls, df):
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df['ax-0'],
                y=df['ax-1'],
                opacity=0.7,
                mode='markers',
                marker_color=df['label'],
                customdata=df[['id', 'title','label']],
                hovertemplate='Id: %{customdata[0]}<br>Title: %{customdata[1]}<br>Cluster: %{customdata[2]}'
        ))

        fig.update_layout(
            xaxis_title='Axis-A',
            yaxis_title='Axis-B'
        )

        update_fig_layout(fig)

        return fig
    
    @classmethod
    def get_pca_explained_variance_plot(cls, df):
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df.index.map(lambda val: val + 1),
                y=df['Cummulative'].map(lambda val: np.round(val * 100,2)),
                mode='lines',
                hovertemplate='#Dimensions: %{x}<br>Explained Variance: %{y}%',
        ))    

        fig.update_layout(
            xaxis_title='Number of PCA vectors (dimensions)',
            yaxis_title='% Variance Explained'
        )

        update_fig_layout(fig)

        return fig

    @classmethod
    def get_wordclouds(cls, frequencies):
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


