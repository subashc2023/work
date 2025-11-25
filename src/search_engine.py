"""Search engine for metadata with keyword and semantic search."""
import re
from typing import List, Dict, Set
from models import TableMetadata, TableDescription, SearchResult


class SearchEngine:
    """Searches through metadata using keyword matching and scoring."""

    def __init__(self, yaml_metadata: List[TableMetadata], txt_descriptions: List[TableDescription]):
        self.yaml_metadata = yaml_metadata
        self.txt_descriptions = txt_descriptions
        self._build_index()

    def _build_index(self):
        """Build search indexes for efficient querying."""
        # Create lookup dictionaries
        self.yaml_by_file = {m.source_file: m for m in self.yaml_metadata}
        self.txt_by_file = {d.source_file: d for d in self.txt_descriptions}

        # Build inverted index for keywords
        self.keyword_index: Dict[str, Set[str]] = {}  # keyword -> set of source files

        # Index YAML metadata
        for metadata in self.yaml_metadata:
            self._index_text(metadata.table_title, metadata.source_file)
            self._index_text(metadata.table_description, metadata.source_file)
            self._index_text(metadata.table_loc, metadata.source_file)

            for keyword in metadata.keywords:
                self._index_text(keyword, metadata.source_file)

            for column in metadata.columns:
                self._index_text(column.name, metadata.source_file)
                self._index_text(column.title, metadata.source_file)
                self._index_text(column.description, metadata.source_file)

        # Index TXT descriptions
        for desc in self.txt_descriptions:
            self._index_text(desc.table_name, desc.source_file)
            self._index_text(desc.purpose, desc.source_file)

            for feature in desc.key_features + desc.joinable_features:
                self._index_text(feature, desc.source_file)

    def _index_text(self, text: str, source_file: str):
        """Add text to the keyword index."""
        if not text:
            return

        # Extract keywords (alphanumeric sequences)
        keywords = re.findall(r'\b\w+\b', text.lower())

        for keyword in keywords:
            if len(keyword) > 2:  # Ignore very short words
                if keyword not in self.keyword_index:
                    self.keyword_index[keyword] = set()
                self.keyword_index[keyword].add(source_file)

    def search(self, query: str, source_type: str = None, max_results: int = 10) -> List[SearchResult]:
        """
        Search for tables matching the query.

        Args:
            query: Search query string
            source_type: Optional filter for 'avs' or 'dlvs'
            max_results: Maximum number of results to return

        Returns:
            List of SearchResult objects ranked by relevance
        """
        query_keywords = re.findall(r'\b\w+\b', query.lower())

        # Find matching files
        file_scores: Dict[str, float] = {}
        file_matches: Dict[str, List[str]] = {}

        for keyword in query_keywords:
            if len(keyword) <= 2:
                continue

            # Exact matches
            if keyword in self.keyword_index:
                for source_file in self.keyword_index[keyword]:
                    file_scores[source_file] = file_scores.get(source_file, 0) + 1.0
                    if source_file not in file_matches:
                        file_matches[source_file] = []
                    file_matches[source_file].append(f"Matched keyword: '{keyword}'")

            # Partial matches (contains)
            for indexed_keyword, files in self.keyword_index.items():
                if keyword in indexed_keyword or indexed_keyword in keyword:
                    for source_file in files:
                        file_scores[source_file] = file_scores.get(source_file, 0) + 0.5
                        if source_file not in file_matches:
                            file_matches[source_file] = []
                        if f"Partial match: '{keyword}' in '{indexed_keyword}'" not in file_matches[source_file]:
                            file_matches[source_file].append(f"Partial match: '{keyword}' ~ '{indexed_keyword}'")

        # Build search results
        results = []

        for source_file, score in file_scores.items():
            yaml_meta = self.yaml_by_file.get(source_file)
            txt_desc = self.txt_by_file.get(source_file.replace('.yaml', '.txt'))

            # Apply source type filter
            if source_type:
                if yaml_meta and yaml_meta.source_type != source_type:
                    continue
                if txt_desc and not yaml_meta and txt_desc.source_type != source_type:
                    continue

            result = SearchResult(
                table_metadata=yaml_meta,
                table_description=txt_desc,
                relevance_score=score,
                match_reasons=file_matches.get(source_file, [])
            )

            results.append(result)

        # Sort by relevance score
        results.sort(key=lambda r: r.relevance_score, reverse=True)

        return results[:max_results]

    def search_by_column(self, column_name: str, source_type: str = None) -> List[SearchResult]:
        """Search for tables that have a specific column."""
        results = []

        for metadata in self.yaml_metadata:
            # Apply source type filter
            if source_type and metadata.source_type != source_type:
                continue

            for column in metadata.columns:
                if column_name.lower() in column.name.lower() or column_name.lower() in column.title.lower():
                    txt_desc = self.txt_by_file.get(metadata.source_file.replace('.yaml', '.txt'))

                    result = SearchResult(
                        table_metadata=metadata,
                        table_description=txt_desc,
                        relevance_score=1.0,
                        match_reasons=[f"Contains column: {column.name}"]
                    )

                    results.append(result)
                    break  # Only add each table once

        return results

    def get_all_tables(self, source_type: str = None) -> List[SearchResult]:
        """Get all tables, optionally filtered by source type."""
        results = []

        for metadata in self.yaml_metadata:
            if source_type and metadata.source_type != source_type:
                continue

            txt_desc = self.txt_by_file.get(metadata.source_file.replace('.yaml', '.txt'))

            result = SearchResult(
                table_metadata=metadata,
                table_description=txt_desc,
                relevance_score=0.0,
                match_reasons=["All tables"]
            )

            results.append(result)

        return results
