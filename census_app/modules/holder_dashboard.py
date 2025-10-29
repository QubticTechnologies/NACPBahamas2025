# census_app/modules/holder_dashboard.py

import streamlit as st
from sqlalchemy import text
from datetime import date
import pandas as pd
from streamlit_js_eval import get_geolocation
import pydeck as pdk
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional, Tuple

from census_app.db import engine
from config import (
    HOLDERS_TABLE,
    TOTAL_SURVEY_SECTIONS
)
from helpers import calculate_age
from modules.agricultural_machinery import agricultural_machinery_section
from modules.land_use import land_use_section


# =============================================================================
# CUSTOM STYLING & THEMING
# =============================================================================
def inject_custom_styles():
    """Inject professional CSS styles for enhanced UI"""
    st.markdown("""
    <style>
        .dashboard-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 15px;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .metric-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            border-left: 4px solid #667eea;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            margin: 0.5rem 0;
        }
        .section-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            border: 1px solid #e1e8ed;
        }
        .progress-container {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
        }
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            margin: 0.25rem;
        }
        .status-complete {
            background: #d4edda;
            color: #155724;
        }
        .status-pending {
            background: #fff3cd;
            color: #856404;
        }
        .location-preview {
            border: 2px solid #e9ecef;
            border-radius: 10px;
            padding: 1rem;
            background: white;
        }
    </style>
    """, unsafe_allow_html=True)


