"""Data models for the Query Suggestion System."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ColumnMetadata:
    """Represents metadata for a single column."""
    name: str
    title: str
    description: str
    datatype: str
    required: bool


@dataclass
class TableMetadata:
    """Represents detailed metadata from YAML files."""
    seal_id: Optional[int]
    dataset_id: str
    table_loc: str
    table_title: str
    table_description: str
    keywords: List[str]
    columns: List[ColumnMetadata]
    source_file: str
    source_type: str  # 'avs' or 'dlvs'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'seal_id': self.seal_id,
            'dataset_id': self.dataset_id,
            'table_loc': self.table_loc,
            'table_title': self.table_title,
            'table_description': self.table_description,
            'keywords': self.keywords,
            'columns': [
                {
                    'name': col.name,
                    'title': col.title,
                    'description': col.description,
                    'datatype': col.datatype,
                    'required': col.required
                }
                for col in self.columns
            ],
            'source_file': self.source_file,
            'source_type': self.source_type
        }


@dataclass
class TableDescription:
    """Represents simplified metadata from TXT files."""
    table_name: str
    purpose: str
    key_features: List[str]
    joinable_features: List[str]
    source_file: str
    source_type: str  # 'avs' or 'dlvs'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'table_name': self.table_name,
            'purpose': self.purpose,
            'key_features': self.key_features,
            'joinable_features': self.joinable_features,
            'source_file': self.source_file,
            'source_type': self.source_type
        }


@dataclass
class SearchResult:
    """Represents a search result with relevance score."""
    table_metadata: Optional[TableMetadata]
    table_description: Optional[TableDescription]
    relevance_score: float
    match_reasons: List[str]  # Why this result matched

    def get_table_title(self) -> str:
        """Get the table title from available sources."""
        if self.table_metadata:
            return self.table_metadata.table_title
        elif self.table_description:
            return self.table_description.table_name
        return "Unknown"

    def get_source_type(self) -> str:
        """Get the source type (avs/dlvs)."""
        if self.table_metadata:
            return self.table_metadata.source_type
        elif self.table_description:
            return self.table_description.source_type
        return "unknown"


@dataclass
class QueryRefinement:
    """Represents a query refinement suggestion."""
    original_query: str
    refined_query: Optional[str]
    clarifying_questions: List[str]
    suggested_filters: Dict[str, Any]  # e.g., {'source_type': 'avs', 'has_column': 'SSN'}
    reasoning: str  # Why this refinement was suggested
