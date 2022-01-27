class Item {
    constructor(params) {
        this.item_id = params.item_id,
        this.type = params.type
    }

    SCHEMA = {
        'item_id': ['number'],
        'type': ['string'],
    }

    OPTIONAL = [];

    json = function () {
        return {
            'item_id': this.item_id !== undefined ? this.item_id : null,
            'type': this.type !== undefined ? this.type : null,
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
        return await fetch(`/api/items/${id}/`)
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
        return await fetch(`/api/items?ids=${idList.join(',')}`)
        .then(res => res.json())
        .then(res => res.data)
        .catch(err => console.log(err))
    }

    add = async function () {
        return;
    }

    update = async function () {
        return;
    }

    delete = async function () {
        return;
    }    
}

class HNItem extends Item {
    constructor(params) {
        super(params);

        this.deleted = params.deleted,
        this.dead = params.dead
    }
}