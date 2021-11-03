from typing import Any, Dict, List, Tuple, Set, Optional, Generator, Union

import sqlite3
from flaskr.db import get_db, close_db

class DBHelper:    
    @classmethod
    def get_connection(cls) -> sqlite3.Cursor:
        return get_db()

    @classmethod
    def close_connection(cls) -> bool:
        close_db()
        return True

    @classmethod
    def row2dict(cls, row: sqlite3.Row) -> Dict:
        fields = row.keys()
        return {
            field: row.__getitem__(field)
            for field in fields
        }

    @classmethod
    def rows2dicts(cls, rows: List[sqlite3.Row]) -> List[Dict]:
        return [
            {
                field: row.__getitem__(field) 
                for field in row.keys()
            } for row in rows
        ]

    @classmethod
    def get_query(cls, query_pattern: str, params: Union[List,Tuple]) -> List[Optional[sqlite3.Row]]:
        db = cls.get_connection()
        rows = db.execute(query_pattern, tuple(params)).fetchall()
        cls.close_connection()
        return cls.rows2dicts(rows) if rows is not None else []

    @classmethod
    def mod_query(cls, query_pattern: str, params: Union[List,Tuple], commit: bool = True) -> List[Optional[sqlite3.Row]]:
        db = cls.get_connection()
        db.execute(query_pattern, tuple(params))
        if commit:
            db.commit()
        cls.close_connection()
        return True
