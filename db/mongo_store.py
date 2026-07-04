"""
MongoDB-backed store for raw ingested document content (bank statement
text, resume text, credit report text, ID scans) -- chosen over the
relational DB for this purpose because document content is inherently
semi/unstructured and varies in shape per document type, while
`db/models.py` (PostgreSQL) holds the normalized, query-heavy structured
records (applicants, applications, decisions) that benefit from relational
integrity and joins.

Falls back to an in-memory dict store if MongoDB isn't reachable, so the
prototype still runs standalone.
"""
import logging

from config import settings

logger = logging.getLogger(__name__)


class _InMemoryFallback:
    def __init__(self):
        self._store = {}

    def insert_one(self, doc: dict) -> str:
        doc_id = doc.get("_id") or str(len(self._store) + 1)
        doc["_id"] = doc_id
        self._store[doc_id] = doc
        return doc_id

    def find_one(self, doc_id: str):
        return self._store.get(doc_id)


class MongoDocumentStore:
    def __init__(self):
        self._client = None
        self._collection = None
        self._fallback = None
        try:
            from pymongo import MongoClient
            self._client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=1500)
            self._client.admin.command("ping")
            self._collection = self._client[settings.MONGO_DB]["raw_documents"]
            logger.info("Connected to MongoDB at %s", settings.MONGO_URI)
        except Exception as e:  # noqa: BLE001
            logger.warning("MongoDB unavailable (%s) - using in-memory fallback store.", e)
            self._fallback = _InMemoryFallback()

    def save_raw_document(self, application_id: str, doc_type: str, content) -> str:
        payload = {"application_id": application_id, "doc_type": doc_type, "content": content}
        if self._collection is not None:
            result = self._collection.insert_one(payload)
            return str(result.inserted_id)
        return self._fallback.insert_one(payload)

    def get_raw_document(self, mongo_ref: str):
        if self._collection is not None:
            from bson import ObjectId
            return self._collection.find_one({"_id": ObjectId(mongo_ref)})
        return self._fallback.find_one(mongo_ref)


mongo_store = MongoDocumentStore()
