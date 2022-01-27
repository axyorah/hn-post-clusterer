class AbstractItem {
    constructor(params) {
        Object.keys(params).forEach(key => {
            this[key] = params[key];
        });
        this.ITEM_ID;
    }

    static ENDPOINT = '';
    static SCHEMA = new Object();
    static OPTIONAL = new Array();

    json = function () {
        const item = new Object();
        Object.keys(this.SCHEMA).forEach(key => {
            item[key] = (this[key] !== undefined) ? this[key] : null;
        })
        return item;
    }

    static validateItem = function (item) {
        Object.keys(this.SCHEMA).forEach(key => {
            if (!(key in item) && !(this.OPTIONAL.includes(key))) {
                throw ReferenceError(`Required '${key}' is missing!`);
            }
            if (!(this.SCHEMA[key].includes(typeof(item[key])))) {
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
               !(this.OPTIONAL.includes(key))
            ) {
                throw ReferenceError(`Required '${key}' is missing!`);
            }
            if (!(this.SCHEMA[key].includes(typeof(this[key])))) {
                throw TypeError(
                    `Field ${key} should be ${this.SCHEMA[key].join(' or ')}, ` +
                    `got ${this[key]} of type ${typeof(this[key])}`
                );
            }
        });
    }

    static getOneById = async function (id) {
        return await fetch(`/api/${this.ENDPOINT}/${id}/`)
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
        return await fetch(`/api/${this.ENDPOINT}?ids=${idList.join(',')}`)
        .then(res => res.json())
        .then(res => res.data)
        .catch(err => console.log(err))
    }

    add = async function () {
        this.validate();
        await postData(`/api/${this.ENDPOINT}/`, this.json(), 'POST');
    }

    update = async function () {
        this.validate();
        await postData(`/api/${this.ENDPOINT}/${this.ITEM_ID}`, this.json(), 'PUT');
    }

    delete = async function () {
        await postData(`/api/${this.ENDPOINT}/${this.ITEM_ID}`, new Object(), 'DELETE');
    }
}
