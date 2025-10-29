# census_app/modules/holding_labour_permanent.py

import streamlit as st
from sqlalchemy import create_engine, text
from config import SQLALCHEMY_DATABASE_URI
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# DATABASE ENGINE WITH SSL HANDLING
# =============================================================================
def create_safe_engine():
    """Create database engine with SSL error handling and fallback options"""
    try:
        # Check if we need to disable SSL for local development
        database_url = SQLALCHEMY_DATABASE_URI

        if database_url and "postgresql" in database_url:
            # Add SSL mode disable for local development
            if "?" in database_url:
                if "sslmode" not in database_url:
                    database_url += "&sslmode=disable"
            else:
                database_url += "?sslmode=disable"

            logger.info("Configured database connection with SSL disabled for local development")

        engine = create_engine(
            database_url,
            echo=False,
            future=True,
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 10,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5
            }
        )

        # Test connection
        with engine.connect() as test_conn:
            test_conn.execute(text("SELECT 1"))

        return engine

    except Exception as e:
        logger.error(f"Database engine creation failed: {e}")
        st.error("🔧 Database connection issue detected")
        return None


# Initialize engine
engine = create_safe_engine()

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================
SECTION_NO = 3  # Permanent Workers Section ID

# Professional dropdown options with enhanced categorization
POSITION_OPTIONS = {
    "Management": {
        "Farm Manager": '1',
        "Operations Manager": '2',
        "Supervisor": '3'
    },
    "Technical": {
        "Agricultural Technician": '4',
        "Irrigation Specialist": '5',
        "Equipment Operator": '6'
    },
    "Field Operations": {
        "Farm Worker": '7',
        "Harvest Specialist": '8',
        "Crop Care Technician": '9'
    },
    "Administrative": {
        "Office Administrator": '10',
        "Sales/Marketing": '11'
    }
}

SEX_OPTIONS = {"Male": 'M', "Female": 'F', "Other": 'O'}

AGE_OPTIONS = {
    "Youth (15-24)": '1',
    "Young Adult (25-34)": '2',
    "Mid-Career (35-44)": '3',
    "Experienced (45-54)": '4',
    "Senior (55-64)": '5',
    "Retirement Age (65+)": '6'
}

NATIONALITY_OPTIONS = {"Bahamian": 'B', "Caribbean National": 'C', "Other Nationality": 'O'}

EDUCATION_OPTIONS = {
    "No Formal Schooling": '1',
    "Primary Education": '2',
    "Junior Secondary": '3',
    "Senior Secondary": '4',
    "Vocational/Trade": '5',
    "Undergraduate Degree": '6',
    "Postgraduate Degree": '7',
    "Professional Certification": '8'
}

AGRI_TRAINING_OPTIONS = {
    "Formal Agricultural Degree": 'D',
    "Vocational Training": 'V',
    "On-the-Job Training": 'O',
    "No Formal Training": 'N'
}

MAIN_DUTIES_OPTIONS = {
    "Crop Management": {
        "Land Preparation": '1',
        "Planting/Establishment": '2',
        "Crop Maintenance": '3',
        "Harvesting": '4'
    },
    "Livestock Management": {
        "Animal Care": '5',
        "Feeding Operations": '6',
        "Health Management": '7'
    },
    "Support Operations": {
        "Equipment Operation": '8',
        "Transportation": '9',
        "Packaging": '10'
    },
    "Business Operations": {
        "Marketing/Sales": '11',
        "Administration": '12',
        "Management": '13'
    }
}

WORKING_TIME_OPTIONS = {
    "Full-Time (Year-Round)": 'F',
    "Part-Time (Regular)": 'P',
    "Seasonal (1-3 months)": 'S3',
    "Seasonal (4-6 months)": 'S6',
    "Seasonal (7+ months)": 'S7',
    "Contract Basis": 'C'
}


