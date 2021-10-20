function removeAllNodeChildren(node) {
    while (node.children.length) {
        node.removeChild(node.lastChild);
    }
}

function addGraphFromRouteToNode(node, route) {
    const nodeRef = document.createElement('iframe');
    nodeRef.setAttribute('class', 'graph-container');
    nodeRef.setAttribute('src', route);
    node.appendChild(nodeRef);

    return nodeRef;
}

function reset() {
    // clear old data files
    const deletable = {
        "sender": "deleter",
        "fnames": "data/df.csv,data/df_tsne.csv,data/pca.txt,data/freq_*.json"
    }
    postData('/file/delete', deletable)
    .then(res => checkForServerErrors(res))
    .catch(err => {
        console.log(err);
        addAlertMessage(err);
    });

    // clear figures
    removeAllNodeChildren(clusterBarPlotRoot);
    removeAllNodeChildren(dailyBarPlotRoot);
    removeAllNodeChildren(embedPcaPlotRoot);
    removeAllNodeChildren(embedTsnePlotRoot);
    removeAllNodeChildren(wordcloudPlotRoot);

    // clear alerts
    removeAllNodeChildren(alertRoot);

    // make figures, select, and table invisible
    figureRoot.style.display = "none";
    selectRoot.style.display = "none";
    tableRoot.style.display = "none";
}

function addClusterBarPlot() {
    removeAllNodeChildren(clusterBarPlotRoot);
    addGraphFromRouteToNode(clusterBarPlotRoot, '/dashapp/cluster-bar-plot');
}

function addDailyBarPlot() {
    removeAllNodeChildren(dailyBarPlotRoot);
    addGraphFromRouteToNode(dailyBarPlotRoot, '/dashapp/daily-bar-plot');
}

function addPcaEmbeddings() {
    removeAllNodeChildren(embedPcaPlotRoot);
    addGraphFromRouteToNode(embedPcaPlotRoot, '/dashapp/embeddings-pca-scatter-plot');
}

function addPcaExplainedVariance() {
    removeAllNodeChildren(pcaExplainedVarianceRoot);
    addGraphFromRouteToNode(pcaExplainedVarianceRoot, '/dashapp/pca-explained-variance-plot');
}

function addTsneEmbeddings() {
    removeAllNodeChildren(embedTsnePlotRoot);
    addGraphFromRouteToNode(embedTsnePlotRoot, '/dashapp/embeddings-tsne-scatter-plot');

    embedTsneBtn.innerHTML = 'Prettify with t-SNE';
}

function addWordCloud( num_clusters ) {
    wordcloudInfo.innerHTML = '';

    removeAllNodeChildren(wordcloudPlotRoot);
    wordcloudPlotRef = addGraphFromRouteToNode(wordcloudPlotRoot,'/dashapp/wordcloud-plot');

    const numRows = Math.ceil(num_clusters / 2);
    wordcloudPlotRef.style.height = `${100 + 200 * numRows}px`;
}

semanticClusterBtn.addEventListener('click', function (evt) {
    // store params for db query
    const params = {
        'sender': 'clusterer',
        'show-id-begin-range': show.id.begin.range.value,
        'show-id-end-range': show.id.end.range.value,
        'show-comm-begin-range': show.comm.begin.range.value,
        'show-comm-end-range': show.comm.end.range.value,
        'show-score-begin-range': show.score.begin.range.value,
        'show-score-end-range': show.score.end.range.value,
        'num-clusters': clustersNum.value,
        'model-name': transformerModelName.value,
    };

    // show `in-progress`
    semanticClusterBtn.innerHTML = `${spinnerAmination} Clustering Posts...`;

    // clear all figures and hide tabs
    reset();

    postData('/cluster/run', params)
        .then(res => checkForServerErrors(res))
        .then(res => {
            semanticClusterBtn.innerHTML = `Cluster Posts`;
    
            // make figures and select visible
            figureRoot.style.display = "";
            selectRoot.style.display = "";
        })
        .then(res => addClusterBarPlot())
        .then(res => addDailyBarPlot())
        .then(res => addPcaEmbeddings())
        .then(res => addPcaExplainedVariance())
        .catch(err => {
            console.log(err);
            semanticClusterBtn.innerHTML = `Cluster Posts`;
            addAlertMessage(err);
        });
});


showSemanticClusterPostsBtn.addEventListener('click', function (evt) {
    console.log('clicked show posts btn');
    const targetLabel = showSemanticClusterPostsNum.value;

    let filtered_ids;

    // add in-progress animation
    this.innerHTML = `${spinnerAmination} Querying DB...`;

    // make table visible
    tableRoot.style.display = "";

    // read all labels
    postData('/file/readcsv', {
        'sender': 'reader',
        'fname': 'data/df.csv'
    })
    .then(res => checkForServerErrors(res))
    .then(res => {
        // filters post ids based on the target label
        filtered_ids = filterAbyBwhereBisC(
            res.data['id'],
            res.data['label'],
            targetLabel
        );
        return postData('/db/get', {
            'sender': 'db-lister',
            'story_ids': filtered_ids.join(','), // TODO: adjust RequestParser to accept list!
        })
    })
    .then(res => checkForServerErrors(res))
    .then(res => {
        // display filtered posts in a new table
        const table = getNewHNPostTable(); // no morePostsBtn!
        appendDataToHNPostTable(table, res.data);
        this.innerHTML = 'Show Posts';
    })
    .catch(err => {
        console.log(err)
        this.innerHTML = 'Show Posts';
        addAlertMessage(err);
    })
})

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