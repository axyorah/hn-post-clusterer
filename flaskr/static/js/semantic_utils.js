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
    wordcloudInfo.innerHTML = `${spinnerAmination} Processing Data...`;

    // clear figures
    while (countsBarPlotRoot.children.length) {
        countsBarPlotRoot.removeChild(countsBarPlotRoot.lastChild);
    }
    while (embedPcaPlotRoot.children.length) {
        embedPcaPlotRoot.removeChild(embedPcaPlotRoot.lastChild);
    }
    while (wordcloudPlotRoot.children.length) {
        wordcloudPlotRoot.removeChild(wordcloudPlotRoot.lastChild);
    }

    // make figures, select, and table invisible
    figureRoot.style.display = "none";
    selectRoot.style.display = "none";
    tableRoot.style.display = "none";

    postData('/semanticcluster', params)
    .then(res => {
        semanticClusterBtn.innerHTML = `Cluster Posts`;

        // make figures and select visible
        figureRoot.style.display = "";
        selectRoot.style.display = "";
    }).then(res => {
        // // create bar plot and store it in barPlotRef
        const countsBarPlotRef = document.createElement('iframe');
        countsBarPlotRef.setAttribute('class', 'graph-container');
        countsBarPlotRef.setAttribute('src', '/dashapp/semantic-cluster-bar-plot');
        countsBarPlotRoot.appendChild(countsBarPlotRef);
    }).then(res => {
        // // create 2d scatter plot with two axes = first two PCA coordinates
        const embedPcaPlotRef = document.createElement('iframe');
        embedPcaPlotRef.setAttribute('class', 'graph-container');
        embedPcaPlotRef.setAttribute('src', '/dashapp/semantic-cluster-scatter-plot');
        embedPcaPlotRoot.append(embedPcaPlotRef);
    }).then(res => {
        // generate data for wordcloud        
        return fetch('/wordcloud');
    }).then(res => {
        wordcloudInfo.innerHTML = '';

        // create wordcloud
        const numRows = Math.ceil(params['num-clusters'] / 2);
        const wordcloudPlotRef = document.createElement('iframe');
        wordcloudPlotRef.setAttribute('class', 'graph-container');
        wordcloudPlotRef.setAttribute('src', '/dashapp/wordcloud-plot');
        wordcloudPlotRef.style.height = `${100 + 200 * numRows}px`;
        wordcloudPlotRoot.append(wordcloudPlotRef);
    }).catch(err => {
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
    tableRoot.style.display = "";

    // read all labels
    postData('/file/readcsv', {
        'sender': 'reader',
        'fname': 'data/df.csv'    
    }).then(res => {
        // filters post ids based on the target label
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