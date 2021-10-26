function adjustDateNodeDisplay(node, date) {
    /*
    Print *actual* date in node's inner's html:
    e.g., if 2021/feb/31 was selected
    it would be corrected to 2021/3/3
    */
    node.innerHTML = 
        node.innerHTML.split(':')[0] + ': ' +
        `${date.getFullYear()}/${date.getMonth()+1}/${date.getDate()} ` +
        node.innerHTML.split(':')[1];
}
 

function getDateFromDateNode(node) {
    /*
    reads year/month/day from node's children 
    if children with id's containing year/month/day are present
    and their values are numerical,
    then returns Date object;
    otherwise throws an error 
    */
    let date = {
        'year': undefined, 
        'month': undefined,
        'day': undefined
    };

    for (let child of node.children) {
        for (let name in date) {
            if (child.id && child.id.includes(name)) {
                date[name] = child.value;
            }
        }
    }

    if (Object.keys(date)
        .map(k => isFinite(date[k]))
        .reduce((a,b) => a && b)
    ) {
        const [y, m, d] = [
            date.year, date.month, date.day
        ].map(val => parseInt(val));
        
        const dateObj = new Date(y, m-1, d);
        adjustDateNodeDisplay(node, dateObj);

        return dateObj;
    } else {
        throw new Error('date is not specified');
    }
}

function getTimestampFromDateNode(node) {
    /*
    attempts to read year/month/day from the date node 
    and adjusts node inner html to reflect the *actual* date
    (e.g., if 2021/feb/31 was selected it would be corrected to 2021/3/3);
    on success returns timestamp in seconds(!);
    on fail throws `date is not specified` error and returns undefined
    */
    const date = getDateFromDateNode(node);
    return isFinite(date.valueOf()) ? parseInt(date.valueOf() / 1000) : undefined;
}