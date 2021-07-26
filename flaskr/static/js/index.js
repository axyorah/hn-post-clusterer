container = document.querySelector('.container');

const seed = new Object();
const show = new Object();

for (let filterBy of ['date', 'id']) {
    if (seed[filterBy] === undefined) {
        seed[filterBy] = new Object();
    }
    for (let loc of ['begin', 'end']) {
        if (seed[filterBy][loc] === undefined) {
            seed[filterBy][loc] = new Object();
        }
        seed[filterBy][loc]['range'] = document.querySelector(`#seed-${loc}-${filterBy}-range`);
        seed[filterBy][loc]['label'] = document.querySelector(`#seed-${loc}-${filterBy}-label`);
    }
}

for (let filterBy of ['date', 'id', 'comm', 'score']) {
    if (show[filterBy] === undefined) {
        show[filterBy] = new Object();
    }
    for (let loc of ['begin', 'end']) {
        if (show[filterBy][loc] === undefined) {
            show[filterBy][loc] = new Object();
        }
        show[filterBy][loc]['range'] = document.querySelector(`#show-${loc}-${filterBy}-range`);
        show[filterBy][loc]['label'] = document.querySelector(`#show-${loc}-${filterBy}-label`);
    }
}

// Globals
const minTS = new Date(2006, 10, 9).valueOf();
const maxTS = new Date().valueOf();

const minID = 27750741
const maxID = 27752765


// Helpers
const config = {
    date: function (beginRange, endRange, beginLabel, endLabel) {
        beginRange.min = minTS;
        beginRange.max = maxTS;
        beginRange.value = minTS;
    
        endRange.min = minTS;
        endRange.max = maxTS;
        endRange.value = maxTS;
    
        const [m0, d0, y0] = new Date(minTS).toLocaleDateString().split('/');
        const [mf, df, yf] = new Date(maxTS).toLocaleDateString().split('/');
        beginLabel.innerText = `From: ${y0}/${m0}/${d0}`;
        endLabel.innerText = `To: ${yf}/${mf}/${df}`;
    },

    id: function (beginRange, endRange, beginLabel, endLabel) {
        beginRange.min = minID;
        beginRange.max = maxID;
        beginRange.value = minID;
    
        endRange.min = minID;
        endRange.max = maxID;
        endRange.value = maxID;
    
        beginLabel.innerText = `From: ${minID}`;
        endLabel.innerText = `To: ${maxID}`;
    }
};

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

    id: {
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
    }
}


// Event Listeners
for (let form of [seed, show]) {
    for (let filterBy of ['date', 'id']) {
        for (let loc of ['begin', 'end']) {

            form[filterBy][loc].range.addEventListener('change', (evt) => {
                update[filterBy][loc](
                    form[filterBy].begin.range, form[filterBy].end.range, form[filterBy].begin.label, form[filterBy].end.label
                );
            })

        }
    }
}

window.addEventListener('load', (evt) => {
    
    for (let form of [seed, show]) {
        for (let filterBy of ['date', 'id']) {
            config[filterBy](form[filterBy].begin.range, form[filterBy].end.range, form[filterBy].begin.label, form[filterBy].end.label)
        }
    }
})