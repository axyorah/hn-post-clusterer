from typing import List, Dict, Tuple, Optional, Union, Generator
from types import FunctionType

from sklearn.decomposition import PCA, IncrementalPCA

from flaskr.utils.cluster_utils import (
    copy_and_measure_generator
)

class Event(list):
    def __call__(self, *args, **kwargs):
        for item in self:
            item(*args, **kwargs)

class Observable:
    def __init__(self):
        self.change = Event()

class Observer:
    def __init__(self, observable: Observable):
        self.observable = observable

class Serializer(Observer):
    def __init__(self, observable: Observable):
        super().__init__(observable)

    def add(self, fun: FunctionType) -> None:
        self.observable.change.append(fun)

class ClustererSerializer(Serializer):
    def __init__(self, clusterer: 'Clusterer'):
        super().__init__(clusterer)
        self.clusterer = clusterer

    def serialize_clustering_result(self, fname: str) -> FunctionType:
        """
        clusterer change event is called as `Clusterer().change(name, val)`;
        however we also need to specify `fname` for serialization;
        `this` high order fun takes `fname` as arg and returns 
        a function handle for fun that is called as `fun(name, val)`
        which complies with `Clusterer().change(.)`;
        we can `add` this inner fun as a trigger for serializer as follows:
        ```
        clusterer = Clusterer()
        serializer = ClustererSerializer(clusterer)
        serializer.add(serializer.serialize_clustering_result(fname))
        ```
        (recall that `serializer.serialize_clustering_result(fname)` 
        returns fun handle for fun that takes (name, val) as args)
        """
        def helper(name, val):
            if name == 'labels':
                print('LABEL SERIALIZER TRIGGERED')
                self._serialize_clustering_result(fname)
        return helper

    def serialize_pca_explained_variance(self, fname: str) -> FunctionType:
        """
        clusterer change event is called as `Clusterer().change(name, val)`;
        however we also need to specify `fname` for serialization;
        `this` high order fun takes `fname` as arg and returns 
        a function handle for fun that is called as `fun(name, val)`
        which complies with `Clusterer().change(.)`;
        we can `add` this inner fun as a trigger for serializer as follows:
        ```
        clusterer = Clusterer()
        serializer = ClustererSerializer(clusterer)
        serializer.add(serializer.serialize_pca_explained_variance(fname))
        ```
        (recall that `serializer.serialize_pca_explained_variance(fname)` 
        returns fun handle for fun that takes (name, val) as args)
        """
        def helper(name, val):
            if name == 'lowdim_embeddings':
                print('PCA SERIALIZER TRIGGERED')
                self._serialize_pca_explained_variance(fname)
        return helper

    def _serialize_clustering_result(self, fname: str = './data/df.csv') -> bool:
        # check if all the necessary data is available
        if self.clusterer.kmeans is None or self.clusterer._embeddings is None:
            raise RuntimeError(
                'There is nothing to serialize yet. ' +\
                'You must obtain and cluster embeddings first!'
            )

        print('[INFO] copying stories...')
        story_batches, (l,_) = copy_and_measure_generator(self.clusterer._stories, num_copies=2)
        self.clusterer._stories = story_batches[0]
        if not l:
            raise RuntimeError(
                'Story generator is empty! ' +\
                'Consider rerunning .get_story_batches()'
            )
        
        print('[INFO] copying embeddings...')
        emb_batches, (l,_) = copy_and_measure_generator(self.clusterer._embeddings, num_copies=2)
        self.clusterer._embeddings = emb_batches[0]
        if not l:
            raise RuntimeError(
                'Embedding generator is empty! ' +\
                'Consider rerunning .get_embedding_batches()'
            )

        if not self.clusterer.labels:
            raise RuntimeError(
                'There are no labels to serialize! ' +\
                'Consider running .cluster_story_batches()'
            )     

        # --- project to low-dim space if it wasn't done already ---
        # embeds were not projected to low-dim space if num_stories < n_pca_dim
        if self.clusterer.pca is None:
            n_dims = min(
                self.clusterer._num_stories, 
                self.clusterer._n_pca_dims
            )
            self.clusterer.pca = PCA(n_components=n_dims)
            self.clusterer.pca.fit(self.kmeans.cluster_centers_)
            print(f'[INFO] pca dim set to {n_dims}')

        # --- serialize ---
        print(f'[INFO] serializing result to {fname}...')
        fields = ['id', 'title', 'url', 'unix_time', 'label', 'embedding']
        with open(fname, 'w') as f:
            f.write('\t'.join(fields) + '\n')

        for st_batch, emb_batch, lbl_batch in zip(
            story_batches[1], emb_batches[1], self.clusterer._labels
        ):
            # reduce dimensionality with pca if it hasn't already been done
            # otehrwise take n_dims first eigenvecs
            emb_proj = self.clusterer.pca.transform(emb_batch) \
                if emb_batch.shape[1] > self.clusterer._n_pca_dims \
                else emb_batch
            
            for st, emb, lbl in zip(st_batch, emb_proj, lbl_batch):
                with open(fname, 'a') as f:
                    f.write(
                        '\t'.join([
                            str(st.get('story_id')),
                            st.get('title') or '',
                            st.get('url') or '', # nullable
                            str(st.get('unix_time')),
                            str(lbl),
                            ','.join(str(val) for val in emb)
                        ]) + '\n'
                    )

        return True

    def _serialize_pca_explained_variance(self, fname: int = 'data/pca.txt') -> bool:
        if self.clusterer.pca is None:
            return False
        
        with open(fname, 'w') as f:
            f.write('\n'.join(
                str(val) for val in self.clusterer.pca.explained_variance_ratio_
            ))

        return True