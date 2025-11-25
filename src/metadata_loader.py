"""Loads and parses metadata from YAML and TXT files."""
import os
import yaml
from pathlib import Path
from typing import List, Tuple
from models import TableMetadata, TableDescription, ColumnMetadata


class MetadataLoader:
    """Loads metadata from data directory structure."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)

    def load_all_metadata(self) -> Tuple[List[TableMetadata], List[TableDescription]]:
        """Load all YAML and TXT metadata files."""
        yaml_metadata = []
        txt_descriptions = []

        # Load from both avs and dlvs
        for source_type in ['avs', 'dlvs']:
            source_path = self.data_dir / source_type

            # Load YAML files
            yaml_path = source_path / 'extracted_metadata'
            if yaml_path.exists():
                yaml_metadata.extend(self._load_yaml_files(yaml_path, source_type))

            # Load TXT files
            txt_path = source_path / 'extracted_metadata_desc'
            if txt_path.exists():
                txt_descriptions.extend(self._load_txt_files(txt_path, source_type))

        return yaml_metadata, txt_descriptions

    def _load_yaml_files(self, yaml_dir: Path, source_type: str) -> List[TableMetadata]:
        """Load all YAML files from a directory."""
        metadata_list = []

        for yaml_file in yaml_dir.glob('*.yaml'):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)

                # Parse columns
                columns = []
                for col_data in data.get('columns', []):
                    # Handle both 'colums' typo and 'columns'
                    if isinstance(col_data, dict):
                        columns.append(ColumnMetadata(
                            name=col_data.get('name', ''),
                            title=col_data.get('title', ''),
                            description=col_data.get('description', ''),
                            datatype=col_data.get('datatype', 'Unknown'),
                            required=col_data.get('required', False)
                        ))

                # Also check for 'colums' typo
                for col_data in data.get('colums', []):
                    if isinstance(col_data, dict):
                        columns.append(ColumnMetadata(
                            name=col_data.get('name', ''),
                            title=col_data.get('title', ''),
                            description=col_data.get('description', ''),
                            datatype=col_data.get('datatype', 'Unknown'),
                            required=col_data.get('required', False)
                        ))

                metadata = TableMetadata(
                    seal_id=data.get('seal_id'),
                    dataset_id=data.get('dataset_id', ''),
                    table_loc=data.get('table_loc', ''),
                    table_title=data.get('table_title', ''),
                    table_description=data.get('table_description', ''),
                    keywords=data.get('keywords', []),
                    columns=columns,
                    source_file=yaml_file.name,
                    source_type=source_type
                )

                metadata_list.append(metadata)

            except Exception as e:
                print(f"Error loading {yaml_file}: {e}")

        return metadata_list

    def _load_txt_files(self, txt_dir: Path, source_type: str) -> List[TableDescription]:
        """Load all TXT description files from a directory."""
        descriptions = []

        for txt_file in txt_dir.glob('*.txt'):
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse the structured text
                parsed = self._parse_txt_content(content)

                description = TableDescription(
                    table_name=parsed.get('table_name', ''),
                    purpose=parsed.get('purpose', ''),
                    key_features=parsed.get('key_features', []),
                    joinable_features=parsed.get('joinable_features', []),
                    source_file=txt_file.name,
                    source_type=source_type
                )

                descriptions.append(description)

            except Exception as e:
                print(f"Error loading {txt_file}: {e}")

        return descriptions

    def _parse_txt_content(self, content: str) -> dict:
        """Parse the structured text content."""
        lines = content.strip().split('\n')
        parsed = {
            'table_name': '',
            'purpose': '',
            'key_features': [],
            'joinable_features': []
        }

        current_field = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('Table Name:'):
                parsed['table_name'] = line.replace('Table Name:', '').strip()
            elif line.startswith('Purpose:'):
                parsed['purpose'] = line.replace('Purpose:', '').strip()
            elif line.startswith('Key Features:'):
                # Parse comma-separated features
                features_str = line.replace('Key Features:', '').strip()
                parsed['key_features'] = [f.strip() for f in features_str.split(',') if f.strip()]
            elif line.startswith('Joinable Features:'):
                # Parse comma-separated features
                features_str = line.replace('Joinable Features:', '').strip()
                parsed['joinable_features'] = [f.strip() for f in features_str.split(',') if f.strip()]

        return parsed
