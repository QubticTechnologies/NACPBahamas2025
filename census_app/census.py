import sys
import os
import streamlit as st
import pandas as pd
import requests
from sqlalchemy import text
from datetime import date
from streamlit_js_eval import get_geolocation
import pydeck as pdk

# --- Paths for imports ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(__file__))

# --- DB & Config ---
from db import engine
from config import USERS_TABLE, HOLDERS_TABLE, TOTAL_SURVEY_SECTIONS

# --- Lazy Imports to avoid circular imports ---
def _import_auth():
    from modules.auth import login_user, register_user, logout_user, create_holder_for_user
    return login_user, register_user, logout_user, create_holder_for_user

def _import_dashboards():
    from modules.dashboards import holder_dashboard, agent_dashboard
    from modules.admin_dashboard.dashboard import admin_dashboard
    return holder_dashboard, agent_dashboard, admin_dashboard

def _import_survey_sidebar():
    from modules.survey_sidebar import survey_sidebar
    return survey_sidebar

# --- Dynamic Imports ---
login_user, register_user, logout_user, create_holder_for_user = _import_auth()
holder_dashboard, agent_dashboard, admin_dashboard = _import_dashboards()
survey_sidebar = _import_survey_sidebar()

# --- Survey Forms & Helpers ---
from modules.household_information import household_information
from modules.holding_labour_form import holding_labour_form
from modules.holder_information_form import holder_information_form
from modules.agricultural_machinery import agricultural_machinery_section
from modules.land_use import land_use_section
from modules.holding_labour_permanent import holding_labour_permanent_form
from helpers import calculate_age

