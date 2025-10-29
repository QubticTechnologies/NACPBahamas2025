# land_use.py
import streamlit as st
import pandas as pd
import io
from psycopg2.extras import execute_values
import psycopg2
import sys
import os

# Add path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your existing database configuration
from .db import engine
from sqlalchemy import text


# ---------------- DATABASE FUNCTIONS ----------------
def get_connection():
    """Get database connection using your existing configuration."""
    try:
        # Use your existing engine to get a raw connection
        return engine.raw_connection()
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None


def save_land_use_to_db(land_use_data, holder_id):
    """Insert land use data into the database for a specific holder."""
    conn = None
    try:
        conn = get_connection()
        if conn is None:
            st.error("❌ Cannot connect to database")
            return False

        with conn.cursor() as cur:
            # Check if land use data already exists for this holder
            cur.execute("SELECT id FROM land_use WHERE holder_id = %s", (holder_id,))
            existing = cur.fetchone()

            if existing:
                # Update existing record
                land_use_id = existing[0]
                cur.execute("""
                    UPDATE land_use 
                    SET total_area_acres = %s, years_agriculture = %s, main_purpose = %s,
                        num_parcels = %s, location = %s, crop_methods = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (
                    land_use_data['total_area'],
                    land_use_data['years_used'],
                    land_use_data['main_purpose'],
                    land_use_data['num_parcels'],
                    land_use_data['location'],
                    land_use_data['crop_methods'],
                    land_use_id
                ))

                # Delete existing parcels
                cur.execute("DELETE FROM land_use_parcels WHERE land_use_id = %s", (land_use_id,))
            else:
                # Insert new land use record
                cur.execute("""
                    INSERT INTO land_use (
                        holder_id, total_area_acres, years_agriculture, main_purpose,
                        num_parcels, location, crop_methods
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    holder_id,
                    land_use_data['total_area'],
                    land_use_data['years_used'],
                    land_use_data['main_purpose'],
                    land_use_data['num_parcels'],
                    land_use_data['location'],
                    land_use_data['crop_methods']
                ))
                land_use_id = cur.fetchone()[0]

            # Insert parcels
            parcel_values = [
                (
                    land_use_id,
                    p['parcel_no'],
                    p['total_acres'],
                    p['developed_acres'],
                    p['tenure'],
                    p['use_of_land'],
                    p['irrigated_area'],
                    p['land_clearing']
                )
                for p in land_use_data['parcels']
            ]

            execute_values(cur, """
                INSERT INTO land_use_parcels (
                    land_use_id, parcel_no, total_acres, developed_acres,
                    tenure, use_of_land, irrigated_area, land_clearing
                ) VALUES %s
            """, parcel_values)

            conn.commit()
            st.success("✅ Land use data saved successfully!")
            return True

    except Exception as e:
        if conn:
            conn.rollback()
        st.error(f"❌ Error saving land use data: {e}")
        return False
    finally:
        if conn:
            conn.close()


def load_existing_land_use_data(holder_id):
    """Load existing land use data for a holder."""
    conn = None
    try:
        conn = get_connection()
        if conn is None:
            return None, None

        with conn.cursor() as cur:
            # Get main land use data
            cur.execute("""
                SELECT total_area_acres, years_agriculture, main_purpose,
                       num_parcels, location, crop_methods
                FROM land_use 
                WHERE holder_id = %s
            """, (holder_id,))
            main_info = cur.fetchone()

            # Get parcels data
            cur.execute("""
                SELECT parcel_no, total_acres, developed_acres, tenure,
                       use_of_land, irrigated_area, land_clearing
                FROM land_use_parcels 
                WHERE land_use_id IN (SELECT id FROM land_use WHERE holder_id = %s)
                ORDER BY parcel_no
            """, (holder_id,))
            parcels_data = cur.fetchall()

        return main_info, parcels_data

    except Exception as e:
        st.error(f"Error loading land use data: {e}")
        return None, None
    finally:
        if conn:
            conn.close()


# ---------------- VALIDATION FUNCTIONS ----------------
def validate_main_land_use(total_area, years_used, crop_methods, num_parcels, location):
    errors = []
    if total_area <= 0:
        errors.append("Total Area must be greater than 0 acres.")
    if years_used < 0:
        errors.append("Years of agricultural use cannot be negative.")
    if not crop_methods:
        errors.append("At least one Crop Method must be selected.")
    if num_parcels < 1:
        errors.append("Number of Parcels must be at least 1.")
    if not location.strip():
        errors.append("Location cannot be empty.")
    if len(location) > 200:
        errors.append("Location must be 200 characters or less.")
    return errors


