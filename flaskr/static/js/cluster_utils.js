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
            console.log(res);
            this.innerHTML = 'Run Simple Clustering';
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
    postData('/readfile', {
        'sender': 'reader',
        'fname': 'data/labels.txt'
    }).then(res => {
        // read all ids
        labels = res.contents;
        return postData('/readfile', {
            'sender': 'reader',
            'fname': 'data/ids.txt'
        })
    }).then(res => {
        // filter ids based on the target label and query db
        all_ids = res.contents;
        filtered_ids = filterAbyBwhereBisC(all_ids, labels, targetLabel);
        return postData('/db', {
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