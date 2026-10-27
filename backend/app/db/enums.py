from enum import Enum


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class MessageKind(str, Enum):
    QUESTION = "question"
    ANSWERS = "answers"
    CLARIFICATION = "clarification"
    REPLY = "reply"