def validate_parcels(parcels_df):
    errors = []
    for idx, row in parcels_df.iterrows():
        parcel_no = row["Parcel No."]
        total_acres = row["Total Acres"]
        developed_acres = row["Developed Acres"]
        irrigated_area = row["Irrigated Area (Acres)"]

        if total_acres < 0:
            errors.append(f"Parcel {parcel_no}: Total Acres must be positive.")
        if developed_acres < 0:
            errors.append(f"Parcel {parcel_no}: Developed Acres must be positive.")
        if irrigated_area < 0:
            errors.append(f"Parcel {parcel_no}: Irrigated Area must be positive.")
        if developed_acres > total_acres:
            errors.append(f"Parcel {parcel_no}: Developed Acres cannot exceed Total Acres.")
        if irrigated_area > total_acres:
            st.warning(f"Parcel {parcel_no}: Irrigated Area exceeds Total Acres.")
    return errors


# ---------------- MAIN LAND USE SECTION ----------------
def land_use_section(holder_id):
    """Main land use section for the agricultural census survey."""
    st.header("🏞️ Section 5: Land Use Information")

    st.markdown("""
    **Instructions:** Please provide detailed information about your land use, including parcel details, 
    tenure arrangements, and agricultural practices.
    """)

    # Load existing data if available
    main_info, parcels_data = load_existing_land_use_data(holder_id)

    # Initialize default values
    default_total_area = main_info[0] if main_info else 0.0
    default_years_used = main_info[1] if main_info else 0.0
    default_main_purpose = main_info[2] if main_info else "For Sale Only/Commercial"
    default_num_parcels = main_info[3] if main_info else 1
    default_location = main_info[4] if main_info else ""
    default_crop_methods = main_info[5] if main_info else []

    # Initialize parcels dataframe
    if parcels_data:
        parcels_df = pd.DataFrame(parcels_data, columns=[
            "Parcel No.", "Total Acres", "Developed Acres", "Tenure of Land",
            "Use of Land", "Irrigated Area (Acres)", "Land Clearing Methods"
        ])
    else:
        parcels_df = pd.DataFrame({
            "Parcel No.": [1],
            "Total Acres": [0.0],
            "Developed Acres": [0.0],
            "Tenure of Land": ["Privately Owned"],
            "Use of Land": ["Temporary Crops"],
            "Irrigated Area (Acres)": [0.0],
            "Land Clearing Methods": ["Regenerative"]
        })

    # Store in session state for persistence
    if "land_use_parcels" not in st.session_state:
        st.session_state.land_use_parcels = parcels_df

    with st.form("land_use_form"):
        # --- Main Land Use Information ---
        st.subheader("📊 Main Land Use Information")

        col1, col2 = st.columns(2)
        with col1:
            total_area = st.number_input(
                "Total Area of Holding (acres)",
                min_value=0.0,
                value=default_total_area,
                step=0.01,
                help="Total land area under your management"
            )

            years_used = st.number_input(
                "Years Land Used for Agriculture",
                min_value=0.0,
                value=default_years_used,
                step=0.01,
                help="Number of years this land has been used for agriculture"
            )

            main_purpose = st.radio(
                "Main Purpose of Holding",
                [
                    "For Sale Only/Commercial",
                    "Mainly Sale with Some Consumption",
                    "For Consumption Only/Subsistence",
                    "Mainly Consumption with Some Sale"
                ],
                index=["For Sale Only/Commercial", "Mainly Sale with Some Consumption",
                       "For Consumption Only/Subsistence", "Mainly Consumption with Some Sale"].index(
                    default_main_purpose) if main_info else 0
            )

        with col2:
            num_parcels = st.number_input(
                "Number of Parcels",
                min_value=1,
                value=default_num_parcels,
                step=1,
                help="Total number of separate land parcels"
            )

            location = st.text_input(
                "Exact Location of Holding",
                max_chars=200,
                value=default_location,
                placeholder="e.g., District, Village, Coordinates",
                help="Specific location details for this holding"
            )

            crop_methods = st.multiselect(
                "Crop Methods Used",
                ["Tunnel", "Open Field", "Net house", "Greenhouse", "Netting", "Other"],
                default=default_crop_methods,
                help="Select all cultivation methods used"
            )

        # --- Parcels Information ---
        st.subheader("📑 Land Parcels Details")
        st.info("💡 Add, edit, or remove parcels using the data editor below.")

        # Data editor for parcels
        edited_df = st.data_editor(
            st.session_state.land_use_parcels,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Parcel No.": st.column_config.NumberColumn(
                    "Parcel No.",
                    help="Parcel identification number",
                    min_value=1
                ),
                "Total Acres": st.column_config.NumberColumn(
                    "Total Acres",
                    help="Total area of this parcel",
                    min_value=0.0,
                    step=0.01
                ),
                "Developed Acres": st.column_config.NumberColumn(
                    "Developed Acres",
                    help="Area currently developed/used",
                    min_value=0.0,
                    step=0.01
                ),
                "Tenure of Land": st.column_config.SelectboxColumn(
                    "Tenure of Land",
                    help="Land ownership/usage arrangement",
                    options=[
                        "Privately Owned",
                        "Generational/Commonage",
                        "Privately Leased/Rented",
                        "Crown Leased/Rented",
                        "Squatting on Private Land",
                        "Squatting on Crown Land",
                        "Borrowed",
                        "Other"
                    ]
                ),
                "Use of Land": st.column_config.SelectboxColumn(
                    "Use of Land",
                    help="Primary use of this parcel",
                    options=[
                        "Temporary Crops",
                        "Temporary Meadows and Pastures",
                        "Temporary Fallow",
                        "Permanent Crops",
                        "Permanent Meadows and Pastures",
                        "Forest & Other Wooded Land",
                        "Wetland",
                        "Farm Buildings & Farmyards",
                        "Other"
                    ]
                ),
                "Irrigated Area (Acres)": st.column_config.NumberColumn(
                    "Irrigated Area (Acres)",
                    help="Area under irrigation",
                    min_value=0.0,
                    step=0.01
                ),
                "Land Clearing Methods": st.column_config.SelectboxColumn(
                    "Land Clearing Methods",
                    help="Method used to clear/prepare land",
                    options=[
                        "Regenerative",
                        "Hand Clearing",
                        "Slash and burn",
                        "Small machine",
                        "Large machine"
                    ]
                )
            }
        )

        # Update session state
        st.session_state.land_use_parcels = edited_df

        # Submit button
        submitted = st.form_submit_button("💾 Save Land Use Data")

        if submitted:
            # Validate data
            main_errors = validate_main_land_use(total_area, years_used, crop_methods, num_parcels, location)
            parcel_errors = validate_parcels(edited_df)
            all_errors = main_errors + parcel_errors

            if all_errors:
                for error in all_errors:
                    st.error(error)
            else:
                # Prepare data for saving
                parcels_list = []
                for _, row in edited_df.iterrows():
                    parcels_list.append({
                        "parcel_no": int(row["Parcel No."]),
                        "total_acres": float(row["Total Acres"]),
                        "developed_acres": float(row["Developed Acres"]),
                        "tenure": row["Tenure of Land"].lower().replace(" ", "_").replace("/", "_").replace("&", "and"),
                        "use_of_land": row["Use of Land"].lower().replace(" ", "_").replace("/", "_").replace("&",
                                                                                                              "and"),
                        "irrigated_area": float(row["Irrigated Area (Acres)"]),
                        "land_clearing": row["Land Clearing Methods"].lower().replace(" ", "_")
                    })

                land_use_data = {
                    "total_area": total_area,
                    "years_used": years_used,
                    "main_purpose": main_purpose,
                    "num_parcels": num_parcels,
                    "location": location,
                    "crop_methods": crop_methods,
                    "parcels": parcels_list
                }

                # Save to database
                if save_land_use_to_db(land_use_data, holder_id):
                    st.balloons()
                    return True

    return False


