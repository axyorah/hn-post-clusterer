function removeAllNodeChildren(node) {
    while (node.children.length) {
        node.removeChild(node.lastChild);
    }
}

function reset() {
    // clear old data files
    const fnamesToBeDeleted = [
        'data/df.csv','data/df_tsne.csv','data/pca.txt','data/freq_*.json'
    ];
    for (let fname of fnamesToBeDeleted) {
        postData('/file', {'sender': 'deleter', 'fname': fname}, method='DELETE')
        .then(res => checkForServerErrors(res))
        .catch(err => {
            console.log(err);
            addAlertMessage(err);
        });
    }

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

semanticClusterBtn.addEventListener('click', function (evt) {
    // store params for db query
    const params = {
        'sender': 'clusterer',
        'show-ts-begin-range': getTimestampFromDateNode(showDateBeginRoot),
        'show-ts-end-range': getTimestampFromDateNode(showDateEndRoot),
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

    fetch('/file?fname=data/df.csv')
    .then(res => checkForServerErrors(res))
    .then(res => res.json())
    .then(res => {
        // filters post ids based on the target label
        filtered_ids = filterAbyBwhereBisC(
            res.data['id'],
            res.data['label'],
            targetLabel
        );
        return fetch(`/db/stories?ids=${filtered_ids.join(',')}`)
    })
    .then(res => checkForServerErrors(res))
    .then(res => res.json())
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
