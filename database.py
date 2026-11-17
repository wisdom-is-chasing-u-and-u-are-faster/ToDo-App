import os
import logging
from flask import Flask
from flask_pymongo import PyMongo
from datetime import datetime as dt

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb://localhost:27017/myDatabase")

# Initialize PyMongo or in-memory fallback
try:
    mongo = PyMongo(app, serverSelectionTimeoutMS=1000)
except Exception:
    mongo = None

# In-memory storage fallback for standalone / demo / Cloud Run executions without external MongoDB
_in_memory_tasks = [
    {
        "title": "Quarterly Audit Wrap-up",
        "description": "Auditing and compliance review",
        "datetime": "2025-10-20 14:30:00",
        "priority": "high",
        "status": "Done"
    },
    {
        "title": "Firewall Rule Hardening",
        "description": "Hardening gateway firewalls",
        "datetime": "2025-10-21 09:15:00",
        "priority": "medium",
        "status": "Done"
    },
    {
        "title": "SAN Storage Rebalancing",
        "description": "Rebalancing storage pools",
        "datetime": "2025-10-22 11:00:00",
        "priority": "low",
        "status": "Done"
    },
    {
        "title": "Active Backlog Grooming",
        "description": "Review sprint backlog items",
        "datetime": "2025-10-23 10:00:00",
        "priority": "high",
        "status": "Pending"
    }
]


def _mongo_is_available():
    """Check if MongoDB is reachable; otherwise gracefully fallback to in-memory store."""
    if not mongo or not hasattr(mongo, "db") or mongo.db is None:
        return False
    # If mongo.db is a mock (e.g. in pytest with mongomock), use it directly
    if mongo.db.__class__.__module__.startswith("mongomock"):
        return True
    try:
        mongo.cx.admin.command("ping")
        return True
    except Exception:
        return False


class myDatabase:
    @staticmethod
    def ensure_indexes():
        """Ensure compound indexes for optimized filtering and export queries."""
        try:
            if _mongo_is_available():
                mongo.db.inventory.create_index([("status", 1), ("priority", 1)])
                mongo.db.inventory.create_index([("datetime", 1)])
        except Exception:
            pass

    @staticmethod
    def addData(title, description, datetime, priority="medium", status="Pending"):
        myDatabase.ensure_indexes()
        doc = {
            "title": str(title),
            "description": str(description),
            "datetime": str(datetime),
            "priority": str(priority),
            "status": str(status)
        }
        if _mongo_is_available():
            try:
                mongo.db.inventory.insert_one(doc)
                return
            except Exception:
                pass
        _in_memory_tasks.append(doc)

    @staticmethod
    def findData(datetime):
        if _mongo_is_available():
            try:
                projection = {"_id": 0, "title": 1, "description": 1, "datetime": 1, "priority": 1, "status": 1}
                return mongo.db.inventory.find_one({"datetime": datetime}, projection)
            except Exception:
                pass
        for task in _in_memory_tasks:
            if task.get("datetime") == datetime:
                return {
                    "title": task.get("title", ""),
                    "description": task.get("description", ""),
                    "datetime": task.get("datetime", ""),
                    "priority": task.get("priority", "medium"),
                    "status": task.get("status", "Pending")
                }
        return None

    @staticmethod
    def showData(priority=None):
        normalized_priority = None
        if priority and isinstance(priority, str):
            p = priority.strip().lower()
            if p in {"low", "medium", "high"}:
                normalized_priority = p

        if _mongo_is_available():
            try:
                query = {}
                if normalized_priority:
                    query["priority"] = normalized_priority
                projection = {"_id": 0, "title": 1, "description": 1, "datetime": 1, "priority": 1, "status": 1}
                return mongo.db.inventory.find(query, projection)
            except Exception:
                pass

        # In-memory fallback
        results = []
        for task in _in_memory_tasks:
            task_priority = str(task.get("priority", "medium")).lower()
            if normalized_priority is None or task_priority == normalized_priority:
                results.append({
                    "title": task.get("title", ""),
                    "description": task.get("description", ""),
                    "datetime": task.get("datetime", ""),
                    "priority": task.get("priority", "medium"),
                    "status": task.get("status", "Pending")
                })
        return results

    @staticmethod
    def get_completed_tasks():
        """Query historical completed tasks (status='Done' or 'completed')."""
        if _mongo_is_available():
            try:
                query = {"status": {"$in": ["Done", "completed", "done", "Completed"]}}
                projection = {"_id": 0, "title": 1, "status": 1, "priority": 1, "description": 1, "datetime": 1}
                return list(mongo.db.inventory.find(query, projection))
            except Exception:
                pass

        results = []
        for task in _in_memory_tasks:
            if str(task.get("status", "")).lower() in {"done", "completed"}:
                results.append({
                    "title": task.get("title", ""),
                    "status": task.get("status", "Done"),
                    "priority": task.get("priority", "medium"),
                    "description": task.get("description", ""),
                    "datetime": task.get("datetime", "")
                })
        return results

    @staticmethod
    def updateData(title, description, datetime, priority=None, status=None):
        new_dt = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        update_fields = {
            "title": title,
            "description": description,
            "datetime": new_dt
        }
        if priority:
            update_fields["priority"] = priority
        if status:
            update_fields["status"] = status

        if _mongo_is_available():
            try:
                mongo.db.inventory.update_one({"datetime": datetime}, {"$set": update_fields})
                return
            except Exception:
                pass

        for task in _in_memory_tasks:
            if task.get("datetime") == datetime:
                task.update(update_fields)
                break

    @staticmethod
    def deleteData(datetime):
        if _mongo_is_available():
            try:
                mongo.db.inventory.delete_one({"datetime": datetime})
                return
            except Exception:
                pass

        global _in_memory_tasks
        _in_memory_tasks = [t for t in _in_memory_tasks if t.get("datetime") != datetime]
