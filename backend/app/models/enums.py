import enum

class ReviewStatus(str, enum.Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"

class Severity(str, enum.Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFO = "Info"

class AgentStatus(str, enum.Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"

class DocumentType(str, enum.Enum):
    README = "README"
    CONTRIBUTING = "CONTRIBUTING"
    ARCHITECTURE = "ARCHITECTURE"
    ADR = "ADR"
    API_DOCS = "API_DOCS"
    GUIDELINES = "GUIDELINES"
    OTHER = "OTHER"
