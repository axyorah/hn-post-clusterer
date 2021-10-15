seedSubmitBtn.addEventListener('click', function (evt) {    
    const params = {
        'sender': 'db-seeder',
        'seed-id-begin-range': seed.id.begin.range.value,
        'seed-id-end-range': seed.id.end.range.value
    };
    //start in-progress spinner animation
    this.innerHTML = `${spinnerAmination} Getting Data from HN...`;

    // seed db with entries withing specified id range
    postData('/db/add', params)
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

for (let filterBy of ['date', 'id']) {
    for (let loc of ['begin', 'end']) {

        seed[filterBy][loc].range.addEventListener('change', (evt) => {
            // `update...` is defined in `index.js`
            update[filterBy][loc](
                seed[filterBy].begin.range, seed[filterBy].end.range, 
                seed[filterBy].begin.label, seed[filterBy].end.label
            );
        })

    }
}

window.addEventListener('load', (evt) => {
    for (let filterBy of ['date', 'id']) {            
        // `config...` is defined in `index.js`
        config[filterBy](
            seed[filterBy].begin.range, seed[filterBy].end.range, 
            seed[filterBy].begin.label, seed[filterBy].end.label,
            range[filterBy].min, range[filterBy].max
        )
    }
})