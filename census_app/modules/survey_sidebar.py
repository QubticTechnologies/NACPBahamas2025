import streamlit as st
from modules.holder_information_form import holder_information_form
from modules.holding_labour_form import holding_labour_form
from modules.holding_labour_permanent import holding_labour_permanent_form
from modules.household_information import household_information
from modules.agricultural_machinery import agricultural_machinery_section
from modules.land_use import land_use_section
from modules.survey_helpers import get_completed_sections

# =============================================================================
# PROFESSIONAL SURVEY CONFIGURATION
# =============================================================================
SURVEY_SECTIONS = {
    1: {
        "label": "👤 Holder Information & Farm Location",
        "func": holder_information_form,
        "needs_holder_id": True,
        "description": "Primary holder details and farm geospatial data"
    },
    2: {
        "label": "👥 Household Information",
        "func": household_information,
        "needs_holder_id": True,
        "description": "Household demographics and member profiles"
    },
    3: {
        "label": "💼 Labour Information (General)",
        "func": holding_labour_form,
        "needs_holder_id": True,
        "description": "General workforce and seasonal labor data"
    },
    4: {
        "label": "👨‍💼 Labour Information (Permanent Workers)",
        "func": holding_labour_permanent_form,
        "needs_holder_id": True,
        "description": "Permanent workforce management and analytics"
    },
    5: {
        "label": "🏭 Agricultural Machinery",
        "func": agricultural_machinery_section,
        "needs_holder_id": True,
        "description": "Farm equipment and machinery inventory"
    },
    6: {
        "label": "🏞️ Land Use & Management",
        "func": land_use_section,
        "needs_holder_id": True,
        "description": "Land utilization patterns and agricultural practices"
    },
}


# =============================================================================
# PROFESSIONAL SURVEY SIDEBAR
# =============================================================================
def inject_survey_styles():
    """Inject professional CSS styles for survey interface"""
    st.markdown("""
    <style>
        .survey-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 12px;
            color: white;
            margin-bottom: 1.5rem;
        }
        .progress-container {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
        }
        .section-btn-completed {
            background: #d4edda !important;
            color: #155724 !important;
            border: 1px solid #c3e6cb !important;
        }
        .section-btn-current {
            background: #cce5ff !important;
            color: #004085 !important;
            border: 1px solid #b8daff !important;
        }
        .section-btn-upcoming {
            background: #e2e3e5 !important;
            color: #383d41 !important;
            border: 1px solid #d6d8db !important;
        }
        .quick-actions {
            background: white;
            border-radius: 10px;
            padding: 1rem;
            border: 1px solid #e9ecef;
            margin: 1rem 0;
        }
    </style>
    """, unsafe_allow_html=True)