# =============================================================================
# STREAMLIT CONFIGURATION & THEMING
# =============================================================================
st.set_page_config(
    page_title="🌾 Agricultural Census Intelligence Platform",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# Custom CSS for enhanced UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 10px 0;
        margin-bottom: 20px;
    }
    .section-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #667eea;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-card {
        background: white;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .progress-bar-container {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 3px;
        margin: 10px 0;
    }
    .success-badge {
        background: #d4edda;
        color: #155724;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .warning-badge {
        background: #fff3cd;
        color: #856404;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SESSION STATE MANAGEMENT
# =============================================================================
def initialize_session_state():
    """Initialize all session state variables with proper defaults"""
    defaults = {
        "user": None,
        "holder_id": None,
        "logged_out": False,
        "current_section": None,
        "holder_form_data": {},
        "labour_form_data": {},
        "permanent_labour_data": {},
        "household_form_data": {},
        "machinery_form_data": {},
        "land_use_form_data": {},
        "section_completion": {},
        "survey_started": False,
        "dashboard_mode": "collapsible"
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state()

# =============================================================================
# ENHANCED HELPER FUNCTIONS
# =============================================================================
def get_user_status(user_id: int):
    """Get user status with enhanced error handling"""
    try:
        with engine.connect() as conn:
            return conn.execute(
                text(f"SELECT status FROM {USERS_TABLE} WHERE id=:uid"),
                {"uid": user_id}
            ).scalar()
    except Exception as e:
        st.error(f"🔧 Database connection error: {e}")
        return None

def mark_section_complete(section_number):
    """Mark a section as completed and auto-advance to next section"""
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
            st.error(f"📊 Progress update failed: {e}")

    # Auto-advance to next section if not the last one
    if section_number < TOTAL_SURVEY_SECTIONS:
        st.session_state["current_section"] = section_number + 1
        st.rerun()

def get_completed_sections_count():
    """Get count of completed sections with validation"""
    completion_dict = st.session_state.get("section_completion", {})
    return sum(1 for section_num in range(1, TOTAL_SURVEY_SECTIONS + 1)
               if completion_dict.get(section_num, False))

def calculate_survey_progress():
    """Calculate comprehensive survey progress metrics"""
    completed = get_completed_sections_count()
    progress_percentage = (completed / TOTAL_SURVEY_SECTIONS) * 100
    return completed, progress_percentage

# =============================================================================
# ENHANCED LOCATION WIDGET COMPONENT
# =============================================================================
def holder_location_widget(holder_id):
    """Advanced farm location mapping component"""

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### 📍 Farm Geospatial Intelligence")
    st.info("🎯 **Location Precision Guide**: Use auto-detection for optimal accuracy or manually input coordinates for precise farm mapping.")

    # Fetch stored coordinates
    with engine.connect() as conn:
        loc = conn.execute(
            text("SELECT latitude, longitude, street_address FROM holders WHERE holder_id=:hid"),
            {"hid": holder_id}
        ).fetchone()

    # Defaults
    stored_lat = loc[0] if loc and loc[0] is not None else 25.0343
    stored_lon = loc[1] if loc and loc[1] is not None else -77.3963
    stored_address = loc[2] if loc and len(loc) > 2 and loc[2] else "No address saved"

    # Session state
    st.session_state.setdefault(f"holder_lat_{holder_id}", stored_lat)
    st.session_state.setdefault(f"holder_lon_{holder_id}", stored_lon)
    st.session_state.setdefault(f"holder_address_{holder_id}", stored_address)

    current_lat = st.session_state[f"holder_lat_{holder_id}"]
    current_lon = st.session_state[f"holder_lon_{holder_id}"]
    current_address = st.session_state[f"holder_address_{holder_id}"]

    # ==================== INTERACTIVE MAP VISUALIZATION ====================
    col_map, col_info = st.columns([2, 1])

    with col_map:
        st.markdown("#### 🗺️ Live Location Preview")
        try:
            view_state = pdk.ViewState(
                latitude=current_lat,
                longitude=current_lon,
                zoom=16,
                pitch=45
            )
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=pd.DataFrame([[current_lat, current_lon]], columns=["lat", "lon"]),
                get_position=["lon", "lat"],
                get_color=[255, 87, 51, 200],
                get_radius=50,
                pickable=True,
            )
            st.pydeck_chart(pdk.Deck(
                map_style="mapbox://styles/mapbox/satellite-streets-v11",
                initial_view_state=view_state,
                layers=[layer],
                tooltip={"html": "<b>Farm Location</b><br/>Lat: {lat}<br/>Lon: {lon}"}
            ))
        except Exception as e:
            st.warning(f"Advanced map unavailable: {e}")
            st.map(pd.DataFrame([[current_lat, current_lon]], columns=["lat", "lon"]), zoom=15)

    with col_info:
        st.markdown("#### 📊 Location Analytics")

        # Precision analysis
        precision_level = "High (Sub-meter)" if abs(current_lat - int(current_lat)) > 0.0001 else "Medium"

        st.metric("Precision Level", precision_level)
        st.metric("Latitude", f"{current_lat:.6f}")
        st.metric("Longitude", f"{current_lon:.6f}")

        # Location status
        if current_lat == 25.0343 and current_lon == -77.3963:
            st.markdown('<div class="warning-badge">⚠️ Default Location</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="success-badge">✅ Custom Location Set</div>', unsafe_allow_html=True)

    # ==================== LOCATION CONTROLS ====================
    st.markdown("---")
    st.markdown("#### 🎮 Location Management")

    col_controls = st.columns([1, 1, 1, 1])

    with col_controls[0]:
        if st.button("🎯 Auto-Detect GPS", type="primary", use_container_width=True):
            with st.spinner("🛰️ Acquiring high-precision GPS coordinates..."):
                try:
                    loc_data = get_geolocation()
                    if loc_data and "coords" in loc_data:
                        detected_lat = loc_data["coords"]["latitude"]
                        detected_lon = loc_data["coords"]["longitude"]

                        st.session_state[f"holder_lat_{holder_id}"] = detected_lat
                        st.session_state[f"holder_lon_{holder_id}"] = detected_lon

                        st.success("✅ GPS Lock Established!")

                        # Enhanced geocoding
                        try:
                            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={detected_lat}&lon={detected_lon}&zoom=18"
                            headers = {"User-Agent": "AgriCensusPlatform/2.0"}
                            resp = requests.get(url, headers=headers, timeout=10).json()
                            address = resp.get("display_name", "Address not available")
                            st.info(f"**Detected Address:**\n{address}")
                        except Exception:
                            st.warning("📍 Address lookup unavailable")

                        st.rerun()
                    else:
                        st.error("🚫 GPS access denied. Enable location services.")
                except Exception as e:
                    st.error(f"❌ GPS acquisition failed: {e}")

    with col_controls[1]:
        if st.button("🔄 Reset to Saved", use_container_width=True):
            st.session_state[f"holder_lat_{holder_id}"] = stored_lat
            st.session_state[f"holder_lon_{holder_id}"] = stored_lon
            st.session_state[f"holder_address_{holder_id}"] = stored_address
            st.rerun()

    # ==================== MANUAL COORDINATE INPUT ====================
    st.markdown("#### ✏️ Coordinate Precision Input")
    col_coords = st.columns(2)

    with col_coords[0]:
        manual_lat = st.number_input(
            "**Latitude**",
            value=float(current_lat),
            min_value=-90.0,
            max_value=90.0,
            step=0.000001,
            format="%.6f",
            help="Precise latitude coordinate (-90 to 90)"
        )
    with col_coords[1]:
        manual_lon = st.number_input(
            "**Longitude**",
            value=float(current_lon),
            min_value=-180.0,
            max_value=180.0,
            step=0.000001,
            format="%.6f",
            help="Precise longitude coordinate (-180 to 180)"
        )

    if st.button("📍 Update Map Preview", use_container_width=True):
        st.session_state[f"holder_lat_{holder_id}"] = manual_lat
        st.session_state[f"holder_lon_{holder_id}"] = manual_lon
        # Update address
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={manual_lat}&lon={manual_lon}&zoom=18&addressdetails=1"
            headers = {"User-Agent": "AgriCensusApp/1.0"}
            resp = requests.get(url, headers=headers, timeout=10).json()
            address = resp.get("display_name", "Address not available")
            st.session_state[f"holder_address_{holder_id}"] = address
        except Exception:
            st.warning("⚠️ Could not fetch address")
        st.rerun()

    # ==================== LOCATION PERSISTENCE ====================
    st.markdown("---")
    col_save, col_status = st.columns([3, 1])

    with col_save:
        if st.button("💾 Persist Farm Location", type="primary", use_container_width=True):
            if -90 <= current_lat <= 90 and -180 <= current_lon <= 180:
                if abs(current_lat - 25.0343) < 0.0001 and abs(current_lon + 77.3963) < 0.0001:
                    st.warning("⚠️ Default location detected. Please set actual farm coordinates.")
                else:
                    try:
                        with engine.begin() as conn:
                            conn.execute(
                                text("UPDATE holders SET latitude=:lat, longitude=:lon WHERE holder_id=:hid"),
                                {"lat": current_lat, "lon": current_lon, "hid": holder_id}
                            )
                        st.success("✅ Farm location persisted successfully!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"❌ Location persistence failed: {e}")
            else:
                st.error("❌ Invalid coordinate values detected.")

    with col_status:
        status = "Custom" if current_lat != 25.0343 or current_lon != -77.3963 else "Default"
        st.metric("Location Status", status)

    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# ADVANCED COLLAPSIBLE DASHBOARD - UPDATED SECTION ORDER
# =============================================================================
def collapsible_dashboard(holder_id):
    """Modern dashboard with intelligent section management - UPDATED ORDER"""

    if "user" not in st.session_state:
        st.error("🔐 Authentication required for dashboard access")
        return

    user_id = st.session_state["user"]["id"]

    # Fetch holder information
    try:
        with engine.connect() as conn:
            holders = conn.execute(
                text(f"SELECT * FROM {HOLDERS_TABLE} WHERE owner_id=:uid ORDER BY holder_id"),
                {"uid": user_id}
            ).mappings().all()
    except Exception as e:
        st.error(f"📊 Data retrieval error: {e}")
        return

    # Holder initialization workflow
    if not holders:
        st.markdown("""
        <div style='text-align: center; padding: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   border-radius: 15px; color: white;'>
            <h2>🏡 Welcome to Agricultural Census</h2>
            <p>Begin your agricultural survey by creating your first farm holder profile</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚀 Initialize First Farm Holder", type="primary", use_container_width=True):
            with engine.begin() as conn:
                result = conn.execute(
                    text("INSERT INTO holders (owner_id, name) VALUES (:uid, :name)"),
                    {"uid": user_id, "name": "Primary Farm Holder"}
                )
                new_holder_id = result.inserted_primary_key[0] if result.inserted_primary_key else None

                if new_holder_id:
                    st.session_state["holder_id"] = new_holder_id
                    st.success("✅ Farm holder profile created successfully!")
                    st.rerun()
                else:
                    st.error("❌ Profile creation failed")
        return

    # Holder selection and context
    selected_holder = next((h for h in holders if h["holder_id"] == holder_id), None)
    if not selected_holder:
        st.error("❌ Selected farm holder not found")
        return

    # ==================== DASHBOARD HEADER ====================
    st.markdown(f"""
    <div class="main-header">
        🌾 Agricultural Census Intelligence Platform
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px;">
        <h3>👋 Welcome, {selected_holder['name']}!</h3>
        <p>Comprehensive agricultural data collection for informed decision making and policy development.</p>
    </div>
    """, unsafe_allow_html=True)

    # ==================== SURVEY SECTIONS MANAGEMENT - UPDATED ORDER ====================
    sections = {
        1: "Holder Information & Geospatial Data",
        2: "Household Demographic Intelligence",  # MOVED TO SECTION 2
        3: "Labor Force Analytics - General",
        4: "Labor Force Analytics - Permanent Workforce",
        5: "Agricultural Machinery & Assets",
        6: "Land Use Optimization Analytics"
    }

    # Progress overview
    completed_count, progress_percentage = calculate_survey_progress()

    # Progress visualization
    st.markdown("### 📈 Survey Progress Overview")
    col_prog1, col_prog2, col_prog3 = st.columns(3)

    with col_prog1:
        st.metric("Completion Rate", f"{progress_percentage:.1f}%")
    with col_prog2:
        st.metric("Sections Completed", f"{completed_count}/{TOTAL_SURVEY_SECTIONS}")
    with col_prog3:
        status = "Completed" if completed_count == TOTAL_SURVEY_SECTIONS else "In Progress"
        st.metric("Survey Status", status)

    st.progress(progress_percentage / 100)

    # ==================== INTELLIGENT SECTION RENDERING - UPDATED ORDER ====================
    st.markdown("### 📋 Survey Sections")

    for section_id, section_name in sections.items():
        is_completed = st.session_state["section_completion"].get(section_id, False)
        status_badge = "✅" if is_completed else "⏳"

        with st.expander(f"{status_badge} Section {section_id}: {section_name}", expanded=False):
            st.markdown('<div class="section-card">', unsafe_allow_html=True)

            if section_id == 1:
                holder_location_widget(selected_holder["holder_id"])
                st.session_state["current_holder_id"] = selected_holder["holder_id"]
                holder_information_form(holder_id=selected_holder["holder_id"])
            elif section_id == 2:  # NOW HOUSEHOLD INFORMATION
                st.session_state["current_holder_id"] = selected_holder["holder_id"]
                household_information(holder_id=selected_holder["holder_id"])
            elif section_id == 3:  # NOW GENERAL LABOUR
                st.session_state["current_holder_id"] = selected_holder["holder_id"]
                holding_labour_form(holder_id=selected_holder["holder_id"])
            elif section_id == 4:  # NOW PERMANENT LABOUR
                st.session_state["current_holder_id"] = selected_holder["holder_id"]
                holding_labour_permanent_form(holder_id=selected_holder["holder_id"])
            elif section_id == 5:
                machinery_data = agricultural_machinery_section(selected_holder["holder_id"])
                if machinery_data:
                    st.session_state["machinery_data"] = machinery_data
            elif section_id == 6:
                land_use_data = land_use_section(selected_holder["holder_id"])
                if land_use_data:
                    st.session_state["land_use_data"] = land_use_data

            st.markdown('</div>', unsafe_allow_html=True)

    # ==================== SIDEBAR ENHANCEMENTS ====================
    st.sidebar.markdown(f"""
    <div style="text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 15px; border-radius: 10px; margin: 10px 0;">
        <h4>{selected_holder['name']}</h4>
    </div>
    """, unsafe_allow_html=True)

    # Age calculation
    try:
        with engine.connect() as conn:
            dob_row = conn.execute(
                text(f"SELECT date_of_birth FROM {HOLDERS_TABLE} WHERE holder_id=:hid"),
                {"hid": selected_holder["holder_id"]}
            ).scalar()
        if dob_row:
            if isinstance(dob_row, str):
                dob_row = date.fromisoformat(dob_row)
            st.sidebar.info(f"🎂 Holder Age: {calculate_age(dob_row)} years")
    except Exception:
        pass

    # Quick actions
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🚀 Rapid Actions")

    if st.sidebar.button("🔄 Reset Survey Progress", use_container_width=True):
        st.session_state["section_completion"] = {}
        st.success("🔄 Survey progress reset successfully!")
        st.rerun()

    if st.sidebar.button("➕ New Farm Holder", use_container_width=True):
        with engine.begin() as conn:
            result = conn.execute(
                text("INSERT INTO holders (owner_id, name) VALUES (:uid, :name)"),
                {"uid": user_id, "name": f"Farm Holder {len(holders) + 1}"}
            )
            new_holder_id = result.inserted_primary_key[0] if result.inserted_primary_key else None

            if new_holder_id:
                st.session_state["holder_id"] = new_holder_id
                st.success("✅ New farm holder created!")
                st.rerun()

# =============================================================================
# ENHANCED NAVIGATION SIDEBAR - UPDATED SECTION ORDER
# =============================================================================
def section_navigation_sidebar(holder_id):
    """Advanced navigation sidebar with progress tracking - UPDATED ORDER"""

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🧭 Survey Navigator")

    sections = {
        1: "👤 Holder Intelligence",
        2: "👥 Household Demographics",  # MOVED TO SECTION 2
        3: "💼 Labor Analytics (General)",
        4: "👨‍💼 Labor Analytics (Permanent)",
        5: "🏭 Machinery Assets",
        6: "🏞️ Land Use Analytics"
    }

    current_section = st.session_state.get("current_section")
    survey_started = st.session_state.get("survey_started", False)

    if current_section is None or not survey_started:
        st.sidebar.info("📝 Survey initialization pending")
        if st.sidebar.button("🚀 Launch Survey", type="primary", use_container_width=True):
            st.session_state["current_section"] = 1
            st.session_state["section_completion"] = {}
            st.session_state["survey_started"] = True
            st.rerun()
        return

    # Section selector
    selected_section = st.sidebar.selectbox(
        "Navigate to Section:",
        options=list(sections.keys()),
        format_func=lambda x: f"Section {x}: {sections[x]}",
        index=max(0, current_section - 1)
    )

    if selected_section != current_section:
        st.session_state["current_section"] = selected_section
        st.rerun()

    # Progress visualization
    st.sidebar.markdown("---")
    completed_count, progress_percentage = calculate_survey_progress()

    st.sidebar.markdown("**Progress Overview**")
    st.sidebar.progress(progress_percentage / 100)
    st.sidebar.metric("Completion", f"{completed_count}/{TOTAL_SURVEY_SECTIONS}")

    # Survey control
    if st.sidebar.button("⏸️ Pause Survey", use_container_width=True):
        st.session_state["current_section"] = None
        st.session_state["survey_started"] = False
        st.rerun()

# =============================================================================
# MAIN APPLICATION FLOW
# =============================================================================
def main():
    """Main application controller with enhanced UI/UX"""

    # ==================== SIDEBAR HEADER ====================
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h1>🌾 Agri Census</h1>
        <p style="color: #666; font-size: 0.9rem;">Intelligence Platform</p>
    </div>
    """, unsafe_allow_html=True)

    # Session cleanup
    if st.session_state.get("logged_out"):
        st.session_state.update({
            "user": None,
            "holder_id": None,
            "logged_out": False,
            "current_section": None
        })
        st.experimental_set_query_params()
        st.rerun()

    # ==================== AUTHENTICATION FLOW ====================
    if st.session_state["user"] is None:
        login_choice = st.sidebar.radio("Access Type", ["Agent/Farmer", "Administrator"])

        if login_choice == "Agent/Farmer":
            action = st.sidebar.radio("Authentication", ["Login", "Register"])
            if action == "Login":
                login_user()
            else:
                register_user()
        else:
            from census_app.modules.admin_auth import login_admin
            login_admin()

    # ==================== AUTHORIZED USER FLOW ====================
    else:
        user = st.session_state["user"]
        role = user["role"].lower()
        user_id = user["id"]

        st.sidebar.success(f"✅ Authenticated as {user['username']} ({role.title()})")
        logout_user()

        if role == "holder":
            holder_id = create_holder_for_user(user_id, user["username"])
            st.session_state["holder_id"] = holder_id

            if get_user_status(user_id) != "approved":
                st.error("🚫 Account pending administrative approval")
                st.stop()

            # Dashboard mode selection
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 🎛️ Interface Mode")

            dashboard_mode = st.sidebar.radio(
                "Navigation Style:",
                ["Collapsible Dashboard", "Linear Survey"],
                index=0 if st.session_state.get("dashboard_mode") == "collapsible" else 1
            )

            st.session_state["dashboard_mode"] = "collapsible" if dashboard_mode == "Collapsible Dashboard" else "linear"

            # Render selected interface
            if st.session_state["dashboard_mode"] == "collapsible":
                collapsible_dashboard(holder_id)
            else:
                render_linear_survey(holder_id)

        elif role == "agent":
            agent_dashboard()
        elif role == "admin":
            admin_dashboard()

    # ==================== APPLICATION FOOTER ====================
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        <strong>🌾 Agricultural Census Intelligence Platform</strong><br/>
        v2.0 • Advanced Analytics • 2025<br/>
        <em>Driving agricultural intelligence</em>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# LINEAR SURVEY RENDERER - UPDATED SECTION ORDER
# =============================================================================
def render_linear_survey(holder_id):
    """Enhanced linear survey interface - UPDATED ORDER"""

    st.markdown('<div class="main-header">📋 Agricultural Census Survey</div>', unsafe_allow_html=True)

    # Location intelligence
    holder_location_widget(holder_id)

    # Navigation sidebar
    section_navigation_sidebar(holder_id)

    current_section = st.session_state.get("current_section")
    survey_started = st.session_state.get("survey_started", False)

    # Dashboard view before survey initiation
    if current_section is None or not survey_started:
        render_survey_dashboard(holder_id)
        return

    # Survey section rendering - UPDATED ORDER
    section_completed = render_survey_section(current_section, holder_id)

    if section_completed and current_section < TOTAL_SURVEY_SECTIONS:
        mark_section_complete(current_section)

    # Advanced navigation controls
    render_navigation_controls(current_section, holder_id)

    # Progress analytics
    render_progress_analytics(current_section)

def render_survey_dashboard(holder_id):
    """Enhanced survey dashboard view"""

    st.markdown("""
    <div style="text-align: center; padding: 40px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; border-radius: 15px; margin-bottom: 30px;">
        <h2>🏠 Farm Holder Dashboard</h2>
        <p>Initiate the Agricultural Census to contribute to national agricultural intelligence</p>
    </div>
    """, unsafe_allow_html=True)

    try:
        with engine.connect() as conn:
            holder_info = conn.execute(
                text("SELECT name, latitude, longitude FROM holders WHERE holder_id = :hid"),
                {"hid": holder_id}
            ).mappings().first()

        if holder_info:
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>👋 Welcome, {holder_info['name']}!</h3>
                    <p><strong>Geospatial Coordinates:</strong> {holder_info['latitude']:.6f}, {holder_info['longitude']:.6f}</p>
                </div>
                """, unsafe_allow_html=True)

                completed_count = get_completed_sections_count()
                if completed_count > 0:
                    st.success(f"✅ Survey Progress: {completed_count}/{TOTAL_SURVEY_SECTIONS} sections completed")
                else:
                    st.info("📋 Awaiting survey initiation")

            with col2:
                status = "Custom" if holder_info['latitude'] != 25.0343 or holder_info['longitude'] != -77.3963 else "Default"
                st.metric("Location Status", status)

            # Interactive map
            st.markdown("### 🗺️ Farm Location Visualization")
            df = pd.DataFrame([[holder_info['latitude'], holder_info['longitude']]], columns=["lat", "lon"])
            st.map(df, zoom=15)

    except Exception as e:
        st.error(f"📊 Dashboard initialization error: {e}")

def render_survey_section(section_id, holder_id):
    """Render individual survey sections - UPDATED ORDER"""

    section_completed = False

    if section_id == 1:
        st.session_state["current_holder_id"] = holder_id
        section_completed = holder_information_form(holder_id=holder_id)
    elif section_id == 2:  # NOW HOUSEHOLD INFORMATION
        st.session_state["current_holder_id"] = holder_id
        section_completed = household_information(holder_id=holder_id)
    elif section_id == 3:  # NOW GENERAL LABOUR
        st.session_state["current_holder_id"] = holder_id
        section_completed = holding_labour_form(holder_id=holder_id)
    elif section_id == 4:  # NOW PERMANENT LABOUR
        st.session_state["current_holder_id"] = holder_id
        section_completed = holding_labour_permanent_form(holder_id=holder_id)
    elif section_id == 5:
        machinery_data = agricultural_machinery_section(holder_id)
        if machinery_data:
            st.session_state["machinery_form_data"] = machinery_data
            section_completed = True
    elif section_id == 6:
        land_use_data = land_use_section(holder_id)
        if land_use_data:
            st.session_state["land_use_form_data"] = land_use_data
            section_completed = True

    return section_completed

def render_navigation_controls(current_section, holder_id):
    """Enhanced navigation controls"""

    st.markdown("---")
    col_nav = st.columns([1, 2, 1])

    with col_nav[0]:
        if st.button("⬅ Previous", disabled=current_section <= 1, use_container_width=True):
            st.session_state["current_section"] -= 1
            st.rerun()

    with col_nav[2]:
        if current_section < TOTAL_SURVEY_SECTIONS:
            if st.button("Next ➡", type="primary", use_container_width=True):
                mark_section_complete(current_section)
        else:
            if st.button("✅ Complete Survey", type="primary", use_container_width=True):
                mark_section_complete(current_section)
                st.success("🎉 Agricultural census completed successfully!")
                st.balloons()

def render_progress_analytics(current_section):
    """Enhanced progress analytics"""

    st.markdown("---")
    st.markdown("### 📊 Survey Analytics")

    completed_count, progress_percentage = calculate_survey_progress()

    col_analytics = st.columns(3)
    with col_analytics[0]:
        st.metric("Completion Rate", f"{progress_percentage:.1f}%")
    with col_analytics[1]:
        st.metric("Current Section", f"Section {current_section}")
    with col_analytics[2]:
        status = "Completed" if completed_count == TOTAL_SURVEY_SECTIONS else "In Progress"
        st.metric("Survey Status", status)

# =============================================================================
# APPLICATION INITIALIZATION
# =============================================================================
if __name__ == "__main__":
    main()