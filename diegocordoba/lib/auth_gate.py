"""
PRIMEnergeia — Authentication Gate
=====================================
Simple, production-ready authentication for client dashboard access.

Uses Streamlit's built-in secrets management (works on Streamlit Cloud).
No external dependencies required.

Setup:
  1. Create .streamlit/secrets.toml with credentials (see template below)
  2. Import and call require_auth() at the top of app.py

Template for .streamlit/secrets.toml:
  [auth]
  admin_password = "<your-secure-password>"
  
  [auth.users]
  admin = {password = "<change-me>", role = "admin", name = "Admin"}
  client_demo = {password = "<change-me>", role = "viewer", name = "Demo Client"}

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import streamlit as st
import hashlib
import time


def _hash_password(password: str) -> str:
    """Simple password hashing."""
    return hashlib.sha256(password.encode()).hexdigest()


def _get_users() -> dict:
    """Get user credentials from secrets or defaults."""
    try:
        return dict(st.secrets.get("auth", {}).get("users", {}))
    except Exception:
        # No fallback credentials — secrets.toml must be configured
        return {}


def require_auth() -> bool:
    """
    Gate the entire app behind authentication.

    Call this at the top of app.py. Returns True if authenticated.
    If not authenticated, shows login form and stops execution.
    """
    # Check if already logged in
    if st.session_state.get("authenticated", False):
        return True

    # Check if auth is disabled via secrets
    try:
        if st.secrets.get("auth", {}).get("disabled", False):
            st.session_state["authenticated"] = True
            st.session_state["user_role"] = "admin"
            st.session_state["user_name"] = "Admin (Auth Disabled)"
            return True
    except Exception:
        pass

    # Show login form
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 80px auto;
        padding: 40px;
        background: linear-gradient(135deg, #0a0f1a 0%, #1a1f2e 100%);
        border-radius: 16px;
        border: 1px solid rgba(0, 209, 255, 0.2);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
    .login-title {
        text-align: center;
        color: #00d1ff;
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .login-subtitle {
        text-align: center;
        color: #94a3b8;
        font-size: 12px;
        margin-bottom: 24px;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='login-title'>PRIMEnergeia</div>", unsafe_allow_html=True)
        st.markdown("<div class='login-subtitle'>Grid Optimization Platform</div>",
                     unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            users = _get_users()

            if username in users:
                user = users[username]
                stored_pw = user.get("password", "") if isinstance(user, dict) else str(user)
                user_name = user.get("name", username) if isinstance(user, dict) else username
                user_role = user.get("role", "viewer") if isinstance(user, dict) else "viewer"

                if password == stored_pw:
                    st.session_state["authenticated"] = True
                    st.session_state["user_name"] = user_name
                    st.session_state["user_role"] = user_role
                    st.session_state["username"] = username
                    st.rerun()
                else:
                    st.error("Invalid password")
            else:
                st.error("Unknown username")

        st.caption("Contact sales@primenergeia.com for access")

    st.stop()
    return False


def logout_button():
    """Show a logout button in the sidebar."""
    if st.session_state.get("authenticated", False):
        user = st.session_state.get("user_name", "User")
        role = st.session_state.get("user_role", "viewer")

        st.sidebar.markdown(f"**{user}** ({role})")
        if st.sidebar.button("Sign Out", use_container_width=True):
            for key in ["authenticated", "user_name", "user_role", "username"]:
                st.session_state.pop(key, None)
            st.rerun()


def is_admin() -> bool:
    """Check if the current user has admin role."""
    return st.session_state.get("user_role", "viewer") == "admin"
