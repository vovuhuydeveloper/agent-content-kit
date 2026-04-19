"""
Data models package
Contains all database model definitions
"""
from .analytics import VideoAnalytics
from .base import Base, BaseModel, TimestampMixin, generate_uuid
from .content_job import ContentJob
from .schedule import ContentSchedule

__all__ = [
    "Base",
    "BaseModel",
    "TimestampMixin",
    "generate_uuid",
    "ContentJob",
    "ContentSchedule",
    "VideoAnalytics",
]

# Try importing legacy models (may not exist)
try:
    from .project import Project
    __all__.append("Project")
except ImportError:
    pass

try:
    from .clip import Clip
    __all__.append("Clip")
except ImportError:
    pass

try:
    from .collection import Collection
    __all__.append("Collection")
except ImportError:
    pass

try:
    from .task import Task, TaskStatus, TaskType
    __all__.extend(["Task", "TaskStatus", "TaskType"])
except ImportError:
    pass

try:
    from .bilibili import BilibiliAccount, UploadRecord
    __all__.extend(["BilibiliAccount", "UploadRecord"])
except ImportError:
    pass
