container = document.querySelector('.container');
seedSubmitBtn = document.querySelector('#seed-submit-btn');
showSubmitBtn = document.querySelector('#show-submit-btn');

// form fields
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
        seed[filterBy][loc]['range'] = document.querySelector(`#seed-${filterBy}-${loc}-range`);
        seed[filterBy][loc]['label'] = document.querySelector(`#seed-${filterBy}-${loc}-label`);
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
        show[filterBy][loc]['range'] = document.querySelector(`#show-${filterBy}-${loc}-range`);
        show[filterBy][loc]['label'] = document.querySelector(`#show-${filterBy}-${loc}-label`);
    }
}

const range = {
    date: {
        min: new Date(2006, 10, 9).valueOf(),
        max: new Date().valueOf()
    }, 

    id: {
        min: 27750741,
        max: 27752765
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


// Event Listeners
seedSubmitBtn.addEventListener('click', (evt) => {
    seedSubmitBtn.innerHTML = 
    '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Getting Data from HN...'
})

for (let form of [seed, show]) {
    
    const filterList = (form === seed) ? ['date', 'id'] : ['date', 'id', 'comm', 'score'];
    
    for (let filterBy of filterList) {
        for (let loc of ['begin', 'end']) {

            form[filterBy][loc].range.addEventListener('change', (evt) => {
                update[filterBy][loc](
                    form[filterBy].begin.range, form[filterBy].end.range, 
                    form[filterBy].begin.label, form[filterBy].end.label
                );
            })

        }
    }

}

window.addEventListener('load', (evt) => {    
    for (let form of [seed, show]) {
        
        const filterList = (form === seed) ? ['date', 'id'] : ['date', 'id', 'comm', 'score'];
        
        for (let filterBy of filterList) {
            
            config[filterBy](
                form[filterBy].begin.range, form[filterBy].end.range, 
                form[filterBy].begin.label, form[filterBy].end.label,
                range[filterBy].min, range[filterBy].max
            )

        }

    }
})