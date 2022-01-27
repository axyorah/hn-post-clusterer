class Story {
    constructor(params) {
        this.story_id = params.story_id,
        this.author = params.author,
        this.unix_time = params.unix_time,
        this.body = params.body,
        this.url = params.url,
        this.score = params.score,
        this.title = params.title,
        this.num_comments = num_comments
    }

    SCHEMA = {
        'story_id': ['number'],
        'author': ['string'],
        'unix_time': ['number'],
        'body': ['string', 'undefined'],
        'url': ['string', 'undefined'],
        'score': ['number'],
        'title': ['string'],
        'num_comments': ['number']
    }

    OPTIONAL = ['body', 'url'];

    json = function () {
        return {
            'story_id': this.story_id !== undefined ? this.story_id : null,
            'author': this.author !== undefined ? this.author : null,
            'unix_time': this.unix_time !== undefined ? this.unix_time : null,
            'body': this.body !== undefined ? this.body : null,
            'url': this.url !== undefined ? this.url : null,
            'score': this.score !== undefined ? this.score : null,
            'title': this.title !== undefined ? this.title : null,
            'num_comments': this.num_comments !== undefined ? this.num_comments : null 
        }
    }

    static validateItem = function (item) {
        Object.keys(this.SCHEMA).forEach(key => {
            if (!(key in item) && !(key in this.OPTIONAL)) {
                throw ReferenceError(`Required '${key}' is missing!`);
            }
            if (!(typeof(item[key]) in this.SCHEMA[key])) {
                throw TypeError(
                    `Field ${key} should be ${this.SCHEMA[key].join(' or ')}, ` +
                    `got ${item[key]} of type ${typeof(item[key])}`
                );
            }
        });
    }

    validate = function() {
        Object.keys(this.SCHEMA).forEach(key => {
            if (
                (this[key] === undefined || this[key] === null) && 
               !(key in this.OPTIONAL)
            ) {
                throw ReferenceError(`Required '${key}' is missing!`);
            }
            if (!(typeof(this[key]) in this.SCHEMA[key])) {
                throw TypeError(
                    `Field ${key} should be ${this.SCHEMA[key].join(' or ')}, ` +
                    `got ${this[key]} of type ${typeof(this[key])}`
                );
            }
        });
    }

    static getOneById = async function (id) {
        return await fetch(`/api/stories/${id}/`)
        .then(res => res.json())
        .then(res => res.data)
        .catch(err => console.log(err));
    }

    static getManyByIds = async function (idList) {
        if (idList.constructor !== Array) {
            throw TypeError(
                `'idList' must be an Array, got ${idList}`
            );
        }
        return await fetch(`/api/stories?ids=${idList.join(',')}`)
        .then(res => res.json())
        .then(res => res.data)
        .catch(err => console.log(err))
    }

    add = async function () {
        this.validate();
        await postData(`/api/stories/`, this.json(), 'POST');
    }

    update = async function () {
        this.validate();
        await postData(`/api/stories/${this.story_id}`, this.json(), 'PUT');
    }

    delete = async function () {
        await postData(`/api/stories/${this.story_id}`, new Object(), 'DELETE');
    }    
}

class HNStory extends Story {
    constructor(params) {
        super(params);

        this.kids = params.kids,
        this.type = params.type,
        this.deleted = params.deleted,
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
        'type': 'type', // not in schema,
        'deleted': 'deleted',
        'dead': 'dead'
    }

    OPTIONAL = [
        'body', 'url', 'kids', 
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