// DOM
container = document.querySelector('.container');
tableRoot = document.querySelector('#table-root');
queryDbBtn = document.querySelector('#post-db-btn');

showLsiTopicsNum = document.querySelector('#show-lsi-topics-num');
showKmeansClustersNum = document.querySelector('#show-kmeans-clusters-num');

const show = new Object();
for (let filterBy of ['date', 'id', 'comm', 'score']) {
    if (show[filterBy] === undefined) {
        show[filterBy] = new Object();
    }
    for (let loc of ['begin', 'end']) {
        if (show[filterBy][loc] === undefined) {
            show[filterBy][loc] = new Object();
        }
        show[filterBy][loc]['range'] = document.querySelector(`#show-${filterBy}-${loc}-range`);
        show[filterBy][loc]['label'] = document.querySelector(`#show-${filterBy}-${loc}-label`);
    }
}

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

const range = {
    date: {
        min: new Date(2006, 10, 9).valueOf(),
        max: new Date().valueOf()
    }, 

    id: {
        min: 27700000,//27750741,27758000,27776268
        max: 27975530//27752765
    },

    comm: {
        min: 0,
        max: 300
    },

    score: {
        min: 0, 
        max: 300
    }
}

// Helpers
const config = {
    date: function (beginRange, endRange, beginLabel, endLabel, minVal, maxVal) {
        beginRange.min = minVal;
        beginRange.max = maxVal;
        beginRange.value = minVal;
    
        endRange.min = minVal;
        endRange.max = maxVal;
        endRange.value = maxVal;
    
        const [m0, d0, y0] = new Date(minVal).toLocaleDateString().split('/');
        const [mf, df, yf] = new Date(maxVal).toLocaleDateString().split('/');
        beginLabel.innerText = `From: ${y0}/${m0}/${d0}`;
        endLabel.innerText = `To: ${yf}/${mf}/${df}`;
    },

    general: function (beginRange, endRange, beginLabel, endLabel, minVal, maxVal) {
        beginRange.min = minVal;
        beginRange.max = maxVal;
        beginRange.value = minVal;
    
        endRange.min = minVal;
        endRange.max = maxVal;
        endRange.value = maxVal;
    
        beginLabel.innerText = `From: ${minVal}`;
        endLabel.innerText = `To: ${maxVal}`;
    }, 
};
config.id = config.general;
config.comm = config.general;
config.score = config.general;

const update = {
    date: {
        begin: function(beginRange, endRange, beginLabel, endLabel) {
            let beginVal = parseInt(beginRange.value);
            let endVal = parseInt(endRange.value);
            if (beginVal >= endVal) {
                beginVal = endVal - 1000 * 60 * 60 * 24;
                beginRange.value = beginVal;
            }
            const [m, d, y] = new Date(beginVal).toLocaleDateString().split('/');
            beginLabel.innerText = `From: ${y}/${m}/${d}`;
        },
        
        end: function(beginRange, endRange, beginLabel, endLabel) {
            let beginVal = parseInt(beginRange.value);
            let endVal = parseInt(endRange.value);
            if (endVal <= beginVal) {
                endVal = beginVal + 1000 * 60 * 60 * 24;
                endDateRange.value = endVal;
            }
            const [m, d, y] = new Date(endVal).toLocaleDateString().split('/');
            endLabel.innerText = `To: ${y}/${m}/${d}`;            
        }
    }, 

    general: {
        begin: function(beginRange, endRange, beginLabel, endLabel) {
            let beginVal = parseInt(beginRange.value);
            let endVal = parseInt(endRange.value);
            if (beginVal >= endVal) {
                beginVal = endVal - 1;
                beginRange.value = beginVal;
            }
            beginLabel.innerText = `From: ${beginVal}`;            
        }, 

        end: function(beginRange, endRange, beginLabel, endLabel) {
            let beginVal = parseInt(beginRange.value);
            let endVal = parseInt(endRange.value);
            if (endVal <= beginVal) {
                endVal = beginVal + 1;
                endRange.value = endVal;
            }
            endLabel.innerText = `To: ${endVal}`;            
        }
    },
}
update.id = update.general;
update.comm = update.general;
update.score = update.general;

function urlify(json) {
    const entries = Object.keys(json).map(key => `${key}=${json[key]}`);
    return entries.join('&')
}

async function postData(url, data) {
    // Default options are marked with *
    const response = await fetch(url, {
        method: 'POST', 
        mode: 'cors', 
        cache: 'no-cache', 
        credentials: 'same-origin', 
        headers: {
            'Accept': 'application/json, text/plain',
            // 'Content-Type': 'application/json; charset=UTF-8'
            'Content-Type': 'application/x-www-form-urlencoded'
      },
      redirect: 'follow', 
      referrerPolicy: 'no-referrer', 
      body: urlify(data)//JSON.stringify(data) 
    });
    return response.json(); 
}

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
            'show-lsi-topics-num': showLsiTopicsNum.value,
            'show-kmeans-clusters-num': showKmeansClustersNum.value        
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
for (let filterBy of ['date', 'id', 'comm', 'score']) {
    for (let loc of ['begin', 'end']) {
        show[filterBy][loc].range.addEventListener('change', (evt) => {
            update[filterBy][loc](
                show[filterBy].begin.range, show[filterBy].end.range, 
                show[filterBy].begin.label, show[filterBy].end.label
            );
        })
    }
}

queryDbBtn.addEventListener('click', function (evt) {
    const data = {
        'show-id-begin-range': show.id.begin.range.value,
        'show-id-end-range': Math.min(parseInt(show.id.begin.range.value) + idRange, parseInt(show.id.end.range.value)),
        'show-comm-begin-range': show.comm.begin.range.value,
        'show-comm-end-range': show.comm.end.range.value,
        'show-score-begin-range': show.score.begin.range.value,
        'show-score-end-range': show.score.end.range.value,
        'show-lsi-topics-num': showLsiTopicsNum.value,
        'show-kmeans-clusters-num': showKmeansClustersNum.value
    };

    postData('/db', data)
        .then(res => {
            const table = getNewHNPostTable();
            console.log(`Posting stuff from #${data['show-id-begin-range']} to #${data['show-id-end-range']}`);
            appendDataToHNPostTable(table, res);
        })
        .catch((err) => console.log(err));
})

window.addEventListener('load', (evt) => {
    for (let filterBy of ['date', 'id', 'comm', 'score']) {            
        config[filterBy](
            show[filterBy].begin.range, show[filterBy].end.range, 
            show[filterBy].begin.label, show[filterBy].end.label,
            range[filterBy].min, range[filterBy].max
        )
    }
})