# =============================================================================
# ENHANCED GIS LOCATION WIDGET
# =============================================================================
class FarmLocationManager:
    """Advanced GIS location management with precision analytics"""

    def __init__(self, holder_id: int):
        self.holder_id = holder_id
        self.lat_key = f"holder_lat_{holder_id}"
        self.lon_key = f"holder_lon_{holder_id}"
        self.load_stored_coordinates()

    def load_stored_coordinates(self) -> Tuple[float, float]:
        """Load stored coordinates from database"""
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT latitude, longitude FROM holders WHERE holder_id = :hid"),
                    {"hid": self.holder_id}
                ).fetchone()

            stored_lat = result[0] if result and result[0] is not None else 25.0343
            stored_lon = result[1] if result and result[1] is not None else -77.3963

            # Initialize session state
            if self.lat_key not in st.session_state:
                st.session_state[self.lat_key] = stored_lat
            if self.lon_key not in st.session_state:
                st.session_state[self.lon_key] = stored_lon

            return stored_lat, stored_lon

        except Exception as e:
            st.error(f"🔧 Coordinate loading error: {e}")
            return 25.0343, -77.3963

    def render_location_analytics(self, current_lat: float, current_lon: float):
        """Render location precision analytics"""
        col1, col2, col3 = st.columns(3)

        with col1:
            precision = self._calculate_precision_level(current_lat)
            st.metric("📍 Precision Level", precision)

        with col2:
            st.metric("📐 Latitude", f"{current_lat:.6f}")

        with col3:
            st.metric("📐 Longitude", f"{current_lon:.6f}")

    def _calculate_precision_level(self, coordinate: float) -> str:
        """Calculate coordinate precision level"""
        decimal_places = len(str(coordinate).split('.')[-1])
        if decimal_places >= 6:
            return "High (Sub-meter)"
        elif decimal_places >= 4:
            return "Medium (10m)"
        else:
            return "Low (1km+)"

    def auto_detect_location(self):
        """Auto-detect location with enhanced error handling"""
        try:
            with st.spinner("🛰️ Acquiring high-precision GPS coordinates..."):
                loc_data = get_geolocation()

                if loc_data and "coords" in loc_data:
                    detected_lat = loc_data["coords"]["latitude"]
                    detected_lon = loc_data["coords"]["longitude"]
                    accuracy = loc_data["coords"].get("accuracy", "Unknown")

                    # Update session state
                    st.session_state[self.lat_key] = detected_lat
                    st.session_state[self.lon_key] = detected_lon

                    # Success feedback
                    st.success("✅ GPS Lock Established!")

                    # Precision analytics
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"**Accuracy:** ±{accuracy}m")
                    with col2:
                        st.info(f"**Precision:** {self._calculate_precision_level(detected_lat)}")

                    return True
                else:
                    st.warning("📍 GPS access denied. Please enable location services.")
                    return False

        except Exception as e:
            st.error(f"❌ GPS acquisition failed: {e}")
            return False

    def render_interactive_map(self, current_lat: float, current_lon: float):
        """Render enhanced interactive map"""
        st.markdown("#### 🗺️ Geospatial Visualization")

        try:
            # Create interactive map with PyDeck
            view_state = pdk.ViewState(
                latitude=current_lat,
                longitude=current_lon,
                zoom=15,
                pitch=45,
                bearing=0
            )

            # Scatter plot layer for farm location
            scatter_layer = pdk.Layer(
                "ScatterplotLayer",
                data=pd.DataFrame([{
                    "lat": current_lat,
                    "lon": current_lon,
                    "radius": 100,
                    "color": [255, 0, 0]
                }]),
                get_position=["lon", "lat"],
                get_color="color",
                get_radius="radius",
                pickable=True,
                opacity=0.8
            )

            # Text layer for marker label
            text_layer = pdk.Layer(
                "TextLayer",
                data=pd.DataFrame([{
                    "lat": current_lat,
                    "lon": current_lon,
                    "text": "Farm Location"
                }]),
                get_position=["lon", "lat"],
                get_text="text",
                get_color=[0, 0, 0],
                get_size=16,
                get_alignment_baseline="bottom"
            )

            # Render the deck
            deck = pdk.Deck(
                layers=[scatter_layer, text_layer],
                initial_view_state=view_state,
                map_style="mapbox://styles/mapbox/satellite-streets-v11",
                tooltip={"text": "Farm Location\nLat: {lat}\nLon: {lon}"}
            )

            st.pydeck_chart(deck)

        except Exception as e:
            st.warning(f"📊 Advanced map unavailable: {e}")
            # Fallback to simple map
            st.map(pd.DataFrame([[current_lat, current_lon]], columns=["lat", "lon"]), zoom=15)

    def save_coordinates(self, current_lat: float, current_lon: float) -> bool:
        """Save coordinates to database with validation"""
        # Validate coordinates
        if not (-90 <= current_lat <= 90 and -180 <= current_lon <= 180):
            st.error("❌ Invalid coordinate values")
            return False

        # Check if using default location
        if abs(current_lat - 25.0343) < 0.001 and abs(current_lon + 77.3963) < 0.001:
            st.warning("⚠️ Default location detected. Please set actual farm coordinates.")
            return False

        try:
            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE holders SET latitude = :lat, longitude = :lon WHERE holder_id = :hid"),
                    {"lat": current_lat, "lon": current_lon, "hid": self.holder_id}
                )
            st.success("✅ Farm location persisted successfully!")
            return True

        except Exception as e:
            st.error(f"❌ Database persistence error: {e}")
            return False


