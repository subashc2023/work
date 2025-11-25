"""LLM-powered SQL query generation from metadata."""
import json
from typing import List, Optional, Dict, Any
from models import SearchResult


class SQLGenerator:
    """Generates SQL queries based on search results and user intent."""

    def __init__(self, llm_client, model: str):
        self.client = llm_client
        self.model = model

    def generate_sql(
        self,
        user_query: str,
        search_results: List[SearchResult],
        conversation_history: List[Dict[str, str]],
        selected_tables: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Generate SQL query based on user intent and available tables.

        Args:
            user_query: The user's original search query
            search_results: List of relevant tables found
            conversation_history: Previous conversation for context
            selected_tables: Optional list of result indices to use (default: top 3)

        Returns:
            Dict with:
                - sql_query: Generated SQL
                - explanation: What the query does
                - tables_used: List of tables referenced
                - assumptions: Any assumptions made
                - alternatives: Other ways to write the query
        """
        # Use top results if no selection
        if selected_tables is None:
            selected_tables = list(range(min(3, len(search_results))))

        # Build context from selected tables
        tables_context = self._build_tables_context(search_results, selected_tables)

        # Create prompt for SQL generation
        system_prompt = """You are an expert SQL query writer for data warehouses.
You have access to table metadata including columns, descriptions, and relationships.

Your job is to:
1. Understand what the user wants to query
2. Generate correct SQL using the available tables and columns
3. Use appropriate JOINs based on joinable features
4. Add helpful WHERE clauses, GROUP BY, ORDER BY as needed
5. Follow best practices for readable SQL

Respond in JSON format:
{
    "sql_query": "SELECT ... FROM ... WHERE ...",
    "explanation": "This query retrieves...",
    "tables_used": ["table1", "table2"],
    "assumptions": ["assuming...", "..."],
    "alternatives": ["Could also use...", "..."]
}

Important:
- Use proper table aliases
- Include comments in SQL for clarity
- Consider performance (use appropriate indexes/filters)
- Handle NULL values appropriately
- Use ANSI SQL standard syntax
"""

        user_prompt = f"""User wants to: "{user_query}"

Available tables and columns:
{tables_context}

Generate an appropriate SQL query that answers the user's need."""

        # Call LLM
        messages = [
            {"role": "system", "content": system_prompt},
        ]

        # Add conversation history for context
        for msg in conversation_history[-4:]:  # Last 2 exchanges
            messages.append(msg)

        messages.append({"role": "user", "content": user_prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )

            llm_response = response.choices[0].message.content

            # Parse JSON response
            json_match = llm_response
            if "```json" in llm_response:
                json_match = llm_response.split("```json")[1].split("```")[0].strip()
            elif "```" in llm_response:
                json_match = llm_response.split("```")[1].split("```")[0].strip()

            parsed = json.loads(json_match)

            return {
                'sql_query': parsed.get('sql_query', ''),
                'explanation': parsed.get('explanation', ''),
                'tables_used': parsed.get('tables_used', []),
                'assumptions': parsed.get('assumptions', []),
                'alternatives': parsed.get('alternatives', []),
                'success': True
            }

        except Exception as e:
            print(f"Error generating SQL: {e}")
            return {
                'sql_query': '-- Error generating SQL',
                'explanation': f'Error: {str(e)}',
                'tables_used': [],
                'assumptions': [],
                'alternatives': [],
                'success': False,
                'error': str(e)
            }

    def refine_sql(
        self,
        original_sql: str,
        refinement_request: str,
        tables_context: str
    ) -> Dict[str, Any]:
        """
        Refine an existing SQL query based on user feedback.

        Args:
            original_sql: The SQL query to refine
            refinement_request: What the user wants to change
            tables_context: Available tables and columns

        Returns:
            Dict with refined SQL and explanation
        """
        system_prompt = """You are an expert SQL query writer.
Refine the given SQL query based on the user's request.

Respond in JSON format:
{
    "sql_query": "refined SQL",
    "explanation": "what changed and why",
    "changes": ["change 1", "change 2"]
}
"""

        user_prompt = f"""Original SQL:
```sql
{original_sql}
```

Available tables:
{tables_context}

User requests: {refinement_request}

Refine the SQL query accordingly."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )

            llm_response = response.choices[0].message.content

            # Parse JSON
            json_match = llm_response
            if "```json" in llm_response:
                json_match = llm_response.split("```json")[1].split("```")[0].strip()
            elif "```" in llm_response:
                json_match = llm_response.split("```")[1].split("```")[0].strip()

            parsed = json.loads(json_match)

            return {
                'sql_query': parsed.get('sql_query', original_sql),
                'explanation': parsed.get('explanation', ''),
                'changes': parsed.get('changes', []),
                'success': True
            }

        except Exception as e:
            return {
                'sql_query': original_sql,
                'explanation': f'Error: {str(e)}',
                'changes': [],
                'success': False,
                'error': str(e)
            }

    def _build_tables_context(
        self,
        search_results: List[SearchResult],
        selected_indices: List[int]
    ) -> str:
        """Build a context string describing available tables and columns."""
        context_parts = []

        for idx in selected_indices:
            if idx >= len(search_results):
                continue

            result = search_results[idx]

            # Build table context
            if result.table_metadata:
                meta = result.table_metadata
                table_info = [
                    f"\nTable: {meta.table_loc}",
                    f"Description: {meta.table_description}",
                    "\nColumns:"
                ]

                for col in meta.columns[:20]:  # Limit to 20 columns
                    col_desc = f"  - {col.name} ({col.datatype})"
                    if col.description:
                        col_desc += f": {col.description}"
                    table_info.append(col_desc)

                if len(meta.columns) > 20:
                    table_info.append(f"  ... and {len(meta.columns) - 20} more columns")

                context_parts.append("\n".join(table_info))

            # Add description info if available
            if result.table_description:
                desc = result.table_description
                context_parts.append(f"\nPurpose: {desc.purpose}")

                if desc.joinable_features:
                    context_parts.append(
                        f"Joinable on: {', '.join(desc.joinable_features[:5])}"
                    )

        return "\n\n".join(context_parts)

    def explain_sql(self, sql_query: str) -> str:
        """Generate a plain English explanation of a SQL query."""
        system_prompt = """You are an expert at explaining SQL queries in plain English.
Explain what the query does in a way that non-technical users can understand."""

        user_prompt = f"""Explain this SQL query:

```sql
{sql_query}
```

Provide a clear, concise explanation."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Error explaining SQL: {str(e)}"
