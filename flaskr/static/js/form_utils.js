// Vars
const range = {
    comm: {
        min: 5,
        max: 300
    },

    score: {
        min: 0, 
        max: 300
    }
}

// General Helpers
const config = {
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
config.comm = config.general;
config.score = config.general;

const update = {
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
update.comm = update.general;
update.score = update.general;


// Date Helpers
function getSelectElement(id) {
    const select = document.createElement('select');
    select.setAttribute('id', (id === undefined) ? 'selector' : id);
    select.setAttribute('class', 'box inpt');
    return select;
}

function addOptionsToSelect(selectNode, optVals, optNames, selectedVal) {
    for (let i = 0; i < optNames.length; i++) {
        const name = optNames[i];
        const val = optVals[i];
        let opt = document.createElement('option');
        if (selectedVal !== undefined && val == selectedVal) {
            opt.setAttribute('selected', true);
        }
        opt.setAttribute('value', val);
        opt.setAttribute('class', 'box');
        opt.innerText = name;
        selectNode.appendChild(opt);
    }
}

function addDateToNode(date, node) {
    const [year, month, day] = [date.getFullYear(), date.getMonth()+1, date.getDate()];

    const selectYear = getSelectElement(node.id + '-year');
    let years = [];
    for (let y = 2006; y <= year; y++) years.push(y);
    addOptionsToSelect(selectYear, years, years, year);

    const selectMonth = getSelectElement(node.id + '-month');
    const months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
    const indices = [...Array(months.length).keys()].map(val => val + 1);
    addOptionsToSelect(selectMonth, indices, months, month);

    const selectDay = getSelectElement(node.id + '-day');
    const days = [...Array(31).keys()].map(val => val+1);
    addOptionsToSelect(selectDay, days, days, day);

    node.appendChild(selectYear);
    node.appendChild(selectMonth);
    node.appendChild(selectDay);
}

function setupDateFilter(fromRoot, toRoot) {
    // set `to`-date: today
    const toDate = new Date();
    addDateToNode(toDate, toRoot);    

    // set `from`-date: min-date or today - 7days
    let fromDate;
    fetch('/db/stats')
    .then(res => res.json())
    .then(res => {
        if (
            res === undefined || res.data === undefined || 
            res.data.stories === undefined || res.data.stories.num === 0
        ) {
            throw new Error('db is empty!');
        }
        return fetch(`https://hacker-news.firebaseio.com/v0/item/${res.data.stories.min}.json?print=pretty`)        
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


// Event Listeners 
for (let filterBy of ['comm', 'score']) {
    for (let loc of ['begin', 'end']) {
        show[filterBy][loc].range.addEventListener('change', (evt) => {
            update[filterBy][loc](
                show[filterBy].begin.range, show[filterBy].end.range, 
                show[filterBy].begin.label, show[filterBy].end.label
            );
        })
    }
}

window.addEventListener('load', (evt) => {
    for (let filterBy of ['comm', 'score']) {            
        config[filterBy](
            show[filterBy].begin.range, show[filterBy].end.range, 
            show[filterBy].begin.label, show[filterBy].end.label,
            range[filterBy].min, range[filterBy].max
        )
    }

    setupDateFilter(showDateBeginRoot, showDateEndRoot);
    setupDateFilter(seedDateBeginRoot, seedDateEndRoot);
})