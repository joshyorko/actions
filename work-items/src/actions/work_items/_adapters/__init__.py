"""
Adapters for work item storage backends.

Available adapters:
- SQLiteAdapter: Persistent local storage using SQLite database
- FileAdapter: JSON file-based storage compatible with Control Room format
- RedisAdapter: Redis-backed work item storage
- DocumentDBAdapter: MongoDB-compatible DocumentDB-backed work item storage
"""

from ._base import BaseAdapter, ManagedAdapter, RuntimeAdapter
from ._docdb import DocumentDBAdapter
from ._file import FileAdapter
from ._redis import RedisAdapter
from ._sqlite import SQLiteAdapter

__all__ = [
    "BaseAdapter",
    "RuntimeAdapter",
    "ManagedAdapter",
    "FileAdapter",
    "SQLiteAdapter",
    "RedisAdapter",
    "DocumentDBAdapter",
]
