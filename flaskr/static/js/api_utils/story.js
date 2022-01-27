class Story extends AbstractItem{
    constructor(params) {
        super(params);
        this.ITEM_ID = params.story_id;
    }

    static ENDPOINT = 'stories';
    static OPTIONAL = ['body', 'url'];
    static SCHEMA = {
        'story_id': ['number'],
        'author': ['string'],
        'unix_time': ['number'],
        'body': ['string', 'undefined', 'object'],
        'url': ['string', 'undefined', 'object'],
        'score': ['number'],
        'title': ['string'],
        'num_comments': ['number']
    };
}

class HNStory extends Story {
    constructor(params) {
        super(params);

        this.children = params.children;
        this.kids = params.kids;
        this.type = params.type;
        this.deleted = params.deleted;
        this.dead = params.dead
    }

    HN_TO_DB = {
        'story_id': 'id',
        'author': 'by',
        'unix_time': 'time',
        'body': 'text',
        'url': 'url',
        'score': 'score',
        'title': 'title',
        'num_comments': 'descendants',
        'kids': 'kids', // not in schema but we need it...
        'children': 'children', // not in schema,
        'type': 'type', // not in schema,
        'deleted': 'deleted',
        'dead': 'dead'
    }

    OPTIONAL = [
        'body', 'url', 'kids', 'children',
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