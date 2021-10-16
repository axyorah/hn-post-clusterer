const spinnerAmination = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';

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

function filterAbyBwhereBisC(a, b, c) {
    const indices = [...Array(a.length).keys()];
    return indices.map(i => {
        if (b[i] === c) {return a[i];}
    }).filter(val => val !== undefined);
}

function addAlertMessage(message) {
    const alert = document.createElement('div');
    alert.setAttribute('class', 'alert alert-danger alert-dismissible fade show');
    alert.setAttribute('role', 'alert');
    alert.style.justifyContent = "space-between";
    alert.style.opacity = "0.7";
    alert.style.margin = "0px";

    const msg = document.createElement('p');
    msg.style.margin = "0px";
    msg.innerText = message;

    const btn = document.createElement('button');
    btn.setAttribute('class', 'btn-close');
    btn.setAttribute('data-bs-dismiss', 'alert');
    btn.setAttribute('aria-label', 'Close');
    btn.style.margin = "0px";

    alert.appendChild(msg);
    alert.appendChild(btn);

    alertRoot.append(alert);
}

function checkForServerErrors(res) {
    if (!res.ok) {
        throw new Error(res.errors);
    }
    return res;
}