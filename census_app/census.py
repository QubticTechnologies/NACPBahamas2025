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
from census_app.db import engine
from census_app.config import USERS_TABLE, HOLDERS_TABLE, TOTAL_SURVEY_SECTIONS

# --- Lazy Imports to avoid circular imports ---
def _import_auth():
    from census_app.modules.auth import login_user, register_user, logout_user, create_holder_for_user
    return login_user, register_user, logout_user, create_holder_for_user

def _import_role_sidebar():
    from census_app.modules.role_sidebar import role_sidebar
    return role_sidebar

def _import_dashboards():
    from census_app.modules.dashboards import holder_dashboard, agent_dashboard
    from census_app.modules.admin_dashboard.dashboard import admin_dashboard
    return holder_dashboard, agent_dashboard, admin_dashboard

def _import_survey_sidebar():
    from census_app.modules.survey_sidebar import survey_sidebar
    return survey_sidebar

# --- Dynamic Imports ---
login_user, register_user, logout_user, create_holder_for_user = _import_auth()
role_sidebar = _import_role_sidebar()
holder_dashboard, agent_dashboard, admin_dashboard = _import_dashboards()
survey_sidebar = _import_survey_sidebar()

# --- Survey Forms & Helpers ---
from census_app.modules.household_information import household_information
from census_app.modules.holding_labour_form import holding_labour_form
from census_app.modules.holder_information_form import holder_information_form
from census_app.helpers import calculate_age

# --- Streamlit Config ---
st.set_page_config(page_title="🌾 Agri Census System", layout="wide")

# --- Session Defaults ---
st.session_state.setdefault("user", None)
st.session_state.setdefault("holder_id", None)
st.session_state.setdefault("logged_out", False)
st.session_state.setdefault("current_section", 1)
st.session_state.setdefault("holder_form_data", {})
st.session_state.setdefault("labour_form_data", {})
st.session_state.setdefault("household_form_data", {})

# -----------------------------
# Helper Functions
# -----------------------------
def get_user_status(user_id: int):
    try:
        with engine.connect() as conn:
            return conn.execute(
                text(f"SELECT status FROM {USERS_TABLE} WHERE id=:uid"),
                {"uid": user_id}
            ).scalar()
    except Exception as e:
        st.error(f"Database error: {e}")
        return None

# -----------------------------
# Holder Location Widget
# -----------------------------
def holder_location_widget(holder_id):
    st.subheader("📍 Farm Location")
    st.info("🎯 Click 'Auto Detect Location' or enter coordinates manually.")

    # Fetch stored coordinates
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT latitude, longitude FROM holders WHERE holder_id=:hid"),
            {"hid": holder_id}
        ).fetchone()

    stored_lat = result[0] if result and result[0] is not None else 25.0343
    stored_lon = result[1] if result and result[1] is not None else -77.3963

    if f"holder_lat_{holder_id}" not in st.session_state:
        st.session_state[f"holder_lat_{holder_id}"] = stored_lat
    if f"holder_lon_{holder_id}" not in st.session_state:
        st.session_state[f"holder_lon_{holder_id}"] = stored_lon

    current_lat = st.session_state[f"holder_lat_{holder_id}"]
    current_lon = st.session_state[f"holder_lon_{holder_id}"]

    # Map
    st.markdown("#### 🗺️ Current Location Preview")
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

    # Auto Detect & Reset
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🎯 Auto Detect My Location", key=f"auto_loc_btn_{holder_id}"):
            try:
                loc_data = get_geolocation()
                if loc_data and "coords" in loc_data:
                    detected_lat = loc_data["coords"]["latitude"]
                    detected_lon = loc_data["coords"]["longitude"]
                    st.session_state[f"holder_lat_{holder_id}"] = detected_lat
                    st.session_state[f"holder_lon_{holder_id}"] = detected_lon
                    st.success(f"✅ GPS Lock Acquired: {detected_lat:.6f}, {detected_lon:.6f}")
                    st.rerun()
            except Exception as e:
                st.error(f"GPS Error: {e}")

    with col_btn2:
        if st.button("🔄 Reset to Saved", key=f"reset_loc_btn_{holder_id}"):
            st.session_state[f"holder_lat_{holder_id}"] = stored_lat
            st.session_state[f"holder_lon_{holder_id}"] = stored_lon
            st.rerun()

    # Manual coordinates
    st.markdown("#### ✏️ Manual Coordinate Entry")
    col1, col2 = st.columns(2)
    with col1:
        manual_lat = st.number_input("Latitude", value=float(current_lat), min_value=-90.0, max_value=90.0,
                                     step=0.000001, format="%.6f", key=f"lat_input_{holder_id}")
    with col2:
        manual_lon = st.number_input("Longitude", value=float(current_lon), min_value=-180.0, max_value=180.0,
                                     step=0.000001, format="%.6f", key=f"lon_input_{holder_id}")
    if st.button("📍 Update Preview", key=f"update_preview_{holder_id}"):
        st.session_state[f"holder_lat_{holder_id}"] = manual_lat
        st.session_state[f"holder_lon_{holder_id}"] = manual_lon
        st.rerun()

