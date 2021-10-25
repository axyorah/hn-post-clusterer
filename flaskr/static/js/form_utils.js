// Vars
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
        min: 5,
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

    general: function (beginRange, endRange, beginLabel, endLabel, minVal, maxVal, showLabel=false) {
        beginRange.min = minVal;
        beginRange.max = maxVal;
        beginRange.value = minVal;
    
        endRange.min = minVal;
        endRange.max = maxVal;
        endRange.value = maxVal;
    
        if (showLabel) {
            beginLabel.innerText = `From: ${minVal}`;
            endLabel.innerText = `To: ${maxVal}`;
        }
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
        begin: function(beginRange, endRange, beginLabel, endLabel, showLabel=false) {
            let beginVal = parseInt(beginRange.value);
            let endVal = parseInt(endRange.value);
            if (beginVal >= endVal) {
                beginVal = endVal - 1;
                beginRange.value = beginVal;
            }
            if (showLabel) {
                beginLabel.innerText = `From: ${beginVal}`;
            }
        }, 

        end: function(beginRange, endRange, beginLabel, endLabel, showLabel=false) {
            let beginVal = parseInt(beginRange.value);
            let endVal = parseInt(endRange.value);
            if (endVal <= beginVal) {
                endVal = beginVal + 1;
                endRange.value = endVal;
            }
            if (showLabel) {
                endLabel.innerText = `To: ${endVal}`;
            }                        
        }
    },
}
update.id = update.general;
update.comm = update.general;
update.score = update.general;


// Event Listeners 
for (let filterBy of ['date', 'id']) {
    for (let loc of ['begin', 'end']) {
        seed[filterBy][loc].range.addEventListener('change', (evt) => {
            update[filterBy][loc](
                seed[filterBy].begin.range, seed[filterBy].end.range, 
                seed[filterBy].begin.label, seed[filterBy].end.label,
                filterBy === 'id' ? true : false
            );
        })

    }
}

for (let filterBy of ['id', 'comm', 'score']) {
    for (let loc of ['begin', 'end']) {
        show[filterBy][loc].range.addEventListener('change', (evt) => {
            update[filterBy][loc](
                show[filterBy].begin.range, show[filterBy].end.range, 
                show[filterBy].begin.label, show[filterBy].end.label,
                filterBy === 'id' ? true : false
            );
        })
    }
}

function addDateToNode(date, node) {
    console.log(date);
    console.log(node);
    const [year, month, day] = [date.getFullYear(), date.getMonth()+1, date.getDate()];

    const selectYear = document.createElement('select');
    selectYear.setAttribute('id', node.id + '-year');
    selectYear.setAttribute('class', 'box');
    for (let y = 2006; y <= year; y++) {
        let opt = document.createElement('option');
        if (y == year) {
            opt.setAttribute('selected', true);
        }
        opt.setAttribute('value', y);
        opt.setAttribute('class', 'box');
        opt.innerText = y;
        selectYear.appendChild(opt);
    }

    const selectMonth = document.createElement('select');
    selectMonth.setAttribute('id', node.id + '-month');
    selectMonth.setAttribute('class', 'box');
    const months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
    for (let i = 0; i < 12; i++) {
        let opt = document.createElement('option');
        if (i+1 == month) {
            opt.setAttribute('selected', true);
        }
        opt.setAttribute('value', i+1);
        opt.setAttribute('class', 'box');
        opt.innerText = months[i];
        selectMonth.appendChild(opt);
    }

    const selectDay = document.createElement('select');
    selectDay.setAttribute('id', node.id + '-day');
    selectDay.setAttribute('class', 'box');
    for (let d = 1; d <= 31; d++) {
        let opt = document.createElement('option');
        if (d == day) {
            opt.setAttribute('selected', true);
        }   
        opt.setAttribute('value', d);
        opt.setAttribute('class', 'box');
        opt.innerText = d;
        selectDay.appendChild(opt);
    }

    node.appendChild(selectYear);
    node.appendChild(selectMonth);
    node.appendChild(selectDay);
}

function setupDateFilter(toRoot, fromRoot) {
    // set to: today
    const toDate = new Date();
    addDateToNode(toDate, toRoot);    

    // set from: mindate or today - 7days
    let fromDate;
    fetch('/db/stories/stats')
    .then(res => res.json())
    .then(res => {
        if (res === undefined || res.data === undefined || res.data.num === 0) {
            throw new Error('db is empty!');
        }
        return fetch(`https://hacker-news.firebaseio.com/v0/item/${res.data.min}.json?print=pretty`)        
    })
    .then(res => res.json())
    .then(res => {
        if (res.time) {
            fromDate = new Date(res.time * 1000);
        } else {
            throw new Error('no timestep provided');
        }
    })
    .catch(err => {
        console.log(`Error: ${err}`);
        if (fromDate === undefined) {
            fromDate = new Date(toDate - 7*24*60*60*1000);
        }
    })
    .finally(res => {
        addDateToNode(fromDate, fromRoot);
    });
}

window.addEventListener('load', (evt) => {
    for (let filterBy of ['date', 'id']) {
        config[filterBy](
            seed[filterBy].begin.range, seed[filterBy].end.range, 
            seed[filterBy].begin.label, seed[filterBy].end.label,
            range[filterBy].min, range[filterBy].max,
            filterBy === 'id' ? true : false
        )
    }

    setupDateFilter(seedDateBeginRoot, seedDateEndRoot);
})

window.addEventListener('load', (evt) => {
    for (let filterBy of ['id', 'comm', 'score']) {            
        config[filterBy](
            show[filterBy].begin.range, show[filterBy].end.range, 
            show[filterBy].begin.label, show[filterBy].end.label,
            range[filterBy].min, range[filterBy].max,
            filterBy === 'id' ? true : false
        )
    }
})