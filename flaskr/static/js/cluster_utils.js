function filterAbyBwhereBisC(a, b, c) {
    const indices = [...Array(a.length).keys()];
    return indices.map(i => {
        if (b[i] === c) {return a[i];}
    }).filter(val => val !== undefined);
}

runSimpleClusterBtn.addEventListener('click', function (evt) {
    console.log('clicked simple cluster button!');
    const params = {
        'sender': 'kmeans-run',
        'show-lsi-topics-num': showLsiTopicsNum.value,
        'show-kmeans-clusters-num': showKmeansClustersNum.value
    }
    
    // add in-progress animation
    this.innerHTML = 
        `${spinnerAmination} Running BoW &rarr; TF-IDF &rarr; LSI &rarr; k-Means...`;

    // run clustering, change button text when done
    postData('/simplecluster', params)
        .then(res => {
            // change button text
            console.log(res);
            this.innerHTML = 'Run Simple Clustering';

            // display plots:
            // create bar plot and store it in barPlotRef
            const barPlotRef = document.createElement('iframe');
            barPlotRef.setAttribute('class', 'graph-container');
            barPlotRef.setAttribute('src', '/dashapp/simple-cluster-bar-plot');

            // create 2d scatter plot with two axes = first two LSI coordinates
            const scatter2DPlotRef = document.createElement('iframe');
            scatter2DPlotRef.setAttribute('class', 'graph-container');
            scatter2DPlotRef.setAttribute('src', '/dashapp/simple-cluster-scatter-plot');
            
            // make sure that the new plots are the only children of simpleClusterPlotRoot
            while (simpleClusterPlotRoot.children.length) {
                simpleClusterPlotRoot.removeChild(simpleClusterPlotRoot.children[simpleClusterPlotRoot.children.length - 1]);
            }
            simpleClusterPlotRoot.appendChild(barPlotRef);
            simpleClusterPlotRoot.appendChild(scatter2DPlotRef);
        })
        .catch(err => {
            console.log(err);
            this.innerHTML = 'Run Simple Clustering';
        });
})

showSimpleClusterPostsBtn.addEventListener('click', function (evt) {
    console.log('clicked show posts btn');
    const targetLabel = showKmeansClusteredPostsNum.value;

    let labels, all_ids, filtered_ids;

    // add in-progress animation
    this.innerHTML = `${spinnerAmination} Querying DB...`;

    // read all labels
    postData('/file/read', {
        'sender': 'reader',
        'fname': 'data/labels.txt'
    }).then(res => {
        // read all ids
        labels = res.contents;
        return postData('/file/read', {
            'sender': 'reader',
            'fname': 'data/ids.txt'
        })
    }).then(res => {
        // filter ids based on the target label and query db
        all_ids = res.contents;
        filtered_ids = filterAbyBwhereBisC(all_ids, labels, targetLabel);
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