# -----------------------------
# Main Flow
# -----------------------------
st.sidebar.title("🌱 Agri Census System")

# Reset after logout
if st.session_state.get("logged_out"):
    st.session_state.update({"user": None, "holder_id": None, "logged_out": False})
    st.experimental_set_query_params()
    st.rerun()

# --- Login Flow ---
if st.session_state["user"] is None:
    login_choice = st.sidebar.radio("Login Type", ["Agent/Farmer", "Admin"])
    if login_choice == "Agent/Farmer":
        action = st.sidebar.radio("Action", ["Login", "Register"])
        if action == "Login":
            login_user()
        else:
            register_user()
    else:
        from census_app.modules.admin_auth import login_admin
        login_admin()

# --- Logged-In Flow ---
else:
    user = st.session_state["user"]
    role = user["role"].lower()
    user_id = user["id"]

    st.sidebar.success(f"✅ Logged in as {user['username']} ({role})")
    logout_user()

    # Holder Flow
    if role == "holder":
        holder_id = create_holder_for_user(user_id, user["username"])
        st.session_state["holder_id"] = holder_id

        # Approval check
        if get_user_status(user_id) != "approved":
            st.error("🚫 Your account is not yet approved by admin.")
            st.stop()

        # Map & Survey
        holder_location_widget(holder_id)

        # Survey Navigation
        if st.session_state["current_section"] < 1:
            st.session_state["current_section"] = 1

        survey_sidebar(holder_id=holder_id)
        st.divider()

        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅ Back") and st.session_state["current_section"] > 1:
                st.session_state["current_section"] -= 1
                st.rerun()
        with col3:
            if st.button("Next ➡") and st.session_state["current_section"] < TOTAL_SURVEY_SECTIONS:
                st.session_state["current_section"] += 1
                st.rerun()

        # Render current survey section
        current = st.session_state["current_section"]
        st.markdown(f"### Section {current} of {TOTAL_SURVEY_SECTIONS}")
        if current == 1:
            holder_information_form(holder_id)
        elif current == 2:
            holding_labour_form(holder_id)
        elif current == 3:
            household_information(holder_id)

        # Holder Dashboard
        st.divider()
        st.title("📊 Holder Dashboard")
        try:
            with engine.connect() as conn:
                dob_row = conn.execute(
                    text(f"SELECT date_of_birth FROM {HOLDERS_TABLE} WHERE holder_id=:hid"),
                    {"hid": holder_id}
                ).scalar()
            if dob_row:
                if isinstance(dob_row, str):
                    dob_row = date.fromisoformat(dob_row)
                st.sidebar.info(f"🎂 Age: {calculate_age(dob_row)} years")
        except Exception as e:
            st.sidebar.warning(f"Could not fetch holder age: {e}")

    # Agent Flow
    elif role == "agent":
        agent_dashboard()

    # Admin Flow
    elif role == "admin":
        admin_dashboard()