# =============================================================================
# ENHANCED HELPER FUNCTIONS
# =============================================================================
class DataManager:
    """Enhanced data management with professional error handling"""

    @staticmethod
    def safe_index(options_dict: Dict, value: str, default_index: int = 0) -> int:
        """Safely get the index of a value in options"""
        if not value:
            return default_index

        # Handle nested dictionaries
        flat_options = DataManager.flatten_options(options_dict)
        options_list = list(flat_options.keys())

        try:
            return options_list.index(value)
        except (ValueError, IndexError):
            return default_index

    @staticmethod
    def flatten_options(nested_dict: Dict) -> Dict:
        """Flatten nested option dictionaries"""
        flat_dict = {}
        for category, options in nested_dict.items():
            if isinstance(options, dict):
                flat_dict.update(options)
            else:
                flat_dict[category] = options
        return flat_dict

    @staticmethod
    def safe_get(data: Dict, key: str, default_value: any) -> any:
        """Safely get a value from dictionary with enhanced null checking"""
        if not data:
            return default_value

        value = data.get(key)
        return value if value is not None else default_value

    @staticmethod
    def get_display_value(options_dict: Dict, code: str) -> str:
        """Get display value from code with nested dict support"""
        flat_options = DataManager.flatten_options(options_dict)
        for display, value in flat_options.items():
            if value == code:
                return display
        return "Unknown"


