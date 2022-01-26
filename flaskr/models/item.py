from typing import Any, Dict, List, Tuple, Set, Optional, Generator, Union

from flaskr.utils.db_utils import DBHelper

class Item:
    SCHEMA = [
        "item_id",
        "type"
    ]
    
    def __init__(self, 
        item_id=None, type=None,
        **kwargs # non-schema api kwargs, e.g., `deleled`, `type`, ...
    ):
        self.item_id = item_id
        self.type = type

    def json(self) -> Dict:
        return {
            "item_id": self.item_id,
            "type": self.type
        }

    @classmethod
    def find_by_id(cls, item_id: int) -> Optional['Item']:
        get_query = """
            SELECT parent_id AS item_id, parent_type AS type
            FROM parent WHERE parent_id = ?
        """
        rows = DBHelper.get_query(get_query, [item_id])
        if rows:
            return cls(**DBHelper.rows2dicts(rows)[0])

class ItemList:
    @classmethod
    def stats(cls) -> Dict:
        num_query = "SELECT COUNT(*) AS num FROM parent;"
        min_query = "SELECT MIN(parent_id) AS min FROM parent;"
        max_query = "SELECT MAX(parent_id) AS max FROM parent;"

        return {
            "num": DBHelper.get_query(num_query, [])[0].__getitem__("num"),
            "min": DBHelper.get_query(min_query, [])[0].__getitem__("min"),
            "max": DBHelper.get_query(max_query, [])[0].__getitem__("max")
        }

    @classmethod
    def find_by_ids(cls, id_list: List[int]) -> List[Item]:
        get_query = f"""
            SELECT parent_id AS item_id, parent_type AS type
            FROM parent 
            WHERE parent_id IN ({', '.join('?' for _ in id_list)})
        """
        rows = DBHelper.get_query(get_query, id_list)
        items = DBHelper.rows2dicts(rows)
        return [Item(**item) for item in items]