def farm_location_widget(holder_id: int):
    """Enhanced GIS location widget with professional interface"""
    st.markdown('<div class="section-card">', unsafe_allow_html=True)

    # Header
    st.markdown("### 📍 Farm Geospatial Intelligence")
    st.info(
        "🎯 **Precision Mapping**: Use auto-detection for optimal accuracy or manual input for specific coordinates.")

    # Initialize location manager
    location_manager = FarmLocationManager(holder_id)
    current_lat = st.session_state[location_manager.lat_key]
    current_lon = st.session_state[location_manager.lon_key]

    # Layout: Analytics and Map
    col_analytics, col_map = st.columns([1, 2])

    with col_analytics:
        location_manager.render_location_analytics(current_lat, current_lon)

        # Control buttons
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🎯 Auto-Detect GPS", use_container_width=True):
                location_manager.auto_detect_location()
                st.rerun()

        with col_btn2:
            if st.button("💾 Save Location", type="primary", use_container_width=True):
                if location_manager.save_coordinates(current_lat, current_lon):
                    st.balloons()

    with col_map:
        location_manager.render_interactive_map(current_lat, current_lon)

    # Manual coordinate input
    st.markdown("#### ✏️ Precision Coordinate Input")
    col_lat, col_lon = st.columns(2)

    with col_lat:
        new_lat = st.number_input(
            "**Latitude**",
            value=float(current_lat),
            min_value=-90.0,
            max_value=90.0,
            step=0.000001,
            format="%.6f",
            help="Decimal degrees (-90 to 90)"
        )

    with col_lon:
        new_lon = st.number_input(
            "**Longitude**",
            value=float(current_lon),
            min_value=-180.0,
            max_value=180.0,
            step=0.000001,
            format="%.6f",
            help="Decimal degrees (-180 to 180)"
        )

    # Update coordinates if changed
    if new_lat != current_lat or new_lon != current_lon:
        st.session_state[location_manager.lat_key] = new_lat
        st.session_state[location_manager.lon_key] = new_lon
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# SURVEY PROGRESS ANALYTICS
# =============================================================================
class SurveyProgressTracker:
    """Advanced survey progress tracking and analytics"""

    @staticmethod
    def get_completed_sections_count() -> int:
        """Get count of completed sections"""
        completion_dict = st.session_state.get("section_completion", {})
        return sum(1 for section_num in range(1, TOTAL_SURVEY_SECTIONS + 1)
                   if completion_dict.get(section_num, False))

    @staticmethod
    def get_survey_progress() -> Tuple[int, float]:
        """Calculate comprehensive survey progress metrics"""
        completed = SurveyProgressTracker.get_completed_sections_count()
        progress_percentage = (completed / TOTAL_SURVEY_SECTIONS) * 100 if TOTAL_SURVEY_SECTIONS > 0 else 0
        return completed, progress_percentage

    @staticmethod
    def render_progress_dashboard(holder_id: int):
        """Render enhanced progress dashboard"""
        completed, progress_percentage = SurveyProgressTracker.get_survey_progress()

        st.markdown("### 📈 Survey Progress Analytics")

        # Progress metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Completion Rate",
                f"{progress_percentage:.1f}%",
                delta=f"{completed}/{TOTAL_SURVEY_SECTIONS}"
            )

        with col2:
            st.metric("Sections Completed", str(completed))

        with col3:
            st.metric("Remaining Sections", str(TOTAL_SURVEY_SECTIONS - completed))

        with col4:
            status = "✅ Complete" if completed == TOTAL_SURVEY_SECTIONS else "🟡 In Progress"
            st.metric("Survey Status", status)

        # Visual progress bar
        st.markdown(f"**Overall Progress:** {progress_percentage:.1f}%")
        st.progress(progress_percentage / 100)

        # Section-wise progress
        SurveyProgressTracker.render_section_progress(completed)

    @staticmethod
    def render_section_progress(completed_count: int):
        """Render detailed section progress breakdown"""
        sections = {
            1: "Holder Information & Location",
            2: "Holding Labour",
            3: "Household Information",
            4: "Agricultural Machinery",
            5: "Land Use"
        }

        st.markdown("#### 📋 Section Completion Status")

        for section_id, section_name in sections.items():
            is_completed = st.session_state.get("section_completion", {}).get(section_id, False)

            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.write(f"**Section {section_id}:** {section_name}")

            with col2:
                status_badge = "✅ Complete" if is_completed else "⏳ Pending"
                badge_class = "status-complete" if is_completed else "status-pending"
                st.markdown(f'<span class="status-badge {badge_class}">{status_badge}</span>',
                            unsafe_allow_html=True)

            with col3:
                if is_completed:
                    st.write("🎯")
                else:
                    st.write("📝")