# ---------------- DATABASE SCHEMA SETUP ----------------
def setup_land_use_tables():
    """Create land use tables if they don't exist."""
    conn = None
    try:
        conn = get_connection()
        if conn is None:
            return False

        with conn.cursor() as cur:
            # Create land_use table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS land_use (
                    id SERIAL PRIMARY KEY,
                    holder_id INTEGER NOT NULL REFERENCES holders(holder_id) ON DELETE CASCADE,
                    total_area_acres DECIMAL(10,2) NOT NULL,
                    years_agriculture DECIMAL(5,2) NOT NULL,
                    main_purpose VARCHAR(100) NOT NULL,
                    num_parcels INTEGER NOT NULL,
                    location VARCHAR(200) NOT NULL,
                    crop_methods TEXT[],
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(holder_id)
                )
            """)

            # Create land_use_parcels table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS land_use_parcels (
                    id SERIAL PRIMARY KEY,
                    land_use_id INTEGER NOT NULL REFERENCES land_use(id) ON DELETE CASCADE,
                    parcel_no INTEGER NOT NULL,
                    total_acres DECIMAL(10,2) NOT NULL,
                    developed_acres DECIMAL(10,2) NOT NULL,
                    tenure VARCHAR(50) NOT NULL,
                    use_of_land VARCHAR(50) NOT NULL,
                    irrigated_area DECIMAL(10,2) NOT NULL,
                    land_clearing VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(land_use_id, parcel_no)
                )
            """)

            conn.commit()
            return True

    except Exception as e:
        st.error(f"Error setting up land use tables: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


# Run table setup when module is imported
setup_land_use_tables()


# ---------------- STANDALONE TEST FUNCTION ----------------
def test_land_use_section():
    """Test function to run land use section standalone."""
    st.title("Land Use Section Test")
    holder_id = st.text_input("Enter Holder ID for testing:", value="1")
    if holder_id:
        land_use_section(int(holder_id))


if __name__ == "__main__":
    test_land_use_section()