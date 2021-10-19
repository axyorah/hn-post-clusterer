from typing import Any, List, Dict, Set, Optional, Union

import os, json, re, datetime
import numpy as np
import scipy as sc
import pandas as pd
from itertools import accumulate

import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator

class ColorHelper:
    def __init__(self, colorscheme=px.colors.sequential.Plasma):
        self.color_hex = colorscheme
        self.color_rgb = np.array([self.hex2rgb(h) for h in self.color_hex])
        self.color_spline = sc.interpolate.CubicSpline(
            np.linspace(0,1,len(self.color_rgb)), self.color_rgb
        )

    @staticmethod
    def hex2rgb(hx):
        r,g,b = [int(hx[i:i+2],16) for i in range(1,7,2)]
        return [r,g,b]

    @staticmethod
    def rgb2hex(rgb):
        r,g,b = rgb
        return f'#{hex(r)[2:].zfill(2)}{hex(g)[2:].zfill(2)}{hex(b)[2:].zfill(2)}'

    def get_rgb_colorseq(self, n):
        return self.color_spline(np.linspace(0, 1, n)).astype(int)

    def get_hex_colorseq(self, n):
        return [self.rgb2hex(rgb) for rgb in self.get_rgb_colorseq(n)]


def update_fig_layout(fig: go.Figure) -> go.Figure:
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
    def get_cluster_barplot_df(cls) -> pd.DataFrame:
        fname = 'data/df.csv'

        if not os.path.isfile(fname):
            print(f'{fname} not found!')
            return pd.DataFrame({'Cluster': [], 'Number of Posts': []})

        df = pd.read_csv(fname, sep='\t')
        
        df_bar = df.groupby('label').count()
        df_bar['Cluster'] = df_bar.index
        df_bar['Number of Posts'] = df_bar['id']
        
        return df_bar

    @classmethod
    def get_daily_barplot_df(cls) -> pd.DataFrame:
        fname = 'data/df.csv'

        if not os.path.isfile(fname):
            print(f'{fname} not found!')
            return pd.DataFrame({'Cluster': [], 'Number of Posts': []})

        df = pd.read_csv(fname, sep='\t')
        df['unix_time'] = df['unix_time'].map(
            lambda ts: datetime.datetime.utcfromtimestamp(int(ts)).date()
        )

        df_bar = df.groupby(['unix_time', 'label']).count()
        df_bar['Date'] = df_bar.index.map(lambda t: str(t[0]))
        df_bar['Cluster'] = df_bar.index.map(lambda t: t[1])
        df_bar['Number of Posts'] = df_bar['id']

        return df_bar[['Date', 'Cluster', 'Number of Posts']]

    @classmethod
    def get_pca_embedding_df(cls) -> pd.DataFrame:
        fname = 'data/df.csv'

        if not os.path.isfile(fname):
            print('`data/df.csv` not found!')
            return pd.DataFrame({'Axis-A': [], 'Axis-B': []})

        df = pd.read_csv(fname, sep='\t')
        df['Axis-A'] = df['embedding'].map(lambda row: float(row.split(',')[0]))
        df['Axis-B'] = df['embedding'].map(lambda row: float(row.split(',')[1]))
        df.columns = [col.title() for col in df.columns]

        return df

    @classmethod
    def get_tsne_embedding_df(cls) -> pd.DataFrame:
        fname = 'data/df_tsne.csv'

        if not os.path.isfile(fname):
            print('`data/df_tsne.csv` not found!')
            return pd.DataFrame({'Axis-A': [], 'Axis-A': []})

        df = pd.read_csv(fname, sep='\t')
        df['Axis-A'] = df['embedding_tsne'].map(lambda row: float(row.split(',')[0]))
        df['Axis-B'] = df['embedding_tsne'].map(lambda row: float(row.split(',')[1]))
        df.columns = [col.title() for col in df.columns]

        return df

    @classmethod
    def get_cluster_frequencies(cls) -> Dict:
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
    def get_pca_explained_variance(cls) -> pd.DataFrame:
        fname = 'data/pca.txt'

        if not os.path.isfile(fname):
            return pd.DataFrame({'Variance': [], 'Cummulative': []})

        with open('data/pca.txt') as f:
            variance = [float(val) for val in f.read().splitlines()]

        cummulative = list(accumulate(variance))
        return pd.DataFrame({'Variance': variance, 'Cummulative': cummulative})
    
class FigureHelper:
    ch = ColorHelper(px.colors.sequential.Plasma)

    @classmethod
    def get_cluster_barplot(cls, df: pd.DataFrame, continuous: bool = True) -> go.Figure:
        n_clusters = len(df['Cluster'].unique())

        if not continuous:
            df['Cluster'] = df['Cluster'].map(str) # str vals -> discrete color scheme
    
        fig = px.bar(
            df,
            x='Cluster',
            y='Number of Posts',
            color='Cluster',
            color_discrete_sequence=cls.ch.get_hex_colorseq(n_clusters),
            category_orders={'Cluster': [str(i) for i in range(n_clusters)]}
        )

        update_fig_layout(fig)

        return fig

    @classmethod
    def get_daily_barplot(cls, df: pd.DataFrame, continuous: bool = True) -> go.Figure:
        n_clusters = len(df['Cluster'].unique())

        if not continuous:
            df['Cluster'] = df['Cluster'].map(str) # str vals -> discrete color scheme

        fig = px.bar(
            df,
            x='Date',
            y='Number of Posts',
            color='Cluster',
            color_discrete_sequence=cls.ch.get_hex_colorseq(n_clusters),
            category_orders={'Cluster': [str(i) for i in range(n_clusters)]}
        )

        update_fig_layout(fig)

        return fig

    @classmethod
    def get_scatterplot(cls, df: pd.DataFrame, continuous: bool = True) -> go.Figure:
        #df['Label'] = df['Label'].astype(str) # str vals -> discrete color scheme (only works for plotly.express)

        fig = go.Figure()
        if continuous:
            fig.add_trace(
                go.Scatter(
                    x=df['Axis-A'],
                    y=df['Axis-B'],
                    opacity=0.7,
                    mode='markers',
                    marker={'color': df['Label']},
                    customdata=df[['Id', 'Title','Label']],
                    hovertemplate='Id: %{customdata[0]}<br>Title: %{customdata[1]}<br>Cluster: %{customdata[2]}'
            ))
        else:   
            for i in range(max(df['Label']) + 1):
                df_cluster = df[df['Label'] == i]
                fig.add_trace(
                    go.Scatter(
                        x=df_cluster['Axis-A'],
                        y=df_cluster['Axis-B'],
                        opacity=0.7,
                        mode='markers',
                        customdata=df_cluster[['Id', 'Title','Label']],
                        hovertemplate='Id: %{customdata[0]}<br>Title: %{customdata[1]}<br>Cluster: %{customdata[2]}',
                        name=str(i)
                    )
                )             

        fig.update_layout(
            xaxis_title='Axis-A',
            yaxis_title='Axis-B'
        )

        update_fig_layout(fig)

        return fig
    
    @classmethod
    def get_pca_explained_variance_plot(cls, df: pd.DataFrame) -> go.Figure:
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
    def get_wordclouds(cls, frequencies: Dict) -> go.Figure:
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