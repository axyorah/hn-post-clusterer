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

window.addEventListener('load', (evt) => {
    for (let filterBy of ['date', 'id']) {
        config[filterBy](
            seed[filterBy].begin.range, seed[filterBy].end.range, 
            seed[filterBy].begin.label, seed[filterBy].end.label,
            range[filterBy].min, range[filterBy].max,
            filterBy === 'id' ? true : false
        )
    }
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