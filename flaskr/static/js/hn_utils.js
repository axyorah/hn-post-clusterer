class HNLoader {
    constructor(submitBtn, cancelBtn, logTextBox) {
        this.submitBtn = submitBtn;
        this.cancelBtn = cancelBtn;
        this.logTextBox = logTextBox;

        this.logLimit = 500;

        this._init();
    }

    _init = function() {
        const submitBtnInitInnerHTML = 'Get Data';
        const submitBtnInProgressInnerHTML = `${spinnerAmination} Getting Data from HN...`;

        this.cancelBtn.reset = function() {
            this.style.display = 'none';
            this.clicked = false;
        };
        this.cancelBtn.ready = function() {
            this.style.display = '';
            this.clicked = false;
        };
        this.cancelBtn.react = function() {
            this.style.display = 'none';
            this.clicked = true;
        };

        this.submitBtn.reset = function() {
            this.innerHTML = submitBtnInitInnerHTML;
        };
        this.submitBtn.ready = function() {
            this.innerHTML = submitBtnInProgressInnerHTML;
        };

        this.cancelBtn.addEventListener('click', (evt) => {
            this.submitBtn.reset();
            this.cancelBtn.react();
        });

        this.submitBtn.addEventListener('click', (evt) => {
            this.onSubmit();
        });

        this.logTextBox.reset = function() {
            this.style.display = 'none';
            this.innerHTML = '';
        }

        this.logTextBox.ready = function() {
            this.style.display = 'block';
            this.innerHTML = '';
        }

        this.submitBtn.reset();
        this.cancelBtn.reset();
        this.logTextBox.reset();
    }

    _getDateRangeFromForm = function () {
        const beginDate = getDateFromDateNode(seedDateBeginRoot);
        const endDate = getDateFromDateNode(seedDateEndRoot);
    
        addDateToNode(beginDate, seedDateBeginRoot);
        addDateToNode(endDate, seedDateEndRoot);
    
        if (beginDate.valueOf() > endDate.valueOf()) {
            const msg = '`From`-date should come before `To`-date';
            addAlertMessage(msg);
            throw Error(msg);
        }

        return {
            'beginDate': beginDate,
            'endDate': endDate
        }
    }

    _getIdRangeFromDateRange = async function (beginDate, endDate) {
        let msg;

        const beginId = await fetchFirstIdOnDay(
            beginDate.getFullYear(), 
            beginDate.getMonth()+1,
            beginDate.getDate()
        );
        msg = (`first id on ${beginDate.toDateString()}: ${beginId}`);
        //console.log(msg);
        this.logTextBox.innerHTML = 
            this.logTextBox.innerHTML + `<span>${msg}</br></span>`;

        const endId = await fetchFirstIdOnDay(
            endDate.getFullYear(), 
            endDate.getMonth()+1,
            endDate.getDate()
        );
        msg = (`first id on ${endDate.toDateString()}: ${endId}`);
        //console.log(msg);
        this.logTextBox.innerHTML = 
            this.logTextBox.innerHTML + `<span>${msg}</br></span>`;

        return {
            'beginId': beginId,
            'endId': endId
        }
    }

    onSubmit = async function() {
        // give buttons appropriate look
        this.submitBtn.ready(); // in-progress animation
        this.cancelBtn.ready(); // unhide, unclick
        this.logTextBox.ready(); // show cleared log window

        // read date range from form
        const {beginDate, endDate} = this._getDateRangeFromForm();

        // convert date range to id range
        const {beginId, endId} = await this._getIdRangeFromDateRange(
            beginDate, endDate
        );

        // fetch items from HN and add them to db
        // adjust log length on each step (in needed)
        // reset buttons at the end
        const go = async (id) => {
            if (!this.cancelBtn.clicked && id <= endId) {
                await this.maybeLoadItemWithKidsRecursively(id);
                while (this.logTextBox.children.length >= this.logLimit) {
                    this.logTextBox.removeChild(this.logTextBox.firstChild);
                }
                setTimeout(() => go(id+1), 1);
            } else {
                this.submitBtn.reset();
                this.cancelBtn.reset();
                //this.logTextBox.reset(); // <-- keep log!
            }
        }
    
        go(beginId)
        .catch(err => {
            this.submitBtn.reset();
            this.cancelBtn.reset();
            //this.logTextBox.reset(); // <-- keep log!
    
            console.log(err);
            addAlertMessage(err);
        });
    }

    maybeLoadItemWithKidsRecursively = async function (id) {
        await this.maybeLoadSingleItem(id)
        .then(item => {
            if (item && item.kids) {
                item.kids.forEach(childId => {
                    if (childId > endId) {
                        this.maybeLoadItemWithKidsRecursively(childId);
                    }
                });
            }
        });
    }

    maybeLoadSingleItem = async function (id) {
        /*
        checks if item with given id is already in db:
        - if item is comment and it is in db - skips
        - if item is story and it is in db - skips
        - if item is not in db: fetches it from hn and adds it to db
        */
       return await Item.getOneById(id)
       .then(async (item) => {
           if (item && item.type === 'story') {
                const msg = (
                    `[${new Date().toISOString()}] ` +
                    `${id}: story already in db, skipping...`
                );
                //console.log(msg);
                this.logTextBox.innerHTML = 
                    this.logTextBox.innerHTML + `<span>${msg}</br></span>`;
                return await Story.getOneById(id);
            } else if (item && item.type === 'comment') {
                const msg = (
                    `[${new Date().toISOString()}] ` +
                    `${id}: comment already in db, skipping...`
                );
                //console.log(msg);
                this.logTextBox.innerHTML = 
                    this.logTextBox.innerHTML + `<span>${msg}</br></span>`;
                return await Comment.getOneById(id);
            } else {
                return await this.loadSingleItem(id);
            }
        });
    }

    loadSingleItem = async function(id) {
        return await fetch(
            `https://hacker-news.firebaseio.com/v0/item/${id}.json`
        )
        .then(res => res.json())
        .then(res => {
            // skip if empty, deleted or dead
            if (!res || res.deleted || res.dead) {
                const msg = (
                    `[${new Date().toISOString()}] `+
                    `${id}: got empty, deleted or dead, skipping...`
                );
                //console.log(msg);
                this.logTextBox.innerHTML = 
                    this.logTextBox.innerHTML + `<span>${msg}</br></span>`;
                return;
            } else {
                return res;
            }
        })
        .then(res => {
            if (!res || res === undefined) {
                return;
            } else if (res.type && res.type === 'story') {
                const story = HNStory.translateHN2DB(res);
                story.add();
                return story.json();
            } else if (res.type && res.type === 'comment') {
                const comment = HNComment.translateHN2DB(res);
                comment.add();
                return comment.json();
            }
        })
        .then(item => {
            if (item) {
                const msg = (
                    `[${new Date().toISOString()}] ` +
                    `${id}: got ${'story_id' in item ? 'story' : 'comment'} from `+
                    `${new Date(parseInt(item.unix_time) * 1000).toISOString()}, `+
                    `adding to db... `
                );
                //console.log(msg);
                this.logTextBox.innerHTML = 
                    this.logTextBox.innerHTML + `<span>${msg}</br></span>`;
                return item;
            }
        })
        .catch(err => console.log(err));
    }
}

const loader = new HNLoader(
    seedSubmitBtn, seedCancelBtn, logTextBox
);