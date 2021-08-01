// DOM
tableRoot = document.querySelector('#table-root');
queryDbBtn = document.querySelector('#post-db-btn');

// Vars
const idRange = 5000;
class Counter {
    constructor() {
        this._count = 0;
    }
    get count() { return this._count; }
    increment = function() {
        this._count += 1;
    }
}

// Helpers
function getMorePostsBtn() {
    const counter = new Counter();
    const moreBtn = document.createElement('button');
    moreBtn.innerText = 'More!';

    moreBtn.addEventListener('click', function (evt) {
        // check fraction of posts/comments at a time
        counter.increment();

        const idBegin = Math.min(
            parseInt(show.id.begin.range.value) + counter.count * idRange,
            parseInt(show.id.end.range.value)
        );
        const idEnd = Math.min(
            parseInt(show.id.begin.range.value) + (counter.count + 1) * idRange,
            parseInt(show.id.end.range.value)
        );

        const data = {
            'show-id-begin-range': idBegin,
            'show-id-end-range': idEnd,
            'show-comm-begin-range': show.comm.begin.range.value,
            'show-comm-end-range': show.comm.end.range.value,
            'show-score-begin-range': show.score.begin.range.value,
            'show-score-end-range': show.score.end.range.value,
            // 'show-lsi-topics-num': showLsiTopicsNum.value,
            // 'show-kmeans-clusters-num': showKmeansClustersNum.value        
        }

        if (idBegin === show.id.end.range.value) {
            return;
        } else {
            postData('/db', data)
            .then(res => {
                console.log(`Posting stuff from #${data['show-id-begin-range']} to #${data['show-id-end-range']}`);
                appendDataToHNPostTable(tableRoot.children[0], res);
            })
            .catch((err) => console.log(err));
        }        

    })

    return moreBtn;
}

function getNewHNPostTable() {
    // clear table
    tableRoot.innerHTML = '';
    const table = document.createElement('table');
    table.id = 'hn-post-table';
    tableRoot.appendChild(table);

    // create header
    const trHead = document.createElement('tr');
    for (let field of ['story_id', 'author', 'unix_time', 'score', 'title', '#comments', 'comments']) {
        const th = document.createElement('th')
        th.innerText = field;
        trHead.appendChild(th);
    }
    table.appendChild(trHead);

    // create `more` button
    moreBtn = getMorePostsBtn();
    tableRoot.appendChild(moreBtn);

    return table;
}

function getHTMLDetails(title, innerHTML) {
    const details = document.createElement('details');
    const summary = document.createElement('summary');
    const p = document.createElement('p');

    summary.innerText = title;
    p.innerHTML = innerHTML;

    details.appendChild(summary);
    details.appendChild(p);

    return details;
}

function appendDataToHNPostTable(table, data) {
    // add data
    for (let storyId of Object.keys(data)) {
        const tr = document.createElement('tr');
        for (let field of ['story_id', 'author', 'unix_time', 'score', 'title', 'descendants']) {
            const td = document.createElement('td') 
            if (field === 'unix_time') {
                const date = new Date(data[storyId][field] * 1000);
                td.innerText = `${date.getFullYear()}/${date.getMonth()}/${date.getDate()}`;
            } else {
                td.innerText = data[storyId][field];
            }
            tr.appendChild(td);
        }
        // add comments as details
        const td = document.createElement('td');
        const details = getHTMLDetails('show', data[storyId]['children']);
        td.appendChild(details);
        tr.appendChild(td);
        
        // add row to table
        table.appendChild(tr);
    }
}

// Event Listeners
queryDbBtn.addEventListener('click', function (evt) {
    const data = {
        'show-id-begin-range': show.id.begin.range.value,
        'show-id-end-range': Math.min(parseInt(show.id.begin.range.value) + idRange, parseInt(show.id.end.range.value)),
        'show-comm-begin-range': show.comm.begin.range.value,
        'show-comm-end-range': show.comm.end.range.value,
        'show-score-begin-range': show.score.begin.range.value,
        'show-score-end-range': show.score.end.range.value,
        // 'show-lsi-topics-num': showLsiTopicsNum.value,
        // 'show-kmeans-clusters-num': showKmeansClustersNum.value
    };

    postData('/db', data)
        .then(res => {
            const table = getNewHNPostTable();
            console.log(`Posting stuff from #${data['show-id-begin-range']} to #${data['show-id-end-range']}`);
            appendDataToHNPostTable(table, res);
        })
        .catch((err) => console.log(err));
})