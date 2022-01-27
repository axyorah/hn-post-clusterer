class Comment extends AbstractItem {
    constructor(params) {
        super(params);
        this.ITEM_ID = params.comment_id;
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

        this.ITEM_ID = params.id;
        this.type = params.type;
        this.deleted = params.deleted;
        this.dead = params.dead
    }

    static DB_TO_HN = {
        'comment_id': 'id',
        'author': 'by',
        'unix_time': 'time',
        'body': 'text',
        'parent_id': 'parent',
        'type': 'type'
    }

    static OPTIONAL = [
        'type', 'deleted', 'dead'
    ];

    static translateHN2DB = function (json) {
        const item = new Object();
        if (json === null) {
            return;
        } else if (json.type === 'comment') {
            Object.keys(this.SCHEMA).forEach(key => {
                item[key] = json[this.DB_TO_HN[key]] !== undefined ? 
                    json[this.DB_TO_HN[key]] : null;
            });
        }
        return new Comment(item);
    }
}