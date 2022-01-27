class Item extends AbstractItem {
    constructor(params) {
        super(params);
        this.ITEM_ID = params.item_id;
    }

    static ENDPOINT = 'items';
    static OPTIONAL = [];
    static SCHEMA = {
        'item_id': ['number'],
        'type': ['string'],
    };

    add = async function () {
        console.log(
            'Item cannot be modified directly; '+
            'it will be automatically modified when corresponding '+
            '"Story" or "Comment" is modified.'
        );
        return;
    }

    update = async function () {
        console.log(
            'Item cannot be modified directly; '+
            'it will be automatically modified when corresponding '+
            '"Story" or "Comment" is modified.'
        );
        return;
    }

    delete = async function () {
        console.log(
            'Item cannot be modified directly; '+
            'it will be automatically modified when corresponding '+
            '"Story" or "Comment" is modified.'
        );
        return;
    }    
}

class HNItem extends Item {
    constructor(params) {
        super(params);

        this.ITEM_ID = params.id;
        this.deleted = params.deleted,
        this.dead = params.dead
    }
}