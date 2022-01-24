const story2schema = {
    'story_id': 'id',
    'author': 'by',
    'unix_time': 'time',
    'body': 'text',
    'url': 'url',
    'score': 'score',
    'title': 'title',
    'num_comments': 'descendants',
    'kids': 'kids', // not in schema but we need it...
    'type': 'type', // not in schema,
    'deleted': 'deleted',
    'dead': 'dead'
};

const comment2schema = {
    'comment_id': 'id',
    'author': 'by',
    'unix_time': 'time',
    'body': 'text',
    'parent_id': 'parent',
    'type': 'type' // not in schema...
};

function translateResponseJsonToSchema(json) {
    const item = new Object();
    if (json === null) {
        return;
    } else if (json.type === 'story') {
        // if undefined - replace by null (undefined in not JSON.stringifiable)
        Object.keys(story2schema).forEach(key => {
            item[key] = json[story2schema[key]] || null;
        });
    } else if (json.type === 'comment') {
        // if undefined - replace by null (undefined in not JSON.stringifiable)
        Object.keys(comment2schema).forEach(key => {
            item[key] = json[comment2schema[key]] || null;
        });
    }
    return item;
}

async function fetchSingleItemFromHNAndAddToDb(id, storyNeedsUpdate=false) {
    // get item from hn
    return await fetch(
        `https://hacker-news.firebaseio.com/v0/item/${id}.json`
    )
    .then(res => res.json())
    .then(res => translateResponseJsonToSchema(res))
    .then(async (item) => {
        // skip if empty, deleted or dead
        if (!item || item.deleted || item.dead) {
            console.log(
                `[${new Date().toISOString()}] `+
                `${id}: got empty, deleted or dead, skipping...`
            );
            return;
        }

        // add to db
        console.log(
            `[${new Date().toISOString()}] `
            `${id}: got ${item.type} from `+
            `${new Date(parseInt(item.unix_time) * 1000).toISOString()}, `+
            `${storyNeedsUpdate ? 'updading' : 'adding to db' }... `
        );
        if (storyNeedsUpdate) {
            await postData(`/api/stories/${id}/`, item, 'PUT');
        } else if (item.type === 'story') {
            await postData(`/api/stories/`, item, 'POST');
        } else if (item.type === 'comment') {
            await postData(`/api/comments/`, item, 'POST');
        }
        return item;
    })
    .catch(err => console.error(err));
}

async function maybeFetchSingleItemFromHNAndAddToDb(id) {
    /*
    checks if item with given id is already in db:
    - if item is comment and it is in db - skips
    - X [if item is story and it is in db - fetches it again and updates db]
    - if item is story and it is in db - skips
    - if item is not in db: fetches it from hn and adds it to db
    */
    
    let story, comment;

    // check if story is in db
    return await fetch(`/api/stories/${id}`)
    .then(res => res.json())
    .then(res => res.data)
    .then(res => {story = res;})
    // check if comment is in db
    .then(_ => fetch(`/api/comments/${id}`))
    .then(res => res.json())
    .then(res => res.data)
    .then(res => {comment = res;})
    // maybe add to db
    .then(async (res) => {
        if ( comment ) {
            console.log(
                `[${new Date().toISOString()}] ` +
                `${id}: comment already in db, skipping...`
            );
            return comment;
        } else if ( story ) {
            console.log(
                `[${new Date().toISOString()}] ` +
                `${id}: story already in db, skipping...`
            );
            return story;
        } else {
            // add new item to db
            return await fetchSingleItemFromHNAndAddToDb(id, false);
        }
    })
    .catch(err => console.error(err));
}

async function getItemRangeFromHNAndAddToDb(beginId, endId) {
    async function fetchItemWithKidsRecursively(id) {
        await maybeFetchSingleItemFromHNAndAddToDb(id)
        .then(item => {
            if (item && item.kids) {
                item.kids.forEach(childId => {
                    if (childId > endId) {
                        fetchItemWithKidsRecursively(childId);
                    }
                });
            }
        });
    }

    const throttler = new Semaphore(1);
    for (let id = beginId; id <= endId; id++) {
        throttler.callFunction(fetchItemWithKidsRecursively, id);
    }

}

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
});