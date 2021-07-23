container = document.querySelector('.container');

seedBeginDateRange = document.querySelector('#seed-begin-date-range');
seedEndDateRange = document.querySelector('#seed-end-date-range');
seedBeginDateLabel = document.querySelector('#seed-begin-date-label');
seedEndDateLabel = document.querySelector('#seed-end-date-label');

seedBeginIdRange = document.querySelector('#seed-begin-id-range');
seedEndIdRange = document.querySelector('#seed-end-id-range');
seedBeginIdLabel = document.querySelector('#seed-begin-id-label');
seedEndIdLabel = document.querySelector('#seed-end-id-label');

showBeginDateRange = document.querySelector('#show-begin-date-range');
showEndDateRange = document.querySelector('#show-end-date-range');
showBeginDateLabel = document.querySelector('#show-begin-date-label');
showEndDateLabel = document.querySelector('#show-end-date-label');

showBeginIdRange = document.querySelector('#show-begin-id-range');
showEndIdRange = document.querySelector('#show-end-id-range');
showBeginIdLabel = document.querySelector('#show-begin-id-label');
showEndIdLabel = document.querySelector('#show-end-id-label');

// Globals
const minTS = new Date(2006, 10, 9).valueOf();
const maxTS = new Date().valueOf();

const minID = 27750741
const maxID = 27752765


// Helpers
configDateRangesAndLabels = function (beginRange, endRange, beginLabel, endLabel) {
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
}

configIdRangesAndLabels = function (beginRange, endRange, beginLabel, endLabel) {
    beginRange.min = minID;
    beginRange.max = maxID;
    beginRange.value = minID;

    endRange.min = minID;
    endRange.max = maxID;
    endRange.value = maxID;

    beginLabel.innerText = `From: ${minID}`;
    endLabel.innerText = `To: ${maxID}`;
}

updateBeginDateRange = function (beginRange, endRange, beginLabel, endLabel) {
    let beginVal = parseInt(beginRange.value);
    let endVal = parseInt(endRange.value);
    if (beginVal >= endVal) {
        beginVal = endVal - 1000 * 60 * 60 * 24;
        beginRange.value = beginVal;
    }
    const [m, d, y] = new Date(beginVal).toLocaleDateString().split('/');
    beginLabel.innerText = `From: ${y}/${m}/${d}`;
}

updateEndDateRange = function (beginRange, endRange, beginLabel, endLabel) {
    let beginVal = parseInt(beginRange.value);
    let endVal = parseInt(endRange.value);
    if (endVal <= beginVal) {
        endVal = beginVal + 1000 * 60 * 60 * 24;
        endDateRange.value = endVal;
    }
    const [m, d, y] = new Date(endVal).toLocaleDateString().split('/');
    endLabel.innerText = `To: ${y}/${m}/${d}`;
}

updateBeginIdRange = function(beginRange, endRange, beginLabel, endLabel) {
    let beginVal = parseInt(beginRange.value);
    let endVal = parseInt(endRange.value);
    if (beginVal >= endVal) {
        beginVal = endVal - 1;
        beginRange.value = beginVal;
    }
    beginLabel.innerText = `From: ${beginVal}`;
}

updateEndIdRange = function (beginRange, endRange, beginLabel, endLabel) {
    let beginVal = parseInt(beginRange.value);
    let endVal = parseInt(endRange.value);
    if (endVal <= beginVal) {
        endVal = beginVal + 1;
        endRange.value = endVal;
    }
    endLabel.innerText = `To: ${endVal}`;
}


// Event Listeners
seedBeginDateRange.addEventListener('change', (evt) => {
    updateBeginDateRange(
        seedBeginDataRange, seedEndDataRange, seedBeginDateLabel, seedEndDateLabel
    );
})

seedEndDateRange.addEventListener('change', (evt) => {
    updateEndDateRange(
        seedBeginDateRange, seedEndDateRange, seedBeginDateLabel, seedEndDataLabel
    );
})

showBeginDateRange.addEventListener('change', (evt) => {
    updateBeginDateRange(
        showBeginDataRange, showEndDataRange, showBeginDateLabel, showEndDateLabel
    );
})

showEndDateRange.addEventListener('change', (evt) => {
    updateEndDateRange(
        showBeginDateRange, showEndDateRange, showBeginDateLabel, showEndDataLabel
    );
})

seedBeginIdRange.addEventListener('change', (evt) => {
    updateBeginIdRange(
        seedBeginIdRange, seedEndIdRange, seedBeginIdLabel, seedEndIdLabel
    );
})

seedEndIdRange.addEventListener('change', (evt) => {
    updateEndIdRange(
        seedBeginIdRange, seedEndIdRange, seedBeginIdLabel, seedEndIdLabel
    )
})

showBeginIdRange.addEventListener('change', (evt) => {
    updateBeginIdRange(
        showBeginIdRange, showEndIdRange, showBeginIdLabel, showEndIdLabel
    );
})

showEndIdRange.addEventListener('change', (evt) => {
    updateEndIdRange(
        showBeginIdRange, showEndIdRange, showBeginIdLabel, showEndIdLabel
    )
})

window.addEventListener('load', (evt) => {
    configDateRangesAndLabels(
        seedBeginDateRange, seedEndDateRange, seedBeginDateLabel, seedEndDateLabel
    );
    configDateRangesAndLabels(
        showBeginDateRange, showEndDateRange, showBeginDateLabel, showEndDateLabel
    );
    configIdRangesAndLabels(
        seedBeginIdRange, seedEndIdRange, seedBeginIdLabel, seedEndIdLabel
    );
    configIdRangesAndLabels(
        showBeginIdRange, showEndIdRange, showBeginIdLabel, showEndIdLabel
    );
})