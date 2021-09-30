semanticClusterBtn.addEventListener('click', function (evt) {
    // store params for db query
    const params = {
        'sender': 'semantic',
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

    // clear figures
    while (countsBarPlotRoot.children.length) {
        countsBarPlotRoot.removeChild(countsBarPlotRoot.lastChild);
    }
    while (embedPcaPlotRoot.children.length) {
        embedPcaPlotRoot.removeChild(embedPcaPlotRoot.lastChild);
    }

    // make figures, select, and table invisible
    figureRoot.style.visibility = "hidden";
    selectRoot.style.visibility = "hidden";
    tableRoot.style.visibility = "hidden";

    postData('/semanticcluster', params)
    .then(res => {
        semanticClusterBtn.innerHTML = `Cluster Posts`;

        // make figures and select visible
        figureRoot.style.visibility = "visible";
        selectRoot.style.visibility = "visible";

        // // display plots:
        // // create bar plot and store it in barPlotRef
        const countsBarPlotRef = document.createElement('iframe');
        countsBarPlotRef.setAttribute('class', 'graph-container');
        countsBarPlotRef.setAttribute('src', '/dashapp/semantic-cluster-bar-plot');
        countsBarPlotRoot.appendChild(countsBarPlotRef);

        // // create 2d scatter plot with two axes = first two PCA coordinates
        const embedPcaPlotRef = document.createElement('iframe');
        embedPcaPlotRef.setAttribute('class', 'graph-container');
        embedPcaPlotRef.setAttribute('src', '/dashapp/semantic-cluster-scatter-plot');
        embedPcaPlotRoot.append(embedPcaPlotRef);      
    })
    .catch(err => {
        console.log(err);
        semanticClusterBtn.innerHTML = `Cluster Posts`;
    });
});


showSemanticClusterPostsBtn.addEventListener('click', function (evt) {
    console.log('clicked show posts btn');
    const targetLabel = showSemanticClusterPostsNum.value;

    let filtered_ids;

    // add in-progress animation
    this.innerHTML = `${spinnerAmination} Querying DB...`;

    // make table visible
    tableRoot.style.visibility = "visible";

    // read all labels
    postData('/file/readcsv', {
        'sender': 'reader',
        'fname': 'data/df.csv'    
    }).then(res => {
        // filter ids based on the target label and query db
        filtered_ids = filterAbyBwhereBisC(
            res.contents['id'], 
            res.contents['label'], 
            targetLabel
        );
        return postData('/db/get', {
            'sender': 'kmeans-show',
            'story_ids': filtered_ids,
        })
    }).then(res => {
        // display filtered posts in a new table
        const table = getNewHNPostTable(); // no morePostsBtn!
        appendDataToHNPostTable(table, res);
        this.innerHTML = 'Show Posts';      
    }).catch(err => {
        console.log(err)
        this.innerHTML = 'Show Posts';
    })
})