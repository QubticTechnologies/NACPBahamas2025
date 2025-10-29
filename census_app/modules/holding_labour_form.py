import streamlit as st
from sqlalchemy import text
from census_app .db import engine
import pandas as pd

# ---------------- Options ----------------
RELATIONSHIP_OPTIONS = [
    "Spouse", "Son", "Daughter", "Grandson", "Granddaughter",
    "Son-in-law", "Daughter-in-law", "Brother", "Sister",
    "Father", "Mother", "Other Relative", "Non-Relative"
]

SEX_OPTIONS = ["Male", "Female"]
AGE_GROUP_OPTIONS = [
    "Under 15", "15-24", "25-34", "35-44",
    "45-54", "55-64", "65 and over"
]

WORK_TYPE_OPTIONS = [
    "Permanent", "Seasonal", "Casual", "Contract"
]


# ---------------- Helper Functions ----------------
def safe_index(options_list, value, default_index=0):
    """Safely get the index of a value in a list"""
    if value is None or value not in options_list:
        return default_index
    return options_list.index(value)


def safe_get(data, key, default_value):
    """Safely get a value from dictionary"""
    value = data.get(key, default_value)
    return value if value is not None else default_value


# ---------------- Holder Labour Form ----------------
def holding_labour_form(holder_id, prefix=""):
    """
    Render the Holding Labour form for a given holder.
    Combines structured questions with dynamic family member addition.
    The `prefix` ensures unique Streamlit keys for multiple holders or survey sessions.
    """
    st.header("Section 2: Holding Labour")

    # Initialize session state for family members
    if f'{prefix}_family_member_count' not in st.session_state:
        st.session_state[f'{prefix}_family_member_count'] = 0

    # Initialize session state for non-family workers
    if f'{prefix}_non_family_worker_count' not in st.session_state:
        st.session_state[f'{prefix}_non_family_worker_count'] = 0

    # ---------------- Family Labour Section ----------------
    st.subheader("👥 Family Labour")

    # Main family members (always visible)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        spouse_working = st.selectbox(
            "Spouse working on farm?",
            ["No", "Yes"],
            key=f"{prefix}_spouse_working"
        )

    with col2:
        sons_working = st.number_input(
            "Number of sons working",
            min_value=0,
            max_value=20,
            value=0,
            key=f"{prefix}_sons_working"
        )

    with col3:
        daughters_working = st.number_input(
            "Number of daughters working",
            min_value=0,
            max_value=20,
            value=0,
            key=f"{prefix}_daughters_working"
        )

    with col4:
        other_relatives = st.number_input(
            "Other relatives working",
            min_value=0,
            max_value=20,
            value=0,
            key=f"{prefix}_other_relatives"
        )

    # ---------------- Additional Family Members (Dynamic) ----------------
    st.markdown("---")

    # Only show add button if user wants to add specific family members
    if st.button("➕ Add Specific Family Member", key=f"{prefix}_add_family_member"):
        st.session_state[f'{prefix}_family_member_count'] += 1

    # Display additional family member forms if any exist
    family_members_data = []
    if st.session_state[f'{prefix}_family_member_count'] > 0:
        st.markdown("#### Specific Family Members")
        st.info("Add details for specific family members working on the farm")

        for i in range(st.session_state[f'{prefix}_family_member_count']):
            with st.expander(f"Family Member {i + 1}", expanded=True):
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    relationship = st.selectbox(
                        "Relationship",
                        RELATIONSHIP_OPTIONS,
                        key=f"{prefix}_fam_rel_{i}"
                    )

                    # Show name field only for non-immediate family
                    if relationship not in ["Spouse", "Son", "Daughter"]:
                        name = st.text_input(
                            "Name",
                            key=f"{prefix}_fam_name_{i}",
                            placeholder="Enter name"
                        )
                    else:
                        name = ""

                with col2:
                    sex = st.selectbox(
                        "Sex",
                        SEX_OPTIONS,
                        key=f"{prefix}_fam_sex_{i}"
                    )

                with col3:
                    age_group = st.selectbox(
                        "Age Group",
                        AGE_GROUP_OPTIONS,
                        key=f"{prefix}_fam_age_{i}"
                    )

                # Remove button
                col_remove, _ = st.columns([1, 5])
                with col_remove:
                    if st.button("🗑️ Remove", key=f"{prefix}_remove_fam_{i}"):
                        st.session_state[f'{prefix}_family_member_count'] -= 1
                        st.rerun()

                family_members_data.append({
                    "relationship": relationship,
                    "name": name,
                    "sex": sex,
                    "age_group": age_group
                })

    # ---------------- Non-Family Workers Section ----------------
    st.markdown("---")
    st.subheader("👨‍💼 Non-Family Workers")

    # Basic non-family worker counts
    col1, col2, col3 = st.columns(3)

    with col1:
        permanent_workers = st.number_input(
            "Permanent workers",
            min_value=0,
            max_value=50,
            value=0,
            key=f"{prefix}_permanent_workers"
        )

    with col2:
        seasonal_workers = st.number_input(
            "Seasonal workers",
            min_value=0,
            max_value=50,
            value=0,
            key=f"{prefix}_seasonal_workers"
        )

    with col3:
        casual_workers = st.number_input(
            "Casual workers",
            min_value=0,
            max_value=50,
            value=0,
            key=f"{prefix}_casual_workers"
        )

    # ---------------- Specific Non-Family Workers (Dynamic) ----------------
    # Only show add button if user wants to add specific workers
    if st.button("➕ Add Specific Non-Family Worker", key=f"{prefix}_add_non_family"):
        st.session_state[f'{prefix}_non_family_worker_count'] += 1

    # Display specific non-family worker forms if any exist
    non_family_workers_data = []
    if st.session_state[f'{prefix}_non_family_worker_count'] > 0:
        st.markdown("#### Specific Non-Family Workers")
        st.info("Add details for specific non-family workers")

        for i in range(st.session_state[f'{prefix}_non_family_worker_count']):
            with st.expander(f"Non-Family Worker {i + 1}", expanded=True):
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

                with col1:
                    name = st.text_input(
                        "Name",
                        key=f"{prefix}_worker_name_{i}",
                        placeholder="Worker name"
                    )

                with col2:
                    sex = st.selectbox(
                        "Sex",
                        SEX_OPTIONS,
                        key=f"{prefix}_worker_sex_{i}"
                    )

                with col3:
                    age_group = st.selectbox(
                        "Age Group",
                        AGE_GROUP_OPTIONS,
                        key=f"{prefix}_worker_age_{i}"
                    )

                with col4:
                    work_type = st.selectbox(
                        "Work Type",
                        WORK_TYPE_OPTIONS,
                        key=f"{prefix}_worker_type_{i}"
                    )

                # Remove button
                col_remove, _ = st.columns([1, 5])
                with col_remove:
                    if st.button("🗑️ Remove", key=f"{prefix}_remove_worker_{i}"):
                        st.session_state[f'{prefix}_non_family_worker_count'] -= 1
                        st.rerun()

                non_family_workers_data.append({
                    "name": name,
                    "sex": sex,
                    "age_group": age_group,
                    "work_type": work_type
                })

    # ---------------- Structured Questions Section ----------------
    st.markdown("---")
    st.subheader("📋 Additional Labour Information")

    # Define questions for the holding labour form
    questions = [
        {"question_no": 2,
         "text": "How many permanent workers including administrative staff were hired on the holding from Aug 1, 2024 to Jul 31, 2025 (excluding household)?",
         "type": "count"},
        {"question_no": 3,
         "text": "How many temporary workers including administrative staff were hired on the holding from Aug 1, 2024 to Jul 31, 2025 (excluding household)?",
         "type": "count"},
        {"question_no": 4,
         "text": "What was the number of non-Bahamian workers on the holding from Aug 1, 2024 to Jul 31, 2025?",
         "type": "count"},
        {"question_no": 5, "text": "Did any of your workers have work permits?", "type": "option",
         "options": ["Yes", "No", "Not Applicable"]},
        {"question_no": 6, "text": "Were there any volunteer workers on the holding (i.e. unpaid labourers)?",
         "type": "option", "options": ["Yes", "No", "Not Applicable"]},
        {"question_no": 7,
         "text": "Did you use any agricultural contracted services (crop protection, pruning, composting, harvesting, animal services, irrigation, farm admin etc.) on the holding?",
         "type": "option", "options": ["Yes", "No", "Not Applicable"]},
    ]

    # Container for saving user responses
    responses = {}

    # Render each question
    for q in questions:
        q_no = q["question_no"]
        key_prefix = f"{prefix}_holder_{holder_id}_q{q_no}"

        if q["type"] == "count":
            # Render number inputs for male/female counts
            male = st.number_input(f"Male - {q['text']}", min_value=0, value=0, key=f"{key_prefix}_male")
            female = st.number_input(f"Female - {q['text']}", min_value=0, value=0, key=f"{key_prefix}_female")
            total = male + female
            st.write(f"Total: {total}")
            responses[q_no] = {"male": male, "female": female, "total": total, "option_response": None}

        elif q["type"] == "option":
            # Render selectbox for options
            option_response = st.selectbox(q["text"], options=q["options"], key=f"{key_prefix}_option")
            responses[q_no] = {"male": None, "female": None, "total": None, "option_response": option_response}

    # ---------------- Summary Preview ----------------
    st.markdown("---")
    st.subheader("📊 Labour Summary")

    summary_data = []

    # Family labour summary
    if spouse_working == "Yes":
        summary_data.append({"Type": "Family", "Category": "Spouse", "Count": 1})
    if sons_working > 0:
        summary_data.append({"Type": "Family", "Category": "Sons", "Count": sons_working})
    if daughters_working > 0:
        summary_data.append({"Type": "Family", "Category": "Daughters", "Count": daughters_working})
    if other_relatives > 0:
        summary_data.append({"Type": "Family", "Category": "Other Relatives", "Count": other_relatives})

    # Specific family members
    for member in family_members_data:
        summary_data.append({
            "Type": "Family",
            "Category": f"Specific: {member['relationship']}",
            "Count": 1
        })

    # Non-family workers summary
    if permanent_workers > 0:
        summary_data.append({"Type": "Non-Family", "Category": "Permanent", "Count": permanent_workers})
    if seasonal_workers > 0:
        summary_data.append({"Type": "Non-Family", "Category": "Seasonal", "Count": seasonal_workers})
    if casual_workers > 0:
        summary_data.append({"Type": "Non-Family", "Category": "Casual", "Count": casual_workers})

    # Specific non-family workers
    for worker in non_family_workers_data:
        summary_data.append({
            "Type": "Non-Family",
            "Category": f"Specific: {worker['work_type']}",
            "Count": 1
        })

    if summary_data:
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

        # Calculate totals
        total_family = sum(item["Count"] for item in summary_data if item["Type"] == "Family")
        total_non_family = sum(item["Count"] for item in summary_data if item["Type"] == "Non-Family")
        grand_total = total_family + total_non_family

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Family Workers", total_family)
        with col2:
            st.metric("Total Non-Family Workers", total_non_family)
        with col3:
            st.metric("Grand Total", grand_total)
    else:
        st.info("No labour information entered yet.")

    # ---------------- Save to Database ----------------
    if st.button("💾 Save Labour Information", type="primary", key=f"{prefix}_save_button", use_container_width=True):
        try:
            with engine.begin() as conn:
                # Save basic labour information
                labour_data = {
                    "holder_id": holder_id,
                    "spouse_working": spouse_working,
                    "sons_working": sons_working,
                    "daughters_working": daughters_working,
                    "other_relatives": other_relatives,
                    "permanent_workers": permanent_workers,
                    "seasonal_workers": seasonal_workers,
                    "casual_workers": casual_workers
                }

                # Save to holding_labour table
                conn.execute(
                    text("""
                        INSERT INTO holding_labour (
                            holder_id, spouse_working, sons_working, daughters_working,
                            other_relatives, permanent_workers, seasonal_workers, casual_workers
                        )
                        VALUES (
                            :holder_id, :spouse_working, :sons_working, :daughters_working,
                            :other_relatives, :permanent_workers, :seasonal_workers, :casual_workers
                        )
                        ON CONFLICT (holder_id) DO UPDATE SET
                            spouse_working = EXCLUDED.spouse_working,
                            sons_working = EXCLUDED.sons_working,
                            daughters_working = EXCLUDED.daughters_working,
                            other_relatives = EXCLUDED.other_relatives,
                            permanent_workers = EXCLUDED.permanent_workers,
                            seasonal_workers = EXCLUDED.seasonal_workers,
                            casual_workers = EXCLUDED.casual_workers
                    """),
                    labour_data
                )

                # Save structured questions
                for q_no, r in responses.items():
                    conn.execute(
                        text("""
                            INSERT INTO holding_labour_questions (
                                holder_id, question_no, question_text, male_count, female_count, total_count, option_response
                            ) VALUES (
                                :holder_id, :q_no, :question_text, :male, :female, :total, :option_response
                            )
                            ON CONFLICT (holder_id, question_no) DO UPDATE
                            SET male_count = EXCLUDED.male_count,
                                female_count = EXCLUDED.female_count,
                                total_count = EXCLUDED.total_count,
                                option_response = EXCLUDED.option_response
                        """),
                        {
                            "holder_id": holder_id,
                            "q_no": q_no,
                            "question_text": questions[q_no - 2]["text"],  # Adjust index since questions start from 2
                            "male": r["male"],
                            "female": r["female"],
                            "total": r["total"],
                            "option_response": r["option_response"]
                        }
                    )

                # TODO: Save specific family members and non-family workers to separate tables
                # This would require additional tables like family_members and non_family_workers

            st.success("✅ Labour information saved successfully!")

        except Exception as e:
            st.error(f"❌ Error saving labour information: {e}")

    return True