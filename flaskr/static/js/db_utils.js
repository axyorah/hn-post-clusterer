seedSubmitBtn.addEventListener('click', function (evt) {
    //start in-progress spinner animation
    this.innerHTML = `${spinnerAmination} Getting Data from HN...`;

    // convert date-filter node values to timestamps
    let beginId, endId;
    const beginDate = getDateFromDateNode(seedDateBeginRoot);
    const endDate = getDateFromDateNode(seedDateEndRoot);

    if (beginDate.valueOf() > endDate.valueOf()) {
        this.innerHTML = 'Get Data';
        addAlertMessage('`From`-date should come before `To`-date');
        return
    }

    // set `beginId` to the first item on `beginTs` date
    fetch(
        `/time/first_id_on?` + 
        `year=${beginDate.getFullYear()}&month=${beginDate.getMonth()+1}&day=${beginDate.getDate()}`
    )
    .then(res => checkForServerErrors(res))
    .then(res => res.json())
    .then(res => {
        console.log(`first id on ${beginDate}: ${res.data.id}`);
        beginId = res.data.id;
    })
    // set `endId` to the first item on `endTs` date
    .then(res => fetch(
        `/time/first_id_on?` + 
        `year=${endDate.getFullYear()}&month=${endDate.getMonth()+1}&day=${endDate.getDate()}`
    ))
    .then(res => checkForServerErrors(res))
    .then(res => res.json())
    .then(res => {
        console.log(`first id on ${endDate}: ${res.data.id}`);
        endId = res.data.id;
    })
    // set `params` obj needed to send post req to `/db/items`
    .then(res => {
        return {
            'sender': 'db-seeder',
            'seed-id-begin-range': beginId,
            'seed-id-end-range': endId
        }        
    })
    // seed db with entries within specified id range
    .then(params => postData('/db/items', params))
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