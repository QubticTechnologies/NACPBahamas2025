# census_app/modules/auth.py
from sqlalchemy.orm import sessionmaker

import streamlit as st
import bcrypt
from census_app.modules.user_utils import register_user_logic, login_user_logic
from census_app.modules.survey_sidebar import survey_sidebar
from census_app.modules.holder_info import show_holder_dashboard, get_holder_name
from sqlalchemy import text
from census_app.db import engine
from census_app.config import TOTAL_SURVEY_SECTIONS
import pandas as pd
import requests
from streamlit_js_eval import get_geolocation
import pydeck as pdk

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --------------------- Enhanced Holder Creation with Location ---------------------
def create_holder_for_user(user_id, username):
    """Ensure holder exists for user; prompt location if new. Uses session_state to prevent duplicates."""
    if st.session_state.get(f"holder_id_{user_id}"):
        return st.session_state[f"holder_id_{user_id}"]

    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT holder_id, latitude, longitude FROM holders WHERE owner_id=:uid"),
            {"uid": user_id}
        ).mappings().first()

        if exists:
            st.session_state[f"holder_id_{user_id}"] = exists["holder_id"]
            return exists["holder_id"]

    # Enhanced location collection for new holder
    st.header("📍 Farm Location Setup")
    st.info("Please set your farm location before starting the survey.")

    # Default coordinates
    default_lat = 25.0343  # Nassau, Bahamas
    default_lon = -77.3963

    # Initialize session state for location
    if f"holder_lat_{user_id}" not in st.session_state:
        st.session_state[f"holder_lat_{user_id}"] = default_lat
    if f"holder_lon_{user_id}" not in st.session_state:
        st.session_state[f"holder_lon_{user_id}"] = default_lon

    current_lat = st.session_state[f"holder_lat_{user_id}"]
    current_lon = st.session_state[f"holder_lon_{user_id}"]


    # Map Preview
    st.markdown("#### 🗺️ Farm Location Preview")
    try:
        view_state = pdk.ViewState(latitude=current_lat, longitude=current_lon, zoom=16, pitch=45)
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame([[current_lat, current_lon]], columns=["lat", "lon"]),
            get_position=["lon", "lat"],
            get_color=[255, 0, 0, 200],
            get_radius=50,
            pickable=True,
        )
        st.pydeck_chart(pdk.Deck(
            map_style="mapbox://styles/mapbox/satellite-streets-v11",
            initial_view_state=view_state,
            layers=[layer],
            tooltip={"text": "Farm Location: {lat}, {lon}"}
        ))
    except Exception:
        st.map(pd.DataFrame([[current_lat, current_lon]], columns=["lat", "lon"]), zoom=15)

    # Location Controls
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🎯 Auto Detect My Location", key=f"auto_loc_btn_{user_id}", type="primary"):
            try:
                loc_data = get_geolocation()
                if loc_data and "coords" in loc_data:
                    detected_lat = loc_data["coords"]["latitude"]
                    detected_lon = loc_data["coords"]["longitude"]
                    st.session_state[f"holder_lat_{user_id}"] = detected_lat
                    st.session_state[f"holder_lon_{user_id}"] = detected_lon
                    st.success(f"✅ GPS Lock Acquired: {detected_lat:.6f}, {detected_lon:.6f}")
                    st.rerun()
            except Exception as e:
                st.error(f"GPS Error: {e}")

    with col_btn2:
        if st.button("🔄 Reset to Default", key=f"reset_loc_btn_{user_id}"):
            st.session_state[f"holder_lat_{user_id}"] = default_lat
            st.session_state[f"holder_lon_{user_id}"] = default_lon
            st.rerun()

    # Manual Coordinate Entry
    st.markdown("#### ✏️ Manual Coordinate Entry")
    col1, col2 = st.columns(2)
    with col1:
        manual_lat = st.number_input("Latitude", value=float(current_lat), min_value=-90.0, max_value=90.0,
                                     step=0.000001, format="%.6f", key=f"lat_input_{user_id}")
    with col2:
        manual_lon = st.number_input("Longitude", value=float(current_lon), min_value=-180.0, max_value=180.0,
                                     step=0.000001, format="%.6f", key=f"lon_input_{user_id}")

    if st.button("📍 Update Preview", key=f"update_preview_{user_id}"):
        st.session_state[f"holder_lat_{user_id}"] = manual_lat
        st.session_state[f"holder_lon_{user_id}"] = manual_lon
        st.rerun()

    # Create Holder Button
    if st.button("✅ Create Holder & Start Survey", key=f"create_holder_{user_id}", type="primary"):
        if -90 <= current_lat <= 90 and -180 <= current_lon <= 180:
            try:
                with engine.begin() as conn:
                    result = conn.execute(
                        text("""
                            INSERT INTO holders (name, owner_id, status, latitude, longitude, created_at)
                            VALUES (:name, :owner_id, 'active', :lat, :lon, NOW())
                            RETURNING holder_id
                        """),
                        {"name": username, "owner_id": user_id, "lat": current_lat, "lon": current_lon}
                    )
                    holder_id = result.scalar_one()

                    # Initialize survey progress for all sections
                    for section_id in range(1, TOTAL_SURVEY_SECTIONS + 1):
                        conn.execute(
                            text("""
                                INSERT INTO holder_survey_progress (holder_id, section_id, completed, last_accessed)
                                VALUES (:hid, :sec, FALSE, NOW())
                            """),
                            {"hid": holder_id, "sec": section_id}
                        )

                st.success("✅ Holder created successfully with location!")
                st.session_state[f"holder_id_{user_id}"] = holder_id
                st.session_state["current_section"] = 1  # Start at section 1
                st.session_state["section_completion"] = {}  # Initialize completion tracking
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to create holder: {e}")
        else:
            st.error("❌ Invalid coordinates. Please check your latitude and longitude values.")

        st.success("📌 Holder created successfully with location!")
        st.session_state[f"holder_id_{user_id}"] = holder_id
        st.rerun()


    st.stop()


