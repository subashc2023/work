"""Streamlit web application for Query Suggestion System."""
import os
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path

from metadata_loader import MetadataLoader
from search_engine import SearchEngine
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

    # Initialize SQL generator
    sql_generator = SQLGenerator(client, model)

    return search_engine, sql_generator, (yaml_metadata, txt_descriptions), mode


def display_search_result(result, index):
    """Display a single search result."""
    # Use container instead of expander for stable display
    st.markdown(f"### #{index + 1} - {result.get_table_title()} ({result.get_source_type().upper()})")
    with st.container(border=True):
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
    st.title("🎯 Query Suggestion Service")
    st.markdown("Describe your data needs → Get SQL automatically")

    # Initialize system
    search_engine, sql_generator, metadata, mode = initialize_system()

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
        - Describe what data you need in natural language
        - System finds tables and generates SQL automatically
        - Review tables used in search results section
        - Refine SQL using natural language below the query
        - Example: "customer with loan applications"
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

    if 'last_results' not in st.session_state:
        st.session_state.last_results = None

    # Main search interface
    st.markdown("## What data do you need?")

    query = st.text_input(
        "Describe the data you want to query:",
        value=st.session_state.current_query,
        placeholder="e.g., 'customer with loan applications', 'borrower information with SSN'",
        key="query_input"
    )

    # Update current_query if user typed something different
    if query != st.session_state.current_query:
        st.session_state.current_query = query

    col1, col2 = st.columns([1, 5])

    with col1:
        search_and_generate_button = st.button("🎯 Search & Generate SQL", type="primary", use_container_width=True)

    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.conversation_history = []
            st.session_state.last_query = ""
            st.session_state.current_query = ""
            st.session_state.last_results = []
            st.session_state.generated_sql = None
            st.rerun()

    # Process search and SQL generation (combined operation)
    if query and search_and_generate_button:
        st.session_state.last_query = query

        with st.spinner("Searching for tables..."):
            # Convert source filter
            source_type = None if source_filter == "All" else source_filter.lower()

            # Perform search
            results = search_engine.search(query, source_type=source_type, max_results=max_results)

            # Store in session state
            st.session_state.last_results = results

        # If we found results, automatically generate SQL
        if results:
            with st.spinner("Generating SQL query..."):
                sql_result = sql_generator.generate_sql(
                    user_query=query,
                    search_results=results,
                    conversation_history=st.session_state.conversation_history
                )

                # Store in session state
                st.session_state.generated_sql = sql_result

        st.rerun()

    # Display search results (separate from search execution)
    if 'last_results' in st.session_state and st.session_state.last_results is not None:
        results = st.session_state.last_results

        st.markdown("---")
        st.markdown(f"## Search Results ({len(results)} found)")

        if results:
            for i, result in enumerate(results):
                display_search_result(result, i)
        else:
            st.warning("No results found. Try different keywords or browse all tables.")

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
