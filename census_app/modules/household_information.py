# census_app/modules/household_information.py

import streamlit as st
import pandas as pd
from sqlalchemy import text
from db import engine
from typing import Dict, List, Optional
import plotly.express as px
import plotly.graph_objects as go

# =============================================================================
# PROFESSIONAL CONSTANTS & CONFIGURATION
# =============================================================================
SECTION_NO = 2  # Now Section 2 as requested

RELATIONSHIP_OPTIONS = {
    1: "👫 Spouse/Partner",
    2: "👦 Son",
    3: "👧 Daughter",
    4: "👨‍👩‍👧 In-Laws",
    5: "👶 Grandchild",
    6: "👴👵 Parent/Parent-In-Law",
    7: "👨‍👩‍👧‍👦 Other Relative",
    8: "👤 Non-Relative"
}

SEX_OPTIONS = ["👨 Male", "👩 Female"]

EDUCATION_OPTIONS = {
    1: "📚 No Schooling",
    2: "🏫 Primary",
    3: "🎒 Junior Secondary",
    4: "🎓 Senior Secondary",
    5: "🎓 Undergraduate",
    6: "🎓 Masters",
    7: "🎓 Doctorate",
    8: "🔧 Vocational",
    9: "📋 Professional Designation"
}

OCCUPATION_OPTIONS = {
    1: "🌾 Agriculture",
    2: "🎣 Fishing",
    3: "💼 Professional/Technical",
    4: "👔 Administrative/Manager",
    5: "🛒 Sales",
    6: "📞 Customer Service",
    7: "🏨 Tourism",
    8: "🏠 Not Economically Active",
    9: "🔧 Other"
}

WORKING_TIME_OPTIONS = {
    "N": "❌ None",
    "F": "🕒 Full time",
    "P": "⏱️ Part time",
    "P3": "📅 1-3 months",
    "P6": "📅 4-6 months",
    "P7": "📅 7+ months"
}