# --------------------- Section Navigation Component ---------------------
def section_navigation_sidebar(holder_id):
    """Enhanced sidebar navigation for survey sections - only show when a section is selected"""
    if st.session_state.get("current_section"):
        st.sidebar.markdown("---")
        st.sidebar.subheader("📋 Survey Navigation")

        sections = {
            1: "👤 Holder Information",
            2: "💼 Labour Information",
            3: "👥 Household Information",
            4: "🏭 Agricultural Machinery",
            5: "🏞️ Land Use Information"
        }

        current_section = st.session_state.get("current_section", 1)

        selected_section = st.sidebar.selectbox(
            "Jump to section:",
            options=list(sections.keys()),
            format_func=lambda x: f"Section {x}: {sections[x]}",
            index=current_section - 1
        )

        if selected_section != current_section:
            st.session_state["current_section"] = selected_section
            st.rerun()

        # Progress tracking
        completed_count = sum(1 for i in range(1, TOTAL_SURVEY_SECTIONS + 1)
                              if st.session_state.get("section_completion", {}).get(i, False))

        st.sidebar.markdown("---")
        progress = completed_count / TOTAL_SURVEY_SECTIONS
        st.sidebar.progress(progress)
        st.sidebar.metric("Survey Progress", f"{completed_count}/{TOTAL_SURVEY_SECTIONS} Completed")


