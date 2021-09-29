semanticClusterBtn.addEventListener('click', function (evt) {
    // store params for db query
    const params = {
        'sender': 'show',
        'show-id-begin-range': show.id.begin.range.value,
        'show-id-end-range': show.id.end.range.value,
        'show-comm-begin-range': show.comm.begin.range.value,
        'show-comm-end-range': show.comm.end.range.value,
        'show-score-begin-range': show.score.begin.range.value,
        'show-score-end-range': show.score.end.range.value,
    };
    
    semanticClusterBtn.innerHTML = `${spinnerAmination} Clustering Posts...`;

    postData('/semanticcluster', params)
    .then(res => {
        console.log(res);
        semanticClusterBtn.innerHTML = `Cluster Posts`;

        // display plots:
        // create bar plot and store it in barPlotRef
        const barPlotRef = document.createElement('iframe');
        barPlotRef.setAttribute('class', 'graph-container');
        barPlotRef.setAttribute('src', '/dashapp/semantic-cluster-bar-plot');

        // create 2d scatter plot with two axes = first two PCA coordinates
        const scatter2DPlotRef = document.createElement('iframe');
        scatter2DPlotRef.setAttribute('class', 'graph-container');
        scatter2DPlotRef.setAttribute('src', '/dashapp/semantic-cluster-scatter-plot');
            
        // make sure that the new plots are the only children of simpleClusterPlotRoot
        while (semanticClusterPlotRoot.children.length) {
            semanticClusterPlotRoot.removeChild(semanticClusterPlotRoot.children[semanticClusterPlotRoot.children.length - 1]);
        }
        semanticClusterPlotRoot.appendChild(barPlotRef);
        semanticClusterPlotRoot.appendChild(scatter2DPlotRef);
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
        console.log(res);
        const table = getNewHNPostTable(); // no morePostsBtn!
        appendDataToHNPostTable(table, res);
        this.innerHTML = 'Show Posts';      
    }).catch(err => {
        console.log(err)
        this.innerHTML = 'Show Posts';
    })
})