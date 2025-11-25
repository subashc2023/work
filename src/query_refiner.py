"""LLM-powered query refinement and suggestion system."""
import json
from typing import List, Optional, Dict, Any
from models import QueryRefinement, SearchResult


class QueryRefiner:
    """Uses LLM to understand and refine user queries."""

    def __init__(self, llm_client, model: str):
        self.client = llm_client
        self.model = model

    def analyze_query(self, query: str, search_results: List[SearchResult], conversation_history: List[Dict[str, str]]) -> QueryRefinement:
        """
        Analyze a user query and suggest refinements.

        Args:
            query: The user's search query
            search_results: Current search results
            conversation_history: Previous conversation context

        Returns:
            QueryRefinement object with suggestions
        """
        # Build context from search results
        results_summary = self._summarize_results(search_results)

        # Create prompt for LLM
        system_prompt = """You are a helpful assistant for a data catalog search system.
The system has two data sources: AVS and DLVS, each containing database table metadata.

Your job is to:
1. Understand what the user is looking for
2. Suggest refined queries if the original is vague
3. Ask clarifying questions if needed
4. Suggest filters (source_type, column names, etc.)

Respond in JSON format with:
{
    "refined_query": "optional refined version of the query",
    "clarifying_questions": ["list", "of", "questions"],
    "suggested_filters": {"key": "value"},
    "reasoning": "why you're making these suggestions"
}
"""

        user_prompt = f"""User query: "{query}"

Current search found {len(search_results)} results:
{results_summary}

Please analyze this query and provide suggestions to help the user find what they need."""

        # Call LLM
        messages = [
            {"role": "system", "content": system_prompt},
        ]

        # Add conversation history
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
            # Try to extract JSON from response (handle markdown code blocks)
            json_match = llm_response
            if "```json" in llm_response:
                json_match = llm_response.split("```json")[1].split("```")[0].strip()
            elif "```" in llm_response:
                json_match = llm_response.split("```")[1].split("```")[0].strip()

            parsed = json.loads(json_match)

            return QueryRefinement(
                original_query=query,
                refined_query=parsed.get("refined_query"),
                clarifying_questions=parsed.get("clarifying_questions", []),
                suggested_filters=parsed.get("suggested_filters", {}),
                reasoning=parsed.get("reasoning", "")
            )

        except Exception as e:
            print(f"Error in query refinement: {e}")
            # Return default refinement
            return QueryRefinement(
                original_query=query,
                refined_query=None,
                clarifying_questions=[],
                suggested_filters={},
                reasoning=f"Error analyzing query: {e}"
            )

    def suggest_next_steps(self, query: str, results: List[SearchResult]) -> str:
        """Suggest what the user should do next based on results."""
        if len(results) == 0:
            return "No results found. Try:\n- Using different keywords\n- Searching for column names\n- Browsing all tables in AVS or DLVS"

        elif len(results) == 1:
            return "Found 1 exact match! Review the table details below."

        elif len(results) <= 5:
            return f"Found {len(results)} relevant tables. Review them below to find the best match."

        else:
            return f"Found {len(results)} tables. Consider refining your query to narrow down results."

    def _summarize_results(self, results: List[SearchResult], max_results: int = 5) -> str:
        """Create a summary of search results for the LLM."""
        if not results:
            return "No results found."

        summary_lines = []
        for i, result in enumerate(results[:max_results], 1):
            title = result.get_table_title()
            source = result.get_source_type()
            score = result.relevance_score

            summary_lines.append(f"{i}. {title} (from {source}, score: {score:.1f})")

        if len(results) > max_results:
            summary_lines.append(f"... and {len(results) - max_results} more results")

        return "\n".join(summary_lines)

    def extract_search_intent(self, query: str) -> Dict[str, Any]:
        """
        Extract structured search intent from natural language query.

        Returns dict with:
        - keywords: List of search terms
        - column_name: Specific column being searched for
        - source_type: 'avs', 'dlvs', or None
        - intent: 'search', 'browse', 'describe'
        """
        query_lower = query.lower()

        intent = {
            'keywords': [],
            'column_name': None,
            'source_type': None,
            'intent': 'search'
        }

        # Detect source type
        if 'avs' in query_lower:
            intent['source_type'] = 'avs'
        elif 'dlvs' in query_lower:
            intent['source_type'] = 'dlvs'

        # Detect column searches
        if 'column' in query_lower or 'field' in query_lower:
            # Try to extract column name
            words = query.split()
            for i, word in enumerate(words):
                if word.lower() in ['column', 'field'] and i + 1 < len(words):
                    intent['column_name'] = words[i + 1].strip('":,.')
                    break

        # Detect browse intent
        if any(word in query_lower for word in ['all', 'list', 'show', 'browse']):
            intent['intent'] = 'browse'

        # Extract keywords (simple approach)
        # Remove common words and extract meaningful terms
        stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'for', 'with', 'about', 'show', 'me', 'find', 'search', 'list', 'all'}
        words = query_lower.split()
        intent['keywords'] = [w.strip('.,!?":;') for w in words if w.strip('.,!?":;') not in stop_words and len(w) > 2]

        return intent
