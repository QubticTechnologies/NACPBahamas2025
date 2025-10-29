# agricultural_machinery.py
import streamlit as st
import psycopg2
from psycopg2.extras import execute_values
import logging
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- DATABASE CONNECTION ----------------
def get_connection():
    """Return a psycopg2 connection to PostgreSQL using .env credentials."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            dbname=os.getenv("DB_NAME", "agri_census"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            port=int(os.getenv("DB_PORT", 5432))
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        st.error("❌ Unable to connect to database. Please check your .env settings.")
        return None

# ---------------- SAVE TO DATABASE ----------------
def save_to_db(machinery_data: List[Dict[str, Any]]) -> bool:
    if not machinery_data:
        st.warning("No data to save.")
        return False

    conn = get_connection()
    if conn is None:
        return False

    cur = None
    try:
        cur = conn.cursor()
        holder_id = machinery_data[0]["holder_id"]
        check_query = "SELECT COUNT(*) FROM agricultural_machinery WHERE holder_id = %s"
        cur.execute(check_query, (holder_id,))
        count = cur.fetchone()[0]

        if count > 0:
            st.info("🔄 Updating existing machinery records...")
            cur.execute("DELETE FROM agricultural_machinery WHERE holder_id = %s", (holder_id,))

        insert_query = """
            INSERT INTO agricultural_machinery
            (holder_id, has_item, equipment_name, quantity_new, quantity_used, 
             quantity_out_of_service, source)
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
            )
            for row in machinery_data
        ]
        execute_values(cur, insert_query, values)
        conn.commit()
        logger.info(f"Successfully saved {len(machinery_data)} machinery records for holder {holder_id}")
        return True

    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        st.error(f"❌ Database error: {e}")
        return False
    except Exception as e:
        conn.rollback()
        logger.error(f"Unexpected error: {e}")
        st.error(f"❌ Error saving data: {e}")
        return False
    finally:
        if cur:
            cur.close()
        conn.close()

# ---------------- LOAD EXISTING DATA ----------------
def load_existing_data(holder_id: str) -> List[Dict[str, Any]]:
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
    validation_passed = True
    for i, row in enumerate(machinery_data):
        equipment_name = row["equipment_name"]

        if "Open Entry" in equipment_name and not row["equipment_name"].strip():
            st.error(f"❌ Please specify the equipment type for Open Entry #{i - 5}")
            validation_passed = False

        if len(equipment_name) > 100:
            st.error(f"❌ Equipment name too long (max 100 characters): {equipment_name}")
            validation_passed = False

        if row["has_item"] == "Y":
            total_qty = row["quantity_new"] + row["quantity_used"] + row["quantity_out_of_service"]
            if total_qty == 0:
                st.error(f"❌ For '{equipment_name}', please enter quantities if you have this equipment (marked 'Yes')")
                validation_passed = False

        for qty_type in ["quantity_new", "quantity_used", "quantity_out_of_service"]:
            qty_value = row[qty_type]
            if qty_value < 0 or qty_value > 20:
                st.error(f"❌ For '{equipment_name}', {qty_type.replace('_', ' ')} must be between 0 and 20")
                validation_passed = False
    return validation_passed

