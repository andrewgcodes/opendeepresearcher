import streamlit as st
import json
import time
from datetime import datetime
import os
from researcher import AgenticResearcher
import pandas as pd
from io import StringIO
import traceback
import sys

# Page configuration
st.set_page_config(page_title="Open Deep Research",
                   page_icon="🔬",
                   layout="wide",
                   initial_sidebar_state="expanded")

# Enable debug mode
DEBUG = True

# Custom CSS
st.markdown("""
<style>
    .stProgress > div > div > div > div {
        background-color: #1f77b4;
    }
    .research-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .debug-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border: 1px solid #ffeaa7;
    }
</style>
""",
            unsafe_allow_html=True)

# Initialize session state
if 'research_started' not in st.session_state:
    st.session_state.research_started = False
if 'research_complete' not in st.session_state:
    st.session_state.research_complete = False
if 'research_data' not in st.session_state:
    st.session_state.research_data = None
if 'final_report' not in st.session_state:
    st.session_state.final_report = None
if 'current_iteration' not in st.session_state:
    st.session_state.current_iteration = 0
if 'debug_messages' not in st.session_state:
    st.session_state.debug_messages = []
if 'error_occurred' not in st.session_state:
    st.session_state.error_occurred = False
if 'research_in_progress' not in st.session_state:
    st.session_state.research_in_progress = False