def survey_sidebar(holder_id=None, prefix=""):
    """Professional survey navigation sidebar"""

    # Inject professional styles
    inject_survey_styles()

    st.sidebar.markdown("""
    <div class="survey-header">
        <h3>📋 Agricultural Census</h3>
        <p>Survey Navigation</p>
    </div>
    """, unsafe_allow_html=True)

    if holder_id is None:
        st.sidebar.info("👈 Please select a farm holder to view survey progress.")
        return

    # ==================== HOLDER INFORMATION ====================
    try:
        from census_app.db import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            holder_info = conn.execute(
                text("SELECT name FROM holders WHERE holder_id = :hid"),
                {"hid": holder_id}
            ).fetchone()
        holder_name = holder_info[0] if holder_info else f"Holder {holder_id}"

        st.sidebar.markdown(
            f"<div style='text-align:center; font-weight:bold; font-size:1.1em; margin-bottom: 1rem; padding: 0.5rem; background: #f8f9fa; border-radius: 8px;'>🏡 {holder_name}</div>",
            unsafe_allow_html=True
        )
    except Exception as e:
        st.sidebar.error(f"🔧 Error loading holder info: {e}")
        return

    st.sidebar.markdown("---")

    # ==================== PROGRESS TRACKING ====================
    completed_sections = set(get_completed_sections(holder_id))
    completed_sections = {s for s in completed_sections if s in SURVEY_SECTIONS}

    # Initialize next section
    state_key_next = f"{prefix}_next_section"
    if state_key_next not in st.session_state:
        for sec_id in sorted(SURVEY_SECTIONS.keys()):
            if sec_id not in completed_sections:
                st.session_state[state_key_next] = sec_id
                break
        else:
            st.session_state[state_key_next] = max(SURVEY_SECTIONS.keys())

    next_section = st.session_state[state_key_next]

    # ==================== PROGRESS VISUALIZATION ====================
    total_sections = len(SURVEY_SECTIONS)
    completed_count = len(completed_sections)

    # Calculate and clamp progress value
    progress = completed_count / total_sections if total_sections > 0 else 0
    progress = min(max(progress, 0.0), 1.0)

    # Progress display
    st.sidebar.markdown("#### 📊 Survey Progress")

    col_prog1, col_prog2 = st.sidebar.columns([2, 1])
    with col_prog1:
        st.sidebar.progress(progress)
    with col_prog2:
        percentage = round((completed_count / total_sections) * 100, 1) if total_sections > 0 else 0
        st.sidebar.metric("", f"{percentage}%")

    st.sidebar.markdown(
        f"<div style='text-align:center; font-size:0.9em; color:#666;'>{completed_count}/{total_sections} sections completed</div>",
        unsafe_allow_html=True
    )

    st.sidebar.markdown("---")

    # ==================== SECTION NAVIGATION ====================
    st.sidebar.markdown("#### 🧭 Navigation")

    for sec_id, sec in SURVEY_SECTIONS.items():
        # Determine section status
        if sec_id in completed_sections:
            status_icon = "✅"
            status_class = "section-btn-completed"
            tooltip = f"Completed: {sec['description']}"
        elif sec_id == next_section:
            status_icon = "🎯"
            status_class = "section-btn-current"
            tooltip = f"Current: {sec['description']}"
        else:
            status_icon = "⏳"
            status_class = "section-btn-upcoming"
            tooltip = f"Upcoming: {sec['description']}"

        label = f"{status_icon} {sec['label']}"
        btn_key = f"{prefix}_sec_btn_{sec_id}"

        # Create navigation button
        clicked = st.sidebar.button(
            label,
            key=btn_key,
            help=tooltip,
            use_container_width=True
        )

        if clicked:
            st.session_state[state_key_next] = sec_id
            st.rerun()

    # ==================== QUICK ACTIONS ====================
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 🚀 Quick Actions")

    with st.sidebar.container():
        col_action1, col_action2 = st.columns(2)

        with col_action1:
            if st.button("🔄 Reset", key=f"{prefix}_reset", use_container_width=True):
                if st.sidebar.checkbox("Confirm reset all progress", key=f"{prefix}_confirm_reset"):
                    reset_survey_progress(holder_id)
                    st.session_state[state_key_next] = 1
                    st.success("✅ Survey progress reset successfully!")
                    st.rerun()

        with col_action2:
            if st.button("📊 Export", key=f"{prefix}_export", use_container_width=True):
                export_survey_progress(holder_id)

    # ==================== CURRENT SECTION CONTROLS ====================
    st.sidebar.markdown("---")
    current_section = SURVEY_SECTIONS.get(st.session_state[state_key_next])
    if current_section:
        st.sidebar.markdown(f"#### 🎯 Current Section")
        st.sidebar.info(f"**{current_section['label']}**\n\n{current_section['description']}")

        if st.sidebar.button(
                "✅ Mark Section Complete",
                key=f"{prefix}_complete_{st.session_state[state_key_next]}",
                use_container_width=True,
                type="primary"
        ):
            mark_section_complete(holder_id, st.session_state[state_key_next], prefix)
            st.rerun()

    # Render main content area
    render_current_section_content(holder_id, prefix)


# =============================================================================
# MAIN CONTENT RENDERER
# =============================================================================
def render_current_section_content(holder_id, prefix=""):
    """Render the current survey section with professional presentation"""

    state_key_next = f"{prefix}_next_section"
    current_section_id = st.session_state.get(state_key_next, 1)
    current_section = SURVEY_SECTIONS.get(current_section_id)

    if not current_section:
        st.error("❌ Invalid section selected")
        return

    # Professional section header
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 15px; color: white; margin-bottom: 2rem;">
        <h1>Section {current_section_id}: {current_section['label']}</h1>
        <p style="margin: 0; opacity: 0.9;">{current_section['description']}</p>
    </div>
    """, unsafe_allow_html=True)

    try:
        # Render the section content
        if current_section["needs_holder_id"]:
            current_section["func"](holder_id=holder_id, prefix=prefix)
        else:
            current_section["func"](prefix=prefix)

    except Exception as e:
        st.error(f"""
        ❌ **Error rendering section {current_section_id}**

        There was an issue loading this section. Please try refreshing the page.

        Technical details: {str(e)}
        """)


# =============================================================================
# PROFESSIONAL HELPER FUNCTIONS
# =============================================================================
def mark_section_complete(holder_id, section_id, prefix=""):
    """Mark a section as complete with professional feedback"""
    try:
        from census_app.db import engine
        from sqlalchemy import text

        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO holder_survey_progress (holder_id, section_id, completed, completed_at)
                    VALUES (:hid, :sec, TRUE, NOW())
                    ON CONFLICT (holder_id, section_id) DO UPDATE
                    SET completed = TRUE, completed_at = NOW()
                """),
                {"hid": holder_id, "sec": section_id}
            )

        # Determine next section
        next_section = section_id + 1
        if next_section in SURVEY_SECTIONS:
            st.session_state[f"{prefix}_next_section"] = next_section

        st.success(f"""
        ✅ **Section {section_id} Completed Successfully!**

        {SURVEY_SECTIONS[section_id]['label']} has been marked as complete.
        You can now proceed to the next section.
        """)

    except Exception as e:
        st.error(f"❌ Error marking section complete: {e}")