# =============================================================================
# ENHANCED HOLDER DASHBOARD
# =============================================================================
class HolderDashboard:
    """Modern holder dashboard with advanced analytics and professional UI"""

    def __init__(self):
        self.user_id = st.session_state.get("user", {}).get("id")
        self.holder_id = st.session_state.get("holder_id")
        self.inject_custom_styles()

    def inject_custom_styles(self):
        """Inject professional CSS styles"""
        inject_custom_styles()

    def validate_access(self) -> bool:
        """Validate user access and permissions"""
        if "user" not in st.session_state:
            st.error("🚫 **Authentication Required**\n\nPlease log in to access the dashboard.")
            st.stop()
            return False
        return True

    def fetch_holders(self) -> List[Dict]:
        """Fetch holders with comprehensive error handling"""
        try:
            with engine.connect() as conn:
                holders = conn.execute(
                    text(f"SELECT * FROM {HOLDERS_TABLE} WHERE owner_id = :uid ORDER BY holder_id"),
                    {"uid": self.user_id}
                ).mappings().all()
            return holders
        except Exception as e:
            st.error(f"🔧 **Data Retrieval Error**\n\nUnable to fetch holder information: {e}")
            return []

    def render_holder_creation(self):
        """Render holder creation interface"""
        st.markdown("""
        <div style='text-align: center; padding: 3rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   border-radius: 15px; color: white; margin: 2rem 0;'>
            <h2>🏡 Welcome to Agricultural Census</h2>
            <p style='font-size: 1.1rem;'>Begin your journey by creating your first farm holder profile</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Initialize First Farm Holder", type="primary", use_container_width=True):
                self.create_new_holder("Primary Farm Holder")

    def create_new_holder(self, name: str) -> bool:
        """Create new holder with enhanced error handling"""
        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text("INSERT INTO holders (owner_id, name) VALUES (:uid, :name) RETURNING holder_id"),
                    {"uid": self.user_id, "name": name}
                )
                new_holder_id = result.scalar()

            if new_holder_id:
                st.session_state["holder_id"] = new_holder_id
                st.success("✅ **Farm holder profile created successfully!**")
                st.rerun()
                return True
            else:
                st.error("❌ **Holder creation failed**")
                return False

        except Exception as e:
            st.error(f"❌ **Database Error**\n\nUnable to create holder: {e}")
            return False

    def render_holder_selector(self, holders: List[Dict]):
        """Render enhanced holder selection interface"""
        st.sidebar.markdown("### 👤 Farm Holder Management")

        # Holder selection
        holder_names = [h["name"] for h in holders]
        current_index = next((i for i, h in enumerate(holders)
                              if h["holder_id"] == self.holder_id), 0)

        selected_name = st.sidebar.selectbox(
            "**Select Holder:**",
            holder_names,
            index=current_index,
            key="holder_selector"
        )

        # Update selection if changed
        if selected_name != holder_names[current_index]:
            selected_holder = next(h for h in holders if h["name"] == selected_name)
            st.session_state["holder_id"] = selected_holder["holder_id"]
            st.rerun()

        return next(h for h in holders if h["holder_id"] == self.holder_id)

    def render_sidebar_analytics(self, holder: Dict):
        """Render sidebar analytics and quick actions"""
        # Holder information
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"### 📊 {holder['name']}")

        # Age calculation
        try:
            dob = holder.get('date_of_birth')
            if dob:
                if isinstance(dob, str):
                    dob = date.fromisoformat(dob)
                age = calculate_age(dob)
                st.sidebar.info(f"**🎂 Holder Age:** {age} years")
        except Exception:
            pass

        # Quick actions
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🚀 Rapid Actions")

        col1, col2 = st.sidebar.columns(2)

        with col1:
            if st.button("🔄 Reset Progress", use_container_width=True):
                st.session_state["section_completion"] = {}
                st.success("✅ Survey progress reset!")
                st.rerun()

        with col2:
            if st.button("➕ New Holder", use_container_width=True):
                self.create_new_holder(f"Farm Holder {len(self.fetch_holders()) + 1}")

    def render_survey_sections(self, holder_id: int):
        """Render enhanced survey sections with professional UI"""
        sections = {
            1: ("👤 Holder Information & Geospatial Data", "holder_info"),
            2: ("💼 Holding Labour Analytics", "labour"),
            3: ("👥 Household Demographic Intelligence", "household"),
            4: ("🏭 Agricultural Machinery & Assets", "machinery"),
            5: ("🏞️ Land Use Optimization", "land_use")
        }

        st.markdown("### 📋 Survey Sections")
        st.info("💡 **Complete all sections for comprehensive agricultural data collection**")

        for section_id, (section_name, section_key) in sections.items():
            is_completed = st.session_state.get("section_completion", {}).get(section_id, False)
            status_icon = "✅" if is_completed else "📝"

            with st.expander(f"{status_icon} Section {section_id}: {section_name}", expanded=False):
                self.render_section_content(section_id, holder_id, section_key)

    def render_section_content(self, section_id: int, holder_id: int, section_key: str):
        """Render individual section content with error handling"""
        try:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)

            if section_id == 1:
                farm_location_widget(holder_id)

                # Dynamic import for holder information form
                from census_app.modules.holder_information_form import holder_information_form
                holder_information_form()

            elif section_id == 2:
                from census_app.modules.holding_labour_form import holding_labour_form
                holding_labour_form()

            elif section_id == 3:
                from census_app.modules.household_information import household_information
                household_information()

            elif section_id == 4:
                machinery_data = agricultural_machinery_section(holder_id)
                if machinery_data:
                    st.session_state["machinery_data"] = machinery_data

            elif section_id == 5:
                land_use_data = land_use_section(holder_id)
                if land_use_data:
                    st.session_state["land_use_data"] = land_use_data

            st.markdown('</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"❌ **Section {section_id} Error**\n\nUnable to load section content: {e}")

    def render_dashboard_header(self):
        """Render professional dashboard header"""
        st.markdown("""
        <div class="dashboard-header">
            <h1>🌾 Agricultural Census Intelligence Platform</h1>
            <p>Comprehensive agricultural data collection for informed decision making</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        **📊 Platform Capabilities:**
        - Geospatial farm mapping and analytics
        - Labor force intelligence and management  
        - Household demographic profiling
        - Agricultural asset inventory
        - Land use optimization insights
        """)

    def main(self):
        """Main dashboard controller"""
        # Validate access
        if not self.validate_access():
            return

        # Fetch holders
        holders = self.fetch_holders()

        # Handle no holders case
        if not holders:
            self.render_holder_creation()
            return

        # Ensure holder_id is set
        if self.holder_id is None:
            self.holder_id = holders[0]["holder_id"]
            st.session_state["holder_id"] = self.holder_id

        # Get current holder
        current_holder = self.render_holder_selector(holders)
        if not current_holder:
            st.error("❌ Selected holder not found")
            return

        # Render main dashboard
        self.render_dashboard_header()
        self.render_survey_sections(current_holder["holder_id"])
        SurveyProgressTracker.render_progress_dashboard(current_holder["holder_id"])
        self.render_sidebar_analytics(current_holder)


# =============================================================================
# MAIN DASHBOARD FUNCTION
# =============================================================================
def holder_dashboard():
    """Main holder dashboard entry point"""
    dashboard = HolderDashboard()
    dashboard.main()

<<<<<<< HEAD
=======
    user_id = st.session_state["user"]["id"]
    holder_id = st.session_state.get("holder_id")
>>>>>>> 52d0578 (Initial commit or update)

# =============================================================================
# STANDALONE TEST FUNCTION
# =============================================================================
def test_holder_dashboard():
    """Enhanced test function for standalone execution"""
    st.title("🧪 Holder Dashboard - Test Environment")

    # Mock session state for testing
    if "user" not in st.session_state:
        st.session_state["user"] = {
            "id": 1,
            "username": "test_user",
            "role": "holder"
        }

    if "holder_id" not in st.session_state:
        st.session_state["holder_id"] = 1

<<<<<<< HEAD
    # Test controls
    st.sidebar.markdown("### 🧪 Test Controls")

    if st.sidebar.button("Reset Session State"):
=======
    st.sidebar.markdown(f"<h4 style='text-align:center;font-weight:bold;'>{selected_holder['name']}</h4>",
                        unsafe_allow_html=True)
    st.sidebar.markdown("---")

    # Section Navigation Sidebar
    st.sidebar.subheader("📋 Survey Navigation")

    sections = {
        1: "📝 Basic Information",
        2: "👥 Household Data",
        3: "💼 Labour Information",
        4: "🏭 Agricultural Machinery"
    }

    current_section = st.session_state.get("next_survey_section", 1)

    selected_section = st.sidebar.selectbox(
        "Jump to Section:",
        options=list(sections.keys()),
        format_func=lambda x: f"Section {x}: {sections[x]}",
        index=current_section - 1
    )

    if selected_section != current_section:
        st.session_state["next_survey_section"] = selected_section
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.metric("Survey Progress", f"{current_section}/{TOTAL_SURVEY_SECTIONS}")

    # Location confirmation
    st.header("🌾 Farm Location Confirmation")
    holder_location_widget(selected_holder["holder_id"])

    # Survey section with navigation
    st.subheader("📋 Survey Section")

    # Progress bar
    progress = current_section / TOTAL_SURVEY_SECTIONS
    st.progress(progress)
    st.caption(f"Section {current_section} of {TOTAL_SURVEY_SECTIONS}")

    # Navigation controls
    col_prev, col_status, col_next = st.columns([1, 2, 1])

    with col_prev:
        if st.button("⬅️ Previous", disabled=current_section <= 1, key="prev_section"):
            st.session_state["next_survey_section"] = max(1, current_section - 1)
            st.rerun()

    with col_next:
        if current_section < TOTAL_SURVEY_SECTIONS:
            if st.button("Next ➡️", key="next_section"):
                st.session_state["next_survey_section"] = current_section + 1
                st.rerun()
        else:
            if st.button("✅ Complete Survey", type="primary", key="complete_survey"):
                st.success("🎉 Survey completed successfully!")
                st.balloons()
                st.session_state["next_survey_section"] = 1

    # Render the appropriate section
    if current_section <= TOTAL_SURVEY_SECTIONS:
        if current_section == 1:
            show_regular_survey_section(section_id=1, holder_id=selected_holder["holder_id"])
        elif current_section == 2:
            show_regular_survey_section(section_id=2, holder_id=selected_holder["holder_id"])
        elif current_section == 3:
            show_regular_survey_section(section_id=3, holder_id=selected_holder["holder_id"])
        elif current_section == 4:
            # Agricultural Machinery Section
            machinery_data = agricultural_machinery_section(selected_holder["holder_id"])
            # Store in session state for dashboard display
            if machinery_data:
                st.session_state["machinery_data"] = machinery_data
    elif run_holding_labour_survey:
        run_holding_labour_survey(holder_id=selected_holder["holder_id"])

    # Agricultural Machinery Summary
    try:
        from census_app.modules.agricultural_machinery import load_existing_data, display_machinery_summary

        existing_machinery = load_existing_data(selected_holder["holder_id"])
        if existing_machinery:
            st.subheader("🏭 Agricultural Machinery Summary")
            display_machinery_summary(selected_holder["holder_id"])
    except Exception as e:
        # Silently fail if machinery module isn't available
        pass

    # Holder info (age)
    try:
        with engine.connect() as conn:
            dob_row = conn.execute(
                text(f"SELECT date_of_birth FROM {HOLDERS_TABLE} WHERE holder_id=:hid"),
                {"hid": selected_holder["holder_id"]}
            ).scalar()
        if dob_row:
            if isinstance(dob_row, str):
                dob_row = date.fromisoformat(dob_row)
            st.sidebar.info(f"🎂 Age: {calculate_age(dob_row)} years")
    except Exception as e:
        st.sidebar.warning(f"Could not fetch holder age: {e}")

    # Holder actions
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✏️ Edit Holder Info", key=f"edit_holder_{selected_holder['holder_id']}"):
            st.session_state["next_survey_section"] = 1
            st.rerun()
    with col3:
        if st.button("➕ Add New Holder", key=f"add_new_holder_{selected_holder['holder_id']}"):
            with engine.begin() as conn:
                result = conn.execute(
                    text("INSERT INTO holders (owner_id, name) VALUES (:uid, :name)"),
                    {"uid": user_id, "name": "New Holder"}
                )
                new_holder_id = result.lastrowid
            st.session_state["holder_id"] = new_holder_id
            st.rerun()

    # Logout
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", key=f"logout_{selected_holder['holder_id']}"):
>>>>>>> 52d0578 (Initial commit or update)
        st.session_state.clear()
        st.rerun()

    # Run dashboard
    holder_dashboard()


if __name__ == "__main__":
    test_holder_dashboard()