def add_debug_message(message, level="INFO"):
    """Add a debug message with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    st.session_state.debug_messages.append(
        f"[{timestamp}] [{level}] {message}")
    if DEBUG:
        print(f"[{timestamp}] [{level}] {message}")


# Title and description
st.markdown('<h1 class="research-title">🔬 Open Deep Research</h1>',
            unsafe_allow_html=True)
st.markdown("""
<div class="info-box">
Conduct comprehensive literature reviews on scientific topics. 
It searches for papers, analyzes content, and generates detailed research reports.
</div>
""",
            unsafe_allow_html=True)

# Debug section at top if enabled
if DEBUG:
    with st.expander("🐛 Debug Panel", expanded=False):
        st.markdown('<div class="debug-box">', unsafe_allow_html=True)
        st.write("**Debug Mode Active**")
        st.write(f"Session State Keys: {list(st.session_state.keys())}")
        st.write(f"Research Started: {st.session_state.research_started}")
        st.write(f"Research Complete: {st.session_state.research_complete}")
        st.write(
            f"Research In Progress: {st.session_state.research_in_progress}")
        st.write(f"Error Occurred: {st.session_state.error_occurred}")
        st.write(f"Current Iteration: {st.session_state.current_iteration}")

        # Show environment variables (without exposing keys)
        st.write("**API Keys Status:**")
        st.write(
            f"- ANTHROPIC_API_KEY: {'✅ Set' if os.environ.get('ANTHROPIC_API_KEY') else '❌ Missing'}"
        )
        st.write(
            f"- EXA_API_KEY: {'✅ Set' if os.environ.get('EXA_API_KEY') else '❌ Missing'}"
        )
        st.write(
            f"- FIRECRAWL_API_KEY: {'✅ Set' if os.environ.get('FIRECRAWL_API_KEY') else '❌ Missing'}"
        )

        # Debug messages
        if st.session_state.debug_messages:
            st.write("**Debug Messages:**")
            for msg in st.session_state.debug_messages[
                    -10:]:  # Show last 10 messages
                st.code(msg)

        st.markdown('</div>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    # API Keys section
    with st.expander("🔑 API Configuration", expanded=False):
        st.info(
            "This app requires API keys for Anthropic, Exa, and Firecrawl.")

        # Check if keys are configured
        keys_configured = all([
            os.environ.get("ANTHROPIC_API_KEY"),
            os.environ.get("EXA_API_KEY"),
            os.environ.get("FIRECRAWL_API_KEY")
        ])

        if keys_configured:
            st.success("✅ All API keys configured")
            add_debug_message("All API keys are configured")
        else:
            st.error("❌ API keys missing")
            missing_keys = []
            if not os.environ.get("ANTHROPIC_API_KEY"):
                missing_keys.append("ANTHROPIC_API_KEY")
            if not os.environ.get("EXA_API_KEY"):
                missing_keys.append("EXA_API_KEY")
            if not os.environ.get("FIRECRAWL_API_KEY"):
                missing_keys.append("FIRECRAWL_API_KEY")
            st.write("Missing keys:", ", ".join(missing_keys))
            add_debug_message(f"Missing API keys: {missing_keys}", "ERROR")

    # Research Settings
    st.header("🔍 Research Settings")

    num_iterations = st.slider(
        "Number of Research Iterations",
        min_value=3,
        max_value=15,
        value=3,
        help="More iterations = more thorough research at the expense of time")

    model_choice = st.selectbox("Claude Model",
                                options=[
                                    "claude-sonnet-4-20250514",
                                    "claude-3-7-sonnet-20250219",
                                    "claude-3-5-haiku-20241022"
                                ],
                                index=0)

    results_per_search = st.slider("Results Retrieved per Search Step",
                                   min_value=3,
                                   max_value=10,
                                   value=5)

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📝 Research Query")

    # Query input
    query = st.text_area(
        "Enter your research topic:",
        placeholder=
        "e.g., 'What are the effects of metformin on liver health?'",
        height=100,
        key="research_query")

    add_debug_message(f"Query entered: '{query}'")

with col2:
    st.header("📊 Status")
    status_container = st.container()

    with status_container:
        if st.session_state.research_started:
            if st.session_state.error_occurred:
                st.error("❌ Research failed")
            elif st.session_state.research_complete:
                st.success("✅ Research Complete!")
            elif st.session_state.research_in_progress:
                st.info("🔄 Research in progress...")
                # Show progress only up to 95% during iterations
                progress_value = min(
                    st.session_state.current_iteration /
                    num_iterations, 0.95) if num_iterations > 0 else 0
                st.progress(progress_value)
                if st.session_state.current_iteration <= num_iterations:
                    st.caption(
                        f"Iteration {st.session_state.current_iteration}/{num_iterations}"
                    )
                else:
                    st.caption("Generating final report...")
        else:
            st.info("Ready to start research")

# Start Research Button
start_button_container = st.container()
with start_button_container:
    if not st.session_state.research_in_progress:
        if st.button("🚀 Start",
                     type="primary",
                     use_container_width=True,
                     disabled=not query or not keys_configured):
            add_debug_message("Start Research button clicked")
            if query and keys_configured:
                add_debug_message(f"Starting research with query: '{query}'")
                st.session_state.research_started = True
                st.session_state.research_complete = False
                st.session_state.research_in_progress = True
                st.session_state.current_iteration = 0
                st.session_state.debug_messages = []
                st.session_state.error_occurred = False
                add_debug_message("Session state updated, triggering rerun")
                st.rerun()
            else:
                if not query:
                    add_debug_message("No query provided", "WARNING")
                if not keys_configured:
                    add_debug_message("API keys not configured", "WARNING")

# Progress display area
progress_container = st.container()

# Research execution
if st.session_state.research_in_progress and not st.session_state.research_complete:
    add_debug_message("Entering research execution block")

    with progress_container:
        st.header("🔍 Research Progress")

        # Create placeholders for live updates
        status_placeholder = st.empty()
        progress_bar = st.progress(0)
        details_placeholder = st.empty()

        try:
            add_debug_message("Initializing researcher")

            # Show initialization status
            status_placeholder.info("🔧 Initializing research assistant...")

            # Initialize researcher
            researcher = AgenticResearcher(
                anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
                exa_api_key=os.environ.get("EXA_API_KEY"),
                firecrawl_api_key=os.environ.get("FIRECRAWL_API_KEY"),
                model=model_choice,
                results_per_search=results_per_search)

            add_debug_message("Researcher initialized successfully")
            status_placeholder.info(f"📚 Starting research: '{query}'")

            # Show research configuration
            details_placeholder.markdown(f"""
            **Research Configuration:**
            - Model: {model_choice}
            - Iterations: {num_iterations}
            - Results per search: {results_per_search}
            """)

            add_debug_message(
                f"Starting research loop with {num_iterations} iterations")

            def progress_callback(message,
                                  progress_type="info",
                                  iteration_num=None,
                                  total_iterations=None):
                add_debug_message(
                    f"Progress: {message} (type: {progress_type}, iter: {iteration_num}/{total_iterations})"
                )

                # Direct iteration tracking - no parsing needed!
                if progress_type == "iteration" and iteration_num is not None and total_iterations is not None:
                    st.session_state.current_iteration = iteration_num
                    # Calculate progress (leave room for final report)
                    progress_value = min(
                        iteration_num / total_iterations * 0.95, 0.95)
                    progress_bar.progress(progress_value)
                    status_placeholder.info(f"📊 {message}")
                    add_debug_message(
                        f"Updated iteration to {iteration_num}/{total_iterations}"
                    )

                elif progress_type == "final_report":
                    # Final report generation - set to 95-100%
                    progress_bar.progress(0.95)
                    status_placeholder.info(f"📝 {message}")
                elif progress_type == "search":
                    status_placeholder.info(f"🔍 {message}")
                elif progress_type == "content":
                    status_placeholder.info(f"📄 {message}")
                elif progress_type == "error":
                    status_placeholder.error(f"❌ {message}")
                else:
                    status_placeholder.info(f"💡 {message}")

            # Set the progress callback
            researcher.progress_callback = progress_callback

            # Run the research
            add_debug_message("Calling researcher.run_research_loop")

            with st.spinner(
                    "Conducting research... This may take several minutes."):
                final_report, research_data = researcher.run_research_loop(
                    user_query=query, max_iterations=num_iterations)

            add_debug_message("Research loop completed")

            # Store results
            st.session_state.final_report = final_report
            st.session_state.research_data = research_data
            st.session_state.research_complete = True
            st.session_state.research_in_progress = False

            add_debug_message("Research completed successfully")
            status_placeholder.success("✅ Research completed!")
            progress_bar.progress(1.0)  # Set to 100% when complete

            # Force a rerun to show results
            time.sleep(1)  # Brief pause to show success message
            st.rerun()

        except Exception as e:
            add_debug_message(f"Error occurred: {str(e)}", "ERROR")
            add_debug_message(f"Traceback: {traceback.format_exc()}", "ERROR")

            st.session_state.error_occurred = True
            st.session_state.research_in_progress = False

            status_placeholder.error(f"❌ Research failed: {str(e)}")

            with st.expander("🔍 View Full Error Details", expanded=True):
                st.code(traceback.format_exc())

                # Show debug messages
                st.subheader("Debug Log:")
                for msg in st.session_state.debug_messages:
                    st.text(msg)

# Display results
if st.session_state.research_complete and st.session_state.final_report:
    add_debug_message("Displaying research results")

    st.header("📄 Report")

    # Download buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        st.download_button(
            label="📥 Download Report (Markdown)",
            data=st.session_state.final_report,
            file_name=
            f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True)

    with col2:
        st.download_button(
            label="📊 Download Research Data (JSON)",
            data=json.dumps(st.session_state.research_data, indent=2),
            file_name=
            f"research_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True)

    with col3:
        if st.button("🔄 New Research", use_container_width=True):
            add_debug_message("New Research button clicked")
            # Clear all state
            for key in [
                    'research_started', 'research_complete', 'research_data',
                    'final_report', 'current_iteration', 'debug_messages',
                    'error_occurred', 'research_in_progress'
            ]:
                st.session_state[
                    key] = False if 'started' in key or 'complete' in key or 'occurred' in key or 'progress' in key else (
                        0 if key == 'current_iteration' else
                        ([] if key == 'debug_messages' else None))
            st.rerun()

    # Display report
    with st.expander("📖 View Full Report", expanded=True):
        st.markdown(st.session_state.final_report)

    # Statistics
    if st.session_state.research_data:
        st.header("📈 Research Statistics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Iterations",
                len(st.session_state.research_data.get('iterations', [])))

        with col2:
            total_papers = sum(
                s.get('num_results', 0)
                for s in st.session_state.research_data.get(
                    'search_history', []))
            st.metric("Papers Found", total_papers)

        with col3:
            st.metric(
                "Articles Retrieved",
                len(
                    st.session_state.research_data.get(
                        'content_retrieval_history', [])))

        with col4:
            st.metric(
                "Searches",
                len(st.session_state.research_data.get('search_history', [])))

# Footer with debug info
st.markdown("---")

# Always show debug log at bottom if debug mode is on
if DEBUG:
    with st.expander("📋 Full Debug Log", expanded=False):
        if st.session_state.debug_messages:
            st.code("\n".join(st.session_state.debug_messages))
        else:
            st.write("No debug messages yet")

        # Session state dump
        st.subheader("Session State Dump:")
        st.json({
            k:
            str(v)[:100] +
            "..." if isinstance(v, str) and len(str(v)) > 100 else v
            for k, v in st.session_state.items()
        })

st.markdown("""
<div style="text-align: center; color: #666;">
    <p>Powered by Claude, Exa, and Firecrawl</p>
    <p>Debug Mode: ON</p>
</div>
""",
            unsafe_allow_html=True)