def reset_survey_progress(holder_id):
    """Reset survey progress with confirmation"""
    try:
        from census_app.db import engine
        from sqlalchemy import text

        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM holder_survey_progress WHERE holder_id = :hid"),
                {"hid": holder_id}
            )

        return True

    except Exception as e:
        st.error(f"❌ Error resetting progress: {e}")
        return False


def export_survey_progress(holder_id):
    """Export survey progress with professional formatting"""
    try:
        from census_app.db import engine
        from sqlalchemy import text
        import pandas as pd
        from datetime import datetime

        with engine.connect() as conn:
            progress_data = conn.execute(
                text("""
                    SELECT section_id, completed, completed_at 
                    FROM holder_survey_progress 
                    WHERE holder_id = :hid
                    ORDER BY section_id
                """),
                {"hid": holder_id}
            ).fetchall()

        if progress_data:
            df = pd.DataFrame(progress_data, columns=['section_id', 'completed', 'completed_at'])
            df['section_name'] = df['section_id'].map(
                lambda x: SURVEY_SECTIONS.get(x, {}).get('label', f'Section {x}')
            )
            df['status'] = df['completed'].map({True: 'Completed', False: 'In Progress'})

            # Format for display
            display_df = df[['section_name', 'status', 'completed_at']].copy()
            display_df.columns = ['Section', 'Status', 'Completed At']

            csv = df.to_csv(index=False)

            st.sidebar.success("📊 Progress data ready for export")
            st.sidebar.download_button(
                label="📥 Download Progress Report",
                data=csv,
                file_name=f"agricultural_census_progress_{holder_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

            # Show preview
            with st.sidebar.expander("📋 Preview Export Data"):
                st.dataframe(display_df, use_container_width=True)

        else:
            st.sidebar.info("📝 No survey progress data available for export")

    except Exception as e:
        st.sidebar.error(f"❌ Error exporting progress: {e}")


# =============================================================================
# INTEGRATION HELPER FUNCTIONS
# =============================================================================
def get_current_section(prefix=""):
    """Get the current active section ID"""
    return st.session_state.get(f"{prefix}_next_section", 1)


def set_current_section(section_id, prefix=""):
    """Set the current active section ID"""
    st.session_state[f"{prefix}_next_section"] = section_id


def get_survey_completion(holder_id):
    """Get comprehensive survey completion statistics"""
    completed_sections = set(get_completed_sections(holder_id))
    completed_sections = {s for s in completed_sections if s in SURVEY_SECTIONS}

    total_sections = len(SURVEY_SECTIONS)
    completed_count = len(completed_sections)
    percentage = (completed_count / total_sections) * 100 if total_sections > 0 else 0

    return {
        "completed": completed_count,
        "total": total_sections,
        "percentage": round(percentage, 1),
        "completed_sections": completed_sections,
        "remaining_sections": total_sections - completed_count,
        "is_complete": completed_count == total_sections
    }


def get_next_incomplete_section(holder_id):
    """Get the next incomplete section ID"""
    completed_sections = set(get_completed_sections(holder_id))
    for sec_id in sorted(SURVEY_SECTIONS.keys()):
        if sec_id not in completed_sections:
            return sec_id
    return max(SURVEY_SECTIONS.keys())


# =============================================================================
# SURVEY STATUS COMPONENT
# =============================================================================
def render_survey_status(holder_id):
    """Render a professional survey status component"""
    completion = get_survey_completion(holder_id)

    st.markdown("### 📈 Survey Progress Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Completion Rate", f"{completion['percentage']}%")

    with col2:
        st.metric("Sections Completed", f"{completion['completed']}/{completion['total']}")

    with col3:
        st.metric("Remaining", completion['remaining_sections'])

    with col4:
        status = "✅ Complete" if completion['is_complete'] else "🟡 In Progress"
        st.metric("Status", status)

    # Progress bar
    st.progress(completion['percentage'] / 100)

    return completion


# =============================================================================
# MAIN SURVEY EXECUTION
# =============================================================================
def execute_survey(holder_id, prefix=""):
    """
    Main function to execute the agricultural census survey
    """
    if not holder_id:
        st.error("🚫 Holder ID required to start survey")
        return

    # Initialize survey state
    if f"{prefix}_next_section" not in st.session_state:
        st.session_state[f"{prefix}_next_section"] = get_next_incomplete_section(holder_id)

    # Render the survey interface
    survey_sidebar(holder_id, prefix)


# =============================================================================
# TEST FUNCTION
# =============================================================================
def test_survey_interface():
    """Test the survey interface"""
    st.title("🧪 Agricultural Census Survey - Test Interface")

    # Test controls
    col1, col2 = st.columns(2)
    with col1:
        holder_id = st.number_input("Test Holder ID", value=1, min_value=1)
    with col2:
        prefix = st.text_input("Test Prefix", value="test")

    # Execute survey
    execute_survey(holder_id, prefix)


if __name__ == "__main__":
    test_survey_interface()