class DatabaseManager:
    """Professional database operations with comprehensive error handling"""

    @staticmethod
    def test_connection() -> bool:
        """Test database connection with detailed error reporting"""
        if not engine:
            return False

        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    @staticmethod
    def load_existing_workers(holder_id: int) -> Dict[int, Dict]:
        """Load existing workers with professional error handling"""
        if not engine:
            st.error("🔧 Database connection unavailable")
            return {}

        try:
            with engine.connect() as conn:
                results = conn.execute(
                    text("""
                        SELECT * FROM holding_labour_permanent 
                        WHERE holder_id = :holder_id 
                        ORDER BY id
                    """),
                    {"holder_id": holder_id}
                ).fetchall()

            workers = {}
            for idx, row in enumerate(results):
                workers[idx] = dict(row._mapping)

            logger.info(f"Loaded {len(workers)} existing workers for holder {holder_id}")
            return workers

        except Exception as e:
            error_msg = f"Database operation failed: {str(e)}"
            logger.error(error_msg)

            # User-friendly error messages
            if "SSL" in str(e).upper():
                st.error("""
                🔒 **Database Connection Issue**

                SSL connection requirement detected. Please contact system administrator 
                or check your database configuration.
                """)
            elif "connection" in str(e).lower():
                st.error("""
                🔌 **Connection Error**

                Unable to connect to database. Please check:
                - Database server status
                - Network connectivity  
                - Connection credentials
                """)
            else:
                st.error(f"📊 **Data Loading Error**\n\n{error_msg}")

            return {}

    @staticmethod
    def save_workers_data(holder_id: int, workers_data: List[Dict]) -> bool:
        """Save workers data with transaction safety"""
        if not engine:
            st.error("🔧 Database connection unavailable")
            return False

        if not workers_data:
            st.warning("No worker data to save")
            return False

        try:
            with engine.begin() as conn:
                # Delete existing records for this holder
                conn.execute(
                    text("DELETE FROM holding_labour_permanent WHERE holder_id = :holder_id"),
                    {"holder_id": holder_id}
                )

                # Insert new records
                for worker in workers_data:
                    conn.execute(text("""
                        INSERT INTO holding_labour_permanent
                        (holder_id, position_title, sex, age_group, nationality, education_level,
                         agri_training, main_duties, working_time)
                        VALUES (:holder_id, :position_title, :sex, :age_group, :nationality, :education_level,
                                :agri_training, :main_duties, :working_time)
                    """), {**worker, "holder_id": holder_id})

                # Update survey progress
                DatabaseManager.mark_section_complete(holder_id, conn)

            logger.info(f"Successfully saved {len(workers_data)} workers for holder {holder_id}")
            return True

        except Exception as e:
            error_msg = f"Failed to save worker data: {str(e)}"
            logger.error(error_msg)
            st.error(f"❌ **Save Failed**\n\n{error_msg}")
            return False

    @staticmethod
    def mark_section_complete(holder_id: int, conn=None) -> bool:
        """Mark section as complete with professional transaction handling"""
        try:
            if conn is None:
                # External transaction
                with engine.begin() as new_conn:
                    return DatabaseManager._update_progress(holder_id, new_conn)
            else:
                # Existing transaction
                return DatabaseManager._update_progress(holder_id, conn)

        except Exception as e:
            logger.error(f"Progress update failed: {e}")
            return False

    @staticmethod
    def _update_progress(holder_id: int, conn) -> bool:
        """Internal progress update implementation"""
        exists = conn.execute(
            text("SELECT id FROM holder_survey_progress WHERE holder_id = :hid AND section_id = :sec"),
            {"hid": holder_id, "sec": SECTION_NO}
        ).fetchone()

        if exists:
            conn.execute(
                text(
                    "UPDATE holder_survey_progress SET completed = true, updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
                {"id": exists[0]}
            )
        else:
            conn.execute(text("""
                INSERT INTO holder_survey_progress (holder_id, section_id, completed, created_at) 
                VALUES (:hid, :sec, true, CURRENT_TIMESTAMP)
            """), {"hid": holder_id, "sec": SECTION_NO})

        return True


# =============================================================================
# ENHANCED UI COMPONENTS
# =============================================================================
def inject_permanent_workers_styles():
    """Inject professional CSS styles for permanent workers section"""
    st.markdown("""
    <style>
        .permanent-workers-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 12px;
            color: white;
            margin-bottom: 1.5rem;
        }
        .worker-card {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .stats-card {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 1rem;
            border-radius: 10px;
            text-align: center;
        }
        .section-complete-btn {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)


def render_worker_statistics(workers_data: List[Dict]):
    """Render professional statistics dashboard for workers"""
    if not workers_data:
        return

    st.markdown("### 📊 Workforce Analytics")

    # Calculate statistics
    total_workers = len(workers_data)
    male_count = sum(1 for w in workers_data if w["sex"] == 'M')
    female_count = sum(1 for w in workers_data if w["sex"] == 'F')
    full_time_count = sum(1 for w in workers_data if w["working_time"] == 'F')

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Workforce", total_workers)

    with col2:
        st.metric("Male Workers", male_count)

    with col3:
        st.metric("Female Workers", female_count)

    with col4:
        st.metric("Full-Time Staff", full_time_count)

    # Additional analytics
    if total_workers > 0:
        col_analytics1, col_analytics2 = st.columns(2)

        with col_analytics1:
            # Gender distribution
            gender_data = pd.DataFrame({
                'Gender': ['Male', 'Female', 'Other'],
                'Count': [male_count, female_count, total_workers - male_count - female_count]
            })
            st.bar_chart(gender_data.set_index('Gender'))

        with col_analytics2:
            # Age distribution
            age_groups = {}
            for worker in workers_data:
                age_code = worker["age_group"]
                age_display = DataManager.get_display_value(AGE_OPTIONS, age_code)
                age_groups[age_display] = age_groups.get(age_display, 0) + 1

            if age_groups:
                age_df = pd.DataFrame(list(age_groups.items()), columns=['Age Group', 'Count'])
                st.bar_chart(age_df.set_index('Age Group'))


def render_worker_summary_table(workers_data: List[Dict]):
    """Render professional summary table of workers"""
    if not workers_data:
        return

    summary_data = []
    for i, worker in enumerate(workers_data):
        summary_data.append({
            "Worker ID": i + 1,
            "Position": DataManager.get_display_value(POSITION_OPTIONS, worker["position_title"]),
            "Gender": DataManager.get_display_value(SEX_OPTIONS, worker["sex"]),
            "Age Group": DataManager.get_display_value(AGE_OPTIONS, worker["age_group"]),
            "Nationality": DataManager.get_display_value(NATIONALITY_OPTIONS, worker["nationality"]),
            "Employment Type": DataManager.get_display_value(WORKING_TIME_OPTIONS, worker["working_time"])
        })

    st.dataframe(
        pd.DataFrame(summary_data),
        use_container_width=True,
        height=min(300, len(summary_data) * 35 + 38)
    )


# =============================================================================
# MAIN PERMANENT WORKERS FORM
# =============================================================================
def holding_labour_permanent_form(holder_id: int, prefix: str = "") -> bool:
    """
    Enhanced Permanent Workers form with professional UI and robust error handling
    """
    # Inject custom styles
    inject_permanent_workers_styles()

    # Header section
    st.markdown("""
    <div class="permanent-workers-header">
        <h2>👨‍💼 Permanent Workforce Management</h2>
        <p>Document your permanent agricultural workforce for comprehensive labor analytics</p>
    </div>
    """, unsafe_allow_html=True)

    # Database connection check
    if not DatabaseManager.test_connection():
        st.error("""
        🔧 **Database Unavailable**

        Please ensure:
        - Database server is running
        - Connection credentials are correct
        - Network connectivity is established

        Contact system administrator if this issue persists.
        """)
        return False

    # Initialize session state for worker management
    worker_count_key = f'{prefix}_permanent_worker_count'
    if worker_count_key not in st.session_state:
        st.session_state[worker_count_key] = 0

    # Load existing workers
    existing_workers = DatabaseManager.load_existing_workers(holder_id)

    # Initialize worker count from existing data
    if existing_workers and st.session_state[worker_count_key] == 0:
        st.session_state[worker_count_key] = len(existing_workers)

    # Worker Management Controls
    st.markdown("### 🎯 Workforce Management")

    col_controls1, col_controls2, col_controls3 = st.columns([2, 1, 1])

    with col_controls1:
        st.info("💼 Manage your permanent agricultural workforce")

    with col_controls2:
        if st.button("➕ Add Worker", key=f"{prefix}_add_worker", use_container_width=True):
            st.session_state[worker_count_key] += 1
            st.rerun()

    with col_controls3:
        if st.session_state[worker_count_key] > 0:
            if st.button("🔄 Reset All", key=f"{prefix}_reset_workers", use_container_width=True):
                st.session_state[worker_count_key] = 0
                st.rerun()

    # Dynamic Worker Input Forms
    workers_data = []

    if st.session_state[worker_count_key] > 0:
        st.markdown("#### 👥 Worker Details")

        for i in range(st.session_state[worker_count_key]):
            with st.container():
                st.markdown(f'<div class="worker-card">', unsafe_allow_html=True)

                st.markdown(f"##### 👤 Permanent Worker #{i + 1}")

                # Get existing data or defaults
                data = existing_workers.get(i, {})

                # Form layout
                col1, col2 = st.columns(2)

                with col1:
                    # Professional Information
                    st.markdown("**Professional Details**")

                    # Enhanced position selection with categories
                    position_categories = list(POSITION_OPTIONS.keys())
                    selected_category = st.selectbox(
                        "Position Category",
                        position_categories,
                        key=f"{prefix}_category_{i}",
                        help="Select the category that best describes this worker's role"
                    )

                    position_options = POSITION_OPTIONS[selected_category]
                    position_default = DataManager.safe_get(data, "position_title", list(position_options.values())[0])
                    position_display_default = DataManager.get_display_value(POSITION_OPTIONS, position_default)

                    position = st.selectbox(
                        "Position Title *",
                        list(position_options.keys()),
                        index=DataManager.safe_index(position_options, position_display_default),
                        key=f"{prefix}_position_{i}"
                    )

                    # Working arrangements
                    working_time_default = DataManager.safe_get(data, "working_time",
                                                                list(WORKING_TIME_OPTIONS.values())[0])
                    working_time_display_default = DataManager.get_display_value(WORKING_TIME_OPTIONS,
                                                                                 working_time_default)

                    working_time = st.selectbox(
                        "Employment Type *",
                        list(WORKING_TIME_OPTIONS.keys()),
                        index=DataManager.safe_index(WORKING_TIME_OPTIONS, working_time_display_default),
                        key=f"{prefix}_worktime_{i}"
                    )

                    # Main duties with enhanced options
                    duties_categories = list(MAIN_DUTIES_OPTIONS.keys())
                    selected_duty_category = st.selectbox(
                        "Duty Category",
                        duties_categories,
                        key=f"{prefix}_duty_category_{i}"
                    )

                    duty_options = MAIN_DUTIES_OPTIONS[selected_duty_category]
                    duties_default = DataManager.safe_get(data, "main_duties", list(duty_options.values())[0])
                    duties_display_default = DataManager.get_display_value(MAIN_DUTIES_OPTIONS, duties_default)

                    main_duties = st.selectbox(
                        "Primary Responsibility *",
                        list(duty_options.keys()),
                        index=DataManager.safe_index(duty_options, duties_display_default),
                        key=f"{prefix}_duties_{i}"
                    )

                with col2:
                    # Personal & Educational Information
                    st.markdown("**Personal & Education**")

                    # Demographics
                    sex_default = DataManager.safe_get(data, "sex", list(SEX_OPTIONS.values())[0])
                    sex_display_default = DataManager.get_display_value(SEX_OPTIONS, sex_default)

                    sex = st.selectbox(
                        "Gender *",
                        list(SEX_OPTIONS.keys()),
                        index=DataManager.safe_index(SEX_OPTIONS, sex_display_default),
                        key=f"{prefix}_sex_{i}"
                    )

                    age_default = DataManager.safe_get(data, "age_group", list(AGE_OPTIONS.values())[0])
                    age_display_default = DataManager.get_display_value(AGE_OPTIONS, age_default)

                    age = st.selectbox(
                        "Age Group *",
                        list(AGE_OPTIONS.keys()),
                        index=DataManager.safe_index(AGE_OPTIONS, age_display_default),
                        key=f"{prefix}_age_{i}"
                    )

                    nationality_default = DataManager.safe_get(data, "nationality",
                                                               list(NATIONALITY_OPTIONS.values())[0])
                    nationality_display_default = DataManager.get_display_value(NATIONALITY_OPTIONS,
                                                                                nationality_default)

                    nationality = st.selectbox(
                        "Nationality *",
                        list(NATIONALITY_OPTIONS.keys()),
                        index=DataManager.safe_index(NATIONALITY_OPTIONS, nationality_display_default),
                        key=f"{prefix}_nationality_{i}"
                    )

                    # Education and Training
                    education_default = DataManager.safe_get(data, "education_level",
                                                             list(EDUCATION_OPTIONS.values())[0])
                    education_display_default = DataManager.get_display_value(EDUCATION_OPTIONS, education_default)

                    education = st.selectbox(
                        "Education Level *",
                        list(EDUCATION_OPTIONS.keys()),
                        index=DataManager.safe_index(EDUCATION_OPTIONS, education_display_default),
                        key=f"{prefix}_education_{i}"
                    )

                    agri_training_default = DataManager.safe_get(data, "agri_training",
                                                                 list(AGRI_TRAINING_OPTIONS.values())[0])
                    agri_training_display_default = DataManager.get_display_value(AGRI_TRAINING_OPTIONS,
                                                                                  agri_training_default)

                    agri_training = st.selectbox(
                        "Agricultural Training *",
                        list(AGRI_TRAINING_OPTIONS.keys()),
                        index=DataManager.safe_index(AGRI_TRAINING_OPTIONS, agri_training_display_default),
                        key=f"{prefix}_agri_{i}"
                    )

                # Remove worker button
                if st.session_state[worker_count_key] > 1:
                    col_remove, _ = st.columns([1, 5])
                    with col_remove:
                        if st.button("🗑️ Remove Worker", key=f"{prefix}_remove_worker_{i}", use_container_width=True):
                            st.session_state[worker_count_key] -= 1
                            st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)

                # Collect worker data
                workers_data.append({
                    "position_title": POSITION_OPTIONS[selected_category][position],
                    "sex": SEX_OPTIONS[sex],
                    "age_group": AGE_OPTIONS[age],
                    "nationality": NATIONALITY_OPTIONS[nationality],
                    "education_level": EDUCATION_OPTIONS[education],
                    "agri_training": AGRI_TRAINING_OPTIONS[agri_training],
                    "main_duties": MAIN_DUTIES_OPTIONS[selected_duty_category][main_duties],
                    "working_time": WORKING_TIME_OPTIONS[working_time]
                })
    else:
        # Empty state
        st.markdown("""
        <div style='text-align: center; padding: 3rem; background: #f8f9fa; border-radius: 10px;'>
            <h3>👥 No Permanent Workers Added</h3>
            <p>Start building your workforce by adding your first permanent worker</p>
        </div>
        """, unsafe_allow_html=True)

    # Summary and Analytics Section
    if workers_data:
        st.markdown("---")

        # Summary Table
        st.markdown("### 📋 Workforce Summary")
        render_worker_summary_table(workers_data)

        # Analytics Dashboard
        render_worker_statistics(workers_data)

    # Save Section
    st.markdown("---")
    st.markdown("### 💾 Data Management")

    col_save1, col_save2 = st.columns([3, 1])

    with col_save1:
        if workers_data:
            st.success(f"✅ Ready to save {len(workers_data)} permanent worker(s)")
        else:
            st.warning("⚠️ No workers added. Add at least one worker to save.")

    with col_save2:
        if st.button("💾 Save Workforce Data", type="primary", key=f"{prefix}_save_permanent", use_container_width=True):
            if not workers_data:
                st.error("❌ Please add at least one permanent worker before saving.")
                return False

            success = DatabaseManager.save_workers_data(holder_id, workers_data)
            if success:
                st.success("""
                ✅ **Workforce Data Saved Successfully!**

                Your permanent workers information has been securely stored 
                and is ready for agricultural census reporting.
                """)
                st.balloons()
                return True

    return False


# =============================================================================
# MAIN EXECUTION FUNCTION
# =============================================================================
def run_holding_labour_permanent(holder_id: int, prefix: str = "") -> bool:
    """
    Enhanced main function to run the permanent workers section
    with comprehensive error handling and professional UI
    """
    if not holder_id:
        st.error("""
        🚫 **Holder Selection Required**

        Please select a farm holder to manage permanent workforce data.
        """)
        return False

    try:
        return holding_labour_permanent_form(holder_id, prefix)

    except Exception as e:
        logger.error(f"Unexpected error in permanent workers section: {e}")
        st.error("""
        ❌ **Unexpected System Error**

        An unexpected error occurred while loading the permanent workers section.
        Please refresh the page and try again.

        If this issue persists, contact system administrator.
        """)
        return False


# =============================================================================
# STANDALONE TEST FUNCTION
# =============================================================================
def test_permanent_workers():
    """Enhanced test function for standalone execution"""
    st.title("🧪 Permanent Workers Module - Test Environment")

    # Test controls
    st.sidebar.markdown("### 🧪 Test Controls")

    if st.sidebar.button("Reset Session State"):
        for key in list(st.session_state.keys()):
            if "permanent_worker" in key:
                del st.session_state[key]
        st.rerun()

    # Mock holder ID for testing
    holder_id = st.sidebar.number_input("Test Holder ID", value=1, min_value=1)

    # Run the module
    run_holding_labour_permanent(holder_id, "test")


if __name__ == "__main__":
    test_permanent_workers()