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

        this.ITEM_ID = params.id;
        this.children = params.children;
        this.kids = params.kids;
        this.type = params.type;
        this.deleted = params.deleted;
        this.dead = params.dead
    }

    static DB_TO_HN = {
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

    static OPTIONAL = [
        'body', 'url', 'kids', 'children',
        'type', 'deleted', 'dead'
    ];

    static translateHN2DB = function (json) {
        const item = new Object();
        if (json === null) {
            return;
        } else if (json.type === 'story') {
            Object.keys(this.SCHEMA).forEach(key => {
                item[key] = json[this.DB_TO_HN[key]] !== undefined ? 
                    json[this.DB_TO_HN[key]] : null;
            });
        }
        return new Story(item);
    }
}