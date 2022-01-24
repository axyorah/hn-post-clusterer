function adjustDateNodeDisplay(node, date) {
    /*
    Print *actual* date in node's inner's html:
    e.g., if 2021/feb/31 was selected
    it would be corrected to 2021/3/3
    */
    const pattern = /[0-9]+\/[0-9]+\/[0-9]+/;
    const r = pattern.exec(node.innerHTML);
    if (r) {
        node.innerHTML = 
            node.innerHTML.replace(
                r[0], `${date.getFullYear()}/${date.getMonth()+1}/${date.getDate()}`
            );
    } else {
        node.innerHTML =     
            node.innerHTML.split(':')[0] + ': ' +
            `${date.getFullYear()}/${date.getMonth()+1}/${date.getDate()} ` +
            node.innerHTML.split(':')[1];
    }
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

function date2ts(year, month, day) {
    /* returns timestamp (in seconds) corresponding to specified date */
    const dateObj = new Date(year, month-1, day);
    return Math.floor(dateObj.getTime() / 1000);
}

async function id2ts(itemId) {
    /* returns timestamp (in seconds) of hn item with specified id */
    const url = `https://hacker-news.firebaseio.com/v0/item/${itemId}.json`;
    const res = await fetch(url)
        .then(res => res.json())
        .catch(err => console.log(err));
    
    if (res && res['time']) {
        return res['time'];
    } else {
        return await id2ts(itemId - 1)
        .then(res => res.json());
    }
}

async function binSearchTs(lo, hi, targetTs) {
    // use binsearch to find first id higher than timestamp
    let mi, ts;
    while (lo <= hi) {
        mi = Math.floor((lo + hi) / 2);
        
        await id2ts(mi).then(res => {ts = res}); // await!!!
        
        if (targetTs > ts) {
            lo = mi + 1;
        } else {
            hi = mi - 1;
        }
    }
    return hi + 1;
}

async function fetchFirstIdOnDay(year, month, day) {
    /*
    returns first hn item id (story or comment) on specified date;
    date specified as as (year, month, day) tuple if ints (1-based indexing),
    e.g. (2021, 1, 1) is 1st January 2021;
    impossible dates (e.g., 31st February 2021) will be resolved
    (e.g. 31st February 2021 -> 3rd March 2021),
    future dates (e.g., 1st January 3021) will raise errors

    use:
        const firstId = await fetchFirstIdOnDay(...);
    */
    URL_MAXID = 'https://hacker-news.firebaseio.com/v0/maxitem.json';

    const targetTs = date2ts(year, month, day);

    let maxId, maxTs;
    return await fetch(URL_MAXID)
    .then(res => res.json())
    .then(res => maxId = res)
    .then(async (res) => {        
        await id2ts(maxId).then(res => {maxTs = res}); // await!!!
        if (targetTs > maxTs) {
            //throw new Error('Specified date is out of range');
            console.log(
                `Specified date (${new Date(targetTs * 1000).toISOString()}) is out of range, ` +
                `using current date ${new Date(maxTs * 1000).toISOString()} instead.`
            );
            return maxId;
        } else {
            return await binSearchTs(1, maxId, targetTs);
        }
    })
    .catch(err => console.log(err));
}
