const tabs = document.querySelectorAll('.nav-link');

window.addEventListener('load', function (evt) {
    for (let t of tabs) {
        t.style.borderRadius = "3px 3px 0px 0px";
        t.style.backgroundColor = "rgba(0,0,0,0)";
        t.style.color = "rgb(100,100,100)"
    }
    // tabs[0].style.backgroundColor = "rgb(76, 73, 82)";
    tabs[0].style.backgroundImage = "linear-gradient(rgb(76, 73, 82), rgb(40, 38, 43))";
    tabs[0].style.borderBottom = "1px solid rgb(40, 38, 43)";
    tabs[0].style.color = "white";
})

for (let tab of tabs) {
    tab.addEventListener('click', function (evt) {
        for (let t of tabs) {
            t.style.backgroundImage = "none";
            t.style.color = "rgb(100,100,100)";   
            t.style.borderBottom = "1px solid white";                 
        }
        // this.style.backgroundColor = "rgb(76, 73, 82)";
        this.style.backgroundImage = "linear-gradient(rgb(76, 73, 82), rgb(40, 38, 43))";
        this.style.borderBottom = "1px solid rgb(40, 38, 43)";
        this.style.color = "white";
    })
}        