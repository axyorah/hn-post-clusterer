class Comment {
    constructor(params) {
        this.comment_id = params.comment_id,
        this.author = params.author,
        this.unix_time = params.unix_time,
        this.body = params.body,
        this.parent_id = params.parent_id
    }

    SCHEMA = {
        'comment_id': ['number'],
        'author': ['string'],
        'unix_time': ['number'],
        'body': ['string', 'undefined'],
        'parent_id': ['number']
    }

    OPTIONAL = [];

    json = function () {
        return {
            'comment_id': this.comment_id !== undefined ? this.comment_id : null,
            'author': this.author !== undefined ? this.author : null,
            'unix_time': this.unix_time !== undefined ? this.unix_time : null,
            'body': this.body !== undefined ? this.body : null,
            'parent_id': this.parent_id !== undefined ? this.parent_id : null
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
        return await fetch(`/api/comments/${id}/`)
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
        return await fetch(`/api/comments?ids=${idList.join(',')}`)
        .then(res => res.json())
        .then(res => res.data)
        .catch(err => console.log(err))
    }

    add = async function () {
        this.validate();
        await postData(`/api/comments/`, this.json(), 'POST');
    }

    update = async function () {
        this.validate();
        await postData(`/api/comments/${this.comment_id}`, this.json(), 'PUT');
    }

    delete = async function () {
        await postData(`/api/comments/${this.comment_id}`, new Object(), 'DELETE');
    }    
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