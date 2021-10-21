function getNewHNPostTable(morePostBtn) {
    // clear table
    tableRoot.innerHTML = '';
    const table = document.createElement('table');
    table.id = 'hn-post-table';
    tableRoot.appendChild(table);

    // create header
    const fields = ['Id', 'Time', 'Title', 'Score', '#Comments', 'Comments'];
    const trHead = document.createElement('tr');
    for (let i = 0; i < fields.length; i++ ) {
        const th = document.createElement('th');
        th.innerText = fields[i];
        th.setAttribute('class', `col_${i}`);
        trHead.appendChild(th);
    }
    table.appendChild(trHead);

    // [optional] add a button to show more posts
    if (morePostBtn) {
        tableRoot.appendChild(morePostBtn);
    }    

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
    const fields = ['story_id', 'unix_time', 'title', 'score', 'num_comments'];
    for (let storyId of Object.keys(data)) {        
        const tr = document.createElement('tr');
        
        for (let i = 0; i < fields.length; i++ ) {
            const td = document.createElement('td');
            td.setAttribute('class', `col_${i}`);

            if (fields[i] === 'unix_time') {
                const date = new Date(data[storyId][fields[i]] * 1000);
                td.innerText = `${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()}`;
            } else {
                td.innerText = data[storyId][fields[i]];
            }
            if (fields[i] === 'title') {
                td.innerHTML = 
                    (data[storyId]['url'] != null ? `<a href=${data[storyId]['url']} target='_blank'>${data[storyId][fields[i]]}</a>` : data[storyId][fields[i]]) + 
                    ` by ${data[storyId]['author']}`
            }
            tr.appendChild(td);
        }
        // add comments as details or popup
        const td = document.createElement('td');
        td.setAttribute('class', `col_${fields.length}`);
        // td.appendChild(getHTMLDetails('show', data[storyId]['children']));
        td.appendChild(getPopup(data[storyId]['children']));
        tr.appendChild(td);        
        
        // add row to table
        table.appendChild(tr);
    }
}

function getPopup(txt) {
    const popupBox = document.createElement('span');
    popupBox.setAttribute('class', 'popup');
    
    const clickable = document.createElement('code');
    clickable.setAttribute('class', 'mark');
    clickable.style.cursor = 'pointer';
    clickable.innerText = 'show';

    const popupText = document.createElement('span');
    popupText.setAttribute('class', 'popuptext');
    popupText.innerHTML = txt;

    popupBox.appendChild(clickable);
    popupBox.appendChild(popupText);

    popupBox.addEventListener('click', function (evt) {
        popupText.classList.toggle('show');
        console.log('popup clicked!');
    })

    return popupBox;
}
