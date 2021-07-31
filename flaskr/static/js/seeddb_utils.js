seedSubmitBtn = document.querySelector('#seed-submit-btn');

const seed = new Object();

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

seedSubmitBtn.addEventListener('click', (evt) => {
    seedSubmitBtn.innerHTML = 
    '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Getting Data from HN...'
})

for (let filterBy of ['date', 'id']) {
    for (let loc of ['begin', 'end']) {

        seed[filterBy][loc].range.addEventListener('change', (evt) => {
            // `update...` is defined in `index.js`
            update[filterBy][loc](
                seed[filterBy].begin.range, seed[filterBy].end.range, 
                seed[filterBy].begin.label, seed[filterBy].end.label
            );
        })

    }
}

window.addEventListener('load', (evt) => {
    for (let filterBy of ['date', 'id']) {            
        // `config...` is defined in `index.js`
        config[filterBy](
            seed[filterBy].begin.range, seed[filterBy].end.range, 
            seed[filterBy].begin.label, seed[filterBy].end.label,
            range[filterBy].min, range[filterBy].max
        )
    }
})