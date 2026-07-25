from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ImportMetadata(BaseModel):
    name: str
    source: Optional[str] = None
    line_number: int

class CommentMetadata(BaseModel):
    content: str
    start_line: int
    end_line: int

class MethodMetadata(BaseModel):
    name: str
    start_line: int
    end_line: int
    decorators: List[str] = Field(default_factory=list)

class ClassMetadata(BaseModel):
    name: str
    start_line: int
    end_line: int
    decorators: List[str] = Field(default_factory=list)
    methods: List[MethodMetadata] = Field(default_factory=list)

class FunctionMetadata(BaseModel):
    name: str
    start_line: int
    end_line: int
    decorators: List[str] = Field(default_factory=list)
    is_method: bool = False
    parent_class: Optional[str] = None

class Symbol(BaseModel):
    name: str
    kind: str  # class, method, function, interface, enum, etc.
    start_line: int
    end_line: int
    parent: Optional[str] = None

class RepositoryStatistics(BaseModel):
    lines: int = 0
    classes: int = 0
    functions: int = 0
    files_count: int = 0

class ChangedFile(BaseModel):
    filename: str
    filepath: str
    language: str
    patch: Optional[str] = None
    content: str

class ParsedFile(BaseModel):
    filepath: str
    language: str
    classes: List[ClassMetadata] = Field(default_factory=list)
    functions: List[FunctionMetadata] = Field(default_factory=list)
    imports: List[ImportMetadata] = Field(default_factory=list)
    comments: List[CommentMetadata] = Field(default_factory=list)
    statistics: Dict[str, int] = Field(default_factory=dict)
    symbols: List[Symbol] = Field(default_factory=list)
