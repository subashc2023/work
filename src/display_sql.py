"""Helper functions for displaying SQL in Streamlit."""
import streamlit as st


def display_generated_sql(sql_result, results):
    """Display generated SQL with explanation and options."""
    st.markdown("---")
    st.markdown("## 🎯 Generated SQL Query")

    if not sql_result.get('success', True):
        st.error(f"Error generating SQL: {sql_result.get('error', 'Unknown error')}")
        return

    # Main SQL display
    st.markdown("### SQL Query")
    st.code(sql_result['sql_query'], language='sql')

    # Copy button
    if st.button("📋 Copy to Clipboard"):
        st.session_state.copied = True
        st.info("SQL copied! (Note: Use browser's copy from code block above)")

    # Two columns for details
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📝 Explanation")
        st.write(sql_result.get('explanation', 'No explanation available'))

        if sql_result.get('tables_used'):
            st.markdown("### 📊 Tables Used")
            for table in sql_result['tables_used']:
                st.write(f"- `{table}`")

    with col2:
        if sql_result.get('assumptions'):
            st.markdown("### 💡 Assumptions")
            for assumption in sql_result['assumptions']:
                st.write(f"- {assumption}")

        if sql_result.get('alternatives'):
            st.markdown("### 🔄 Alternatives")
            for alt in sql_result['alternatives']:
                st.write(f"- {alt}")

    # Refinement section
    st.markdown("---")
    st.markdown("### ✏️ Refine SQL")

    refine_col1, refine_col2 = st.columns([3, 1])

    with refine_col1:
        refinement_request = st.text_input(
            "How would you like to modify the SQL?",
            placeholder="e.g., 'add a WHERE clause for last 30 days', 'group by customer'",
            key="sql_refinement_input"
        )

    with refine_col2:
        st.write("")  # Spacing
        refine_sql_button = st.button("🔄 Refine SQL", use_container_width=True)

    return refine_sql_button, refinement_request
