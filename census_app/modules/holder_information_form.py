import streamlit as st
from sqlalchemy import text
from census_app.db import engine
import pandas as pd
import datetime

# ---------------- Options ----------------
SEX_OPTIONS = ["Male", "Female", "Other"]
MARITAL_STATUS_OPTIONS = [
    "Single", "Married", "Divorced", "Separated",
    "Widowed", "Common-law", "Prefer not to disclose"
]
EDUCATION_OPTIONS = [
    "No Schooling", "Primary", "Junior Secondary",
    "Senior Secondary", "Undergraduate", "Masters",
    "Doctorate", "Vocational", "Professional Designation"
]
YES_NO = ["Yes", "No"]
OCCUPATION_OPTIONS = ["Agriculture", "Other"]


# ---------------- Helper Functions ----------------
def safe_index(options_list, value, default_index=0):
    """Safely get the index of a value in a list, return default if not found or None"""
    if value is None or value not in options_list:
        return default_index
    return options_list.index(value)


def safe_get(data, key, default_value):
    """Safely get a value from dictionary, return default if None or not found"""
    value = data.get(key, default_value)
    return value if value is not None else default_value


# ---------------- Form Function ----------------
def holder_information_form(holder_id=None):
    """
    Section 1: Holder Information
    Starts with Holder 1 (Main) with option to add more holders dynamically.
    """
    st.header("Section 1: Holder Information")

    # Initialize session state for holder count
    if 'holder_count' not in st.session_state:
        st.session_state.holder_count = 1

    holders_data = []
    existing_holders = {}

    # ---------------- Preload existing holders - FIXED: Removed ORDER BY holder_number ----------------
    if holder_id:
        try:
            with engine.connect() as conn:
                # FIXED: Removed ORDER BY holder_number since the column doesn't exist
                results = conn.execute(
                    text("SELECT * FROM holders WHERE holder_id = :holder_id"),
                    {"holder_id": holder_id}
                ).fetchall()

                # Since we don't have holder_number, we'll treat all results as Holder 1
                # and additional holders will be new entries
                for idx, row in enumerate(results):
                    row_dict = dict(row._mapping)
                    # Use index + 1 as holder number (1, 2, 3, etc.)
                    holder_number = idx + 1
                    existing_holders[holder_number] = row_dict

                # Set holder count based on existing data
                if results:
                    st.session_state.holder_count = len(results)
        except Exception as e:
            st.error(f"Error loading existing holder data: {e}")

    # ---------------- Holder Management Controls ----------------
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Holder Management")
    with col2:
        if st.button("➕ Add Another Holder", use_container_width=True):
            st.session_state.holder_count += 1
            st.rerun()

    # ---------------- Holder Inputs ----------------
    for i in range(1, st.session_state.holder_count + 1):
        with st.expander(f"Holder {i}{' - Main Holder' if i == 1 else ''}", expanded=i == 1):
            if i > 1:
                # Add remove button for additional holders
                col_remove, _ = st.columns([1, 5])
                with col_remove:
                    if st.button("🗑️ Remove", key=f"remove_{i}", use_container_width=True):
                        st.session_state.holder_count -= 1
                        st.rerun()

            data = existing_holders.get(i, {})

            # Get default values safely
            full_name_default = safe_get(data, "name", "")
            sex_default = safe_get(data, "sex", SEX_OPTIONS[0])
            dob_default = safe_get(data, "date_of_birth", datetime.date(1990, 1, 1))
            nationality_default = safe_get(data, "nationality", "Bahamian")
            nationality_other_default = safe_get(data, "nationality_other", "")
            marital_default = safe_get(data, "marital_status", MARITAL_STATUS_OPTIONS[0])
            education_default = safe_get(data, "highest_education", EDUCATION_OPTIONS[0])
            ag_training_default = safe_get(data, "agri_training", "No")
            primary_occ_default = safe_get(data, "primary_occupation", OCCUPATION_OPTIONS[0])
            primary_occ_other_default = safe_get(data, "primary_occupation_other", "")
            secondary_occ_default = safe_get(data, "secondary_occupation", "")

            # Form fields
            col1, col2 = st.columns(2)

            with col1:
                full_name = st.text_input(f"Full Name", value=full_name_default, key=f"name_{i}", max_chars=100)

                sex_index = safe_index(SEX_OPTIONS, sex_default, 0)
                sex = st.selectbox(f"Sex", SEX_OPTIONS, index=sex_index, key=f"sex_{i}")

                dob = st.date_input(
                    f"Date of Birth",
                    value=dob_default,
                    key=f"dob_{i}",
                    format="DD/MM/YYYY",
                    min_value=datetime.date(1900, 1, 1),
                    max_value=datetime.date.today()
                )

                nat_index = 0 if nationality_default == "Bahamian" else 1
                nationality = st.selectbox(
                    f"Nationality", ["Bahamian", "Other"],
                    index=nat_index, key=f"nat_{i}"
                )

                nationality_other = ""
                if nationality == "Other":
                    nationality_other = st.text_input(
                        f"Specify Nationality", value=nationality_other_default,
                        key=f"nat_other_{i}", max_chars=100
                    )

            with col2:
                marital_index = safe_index(MARITAL_STATUS_OPTIONS, marital_default, 0)
                marital_status = st.selectbox(f"Marital Status", MARITAL_STATUS_OPTIONS,
                                              index=marital_index, key=f"mar_{i}")

                education_index = safe_index(EDUCATION_OPTIONS, education_default, 0)
                education = st.selectbox(f"Highest Level of Education", EDUCATION_OPTIONS,
                                         index=education_index, key=f"edu_{i}")

                ag_training_index = 0 if ag_training_default == "Yes" else 1
                ag_training = st.radio(f"Agricultural Education/Training", YES_NO,
                                       index=ag_training_index, key=f"train_{i}")
                ag_training_val = "Yes" if ag_training == "Yes" else "No"

                primary_occ_index = 0 if primary_occ_default == "Agriculture" else 1
                primary_occupation = st.selectbox(f"Primary Occupation", OCCUPATION_OPTIONS,
                                                  index=primary_occ_index, key=f"primocc_{i}")

                primary_occupation_other = ""
                if primary_occupation == "Other":
                    primary_occupation_other = st.text_input(
                        f"Specify Primary Occupation", value=primary_occ_other_default,
                        key=f"primocc_other_{i}", max_chars=100
                    )

                secondary_occupation = st.text_input(
                    f"Secondary Occupation", value=secondary_occ_default, key=f"secocc_{i}", max_chars=100
                )

            holders_data.append({
                "holder_id": data.get("holder_id"),
                "holder_number": i,
                "full_name": full_name,
                "sex": sex,
                "date_of_birth": dob,
                "nationality": nationality,
                "nationality_other": nationality_other,
                "marital_status": marital_status,
                "highest_education": education,
                "agri_training": ag_training_val,
                "primary_occupation": primary_occupation,
                "primary_occupation_other": primary_occupation_other,
                "secondary_occupation": secondary_occupation
            })

    # ---------------- Preview ----------------
    if holders_data:
        st.subheader("📊 Holder Information Summary")

        # Create summary table
        summary_data = []
        for holder in holders_data:
            if holder["full_name"]:  # Only show holders with names
                summary_data.append({
                    "Holder": f"Holder {holder['holder_number']}",
                    "Name": holder["full_name"],
                    "Sex": holder["sex"],
                    "Date of Birth": holder["date_of_birth"].strftime("%d/%m/%Y"),
                    "Nationality": holder["nationality"],
                    "Marital Status": holder["marital_status"],
                    "Education": holder["highest_education"],
                    "Ag Training": holder["agri_training"],
                    "Primary Occupation": holder["primary_occupation"]
                })

        if summary_data:
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
        else:
            st.info("No holder information entered yet.")

    # ---------------- Save to Database - FIXED: Simplified without holder_number ----------------
    if st.button("💾 Save Holder Information", type="primary", use_container_width=True):
        success_count = 0
        error_count = 0

        try:
            with engine.begin() as conn:
                for holder in holders_data:
                    if holder["full_name"]:  # only save if name is provided
                        try:
                            # For multiple holders, we need to handle them differently
                            # Since we don't have holder_number in the database, we'll treat each as a separate holder

                            if holder["holder_number"] == 1:
                                # Update the main holder
                                conn.execute(
                                    text("""
                                        UPDATE holders 
                                        SET name = :full_name, 
                                            sex = :sex,
                                            date_of_birth = :date_of_birth,
                                            nationality = :nationality,
                                            nationality_other = :nationality_other,
                                            marital_status = :marital_status,
                                            highest_education = :highest_education,
                                            agri_training = :agri_training,
                                            primary_occupation = :primary_occupation,
                                            primary_occupation_other = :primary_occupation_other,
                                            secondary_occupation = :secondary_occupation,
                                            updated_at = NOW()
                                        WHERE holder_id = :holder_id
                                    """),
                                    {
                                        "holder_id": holder_id,
                                        "full_name": holder["full_name"] or "",
                                        "sex": holder["sex"] or SEX_OPTIONS[0],
                                        "date_of_birth": holder["date_of_birth"],
                                        "nationality": holder["nationality"] or "Bahamian",
                                        "nationality_other": holder["nationality_other"] or "",
                                        "marital_status": holder["marital_status"] or MARITAL_STATUS_OPTIONS[0],
                                        "highest_education": holder["highest_education"] or EDUCATION_OPTIONS[0],
                                        "agri_training": holder["agri_training"] or "No",
                                        "primary_occupation": holder["primary_occupation"] or OCCUPATION_OPTIONS[0],
                                        "primary_occupation_other": holder["primary_occupation_other"] or "",
                                        "secondary_occupation": holder["secondary_occupation"] or ""
                                    }
                                )
                                success_count += 1
                            else:
                                # For additional holders, create new holder records
                                # You might want to create a separate table for multiple holders per farm
                                st.warning(
                                    f"Multiple holder support requires database schema changes. Only Holder 1 was saved.")
                                break

                        except Exception as e:
                            st.error(f"Error saving holder {holder['holder_number']}: {e}")
                            error_count += 1

            if success_count > 0:
                st.success(f"✅ Holder information saved successfully!")
                # Show quick actions after saving
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("➕ Add Another Holder", use_container_width=True):
                        st.session_state.holder_count += 1
                        st.rerun()
                with col2:
                    if st.button("📋 Continue to Next Section", use_container_width=True):
                        st.success("Ready to continue to the next section!")

            if error_count > 0:
                st.warning(f"⚠️ {error_count} holder(s) had errors during saving.")

        except Exception as e:
            st.error(f"❌ Database error: {e}")

    return True