# --------------------- Section Completion Tracking ---------------------
def mark_section_complete(section_number):
    """Mark a section as completed and auto-advance to next section"""
    st.session_state["section_completion"] = st.session_state.get("section_completion", {})
    st.session_state["section_completion"][section_number] = True

    # Update database progress
    holder_id = st.session_state.get("holder_id")
    if holder_id:
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        UPDATE holder_survey_progress 
                        SET completed = TRUE, completed_at = NOW()
                        WHERE holder_id = :hid AND section_id = :sec
                    """),
                    {"hid": holder_id, "sec": section_number}
                )
        except Exception as e:
            st.error(f"Error updating progress: {e}")

    # Auto-advance to next section if not the last one
    if section_number < TOTAL_SURVEY_SECTIONS:
        st.session_state["current_section"] = section_number + 1
        st.rerun()


# --------------------- Registration Form ---------------------
def register_user():
    st.subheader("📝 Register")

    username = st.text_input("Username", key="reg_username")
    email = st.text_input("Email", key="reg_email")
    password = st.text_input("Password", type="password", key="reg_password")
    role = st.selectbox("Role", ["Holder", "Agent"], key="reg_role")

    if st.button("Register", key="register_btn"):
        if not username or not password or not email:
            st.error("⚠️ All fields are required.")
            return

        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        success, msg = register_user_logic(username, email, hashed_pw, role)

        if success:
            st.success(msg)
            if role.lower() == "holder":
                # Set user in session state before creating holder
                st.session_state["user"] = {
                    "id": success,
                    "username": username,
                    "role": role
                }
                create_holder_for_user(user_id=success, username=username)
            st.rerun()
        else:
            st.error(msg)


# --------------------- Login Form ---------------------
def login_user(role=None):
    st.subheader("🔑 Login")

    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if role:
        st.info(f"Logging in as: {role}")

    if st.button("Login", key="login_btn"):
        if not username or not password:
            st.error("⚠️ Username and password are required.")
            return

        success, msg, session_info = login_user_logic(username, password, role=role)

        if success:
            st.session_state["user"] = {
                "id": session_info["user_id"],
                "username": session_info["username"],
                "role": session_info["user_role"]
            }

            # Initialize survey state for holders
            if session_info["user_role"].lower() == "holder":
                st.session_state["current_section"] = None  # Don't auto-start survey
                st.session_state["section_completion"] = {}
                create_holder_for_user(session_info["user_id"], session_info["username"])

            st.success(msg)
            st.rerun()
        else:
            st.error(msg)


# --------------------- Logout ---------------------
def logout_user():
    if st.button("🚪 Logout", key="logout_btn"):
        for key in ["user", "current_section", "section_completion", "holder_id"]:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state["logged_out"] = True
        st.success("Logged out successfully!")
        st.rerun()


# --------------------- Enhanced Holder Dashboard Integration ---------------------
def show_enhanced_holder_dashboard(holder_id):
    """Enhanced holder dashboard - only show survey sections when explicitly started"""
    if not holder_id:
        st.error("No holder ID provided.")
        return

    # Get holder info
    try:
        with engine.connect() as conn:
            holder_info = conn.execute(
                text("SELECT name, latitude, longitude FROM holders WHERE holder_id = :hid"),
                {"hid": holder_id}
            ).mappings().first()
    except Exception as e:
        st.error(f"Error fetching holder info: {e}")
        return

    if not holder_info:
        st.error("Holder not found.")
        return

    st.sidebar.markdown(f"<h4 style='text-align:center;font-weight:bold;'>{holder_info['name']}</h4>",
                        unsafe_allow_html=True)

    # Show holder information and start survey button
    st.title(f"🏠 Holder Dashboard: {holder_info['name']}")

    # Holder location display
    st.subheader("📍 Farm Location")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Latitude:** {holder_info['latitude']:.6f}")
    with col2:
        st.write(f"**Longitude:** {holder_info['longitude']:.6f}")

    # Show map of holder location
    try:
        df = pd.DataFrame([[holder_info['latitude'], holder_info['longitude']]], columns=["lat", "lon"])
        st.map(df, zoom=15)
    except Exception as e:
        st.error(f"Error displaying map: {e}")

    # Survey management section
    st.subheader("📋 Survey Management")

    # Check if survey is in progress
    current_section = st.session_state.get("current_section")

    if current_section is None:
        # Survey not started - show start button
        st.info("🎯 No survey in progress. Start a new survey to begin data collection.")

        col_start1, col_start2 = st.columns([2, 1])
        with col_start1:
            if st.button("🚀 Start New Survey", type="primary", use_container_width=True):
                st.session_state["current_section"] = 1
                st.session_state["section_completion"] = {}
                st.rerun()

        # Show previous completion status if any
        try:
            with engine.connect() as conn:
                completed_sections = conn.execute(
                    text("""
                        SELECT COUNT(*) as completed_count 
                        FROM holder_survey_progress 
                        WHERE holder_id = :hid AND completed = TRUE
                    """),
                    {"hid": holder_id}
                ).scalar()

                if completed_sections > 0:
                    st.success(
                        f"✅ You have completed {completed_sections}/{TOTAL_SURVEY_SECTIONS} sections in previous surveys.")

        except Exception as e:
            # Silently handle database errors
            pass

    else:
        # Survey in progress - show survey sections
        section_navigation_sidebar(holder_id)

        # Progress header
        col_prog1, col_prog2, col_prog3 = st.columns([1, 2, 1])
        with col_prog2:
            st.markdown(f"### Section {current_section} of {TOTAL_SURVEY_SECTIONS}")
            progress = current_section / TOTAL_SURVEY_SECTIONS
            st.progress(progress)

        # Import survey sections
        try:
            from modules . household_information import household_information
            from modules . holding_labour_form import holding_labour_form
            from modules . holder_information_form import holder_information_form
            from modules . agricultural_machinery import agricultural_machinery_section
            from modules . land_use import land_use_section
        except ImportError as e:
            st.error(f"Error importing survey sections: {e}")
            return

        # Render current survey section with auto-advance capability
        section_completed = False

        if current_section == 1:
            st.session_state["current_holder_id"] = holder_id
            section_completed = holder_information_form()
        elif current_section == 2:
            st.session_state["current_holder_id"] = holder_id
            section_completed = holding_labour_form()
        elif current_section == 3:
            st.session_state["current_holder_id"] = holder_id
            section_completed = household_information()
        elif current_section == 4:
            # Agricultural Machinery Section
            machinery_data = agricultural_machinery_section(holder_id)
            if machinery_data:
                st.session_state["machinery_form_data"] = machinery_data
                section_completed = True
        elif current_section == 5:
            # Land Use Section
            land_use_data = land_use_section(holder_id)
            if land_use_data:
                st.session_state["land_use_form_data"] = land_use_data
                section_completed = True

        # Auto-advance if section is completed
        if section_completed and current_section < TOTAL_SURVEY_SECTIONS:
            mark_section_complete(current_section)

        # Navigation buttons (only show when survey is active)
        st.divider()
        col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])

        with col_nav1:
            if st.button("⬅ Previous",
                         disabled=current_section <= 1,
                         use_container_width=True,
                         help="Go to previous section") and current_section > 1:
                st.session_state["current_section"] -= 1
                st.rerun()

        with col_nav3:
            if current_section < TOTAL_SURVEY_SECTIONS:
                if st.button("Next ➡",
                             type="primary",
                             use_container_width=True,
                             help="Continue to next section"):
                    # Mark current section as completed before moving forward
                    mark_section_complete(current_section)
            else:
                if st.button("✅ Complete Survey",
                             type="primary",
                             use_container_width=True,
                             help="Finish all survey sections"):
                    # Mark final section as completed
                    mark_section_complete(current_section)
                    st.success("🎉 Survey completed successfully!")
                    st.balloons()

                    # Show completion summary
                    with st.expander("📋 Survey Completion Summary", expanded=True):
                        st.info(f"""
                        **All {TOTAL_SURVEY_SECTIONS} survey sections have been completed:**
                        - ✅ Section 1: Holder Information
                        - ✅ Section 2: Labour Information  
                        - ✅ Section 3: Household Information
                        - ✅ Section 4: Agricultural Machinery
                        - ✅ Section 5: Land Use Information

                        **Thank you for participating in the Agricultural Census!**

                        Your data has been securely saved and will contribute to national agricultural planning.
                        """)

                    # Option to restart survey
                    if st.button("🔄 Start New Survey"):
                        st.session_state["current_section"] = None  # Return to dashboard
                        st.session_state["section_completion"] = {}
                        st.rerun()

        # Survey progress dashboard (only show when survey is active)
        st.divider()
        st.subheader("📊 Survey Progress")

        # Completion status
        completed_count = sum(1 for i in range(1, TOTAL_SURVEY_SECTIONS + 1)
                              if st.session_state.get("section_completion", {}).get(i, False))

        col_dash1, col_dash2, col_dash3 = st.columns(3)
        with col_dash1:
            st.metric("Completed", f"{completed_count}/{TOTAL_SURVEY_SECTIONS}")
        with col_dash2:
            st.metric("Current Section", f"Section {current_section}")
        with col_dash3:
            status = "Completed" if completed_count == TOTAL_SURVEY_SECTIONS else "In Progress"
            st.metric("Status", status)

    # Quick actions in sidebar (always show)
    st.sidebar.markdown("---")
    st.sidebar.subheader("🚀 Quick Actions")

    if current_section is not None:
        # Survey is active - show pause/restart options
        if st.sidebar.button("⏸️ Pause Survey", key="pause_survey"):
            st.session_state["current_section"] = None
            st.rerun()

        if st.sidebar.button("🔄 Restart Survey", key="restart_survey"):
            st.session_state["current_section"] = 1
            st.session_state["section_completion"] = {}
            st.rerun()
    else:
        # Survey not active - show start option
        if st.sidebar.button("🚀 Start Survey", key="start_survey_sidebar", type="primary"):
            st.session_state["current_section"] = 1
            st.session_state["section_completion"] = {}
            st.rerun()


# --------------------- Enhanced Sidebar Wrapper ---------------------
def auth_sidebar():
    """Enhanced sidebar for auth + holder dashboard integration"""
    if not st.session_state.get("user"):
        # Login/Register section
        survey_sidebar(holder_id=None)

        tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])

        with tab1:
            login_user()

        with tab2:
            register_user()

    else:
        user_role = st.session_state["user"]["role"]
        user_id = st.session_state["user"]["id"]

        if user_role.lower() == "holder":
            # Create holder safely and get holder_id
            holder_id = create_holder_for_user(user_id, st.session_state["user"]["username"])

            # Render enhanced holder dashboard (shows holder info first, survey only when started)
            show_enhanced_holder_dashboard(holder_id)

            # Render survey sidebar for holder
            survey_sidebar(holder_id=holder_id)

        else:
            # Agents or other roles
            survey_sidebar(holder_id=None)
            st.info(f"👤 Logged in as: **{st.session_state['user']['username']}** ({user_role})")
            st.write("Agent dashboard functionality coming soon...")

        # Logout button
        st.sidebar.markdown("---")
        logout_user()


# --------------------- Quick Access Functions ---------------------
def get_current_section():
    """Get current survey section"""
    return st.session_state.get("current_section")


def get_section_completion_status():
    """Get completion status for all sections"""
    return st.session_state.get("section_completion", {})


def reset_survey_progress():
    """Reset survey progress to start"""
    st.session_state["current_section"] = None  # Return to dashboard
    st.session_state["section_completion"] = {}