# census_app/modules/general_info_form.py

import streamlit as st
from datetime import date
from sqlalchemy import text
from census_app.db import engine

# Optional: import streamlit_javascript for browser geolocation
try:
    from streamlit_javascript import st_javascript
    JS_ENABLED = True
except ImportError:
    JS_ENABLED = False

# List of islands in the Bahamas
ISLANDS = [
    "New Providence", "Grand Bahama", "Abaco", "Acklins", "Andros", "Berry Islands",
    "Bimini", "Cat Island", "Crooked Island", "Eleuthera", "Exuma",
    "Inagua", "Long Island", "Mayaguana", "Ragged Island", "Rum Cay", "San Salvador"
]

def general_info_form(holder_id=None):
    st.subheader("📋 General Information Form")

    # --- Auto-fetch coordinates if browser supports JS ---
    latitude = ""
    longitude = ""
    if JS_ENABLED:
        coords = st_javascript("navigator.geolocation.getCurrentPosition(pos => pos.coords)")
        if coords:
            latitude = coords.get("latitude", "")
            longitude = coords.get("longitude", "")

    with st.form("general_info_form"):
        # --- Basic Info ---
        holding_id = st.text_input("Holding 10-digit ID")
        interview_date = st.date_input("Interview Date", value=date.today())
        respondent_name = st.text_input("Respondent Name")
        respondent_phone = st.text_input("Respondent Phone")
        respondent_email = st.text_input("Respondent Email")

        # --- Holder Confirmation ---
        is_holder = st.checkbox("Are you (one of) the holder(s)?")
        holder_name = st.text_input("Holder Name")
        holder_phone = st.text_input("Holder Phone (N/A if not applicable)")
        holding_name = st.text_input("Holding Name (if applicable)")
        holding_phone = st.text_input("Holding Phone (e.g. (242) 999-9999)")

        # --- Location ---
        st.markdown("### 📍 Location Information")
        island = st.selectbox("Island", ISLANDS)
        area_city = st.text_input("Area/City (official name)")
        subdivision = st.text_input("Subdivision")
        city_province = st.text_input("City/Province/Settlement")
        latitude = st.text_input("Latitude", value=latitude)
        longitude = st.text_input("Longitude", value=longitude)
        address_street = st.text_input("Street Address")
        address_po = st.text_input("P.O. Box", value="N-59195")

        # --- Legal Status ---
        st.markdown("### 🏠 Legal Status of Holder")
        legal_status_type = st.radio("Legal Status", ["Household", "Non-Household"])
        if legal_status_type == "Household":
            household_status = st.radio("Select Household Type", ["Individual", "Joint-Family", "Joint-Partnership"])
            nonhouse_status = None
        else:
            nonhouse_status = st.radio(
                "Select Non-Household Type",
                ["Corporation", "Government Institution", "Educational Institution", "Church", "Cooperative", "Other"]
            )
            household_status = None

        # --- Submit Button ---
        submitted = st.form_submit_button("💾 Save General Information")

        if submitted:
            # Save to database
            with engine.begin() as conn:
                query = text("""
                    INSERT INTO general_information (
                        holder_id, holding_id, interview_date, respondent_name,
                        respondent_phone, respondent_email, is_holder,
                        holder_name, holder_phone, holding_name, holding_phone,
                        island, area_city, subdivision, city_province, latitude,
                        longitude, address_street, address_po, legal_status_type,
                        household_status, nonhouse_status
                    )
                    VALUES (
                        :holder_id, :holding_id, :interview_date, :respondent_name,
                        :respondent_phone, :respondent_email, :is_holder,
                        :holder_name, :holder_phone, :holding_name, :holding_phone,
                        :island, :area_city, :subdivision, :city_province, :latitude,
                        :longitude, :address_street, :address_po, :legal_status_type,
                        :household_status, :nonhouse_status
                    )
                """)
                conn.execute(query, {
                    "holder_id": holder_id,
                    "holding_id": holding_id,
                    "interview_date": interview_date,
                    "respondent_name": respondent_name,
                    "respondent_phone": respondent_phone,
                    "respondent_email": respondent_email,
                    "is_holder": is_holder,
                    "holder_name": holder_name,
                    "holder_phone": holder_phone,
                    "holding_name": holding_name,
                    "holding_phone": holding_phone,
                    "island": island,
                    "area_city": area_city,
                    "subdivision": subdivision,
                    "city_province": city_province,
                    "latitude": latitude,
                    "longitude": longitude,
                    "address_street": address_street,
                    "address_po": address_po,
                    "legal_status_type": legal_status_type,
                    "household_status": household_status,
                    "nonhouse_status": nonhouse_status
                })

            st.success("✅ General Information saved successfully.")
            return True

    return False
