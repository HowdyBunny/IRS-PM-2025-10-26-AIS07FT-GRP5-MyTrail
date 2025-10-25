"""
User feedback service for storing and retrieving route selection data
using MongoDB as the persistence layer. Falls back to no-op mode if MongoDB is unavailable.
"""
from datetime import datetime
from typing import List, Optional

from app.config import settings
from app.models.feedback import RouteFeedback

# Try to import MongoDB dependencies, but don't fail if they're not available
try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
    from pymongo.errors import PyMongoError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    print("⚠️ PyMongo not available. Feedback functionality will be disabled.")


class FeedbackService:
    """Service for managing user feedback data in MongoDB or no-op mode"""

    def __init__(
        self,
        mongo_uri: Optional[str] = None,
        database_name: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        self.mongo_uri = mongo_uri or settings.mongo_uri
        self.database_name = database_name or settings.mongo_db_name
        self.collection_name = (
            collection_name or settings.mongo_feedback_collection
        )
        
        self.mongodb_available = False
        self.client = None
        self.collection = None
        
        # Try to initialize MongoDB connection if dependencies are available
        if MONGODB_AVAILABLE:
            try:
                self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=2000)
                # Test connection
                self.client.server_info()
                self.collection = self.client[self.database_name][self.collection_name]
                self.mongodb_available = True
                self._init_collection()
                print("✅ MongoDB connection established for feedback storage")
            except Exception as e:
                print(f"⚠️ MongoDB not available: {e}")
                print("💡 Feedback functionality will be disabled")
                self.mongodb_available = False
        else:
            print("💡 MongoDB dependencies not available. Feedback functionality disabled.")
            self.mongodb_available = False

    def _init_collection(self) -> None:
        """Create indexes that support frequent query patterns."""
        if not self.mongodb_available or not self.collection:
            return
            
        try:
            self.collection.create_index("route_id")
            self.collection.create_index("selected")
            self.collection.create_index("timestamp")
        except Exception as exc:
            print(f"Error initializing feedback collection: {exc}")

    def store_feedback(self, routes: List[RouteFeedback]) -> bool:
        """Store user feedback data in MongoDB or no-op if MongoDB unavailable."""
        if not routes:
            return True

        # If MongoDB is not available, just log and return success
        if not self.mongodb_available:
            print("💡 Feedback received but not stored (MongoDB unavailable)")
            return True

        timestamp = datetime.utcnow()
        documents = [
            {
                "route_id": route.id,
                "selected": route.selected,
                "name": route.name,
                "distance": route.distance,
                "duration": route.duration,
                "waypoints": route.waypoints,
                "criteria": route.criteria,
                "score": route.score,
                "timestamp": timestamp,
                "created_at": timestamp,
            }
            for route in routes
        ]

        try:
            self.collection.insert_many(documents)
            return True
        except Exception as exc:
            print(f"Error storing feedback in MongoDB: {exc}")
            return False
    
    def is_available(self) -> bool:
        """Check if feedback storage is available."""
        return self.mongodb_available
    
