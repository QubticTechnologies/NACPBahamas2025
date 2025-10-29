import streamlit as st
from sqlalchemy import text
from db import engine
import bcrypt
from config import USERS_TABLE, ROLE_HOLDER, ROLE_ADMIN, STATUS_ACTIVE, STATUS_PENDING, STATUS_APPROVED

# --------------------- Password Utilities ---------------------
def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    """Verify a stored password against one provided by user."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# --------------------- User Registration ---------------------
def register_user_logic(username: str, email: str, password: str, role: str):
    if not username or not email or not password:
        return False, "All fields are required!"

    password_hash = hash_password(password)
    status = STATUS_ACTIVE if role == ROLE_HOLDER else STATUS_PENDING

    try:
        with engine.begin() as conn:
            query = text(f"""
                INSERT INTO {USERS_TABLE} (username, email, password_hash, role, status, timestamp)
                VALUES (:username, :email, :password_hash, :role, :status, now())
            """)
            conn.execute(query, {
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "role": role,
                "status": status
            })
        return True, f"Registered {role} successfully!"
    except Exception as e:
        return False, f"Registration error: {e}"


# --------------------- User Login ---------------------
def login_user_logic(username: str, password: str, role: str = None):
    """
    Login logic with optional role filtering.
    Returns: (success: bool, message: str, session_info: dict|None)
    """
    if not username or not password:
        return False, "Please enter both username and password.", None

    try:
        with engine.connect() as conn:
            query = text(f"SELECT * FROM {USERS_TABLE} WHERE username=:username")
            result = conn.execute(query, {"username": username}).mappings().first()

            if result:
                # If a role is specified, check it
                if role and result["role"] != role:
                    return False, f"User role does not match '{role}'.", None

                if verify_password(password, result["password_hash"]):
                    if result["role"] != ROLE_ADMIN and result["status"] != STATUS_APPROVED:
                        return False, f"User status is '{result['status']}'. Cannot login yet.", None

                    session_info = {
                        "user_id": result["id"],
                        "username": result["username"],
                        "user_role": result["role"]
                    }
                    return True, "Login successful!", session_info
                else:
                    return False, "Invalid password.", None
            else:
                return False, "Username not found.", None
    except Exception as e:
        return False, f"Login error: {e}", None


# --------------------- Session Reset (Logout) ---------------------
def reset_session():
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.next_survey_section = None
