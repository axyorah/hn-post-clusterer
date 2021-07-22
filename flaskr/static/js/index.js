container = document.querySelector('.container');

beginDateRange = document.querySelector('#begin-date-range');
endDateRange = document.querySelector('#end-date-range');
beginDateLabel = document.querySelector('#begin-date-label');
endDateLabel = document.querySelector('#end-date-label');

beginIdRange = document.querySelector('#begin-id-range');
endIdRange = document.querySelector('#end-id-range');
beginIdLabel = document.querySelector('#begin-id-label');
endIdLabel = document.querySelector('#end-id-label');

const minTS = new Date(2006, 10, 9).valueOf();
const maxTS = new Date().valueOf();

const minID = 27750741
const maxID = 27752765

const configDateRangesAndLabels = () => {
    beginDateRange.min = minTS;
    beginDateRange.max = maxTS;
    beginDateRange.value = minTS;

    endDateRange.min = minTS;
    endDateRange.max = maxTS;
    endDateRange.value = maxTS;

    const [m0, d0, y0] = new Date(minTS).toLocaleDateString().split('/');
    const [mf, df, yf] = new Date(maxTS).toLocaleDateString().split('/');
    beginDateLabel.innerText = `From: ${y0}/${m0}/${d0}`;
    endDateLabel.innerText = `To: ${yf}/${mf}/${df}`;
}

const configIdRangesAndLabels = () => {
    beginIdRange.min = minID;
    beginIdRange.max = maxID;
    beginIdRange.value = minID;

    endIdRange.min = minID;
    endIdRange.max = maxID;
    endIdRange.value = maxID;

    beginIdLabel.innerText = `From: ${minID}`;
    endIdLabel.innerText = `To: ${maxID}`;
}

beginDateRange.addEventListener('change', (evt) => {
    let beginVal = parseInt(beginDateRange.value);
    let endVal = parseInt(endDateRange.value);
    if (beginVal >= endVal) {
        beginVal = endVal - 1000 * 60 * 60 * 24;
        beginDateRange.value = beginVal;
    }
    const [m, d, y] = new Date(beginVal).toLocaleDateString().split('/');
    beginDateLabel.innerText = `From: ${y}/${m}/${d}`;
})


endDateRange.addEventListener('change', (evt) => {
    let beginVal = parseInt(beginDateRange.value);
    let endVal = parseInt(endDateRange.value);
    if (endVal <= beginVal) {
        endVal = beginVal + 1000 * 60 * 60 * 24;
        endDateRange.value = endVal;
    }
    const [m, d, y] = new Date(endVal).toLocaleDateString().split('/');
    endDateLabel.innerText = `To: ${y}/${m}/${d}`;
})

beginIdRange.addEventListener('change', (evt) => {
    let beginVal = parseInt(beginIdRange.value);
    let endVal = parseInt(endIdRange.value);
    if (beginVal >= endVal) {
        beginVal = endVal - 1;
        beginIdRange.value = beginVal;
    }
    beginIdLabel.innerText = `From: ${beginVal}`;
})


endIdRange.addEventListener('change', (evt) => {
    let beginVal = parseInt(beginIdRange.value);
    let endVal = parseInt(endIdRange.value);
    if (endVal <= beginVal) {
        endVal = beginVal + 1;
        endIdRange.value = endVal;
    }
    endIdLabel.innerText = `To: ${endVal}`;
})

window.addEventListener('load', (evt) => {
    configDateRangesAndLabels();
    configIdRangesAndLabels();
})