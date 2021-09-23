trainFaissBtn.addEventListener('click', function (evt) {
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
    
    trainFaissBtn.innerHTML = `${spinnerAmination} Clustering Posts...`;

    postData('/semanticcluster', params)
    .then(res => {
        console.log(res);
        trainFaissBtn.innerHTML = `Cluster Posts`;
    })
    .catch(err => {
        console.log(err);
        trainFaissBtn.innerHTML = `Cluster Posts`;
    });
})