# =============================================================================
# ENHANCED DATA MANAGER
# =============================================================================
class HouseholdDataManager:
    """Professional data management for household information"""

    @staticmethod
    def load_household_summary(holder_id: int) -> Optional[Dict]:
        """Load household summary with professional error handling"""
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT total_persons, persons_under_14_male, persons_under_14_female,
                               persons_14plus_male, persons_14plus_female
                        FROM household_summary 
                        WHERE holdings_id = :holder_id
                    """),
                    {"holder_id": holder_id}
                ).fetchone()
                return dict(result._mapping) if result else None
        except Exception as e:
            st.error(f"🔧 Database error loading summary: {e}")
            return None

    @staticmethod
    def load_existing_members(holder_id: int) -> List[Dict]:
        """Load existing household members with professional formatting"""
        try:
            with engine.connect() as conn:
                members = conn.execute(
                    text("""
                        SELECT id, relationship_to_holder, sex, age, education_level,
                               primary_occupation, secondary_occupation, working_time_on_holding
                        FROM household_information
                        WHERE holder_id = :holder_id
                        ORDER BY id
                    """),
                    {"holder_id": holder_id}
                ).fetchall()

                return [dict(member._mapping) for member in members]
        except Exception as e:
            st.error(f"🔧 Database error loading members: {e}")
            return []

    @staticmethod
    def save_household_summary(holder_id: int, summary_data: Dict) -> bool:
        """Save household summary with transaction safety"""
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO household_summary (
                        holdings_id, holder_number, total_persons,
                        persons_under_14_male, persons_under_14_female,
                        persons_14plus_male, persons_14plus_female
                    ) VALUES (
                        :holdings_id, :holder_number, :total_persons,
                        :u14_male, :u14_female, :plus14_male, :plus14_female
                    )
                    ON CONFLICT (holdings_id, holder_number)
                    DO UPDATE SET
                        total_persons = EXCLUDED.total_persons,
                        persons_under_14_male = EXCLUDED.persons_under_14_male,
                        persons_under_14_female = EXCLUDED.persons_under_14_female,
                        persons_14plus_male = EXCLUDED.persons_14plus_male,
                        persons_14plus_female = EXCLUDED.persons_14plus_female
                """), summary_data)
            return True
        except Exception as e:
            st.error(f"❌ Failed to save household summary: {e}")
            return False

    @staticmethod
    def add_household_member(holder_id: int, member_data: Dict) -> bool:
        """Add new household member with validation"""
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO household_information
                    (holder_id, relationship_to_holder, sex, age, education_level,
                     primary_occupation, secondary_occupation, working_time_on_holding)
                    VALUES (:holder_id, :relationship, :sex, :age, :edu, 
                            :primary_occ, :secondary_occ, :work_time)
                """), member_data)
            return True
        except Exception as e:
            st.error(f"❌ Failed to add household member: {e}")
            return False


# =============================================================================
# PROFESSIONAL UI COMPONENTS
# =============================================================================
def inject_household_styles():
    """Inject professional CSS styles for household section"""
    st.markdown("""
    <style>
        .household-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 15px;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .summary-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            border-left: 4px solid #667eea;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin: 1rem 0;
        }
        .member-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            border: 1px solid #e1e8ed;
        }
        .stats-highlight {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 1rem;
            border-radius: 10px;
            text-align: center;
            font-weight: 600;
        }
        .validation-warning {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
        }
    </style>
    """, unsafe_allow_html=True)


def render_household_summary_section(holder_id: int, prefix: str) -> Dict:
    """Render professional household summary section"""
    st.markdown("### 🏠 Household Demographics Summary")

    # Load existing data
    existing_summary = HouseholdDataManager.load_household_summary(holder_id)

    with st.container():
        st.markdown('<div class="summary-card">', unsafe_allow_html=True)

        col1, col2 = st.columns([2, 1])

        with col1:
            total_persons = st.number_input(
                "👨‍👩‍👧‍👦 **Total persons in household** (including holder)",
                min_value=0,
                max_value=100,
                step=1,
                value=existing_summary.get('total_persons', 0) if existing_summary else 0,
                key=f"{prefix}_total_persons",
                help="Total number of people living in this household"
            )

        with col2:
            if total_persons > 0:
                st.metric("Household Size", total_persons)
            else:
                st.metric("Status", "Not Set")

        st.markdown("#### 📊 Age & Gender Distribution")

        age_col1, age_col2 = st.columns(2)

        with age_col1:
            st.markdown("**👦 Children (Under 14)**")
            u14_male = st.number_input(
                "Male",
                0, 100,
                existing_summary.get('persons_under_14_male', 0) if existing_summary else 0,
                key=f"{prefix}_u14_male"
            )
            u14_female = st.number_input(
                "Female",
                0, 100,
                existing_summary.get('persons_under_14_female', 0) if existing_summary else 0,
                key=f"{prefix}_u14_female"
            )

        with age_col2:
            st.markdown("**👨‍🎓 Adults (14+)**")
            plus14_male = st.number_input(
                "Male",
                0, 100,
                existing_summary.get('persons_14plus_male', 0) if existing_summary else 0,
                key=f"{prefix}_14plus_male"
            )
            plus14_female = st.number_input(
                "Female",
                0, 100,
                existing_summary.get('persons_14plus_female', 0) if existing_summary else 0,
                key=f"{prefix}_14plus_female"
            )

        # Validation
        total_by_age = u14_male + u14_female + plus14_male + plus14_female
        if total_persons > 0 and total_by_age != total_persons:
            st.markdown(f"""
            <div class="validation-warning">
                ⚠️ **Data Validation Notice**
                <br>Sum of age groups ({total_by_age}) doesn't match total persons ({total_persons})
            </div>
            """, unsafe_allow_html=True)

        # Save summary button
        if st.button("💾 Save Household Summary", key=f"{prefix}_save_summary", type="primary"):
            summary_data = {
                "holdings_id": holder_id,
                "holder_number": holder_id,
                "total_persons": total_persons,
                "u14_male": u14_male,
                "u14_female": u14_female,
                "plus14_male": plus14_male,
                "plus14_female": plus14_female
            }

            if HouseholdDataManager.save_household_summary(holder_id, summary_data):
                st.success("✅ Household summary saved successfully!")
                st.balloons()

        st.markdown('</div>', unsafe_allow_html=True)

    return {
        "total_persons": total_persons,
        "u14_male": u14_male,
        "u14_female": u14_female,
        "plus14_male": plus14_male,
        "plus14_female": plus14_female
    }


def render_existing_members_section(holder_id: int):
    """Render professional existing members display"""
    st.markdown("### 👥 Current Household Members")

    members = HouseholdDataManager.load_existing_members(holder_id)

    if members:
        # Enhanced dataframe with professional styling
        df_data = []
        for member in members:
            df_data.append({
                "ID": member['id'],
                "Relationship": RELATIONSHIP_OPTIONS.get(member['relationship_to_holder'], "Unknown"),
                "Gender": member['sex'],
                "Age": member['age'],
                "Education": EDUCATION_OPTIONS.get(member['education_level'], "Unknown"),
                "Primary Occupation": OCCUPATION_OPTIONS.get(member['primary_occupation'], "Unknown"),
                "Work Time": WORKING_TIME_OPTIONS.get(member['working_time_on_holding'], "Unknown")
            })

        df = pd.DataFrame(df_data)

        # Display with enhanced styling
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=min(400, len(df) * 35 + 40)
        )

        # Quick statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Members", len(members))
        with col2:
            avg_age = df['Age'].mean() if not df.empty else 0
            st.metric("Average Age", f"{avg_age:.1f}")
        with col3:
            working_count = sum(1 for m in members if m['working_time_on_holding'] != 'N')
            st.metric("Working on Farm", working_count)

    else:
        st.info("""
        📝 **No household members recorded yet.**

        Add household members using the form below to build your household profile.
        """)


def render_new_member_form(holder_id: int, current_count: int, max_new_members: int, prefix: str):
    """Render professional new member form section"""
    st.markdown("### ➕ Add Household Members")

    if max_new_members <= 0:
        st.success("🎉 All household members have been added based on your total persons count!")
        return

    st.info(f"**Available slots:** {max_new_members} new member(s) can be added")

    # Show only one form if only one member can be added
    if max_new_members == 1:
        render_single_member_form(holder_id, current_count + 1, prefix)
    else:
        # Use expanders for multiple members
        for i in range(1, max_new_members + 1):
            with st.expander(f"👤 New Member {i}", expanded=i == 1):
                render_member_form_fields(holder_id, current_count + i, prefix, i)


def render_single_member_form(holder_id: int, member_number: int, prefix: str):
    """Render form for single member (no expander)"""
    st.markdown("#### 👤 Add Household Member")
    render_member_form_fields(holder_id, member_number, prefix, 1)


def render_member_form_fields(holder_id: int, member_number: int, prefix: str, form_index: int):
    """Render the actual member form fields"""
    with st.form(f"{prefix}_new_member_form_{form_index}", clear_on_submit=True):
        st.markdown(f"**Member Details**")

        col1, col2 = st.columns(2)

        with col1:
            relationship = st.selectbox(
                "👨‍👩‍👧‍👦 Relationship to Holder",
                options=list(RELATIONSHIP_OPTIONS.keys()),
                format_func=lambda x: RELATIONSHIP_OPTIONS[x],
                key=f"{prefix}_rel_{form_index}"
            )

            sex = st.radio(
                "⚧️ Gender",
                SEX_OPTIONS,
                horizontal=True,
                key=f"{prefix}_sex_{form_index}"
            )

            age = st.number_input(
                "🎂 Age",
                min_value=0,
                max_value=120,
                step=1,
                key=f"{prefix}_age_{form_index}"
            )

            edu = st.selectbox(
                "🎓 Education Level",
                options=list(EDUCATION_OPTIONS.keys()),
                format_func=lambda x: EDUCATION_OPTIONS[x],
                key=f"{prefix}_edu_{form_index}"
            )

        with col2:
            primary_occ = st.selectbox(
                "💼 Primary Occupation",
                options=list(OCCUPATION_OPTIONS.keys()),
                format_func=lambda x: OCCUPATION_OPTIONS[x],
                key=f"{prefix}_primary_occ_{form_index}"
            )

            secondary_occ = st.selectbox(
                "📋 Secondary Occupation (optional)",
                options=[None] + list(OCCUPATION_OPTIONS.keys()),
                format_func=lambda x: OCCUPATION_OPTIONS[x] if x else "None",
                key=f"{prefix}_secondary_occ_{form_index}"
            )

            work_time = st.selectbox(
                "🌾 Working Time on Holding",
                options=list(WORKING_TIME_OPTIONS.keys()),
                format_func=lambda x: WORKING_TIME_OPTIONS[x],
                key=f"{prefix}_work_time_{form_index}"
            )

        submitted = st.form_submit_button(
            f"💾 Add Member {member_number}",
            use_container_width=True,
            type="primary"
        )

        if submitted:
            member_data = {
                "holder_id": holder_id,
                "relationship": relationship,
                "sex": sex.replace("👨 ", "").replace("👩 ", ""),  # Remove emoji for storage
                "age": age,
                "edu": edu,
                "primary_occ": primary_occ,
                "secondary_occ": secondary_occ,
                "work_time": work_time
            }

            if HouseholdDataManager.add_household_member(holder_id, member_data):
                st.success(f"✅ Member {member_number} added successfully!")
                st.rerun()


def render_household_analytics(summary_data: Dict, members: List[Dict]):
    """Render professional analytics dashboard"""
    if not members:
        return

    st.markdown("---")
    st.markdown("### 📊 Household Analytics")

    # Create analytics columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Household Size", len(members))

    with col2:
        male_count = sum(1 for m in members if 'Male' in m['sex'])
        st.metric("Male Members", male_count)

    with col3:
        female_count = sum(1 for m in members if 'Female' in m['sex'])
        st.metric("Female Members", female_count)

    with col4:
        avg_age = sum(m['age'] for m in members) / len(members)
        st.metric("Average Age", f"{avg_age:.1f}")

    # Age distribution
    age_groups = {"Children (0-13)": 0, "Youth (14-24)": 0, "Adults (25-64)": 0, "Seniors (65+)": 0}
    for member in members:
        age = member['age']
        if age < 14:
            age_groups["Children (0-13)"] += 1
        elif age < 25:
            age_groups["Youth (14-24)"] += 1
        elif age < 65:
            age_groups["Adults (25-64)"] += 1
        else:
            age_groups["Seniors (65+)"] += 1

    # Display age distribution
    st.markdown("#### 👥 Age Distribution")
    age_df = pd.DataFrame(list(age_groups.items()), columns=['Age Group', 'Count'])
    st.bar_chart(age_df.set_index('Age Group'))


# =============================================================================
# MAIN HOUSEHOLD INFORMATION FUNCTION
# =============================================================================
def household_information(holder_id: int, prefix: str = "household"):
    """
    Professional Household Information Section (Now Section 2)
    Maintains original functionality with enhanced UI/UX
    """
    # Initialize professional styling
    inject_household_styles()

    # Professional header
    st.markdown("""
    <div class="household-header">
        <h2>🏠 Section 2 - Household Information</h2>
        <p>Comprehensive demographic profiling of agricultural households</p>
    </div>
    """, unsafe_allow_html=True)

    # Initialize session data safely
    if "household_form_data" not in st.session_state:
        st.session_state["household_form_data"] = {}

    # Load existing data
    existing_members = HouseholdDataManager.load_existing_members(holder_id)
    current_member_count = len(existing_members)

    # 1. Household Summary Section
    summary_data = render_household_summary_section(holder_id, prefix)
    total_persons = summary_data["total_persons"]

    # Calculate available member slots
    max_new_members = min(10, max(0, total_persons - current_member_count))

    # 2. Existing Members Section
    render_existing_members_section(holder_id)

    # 3. Add New Members Section (only show if slots available)
    if total_persons > 0 and max_new_members > 0:
        render_new_member_form(holder_id, current_member_count, max_new_members, prefix)
    elif total_persons == 0:
        st.info("📋 Enter total persons in household first to add members.")
    else:
        st.success("✅ All household members have been recorded!")

    # 4. Analytics Section
    if existing_members:
        render_household_analytics(summary_data, existing_members)

    # Section completion status
    st.markdown("---")
    if current_member_count >= total_persons > 0:
        st.success("🎉 Household section completed! All members have been recorded.")
        return True

    return False


# =============================================================================
# EXECUTION FUNCTION
# =============================================================================
def run_household_information(holder_id: int, prefix: str = "household") -> bool:
    """
    Execute household information section with professional error handling
    """
    try:
        return household_information(holder_id, prefix)
    except Exception as e:
        st.error(f"❌ Error in household information section: {e}")
        return False


# =============================================================================
# TEST FUNCTION
# =============================================================================
def test_household_information():
    """Professional test environment"""
    st.title("🧪 Household Information - Test Environment")

    # Test controls
    st.sidebar.markdown("### 🧪 Test Controls")
    holder_id = st.sidebar.number_input("Test Holder ID", value=1, min_value=1)

    # Run the module
    run_household_information(holder_id, "test")


if __name__ == "__main__":
    test_household_information()