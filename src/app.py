"""Streamlit web application for Query Suggestion System."""
import os
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path

from metadata_loader import MetadataLoader
from search_engine import SearchEngine
from query_refiner import QueryRefiner
from sql_generator import SQLGenerator
from display_sql import display_generated_sql
from azure_auth import setup_azure_openai_client
from local_openai import setup_local_openai_client

# Page configuration
st.set_page_config(
    page_title="Query Suggestion System",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv()


@st.cache_resource
def initialize_system():
    """Initialize the search system (cached for performance)."""
    # Setup LLM client
    use_azure = os.getenv("USE_AZURE", "false").lower() == "true"

    if use_azure:
        client = setup_azure_openai_client()
        model = os.environ["AZURE_OPENAI_MODEL"]
        mode = "Azure OpenAI"
    else:
        client = setup_local_openai_client()
        model = os.environ["OPENAI_MODEL"]
        mode = "OpenAI"

    # Load metadata
    data_dir = Path("data")
    if not data_dir.exists():
        return None, None, None, mode

    loader = MetadataLoader(str(data_dir))
    yaml_metadata, txt_descriptions = loader.load_all_metadata()

    # Initialize search engine
    search_engine = SearchEngine(yaml_metadata, txt_descriptions)

    # Initialize query refiner
    query_refiner = QueryRefiner(client, model)

    # Initialize SQL generator
    sql_generator = SQLGenerator(client, model)

    return search_engine, query_refiner, sql_generator, (yaml_metadata, txt_descriptions), mode


def display_search_result(result, index):
    """Display a single search result."""
    with st.expander(f"#{index + 1} - {result.get_table_title()} ({result.get_source_type().upper()})", expanded=index == 0):
        col1, col2 = st.columns([2, 1])

        with col1:
            # Display table metadata
            if result.table_metadata:
                st.markdown("### Table Information")
                st.write(f"**Location:** `{result.table_metadata.table_loc}`")
                st.write(f"**Description:** {result.table_metadata.table_description}")

                if result.table_metadata.keywords:
                    st.write(f"**Keywords:** {', '.join(result.table_metadata.keywords)}")

                # Display columns
                if result.table_metadata.columns:
                    st.markdown("### Columns")
                    for col in result.table_metadata.columns[:10]:  # Show first 10 columns
                        with st.container():
                            st.markdown(f"**{col.name}** ({col.datatype})")
                            if col.description:
                                st.caption(col.description)

                    if len(result.table_metadata.columns) > 10:
                        st.caption(f"... and {len(result.table_metadata.columns) - 10} more columns")

            # Display text description
            if result.table_description:
                st.markdown("### Summary")
                st.write(f"**Purpose:** {result.table_description.purpose}")

                if result.table_description.key_features:
                    st.write("**Key Features:**")
                    for feature in result.table_description.key_features[:5]:
                        st.write(f"- {feature}")

                if result.table_description.joinable_features:
                    st.write("**Joinable Features:**")
                    for feature in result.table_description.joinable_features[:5]:
                        st.write(f"- {feature}")

        with col2:
            st.markdown("### Match Details")
            st.metric("Relevance Score", f"{result.relevance_score:.2f}")

            st.markdown("**Match Reasons:**")
            for reason in result.match_reasons[:5]:
                st.caption(f"- {reason}")

            if len(result.match_reasons) > 5:
                st.caption(f"... and {len(result.match_reasons) - 5} more matches")


def main():
    """Main application."""
    st.title("🔍 Query Suggestion Service")
    st.markdown("Search metadata and generate SQL queries with AI assistance")

    # Initialize system
    search_engine, query_refiner, sql_generator, metadata, mode = initialize_system()

    # Sidebar
    with st.sidebar:
        st.markdown(f"### System Info")
        st.info(f"**LLM Mode:** {mode}")

        if metadata:
            yaml_metadata, txt_descriptions = metadata
            st.metric("Total Tables", len(yaml_metadata))
            st.metric("AVS Tables", len([m for m in yaml_metadata if m.source_type == 'avs']))
            st.metric("DLVS Tables", len([m for m in yaml_metadata if m.source_type == 'dlvs']))

        st.markdown("---")
        st.markdown("### Filters")
        source_filter = st.selectbox(
            "Source Type",
            ["All", "AVS", "DLVS"],
            index=0
        )

        max_results = st.slider("Max Results", 1, 50, 10)

        st.markdown("---")
        st.markdown("### Tips")
        st.markdown("""
        - Search by table name, description, or column name
        - Ask questions in natural language
        - Use specific keywords for better results
        - Try "show all AVS tables" or "tables with SSN column"
        """)

    # Check if data directory exists
    if not search_engine:
        st.error("⚠️ Data directory not found. Please create the `data` folder with AVS and DLVS metadata.")
        st.markdown("""
        Expected structure:
        ```
        data/
        ├── avs/
        │   ├── extracted_metadata/ (YAML files)
        │   └── extracted_metadata_desc/ (TXT files)
        └── dlvs/
            ├── extracted_metadata/ (YAML files)
            └── extracted_metadata_desc/ (TXT files)
        ```
        """)
        return

    # Initialize session state
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []

    if 'last_query' not in st.session_state:
        st.session_state.last_query = ""

    if 'current_query' not in st.session_state:
        st.session_state.current_query = ""

    # Main search interface
    st.markdown("## Enter Your Query")

    query = st.text_input(
        "What are you looking for?",
        value=st.session_state.current_query,
        placeholder="e.g., 'borrower information', 'tables with SSN', 'business banking data'",
        key="query_input"
    )

    # Update current_query if user typed something different
    if query != st.session_state.current_query:
        st.session_state.current_query = query

    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)

    with col2:
        refine_button = st.button("✨ Get Suggestions", use_container_width=True)

    with col3:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.conversation_history = []
            st.session_state.last_query = ""
            st.session_state.current_query = ""
            st.session_state.last_refinement = None
            st.session_state.last_results = []
            st.session_state.generated_sql = None
            st.rerun()

    # Process search
    if query and (search_button or query != st.session_state.last_query):
        st.session_state.last_query = query
        # Clear any previous refinement suggestions and generated SQL
        st.session_state.last_refinement = None
        st.session_state.generated_sql = None

        with st.spinner("Searching..."):
            # Convert source filter
            source_type = None if source_filter == "All" else source_filter.lower()

            # Perform search
            results = search_engine.search(query, source_type=source_type, max_results=max_results)

            # Store in session state
            st.session_state.last_results = results

            # Display results
            st.markdown("---")
            st.markdown(f"## Search Results ({len(results)} found)")

            if results:
                for i, result in enumerate(results):
                    display_search_result(result, i)

                # Add SQL generation section
                st.markdown("---")
                st.markdown("## 🎯 Generate SQL Query")

                sql_col1, sql_col2 = st.columns([3, 1])

                with sql_col1:
                    st.markdown("Based on the tables above, generate a SQL query:")

                with sql_col2:
                    generate_sql_button = st.button("⚡ Generate SQL", type="primary", use_container_width=True)

                if generate_sql_button:
                    with st.spinner("Generating SQL query..."):
                        # Generate SQL from search results
                        sql_result = sql_generator.generate_sql(
                            user_query=query,
                            search_results=results,
                            conversation_history=st.session_state.conversation_history
                        )

                        # Store in session state
                        st.session_state.generated_sql = sql_result
                        st.rerun()
            else:
                st.warning("No results found. Try different keywords or browse all tables.")

                # Show suggestion
                st.markdown("### Suggestions")
                st.info(query_refiner.suggest_next_steps(query, results))

    # Process refinement request
    if query and refine_button:
        with st.spinner("Analyzing your query..."):
            # Get current results if available
            results = st.session_state.get('last_results', [])

            # Get refinement suggestions
            refinement = query_refiner.analyze_query(
                query,
                results,
                st.session_state.conversation_history
            )

            # Store refinement in session state
            st.session_state.last_refinement = refinement

    # Display refinement suggestions if available
    if 'last_refinement' in st.session_state and st.session_state.last_refinement:
        refinement = st.session_state.last_refinement

        # Display refinement suggestions
        st.markdown("---")
        st.markdown("## 💡 Query Suggestions")

        col1, col2 = st.columns(2)

        with col1:
            if refinement.refined_query:
                st.markdown("### Refined Query")
                st.success(refinement.refined_query)

                if st.button("🔍 Search with refined query"):
                    # Update the current query with the refined query
                    st.session_state.current_query = refinement.refined_query
                    # Clear last_query so the search will trigger
                    st.session_state.last_query = ""
                    # Clear the refinement so it doesn't show after search
                    st.session_state.last_refinement = None
                    st.rerun()

            if refinement.clarifying_questions:
                st.markdown("### Clarifying Questions")
                for question in refinement.clarifying_questions:
                    st.write(f"❓ {question}")

        with col2:
            if refinement.suggested_filters:
                st.markdown("### Suggested Filters")
                st.json(refinement.suggested_filters)

            if refinement.reasoning:
                st.markdown("### Reasoning")
                st.info(refinement.reasoning)

    # Display generated SQL if available
    if 'generated_sql' in st.session_state and st.session_state.generated_sql:
        sql_result = st.session_state.generated_sql
        results = st.session_state.get('last_results', [])

        refine_button, refinement_request = display_generated_sql(sql_result, results)

        # Handle SQL refinement
        if refine_button and refinement_request:
            with st.spinner("Refining SQL..."):
                # Build tables context
                tables_context = sql_generator._build_tables_context(
                    results,
                    list(range(min(3, len(results))))
                )

                # Refine the SQL
                refined_result = sql_generator.refine_sql(
                    sql_result['sql_query'],
                    refinement_request,
                    tables_context
                )

                # Update session state with refined SQL
                if refined_result['success']:
                    st.session_state.generated_sql = {
                        'sql_query': refined_result['sql_query'],
                        'explanation': refined_result['explanation'],
                        'tables_used': sql_result.get('tables_used', []),
                        'assumptions': [],
                        'alternatives': [],
                        'success': True
                    }
                    st.rerun()
                else:
                    st.error(f"Error refining SQL: {refined_result.get('error', 'Unknown error')}")

    # Show conversation history
    if st.session_state.conversation_history:
        with st.sidebar:
            st.markdown("---")
            st.markdown("### Recent Queries")
            for i, msg in enumerate(reversed(st.session_state.conversation_history[-6:])):
                if msg['role'] == 'user':
                    st.caption(f"🔍 {msg['content'][:50]}...")


if __name__ == "__main__":
    main()
