function addGraphFromRouteToNode(node, route) {
    const nodeRef = document.createElement('iframe');
    nodeRef.setAttribute('class', 'graph-container');
    nodeRef.setAttribute('src', route);
    node.appendChild(nodeRef);

    return nodeRef;
}

function addClusterBarPlot() {
    removeAllNodeChildren(clusterBarPlotRoot);
    addGraphFromRouteToNode(
        clusterBarPlotRoot, 
        '/dashapp/cluster-bar-plot'
    );
}

function addDailyBarPlot() {
    removeAllNodeChildren(dailyBarPlotRoot);
    addGraphFromRouteToNode(
        dailyBarPlotRoot, 
        '/dashapp/daily-bar-plot'
    );
}

function addPcaEmbeddings() {
    removeAllNodeChildren(embedPcaPlotRoot);
    addGraphFromRouteToNode(
        embedPcaPlotRoot, 
        '/dashapp/embeddings-pca-scatter-plot'
    );
}

function addPcaExplainedVariance() {
    removeAllNodeChildren(pcaExplainedVarianceRoot);
    addGraphFromRouteToNode(
        pcaExplainedVarianceRoot, 
        '/dashapp/pca-explained-variance-plot'
    );
}

function addTsneEmbeddings() {
    removeAllNodeChildren(embedTsnePlotRoot);
    addGraphFromRouteToNode(
        embedTsnePlotRoot, 
        '/dashapp/embeddings-tsne-scatter-plot'
    );

    embedTsneBtn.innerHTML = 'Prettify with t-SNE';
}

function addWordCloud( num_clusters ) {
    wordcloudInfo.innerHTML = '';

    removeAllNodeChildren(wordcloudPlotRoot);
    wordcloudPlotRef = addGraphFromRouteToNode(
        wordcloudPlotRoot,
        '/dashapp/wordcloud-plot'
    );

    const numRows = Math.ceil(num_clusters / 2);
    wordcloudPlotRef.style.height = `${100 + 200 * numRows}px`;
}

embedTsneBtn.addEventListener('click', function (res) {
    // add in-progress animation
    this.innerHTML = `${spinnerAmination} Recalculating embedding projection...`;

    const params = {
        'sender': 'tsneer',
        'perplexity': tsnePerplexityNum.value,
        'dims': tsneDimsNum.value
    }

    // calculate reduced-dim embeddings with tsne and add plot
    postData('/cluster/visuals/tsne', params)
    .then(res => checkForServerErrors(res))
    .then(res => addTsneEmbeddings())
    .catch(err => {
        console.log(err);
        embedTsneBtn.innerHTML = 'Prettify with t-SNE';
        addAlertMessage(err);
    });
})

wordcloudBtn.addEventListener('click', function (evt) {
    this.innerHTML = `${spinnerAmination} Generating WordClouds...`;

    postData('/cluster/visuals/wordcloud', {})
    .then(res => checkForServerErrors(res))
    .then(res => addWordCloud(res.data['num_clusters']))
    .then(res => {
        wordcloudBtn.innerHTML = 'Generate WordClouds';
    })
    .catch(err => {
        console.log(err);
        wordcloudBtn.innerHTML = 'Generate WordClouds';
        addAlertMessage(err);
    })
})