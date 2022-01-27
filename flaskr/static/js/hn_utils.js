class HNLoader {
    constructor(submitBtn, cancelBtn, logTextBox) {
        this.submitBtn = submitBtn;
        this.cancelBtn = cancelBtn;
        this.logTextBox = logTextBox;

        this._prepareButtons();
    }

    _prepareButtons = function() {
        const submitBtnInitInnerHTML = 'Get Data';
        const submitBtnInProgressInnerHTML = `${spinnerAmination} Getting Data from HN...`;

        this.cancelBtn.reset = function() {
            //this.hidden = true;
            this.style.display = 'none';
            this.clicked = false;
        };
        this.cancelBtn.ready = function() {
            //this.hidden = false;
            this.style.display = '';
            this.clicked = false;
        };
        this.cancelBtn.react = function() {
            //this.hidden = true;
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

        this.submitBtn.reset();
        this.cancelBtn.reset();
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
        const beginId = await fetchFirstIdOnDay(
            beginDate.getFullYear(), 
            beginDate.getMonth()+1,
            beginDate.getDate()
        );
        console.log(`first id on ${beginDate}: ${beginId}`);

        const endId = await fetchFirstIdOnDay(
            endDate.getFullYear(), 
            endDate.getMonth()+1,
            endDate.getDate()
        );
        console.log(`first id on ${endDate}: ${endId}`);

        return {
            'beginId': beginId,
            'endId': endId
        }
    }

    onSubmit = async function() {
        // give buttons appropriate look
        this.submitBtn.ready(); // in-progress animation
        this.cancelBtn.ready(); // unhide, unclick

        // read date range from form
        const {beginDate, endDate} = this._getDateRangeFromForm();

        // convert date range to id range
        const {beginId, endId} = await this._getIdRangeFromDateRange(
            beginDate, endDate)
        ;

        // fetch items from HN and add them to db
        // reset buttons at the end
        const go = async (id) => {
            if (!this.cancelBtn.clicked && id <= endId) {
                await this.maybeLoadItemWithKidsRecursively(id);
                setTimeout(() => go(id+1), 1);
            } else {
                this.submitBtn.reset();
                this.cancelBtn.reset();
            }
        }
    
        go(beginId)
        .catch(err => {
            this.submitBtn.reset();
            this.cancelBtn.reset();
    
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
                console.log(
                    `[${new Date().toISOString()}] ` +
                    `${id}: story already in db, skipping...`
                );
                return await Story.getOneById(id);
            } else if (item && item.type === 'comment') {
                console.log(
                    `[${new Date().toISOString()}] ` +
                    `${id}: comment already in db, skipping...`
                );
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
                console.log(msg);
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
                console.log(
                    `[${new Date().toISOString()}] ` +
                    `${id}: got ${'story_id' in item ? 'story' : 'comment'} from `+
                    `${new Date(parseInt(item.unix_time) * 1000).toISOString()}, `+
                    `adding to db... `
                );
                return item;
            }
        })
        .catch(err => console.log(err));
    }
}

const loader = new HNLoader(seedSubmitBtn, seedCancelBtn);