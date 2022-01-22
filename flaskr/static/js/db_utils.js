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

    // set `beginId` to the first item on `beginDate`
    fetchFirstIdOnDay(
        beginDate.getFullYear(), 
        beginDate.getMonth()+1,
        beginDate.getDate()
    )
    .then(res => {
        beginId = res;
        console.log(`first id on ${beginDate}: ${beginId}`);
    })
    // set `endId` to the first item on `endDate`
    .then(_ => fetchFirstIdOnDay(
        endDate.getFullYear(), 
        endDate.getMonth()+1,
        endDate.getDate()
    ))
    .then(res => {
        endId = res;
        console.log(`first id on ${endDate}: ${endId}`);
    })
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
    });
})