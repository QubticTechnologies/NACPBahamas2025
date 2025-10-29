# agricultural_machinery.py
import streamlit as st
import psycopg2
from psycopg2.extras import execute_values
import logging
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------- DATABASE CONNECTION ----------------
def get_connection():
    """Return a psycopg2 connection to PostgreSQL."""
    try:
        conn = psycopg2.connect(
            host=st.secrets.get("DB_HOST", "localhost"),
            dbname=st.secrets.get("DB_NAME", "agri_census"),
            user=st.secrets.get("DB_USER", "postgres"),
            password=st.secrets.get("DB_PASSWORD", "yourpassword"),
            port=st.secrets.get("DB_PORT", 5432)
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        st.error("❌ Unable to connect to database. Please check your connection settings.")
        return None


# ---------------- SAVE TO DATABASE ----------------
def save_to_db(machinery_data: List[Dict[str, Any]]) -> bool:
    """Insert machinery data into the agricultural_machinery table."""
    if not machinery_data:
        st.warning("No data to save.")
        return False

    conn = get_connection()
    if conn is None:
        return False

    cur = None
    try:
        cur = conn.cursor()

        # Check if data already exists for this holder_id
        holder_id = machinery_data[0]["holder_id"]
        check_query = "SELECT COUNT(*) FROM agricultural_machinery WHERE holder_id = %s"
        cur.execute(check_query, (holder_id,))
        count = cur.fetchone()[0]

        if count > 0:
            # Update existing records
            st.info("🔄 Updating existing machinery records...")
            delete_query = "DELETE FROM agricultural_machinery WHERE holder_id = %s"
            cur.execute(delete_query, (holder_id,))

        insert_query = """
            INSERT INTO agricultural_machinery
            (holder_id, has_item, equipment_name, quantity_new, quantity_used, 
             quantity_out_of_service, source, created_at)
            VALUES %s
        """

        values = [
            (
                row["holder_id"],
                row["has_item"],
                row["equipment_name"],
                row["quantity_new"],
                row["quantity_used"],
                row["quantity_out_of_service"],
                row["source"],
                "NOW()"  # PostgreSQL function
            )
            for row in machinery_data
        ]

        execute_values(cur, insert_query, values)
        conn.commit()
        logger.info(f"Successfully saved {len(machinery_data)} machinery records for holder {holder_id}")
        return True

    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        st.error(f"❌ Error saving data: {e}")
        return False
    finally:
        if cur:
            cur.close()
        conn.close()


# ---------------- LOAD EXISTING DATA ----------------
def load_existing_data(holder_id: str) -> List[Dict[str, Any]]:
    """Load existing machinery data for a holder."""
    conn = get_connection()
    if conn is None:
        return []

    cur = None
    try:
        cur = conn.cursor()
        query = """
            SELECT has_item, equipment_name, quantity_new, quantity_used, 
                   quantity_out_of_service, source
            FROM agricultural_machinery 
            WHERE holder_id = %s
            ORDER BY id
        """
        cur.execute(query, (holder_id,))
        rows = cur.fetchall()

        existing_data = []
        for row in rows:
            existing_data.append({
                "has_item": row[0],
                "equipment_name": row[1],
                "quantity_new": row[2],
                "quantity_used": row[3],
                "quantity_out_of_service": row[4],
                "source": row[5]
            })

        return existing_data

    except Exception as e:
        logger.error(f"Error loading existing data: {e}")
        return []
    finally:
        if cur:
            cur.close()
        conn.close()


# ---------------- VALIDATION ----------------
def validate_machinery_data(machinery_data: List[Dict[str, Any]]) -> bool:
    """Validate the machinery data before saving."""
    for i, row in enumerate(machinery_data):
        equipment_name = row["equipment_name"]

        # Check if "Other" equipment is specified
        if "Other" in equipment_name and not row["equipment_name"].strip():
            st.error(f"❌ Please specify the equipment type for 'Other' item #{i + 1}")
            return False

        # Validate that if has_item is "Y", at least one quantity should be > 0
        if row["has_item"] == "Y":
            total_qty = row["quantity_new"] + row["quantity_used"] + row["quantity_out_of_service"]
            if total_qty == 0:
                st.error(f"❌ For '{equipment_name}', please enter quantities if you have this equipment")
                return False

    return True


# ---------------- AGRICULTURAL MACHINERY SECTION ----------------
def agricultural_machinery_section(holder_id: str):
    """Display the Agricultural Machinery form and save to DB."""
    st.subheader("🏭 Agricultural Machinery")
    st.markdown(
        "**For the items listed below, report the number of machinery and equipment on the holdings on July 31, 2025.**"
    )

    # Source explanation
    with st.expander("ℹ️ Source Codes Explanation"):
        st.markdown("""
        - **O**: Owned
        - **RL**: Rented or Leased  
        - **B**: Both Owned and Rented/Leased
        """)

    # Predefined equipment rows
    equipment_list = [
        "Small Engine Machines (e.g. pole-saw, push mower, weed wacker, auger etc.)",
        "Tractors (below 100 horsepower)",
        "Tractors (100 horsepower or greater)",
        "Sprayers and dusters",
        "Trucks (including pickups)",
        "Cars / Jeeps / Station Wagons",
        "Other (specify 1)",
        "Other (specify 2)",
        "Other (specify 3)"
    ]

    # Load existing data
    existing_data = load_existing_data(holder_id)

    machinery_data = []

    # Streamlit form for submission
    with st.form("machinery_form", clear_on_submit=False):
        for idx, equipment in enumerate(equipment_list, start=1):
            st.markdown(f"### {idx}. {equipment}")

            # Pre-fill with existing data if available
            default_values = {
                "has_item": "N",
                "equipment_name": equipment,
                "quantity_new": 0,
                "quantity_used": 0,
                "quantity_out_of_service": 0,
                "source": "O"
            }

            if existing_data and idx <= len(existing_data):
                existing_row = existing_data[idx - 1]
                default_values.update(existing_row)

            col1, col2, col3, col4, col5 = st.columns([1, 3, 1, 1, 1])

            # Yes / No
            with col1:
                has_item = st.radio(
                    "Has Item?",
                    ["Y", "N"],
                    index=0 if default_values["has_item"] == "Y" else 1,
                    horizontal=True,
                    key=f"has_{equipment}_{holder_id}"
                )

            # Equipment Name (editable only for "Other" rows)
            with col2:
                if "Other" in equipment:
                    equipment_name = st.text_input(
                        "Specify other equipment",
                        value=default_values["equipment_name"] if "Other" in default_values["equipment_name"] else "",
                        max_chars=100,
                        key=f"equip_{equipment}_{holder_id}"
                    )
                else:
                    equipment_name = equipment
                    st.markdown(f"**{equipment}**")

            # Quantity: New / Used / Out of Service
            with col3:
                qty_new = st.number_input(
                    "New",
                    min_value=0,
                    max_value=100,
                    value=default_values["quantity_new"],
                    step=1,
                    key=f"new_{equipment}_{holder_id}"
                )
            with col4:
                qty_used = st.number_input(
                    "Used",
                    min_value=0,
                    max_value=100,
                    value=default_values["quantity_used"],
                    step=1,
                    key=f"used_{equipment}_{holder_id}"
                )
            with col5:
                qty_out = st.number_input(
                    "Out of Service",
                    min_value=0,
                    max_value=100,
                    value=default_values["quantity_out_of_service"],
                    step=1,
                    key=f"out_{equipment}_{holder_id}"
                )

            # Source
            source_options = ["O", "RL", "B"]
            source_index = source_options.index(default_values["source"]) if default_values[
                                                                                 "source"] in source_options else 0
            source = st.radio(
                "Source",
                source_options,
                index=source_index,
                horizontal=True,
                key=f"source_{equipment}_{holder_id}"
            )

            # Append row to data list
            machinery_data.append({
                "holder_id": holder_id,
                "has_item": has_item,
                "equipment_name": equipment_name,
                "quantity_new": qty_new,
                "quantity_used": qty_used,
                "quantity_out_of_service": qty_out,
                "source": source,
            })

        # Submit button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button("💾 Save Machinery Data", use_container_width=True)

        if submitted:
            if validate_machinery_data(machinery_data):
                if save_to_db(machinery_data):
                    st.success("✅ Agricultural machinery data saved successfully!")
                    st.balloons()
                    # Refresh the page to show updated data
                    st.rerun()

    return machinery_data


# ---------------- SUMMARY DISPLAY ----------------
def display_machinery_summary(holder_id: str):
    """Display a summary of saved machinery data."""
    existing_data = load_existing_data(holder_id)

    if existing_data:
        st.subheader("📊 Saved Machinery Data")

        # Filter out items that are marked as "N" or have no quantities
        active_equipment = [
            row for row in existing_data
            if row["has_item"] == "Y" and (
                    row["quantity_new"] > 0 or
                    row["quantity_used"] > 0 or
                    row["quantity_out_of_service"] > 0
            )
        ]

        if active_equipment:
            for row in active_equipment:
                total = row["quantity_new"] + row["quantity_used"] + row["quantity_out_of_service"]
                st.write(f"**{row['equipment_name']}**: {total} total "
                         f"(New: {row['quantity_new']}, Used: {row['quantity_used']}, "
                         f"Out of Service: {row['quantity_out_of_service']}) - Source: {row['source']}")
        else:
            st.info("No machinery data saved yet or all items marked as 'No'.")