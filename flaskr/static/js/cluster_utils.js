simpleClusterBtn.addEventListener('click', function (evt) {
    console.log('clicked simple cluster button!');
    const params = {
        'show-lsi-topics-num': showLsiTopicsNum.value,
        'show-kmeans-clusters-num': showKmeansClustersNum.value
    }

    postData('/simplecluster', params)
        .then(res => {
            console.log(res);
        })
        .catch(err => console.log(err));
})