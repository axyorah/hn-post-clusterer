seedSubmitBtn.addEventListener('click', function (evt) {    
    const params = {
        'sender': 'db-seeder',
        'seed-id-begin-range': seed.id.begin.range.value,
        'seed-id-end-range': seed.id.end.range.value
    };
    //start in-progress spinner animation
    this.innerHTML = `${spinnerAmination} Getting Data from HN...`;

    // seed db with entries withing specified id range
    postData('/db/items', params)//('/db/add', params)
    .then(res => checkForServerErrors(res))
    .then(res => {
        // stop spinner animation
        this.innerHTML = 'Get Data';
    })
    .catch(err => {
        this.innerHTML = 'Get Data';
        console.log(err);
        addAlertMessage(err);
    })
})