# ---------------- AGRICULTURAL MACHINERY SECTION ----------------
def agricultural_machinery_section(holder_id: str):
    st.subheader("🏭 Agricultural Machinery")
    st.markdown("**For the items listed below, report the number of machinery and equipment on the holdings on July 31, 2025.**")

    with st.expander("ℹ️ Source Codes Explanation"):
        st.markdown("""
        - **O**: Owned
        - **RL**: Rented or Leased  
        - **B**: Both Owned and Rented/Leased
        """)

    equipment_list = [
        "Small Engine Machines (e.g. pole-saw, push mower, weed wacker, auger etc.)",
        "Tractors (below 100 horsepower)",
        "Tractors (100 horsepower or greater)",
        "Sprayers and dusters",
        "Trucks (including pickups)",
        "Cars / Jeeps / Station Wagons",
        "Open Entry 1",
        "Open Entry 2"
    ]

    existing_data = load_existing_data(holder_id)
    machinery_data = []

    with st.form("machinery_form", clear_on_submit=False):
        col1, col2, col3, col4 = st.columns([1, 3, 3, 1])
        with col1: st.markdown("**Yes / No**")
        with col2: st.markdown("**Agricultural Equipment / Machinery**")
        with col3: st.markdown("**Quantity on the Holding**")
        with col4: st.markdown("**Source**")
        st.markdown("---")

        for idx, equipment in enumerate(equipment_list, start=1):
            default_values = {
                "has_item": "N",
                "equipment_name": equipment,
                "quantity_new": 0,
                "quantity_used": 0,
                "quantity_out_of_service": 0,
                "source": "O"
            }
            if existing_data and idx <= len(existing_data):
                default_values.update(existing_data[idx - 1])

            col1, col2, col3, col4 = st.columns([1, 3, 3, 1])

            # Column 1: Yes / No
            with col1:
                has_item = st.radio("", ["Y", "N"], index=0 if default_values["has_item"]=="Y" else 1,
                                    horizontal=True, key=f"has_{equipment}_{holder_id}_{idx}")

            # Column 2: Equipment Name
            with col2:
                if "Open Entry" in equipment:
                    default_name = ""
                    if existing_data and idx <= len(existing_data):
                        existing_equip_name = existing_data[idx - 1]["equipment_name"]
                        if existing_equip_name != equipment:
                            default_name = existing_equip_name
                    equipment_name = st.text_input("", value=default_name,
                                                   placeholder="Specify equipment type...",
                                                   max_chars=100,
                                                   key=f"equip_{equipment}_{holder_id}_{idx}",
                                                   label_visibility="collapsed")
                    if not equipment_name:
                        equipment_name = f"Open Entry {idx - 6}"
                else:
                    equipment_name = equipment
                    st.markdown(f"{equipment}")

            # Column 3: Quantities
            with col3:
                q_col1, q_col2, q_col3 = st.columns(3)
                with q_col1: st.markdown("**New**")
                qty_new = st.number_input("", min_value=0, max_value=20, value=default_values["quantity_new"],
                                          step=1, key=f"new_{equipment}_{holder_id}_{idx}", label_visibility="collapsed")
                with q_col2: st.markdown("**Used**")
                qty_used = st.number_input("", min_value=0, max_value=20, value=default_values["quantity_used"],
                                           step=1, key=f"used_{equipment}_{holder_id}_{idx}", label_visibility="collapsed")
                with q_col3: st.markdown("**Out of Service**")
                qty_out = st.number_input("", min_value=0, max_value=20, value=default_values["quantity_out_of_service"],
                                          step=1, key=f"out_{equipment}_{holder_id}_{idx}", label_visibility="collapsed")

            # Column 4: Source
            with col4:
                source_options = ["O", "RL", "B"]
                source_index = source_options.index(default_values["source"]) if default_values["source"] in source_options else 0
                source = st.radio("", source_options, index=source_index, horizontal=True,
                                  key=f"source_{equipment}_{holder_id}_{idx}")

            machinery_data.append({
                "holder_id": holder_id,
                "has_item": has_item,
                "equipment_name": equipment_name,
                "quantity_new": qty_new,
                "quantity_used": qty_used,
                "quantity_out_of_service": qty_out,
                "source": source,
            })

        st.markdown("---")
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            submitted = st.form_submit_button("💾 Save Machinery Data", use_container_width=True)
        if submitted:
            if validate_machinery_data(machinery_data):
                if save_to_db(machinery_data):
                    st.success("✅ Agricultural machinery data saved successfully!")
                    st.balloons()
                    st.rerun()

    display_machinery_summary(holder_id)
    return machinery_data

# ---------------- SUMMARY DISPLAY ----------------
def display_machinery_summary(holder_id: str):
    existing_data = load_existing_data(holder_id)
    if existing_data:
        st.subheader("📊 Saved Machinery Data")
        active_equipment = [row for row in existing_data if row["has_item"]=="Y" and (
            row["quantity_new"]>0 or row["quantity_used"]>0 or row["quantity_out_of_service"]>0)]
        if active_equipment:
            for row in active_equipment:
                col1,col2,col3 = st.columns([3,2,1])
                with col1: st.write(f"**{row['equipment_name']}**")
                with col2: st.write(f"New: {row['quantity_new']}, Used: {row['quantity_used']}, Out: {row['quantity_out_of_service']}")
                with col3: st.write(f"Source: {row['source']}")
                st.markdown("---")
        else:
            st.info("No active machinery data found (all items marked as 'No' or zero quantities).")
    else:
        st.info("No machinery data saved yet.")

# ---------------- STANDALONE TEST FUNCTION ----------------
def test_machinery_section():
    st.title("Agricultural Machinery Test")
    holder_id = st.text_input("Enter Holder ID for testing:", value="1")
    if holder_id:
        agricultural_machinery_section(holder_id)

if __name__ == "__main__":
    test_machinery_section()
