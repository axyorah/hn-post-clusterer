class Comment extends AbstractItem {
    constructor(params) {
        super(params);
        this.ITEM_ID = params.commend_id;
    }

    static ENDPOINT = 'comments';
    static OPTIONAL = [];
    static SCHEMA = {
        'comment_id': ['number'],
        'author': ['string'],
        'unix_time': ['number'],
        'body': ['string', 'undefined'],
        'parent_id': ['number']
    };
}

class HNComment extends Comment {
    constructor(params) {
        super(params);

        this.type = params.type,
        this.deleted = params.deleted,
        this.dead = params.dead
    }

    HN_TO_DB = {
        'comment_id': 'id',
        'author': 'by',
        'unix_time': 'time',
        'body': 'text',
        'parent_id': 'parent',
        'type': 'type'
    }

    OPTIONAL = [
        'type', 'deleted', 'dead'
    ];

    static translateHN2DB = function (json) {
        const item = new Object();
        if (json === null) {
            return;
        } else if ('story_id' in json) {
            Object.keys(this.SCHEMA).forEach(key => {
                item[key] = json[this.SCHEMA[key]] !== undefined ? 
                    json[this.SCHEMA[key]] : null;
            });
        }
        return item;
    }
}