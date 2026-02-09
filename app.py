import streamlit as st
import os
import re
import subprocess
import base64
import shutil
import json
import bcrypt
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

# Import block system for visual editor
from block_system import (
    BlockManager, BlockType, SectionType, Block,
    parse_section_file, save_section_file,
    get_default_block_content, get_block_icon, get_block_name,
    estimate_block_height, SECTION_PALETTES
)

# ==========================================
# 1. CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    layout="wide",
    page_title="ECES Barometer Suite",
    page_icon="📊",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. AUTHENTICATION & AUDIT MODULE
# ==========================================
class AuthManager:
    """Handles user authentication and management"""

    def __init__(self, auth_dir: str):
        self.auth_dir = Path(auth_dir)
        self.users_file = self.auth_dir / "users.json"
        self._ensure_auth_dir()

    def _ensure_auth_dir(self):
        """Create auth directory and bootstrap admin user if needed"""
        self.auth_dir.mkdir(exist_ok=True)

        if not self.users_file.exists():
            # Bootstrap initial admin
            initial_data = {
                "version": "1.0",
                "users": {
                    "admin": {
                        "username": "admin",
                        "password_hash": self._hash_password("admin123"),
                        "role": "admin",
                        "created_at": datetime.utcnow().isoformat() + "Z",
                        "created_by": "system",
                        "last_login": None,
                        "is_active": True
                    }
                }
            }
            self._save_users(initial_data)

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'),
                            bcrypt.gensalt(rounds=12)).decode('utf-8')

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'),
                             password_hash.encode('utf-8'))

    def _load_users(self) -> Dict:
        """Load users from JSON file"""
        with open(self.users_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_users(self, data: Dict):
        """Save users to JSON file"""
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user data if successful"""
        users_data = self._load_users()
        user = users_data["users"].get(username)

        if user and user["is_active"] and self._verify_password(password, user["password_hash"]):
            # Update last login
            user["last_login"] = datetime.utcnow().isoformat() + "Z"
            users_data["users"][username] = user
            self._save_users(users_data)
            return user
        return None

    def create_user(self, username: str, password: str, role: str,
                   created_by: str) -> tuple:
        """Create new user (admin only)"""
        users_data = self._load_users()

        if username in users_data["users"]:
            return False, "Username already exists"

        if role not in ["admin", "user"]:
            return False, "Invalid role"

        users_data["users"][username] = {
            "username": username,
            "password_hash": self._hash_password(password),
            "role": role,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "created_by": created_by,
            "last_login": None,
            "is_active": True
        }
        self._save_users(users_data)
        return True, "User created successfully"

    def get_all_users(self) -> List[Dict]:
        """Get list of all users (for admin panel)"""
        users_data = self._load_users()
        return list(users_data["users"].values())

    def update_user_status(self, username: str, is_active: bool) -> tuple:
        """Enable/disable user account"""
        users_data = self._load_users()
        if username not in users_data["users"]:
            return False, "User not found"

        users_data["users"][username]["is_active"] = is_active
        self._save_users(users_data)
        return True, f"User {'activated' if is_active else 'deactivated'}"

    def change_password(self, username: str, new_password: str) -> tuple:
        """Change user password"""
        users_data = self._load_users()
        if username not in users_data["users"]:
            return False, "User not found"

        users_data["users"][username]["password_hash"] = self._hash_password(new_password)
        self._save_users(users_data)
        return True, "Password changed successfully"


class AuditLogger:
    """Handles activity logging"""

    def __init__(self, auth_dir: str):
        self.log_file = Path(auth_dir) / "audit_log.jsonl"

    def log(self, username: str, action: str, details: Dict = None):
        """Append log entry"""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "username": username,
            "action": action,
            "details": details or {}
        }

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def get_recent_logs(self, limit: int = 100) -> List[Dict]:
        """Get recent log entries (for admin panel)"""
        if not self.log_file.exists():
            return []

        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Get last N lines
        recent_lines = lines[-limit:] if len(lines) > limit else lines
        return [json.loads(line) for line in recent_lines if line.strip()]

# Initialize Session State for Language
if 'language' not in st.session_state:
    st.session_state['language'] = 'English'

# Define Language-Specific Logic
is_arabic = st.session_state['language'] == 'Arabic'
text_direction = "rtl" if is_arabic else "ltr"
font_family = "'Amiri', 'Arial', sans-serif" if is_arabic else "'Source Sans Pro', sans-serif"
editor_align = "right" if is_arabic else "left"

st.markdown(f"""
    <style>
    /* PROFESSIONAL BLUE CORPORATE THEME - Optimized for Performance */

    :root {{
        /* Corporate Blue Palette */
        --primary-blue: #1e3a5f;
        --secondary-blue: #2563eb;
        --accent-blue: #3b82f6;
        --light-blue: #60a5fa;

        /* Backgrounds */
        --bg-dark: #0f172a;
        --bg-primary: #1e293b;
        --bg-secondary: #334155;
        --sidebar-bg: #1e293b;
        --card-bg: #1e293b;

        /* Text */
        --text-primary: #f1f5f9;
        --text-secondary: #cbd5e1;

        /* Borders & Status */
        --border-color: #475569;
        --success: #10b981;
        --warning: #f59e0b;
        --error: #ef4444;
    }}

    /* Base Styles */
    .stApp {{
        background: var(--bg-primary);
        color: var(--text-primary);
        font-family: 'Inter', 'Source Sans Pro', sans-serif;
    }}

    h1, h2, h3, h4, h5, h6 {{
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }}

    p, label, span, div {{
        color: var(--text-primary) !important;
        line-height: 1.6;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: var(--sidebar-bg);
        border-right: 1px solid var(--border-color);
    }}

    section[data-testid="stSidebar"] > div {{
        padding-top: 1rem;
    }}

    section[data-testid="stSidebar"] h3 {{
        color: var(--accent-blue);
        font-weight: 600 !important;
        margin-bottom: 0.75rem !important;
    }}

    /* Cards - Simple & Fast */
    .css-card {{
        background: var(--card-bg);
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid var(--border-color);
        margin-bottom: 1rem;
    }}

    .css-card:hover {{
        border-color: var(--accent-blue);
    }}

    /* Text Editors */
    .stTextArea textarea {{
        background: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        font-family: {font_family} !important;
        font-size: 16px !important;
        line-height: 1.6 !important;
        direction: {text_direction} !important;
        text-align: {editor_align} !important;
        padding: 0.75rem !important;
    }}

    .stTextArea textarea:focus {{
        border-color: var(--accent-blue) !important;
        outline: none !important;
    }}

    /* Buttons */
    div.stButton > button {{
        background: var(--card-bg);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }}

    div.stButton > button:hover {{
        border-color: var(--accent-blue);
        color: var(--light-blue);
    }}

    button[kind="primary"] {{
        background: var(--secondary-blue) !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
    }}

    button[kind="primary"]:hover {{
        background: var(--accent-blue) !important;
    }}

    /* Form Elements */
    .stSelectbox > div > div,
    .stRadio > div {{
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 6px;
    }}

    /* Status Messages */
    .stSuccess {{
        background: rgba(16, 185, 129, 0.1) !important;
        border-left: 3px solid var(--success) !important;
    }}

    .stWarning {{
        background: rgba(245, 158, 11, 0.1) !important;
        border-left: 3px solid var(--warning) !important;
    }}

    .stError {{
        background: rgba(239, 68, 68, 0.1) !important;
        border-left: 3px solid var(--error) !important;
    }}

    .stInfo {{
        background: rgba(59, 130, 246, 0.1) !important;
        border-left: 3px solid var(--accent-blue) !important;
    }}

    /* PDF Viewer */
    iframe {{
        border: 1px solid var(--border-color);
        border-radius: 8px;
        background: white;
    }}

    /* Expanders */
    div[data-testid="stExpander"] {{
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        margin-bottom: 0.75rem;
    }}

    /* File Uploader */
    .stFileUploader > div {{
        background: var(--card-bg);
        border: 1px dashed var(--border-color);
        border-radius: 6px;
    }}

    /* Scrollbar */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}

    ::-webkit-scrollbar-track {{
        background: var(--bg-primary);
    }}

    ::-webkit-scrollbar-thumb {{
        background: var(--border-color);
        border-radius: 4px;
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: var(--accent-blue);
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. FILE SYSTEM & MAPPING LOGIC
# ==========================================
BASE_DIR = os.getcwd()
IMAGES_DIR = os.path.join(BASE_DIR, "images", "charts")
os.makedirs(IMAGES_DIR, exist_ok=True)

# Initialize authentication system
AUTH_DIR = os.path.join(BASE_DIR, ".auth")
auth_manager = AuthManager(AUTH_DIR)
audit_logger = AuditLogger(AUTH_DIR)

# ==========================================
# 3. LOGIN PAGE
# ==========================================
def show_login_page():
    """Render full-screen login page"""

    # Login page styling
    st.markdown("""
        <style>
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 2rem;
            background: var(--card-bg);
            border-radius: 12px;
            border: 1px solid var(--border-color);
        }
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .login-header h1 {
            color: var(--accent-blue);
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        .login-header p {
            color: var(--text-secondary);
            font-size: 0.9rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # Center layout
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)

        # Header
        st.markdown("""
            <div class="login-header">
                <h1>📊 ECES Barometer</h1>
                <p>Content Management System</p>
            </div>
        """, unsafe_allow_html=True)

        # Login form
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                login_btn = st.form_submit_button("Login", type="primary", use_container_width=True)

            if login_btn:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    user = auth_manager.authenticate(username, password)
                    if user:
                        # Set session state
                        st.session_state['authenticated'] = True
                        st.session_state['username'] = user['username']
                        st.session_state['role'] = user['role']

                        # Log login
                        audit_logger.log(username, "login", {"success": True})

                        st.success(f"Welcome, {username}!")
                        st.rerun()
                    else:
                        audit_logger.log(username, "failed_login", {"reason": "invalid_credentials"})
                        st.error("Invalid username or password")

        st.markdown('</div>', unsafe_allow_html=True)

        # Footer
        st.markdown("---")
        st.markdown("""
            <div style='text-align: center; color: var(--text-secondary); font-size: 0.8rem;'>
                Default credentials: admin / admin123<br>
                Please change password after first login
            </div>
        """, unsafe_allow_html=True)


# ==========================================
# 4. AUTHENTICATION GUARD
# ==========================================
# Check authentication before showing main app
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    show_login_page()
    st.stop()  # Prevent rendering rest of app

# User is authenticated at this point
current_user = st.session_state['username']
current_role = st.session_state['role']

# ==========================================
# FACTORY RESET SYSTEM
# ==========================================
BACKUP_DIR = os.path.join(BASE_DIR, "templates_backup")

def initialize_factory_backup():
    """Create initial backup of templates if not exists"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

        # Backup content files
        content_backup = os.path.join(BACKUP_DIR, "content")
        os.makedirs(content_backup, exist_ok=True)
        if os.path.exists(os.path.join(BASE_DIR, "content")):
            for file in os.listdir(os.path.join(BASE_DIR, "content")):
                if file.endswith(".tex"):
                    shutil.copy2(
                        os.path.join(BASE_DIR, "content", file),
                        os.path.join(content_backup, file)
                    )

        # Backup static sections
        static_backup = os.path.join(BACKUP_DIR, "static_sections")
        os.makedirs(static_backup, exist_ok=True)
        if os.path.exists(os.path.join(BASE_DIR, "static_sections")):
            for file in os.listdir(os.path.join(BASE_DIR, "static_sections")):
                if file.endswith(".tex"):
                    shutil.copy2(
                        os.path.join(BASE_DIR, "static_sections", file),
                        os.path.join(static_backup, file)
                    )

        # Backup config files
        for config_file in ["config.tex", "config_ar.tex"]:
            if os.path.exists(os.path.join(BASE_DIR, config_file)):
                shutil.copy2(
                    os.path.join(BASE_DIR, config_file),
                    os.path.join(BACKUP_DIR, config_file)
                )

        return True
    return False

def factory_reset(target="all"):
    """
    Restore files from factory backup

    Args:
        target: "all" or specific filename
    """
    if not os.path.exists(BACKUP_DIR):
        return False, "No factory backup found. Cannot reset."

    try:
        if target == "all":
            # Reset all content files
            backup_content = os.path.join(BACKUP_DIR, "content")
            if os.path.exists(backup_content):
                for file in os.listdir(backup_content):
                    shutil.copy2(
                        os.path.join(backup_content, file),
                        os.path.join(BASE_DIR, "content", file)
                    )

            # Reset all static sections
            backup_static = os.path.join(BACKUP_DIR, "static_sections")
            if os.path.exists(backup_static):
                for file in os.listdir(backup_static):
                    shutil.copy2(
                        os.path.join(backup_static, file),
                        os.path.join(BASE_DIR, "static_sections", file)
                    )

            # Reset config files
            for config_file in ["config.tex", "config_ar.tex"]:
                if os.path.exists(os.path.join(BACKUP_DIR, config_file)):
                    shutil.copy2(
                        os.path.join(BACKUP_DIR, config_file),
                        os.path.join(BASE_DIR, config_file)
                    )

            # Log the reset
            audit_logger.log(
                st.session_state.get('username', 'unknown'),
                "factory_reset",
                {
                    "target": target,
                    "language": st.session_state.get('language', 'Unknown')
                }
            )
            return True, "All files restored to factory state"

        else:
            # Reset specific file
            # Determine source path
            if os.path.exists(os.path.join(BACKUP_DIR, "content", target)):
                src = os.path.join(BACKUP_DIR, "content", target)
                dst = os.path.join(BASE_DIR, "content", target)
            elif os.path.exists(os.path.join(BACKUP_DIR, "static_sections", target)):
                src = os.path.join(BACKUP_DIR, "static_sections", target)
                dst = os.path.join(BASE_DIR, "static_sections", target)
            else:
                return False, f"File {target} not found in backup"

            shutil.copy2(src, dst)
            # Log the reset
            audit_logger.log(
                st.session_state.get('username', 'unknown'),
                "factory_reset",
                {
                    "target": target,
                    "language": st.session_state.get('language', 'Unknown')
                }
            )
            return True, f"Restored {target}"

    except Exception as e:
        return False, f"Reset failed: {str(e)}"

# Initialize backup on startup
initialize_factory_backup()

# --- DYNAMIC PROJECT STRUCTURE ---
# This maps sections to specific files based on the language
PROJECT_CONFIG = {
    "English": {
        "main": "main.tex",
        "config": "config.tex",
        "preamble": "preamble.tex",
        "sections": {
            "Executive Summary": "content/01_exec_summary.tex",
            "Macroeconomic Overview": "content/02_macro_overview.tex",
            "Analysis: Overall Index": "content/03_analysis_overall.tex",
            "Analysis: Constraints": "content/04_constraints.tex",
            "Analysis: Sub-Indices": "content/05_subindices.tex",
            "Appendix: Data Tables": "content/06_tables.tex",
            "Cover Page Text": "static_sections/00_cover.tex",
            "About ECES": "static_sections/00_about_eces.tex",
            "Methodology": "static_sections/00_methodology.tex",
        }
    },
    "Arabic": {
        "main": "main_ar.tex",
        "config": "config_ar.tex",
        "preamble": "preamble_ar.tex",
        "sections": {
            "Executive Summary": "content/01_exec_summary_ar.tex",
            "Macroeconomic Overview": "content/02_macro_overview_ar.tex",
            "Analysis: Overall Index": "content/03_analysis_overall_ar.tex",
            "Analysis: Constraints": "content/04_constraints_ar.tex",
            "Analysis: Sub-Indices": "content/05_subindices_ar.tex",
            "Appendix: Data Tables": "content/06_tables_ar.tex",
            "Cover Page Text": "static_sections/00_cover_ar.tex",
            "About ECES": "static_sections/00_about_eces_ar.tex",
            "Methodology": "static_sections/00_methodology_ar.tex",
        }
    }
}

# Get current config based on selection
active_config = PROJECT_CONFIG[st.session_state['language']]
SECTION_MAP = active_config["sections"]
CONFIG_FILE = os.path.join(BASE_DIR, active_config["config"])
MAIN_FILE = os.path.join(BASE_DIR, active_config["main"])
PREAMBLE_FILE = active_config["preamble"]

def load_file(filepath):
    if not os.path.exists(filepath): return ""
    with open(filepath, 'r', encoding='utf-8') as f: return f.read()

def save_file(filepath, content):
    """Save file with audit logging"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # Log the save operation
    audit_logger.log(
        st.session_state.get('username', 'unknown'),
        "save_file",
        {
            "filepath": os.path.relpath(filepath, BASE_DIR),
            "language": st.session_state.get('language', 'Unknown'),
            "size_bytes": len(content)
        }
    )

def display_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        st.error("Preview file not found.")
        return

    # Read PDF file
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Try iframe method first (works on some browsers)
    try:
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}#toolbar=0&navpanes=0&scrollbar=0" width="100%" height="800" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except:
        pass

    # Always provide download button as fallback
    st.download_button(
        label="📥 Download Preview PDF",
        data=pdf_bytes,
        file_name=os.path.basename(pdf_path),
        mime="application/pdf",
        use_container_width=True
    )

# ==========================================
# 3. COMPILER & TOOLS
# ==========================================
def parse_latex_log(log_path):
    """Parse LaTeX log file for detailed error information"""
    if not os.path.exists(log_path):
        return "Log file not found."

    errors = []
    warnings = []

    try:
        with open(log_path, "r", encoding="latin-1", errors='ignore') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i]

            # Critical errors starting with !
            if line.startswith("!"):
                context = lines[i:i+5]  # Get more context
                error_block = "".join(context).strip()
                errors.append(f"❌ ERROR:\n{error_block}")
                i += 5
                continue

            # Missing file errors
            if "File" in line and "not found" in line:
                errors.append(f"📁 MISSING FILE:\n{line.strip()}")

            # Font errors
            if "Font" in line and ("not found" in line or "undefined" in line.lower()):
                errors.append(f"🔤 FONT ERROR:\n{line.strip()}")

            # Undefined control sequence
            if "Undefined control sequence" in line:
                context = lines[i:i+3]
                errors.append(f"⚠️ UNDEFINED COMMAND:\n{''.join(context).strip()}")
                i += 3
                continue

            # Missing package
            if "LaTeX Error: File" in line and ".sty" in line:
                errors.append(f"📦 MISSING PACKAGE:\n{line.strip()}")

            # Overfull/underfull boxes (warnings)
            if "Overfull" in line or "Underfull" in line:
                warnings.append(line.strip())

            i += 1

        # Build result
        result_parts = []

        if errors:
            result_parts.append("=== ERRORS ===\n" + "\n\n".join(errors))

        if warnings and len(warnings) <= 10:  # Only show if not too many
            result_parts.append("=== WARNINGS ===\n" + "\n".join(warnings[:5]))

        if result_parts:
            return "\n\n".join(result_parts)
        else:
            return "Unknown error. Check LaTeX syntax and file paths."

    except Exception as e:
        return f"Could not parse log: {str(e)}"

def render_toolbar():
    # Toolbar text logic adjusted for current language if needed (optional)
    st.markdown("##### 🛠️ Quick Tools")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    def show_hint(msg, code):
        st.toast(msg, icon="💡")
        st.sidebar.code(code, language="latex")
        st.sidebar.info("Code copied to sidebar! ↖️")

    with col1:
        if st.button("Bold", width='stretch'): show_hint("Bold Text", r"\textbf{ Text }")
    with col2:
        if st.button("Italic", width='stretch'): show_hint("Italic Text", r"\textit{ Text }")
    with col3:
        if st.button("% Sign", width='stretch'): show_hint("Escape %", r"\%")
    with col4:
        if st.button("List", width='stretch'):
            code = r"""\begin{itemize}
    \item Point 1
    \item Point 2
\end{itemize}"""
            show_hint("Bulleted List", code)
    with col5:
        if st.button("New Line", width='stretch'): show_hint("Line Break", r"\\")

def generate_preview(content_latex):
    """
    Generates a standalone PDF snippet. 
    Crucially, uses the active language's preamble to ensure fonts/RTL work.
    """
    preview_filename = "preview_temp"
    preview_tex = f"{preview_filename}.tex"
    preview_pdf = f"{preview_filename}.pdf"
    preview_log = f"{preview_filename}.log"
    
    if os.path.exists(preview_pdf): os.remove(preview_pdf)
    if os.path.exists(preview_log): os.remove(preview_log)
    
    # Construct LaTeX wrapper
    # We include the specific preamble (English or Arabic) and the matching config
    full_latex_code = f"\\documentclass[a4paper,12pt]{{article}}\n"
    full_latex_code += f"\\input{{{PREAMBLE_FILE}}}\n"
    full_latex_code += f"\\input{{{active_config['config']}}}\n"
    full_latex_code += "\\begin{document}\n"
    
    # If Arabic, ensure the environment is set if not handled by preamble globally
    # Ideally preamble_ar.tex has \usepackage{polyglossia} \setmainlanguage{arabic}
    full_latex_code += content_latex
    full_latex_code += "\n\\end{document}"
    
    with open(preview_tex, "w", encoding="utf-8") as f:
        f.write(full_latex_code)
        
    try:
        # ALWAYS use xelatex for best compatibility (required for Arabic, fine for English)
        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", preview_tex],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if os.path.exists(preview_pdf):
            # Log successful preview
            audit_logger.log(
                st.session_state.get('username', 'unknown'),
                "generate_preview",
                {
                    "language": st.session_state.get('language', 'Unknown'),
                    "success": True
                }
            )
            return preview_pdf, None
        else:
            error_msg = parse_latex_log(os.path.join(BASE_DIR, preview_log))
            # Log failed preview
            audit_logger.log(
                st.session_state.get('username', 'unknown'),
                "generate_preview",
                {
                    "language": st.session_state.get('language', 'Unknown'),
                    "success": False,
                    "error": error_msg[:200] if error_msg else "Unknown error"
                }
            )
            return None, error_msg
    except Exception as e:
        # Log exception
        audit_logger.log(
            st.session_state.get('username', 'unknown'),
            "generate_preview",
            {
                "language": st.session_state.get('language', 'Unknown'),
                "success": False,
                "error": str(e)[:200]
            }
        )
        return None, str(e)

def parse_latex_blocks(content):
    lines = content.splitlines()
    blocks = []
    current_chunk = []
    current_type = None 
    latex_cmd_pattern = re.compile(r'^(\\|\%|\{|}|\s*\\)')

    for line in lines:
        is_code = bool(latex_cmd_pattern.match(line.strip())) or line.strip() == ""
        line_type = 'code' if is_code else 'text'
        if current_type is None: current_type = line_type
        
        if line_type != current_type:
            blocks.append({'type': current_type, 'content': "\n".join(current_chunk)})
            current_chunk = [line]
            current_type = line_type
        else:
            current_chunk.append(line)
    if current_chunk:
        blocks.append({'type': current_type, 'content': "\n".join(current_chunk)})
    return blocks

def reconstruct_latex(blocks):
    return "\n".join([b['content'] for b in blocks])


# ==========================================
# BLOCK EDITOR UI FUNCTIONS
# ==========================================

# Section type mapping
SECTION_TYPE_MAP = {
    "Executive Summary": SectionType.EXECUTIVE_SUMMARY,
    "Macroeconomic Overview": SectionType.MACRO_OVERVIEW,
    "Analysis: Overall Index": SectionType.ANALYSIS_OVERALL,
    "Analysis: Constraints": SectionType.CONSTRAINTS,
    "Analysis: Sub-Indices": SectionType.SUBINDICES,
    "Appendix: Data Tables": SectionType.TABLES,
}


def render_block_editor(section_name: str, section_type: SectionType, filepath: str):
    """
    Render visual block editor for a section
    """
    is_arabic = st.session_state.get('language') == 'Arabic'

    # Initialize session state for this section
    editor_key = f"block_editor_{section_name}_{st.session_state.get('language', 'en')}"

    if editor_key not in st.session_state:
        try:
            manager = parse_section_file(filepath, section_type)
            st.session_state[editor_key] = {
                "manager": manager,
                "selected_block": None,
            }
        except Exception as e:
            st.error(f"Error parsing LaTeX file: {str(e)}")
            st.code(str(e))
            return

    editor_state = st.session_state[editor_key]
    manager: BlockManager = editor_state["manager"]

    # ===== HEADER (compact - save/reload buttons are in parent) =====
    col_info, col_stats = st.columns([2, 1])

    with col_info:
        st.caption(f"📄 {os.path.basename(filepath)}")

    with col_stats:
        block_count = len(manager.blocks)
        page_breaks = manager.get_page_breaks()
        st.caption(f"{block_count} {'كتل' if is_arabic else 'blocks'} | ~{len(page_breaks)+1} {'صفحات' if is_arabic else 'pages'}")

    # ===== MAIN LAYOUT =====
    col_blocks, col_palette = st.columns([3, 1])

    # ===== BLOCK PALETTE (Right side) =====
    with col_palette:
        st.markdown("### " + ("➕ إضافة كتلة" if is_arabic else "➕ Add Block"))

        available_blocks = SECTION_PALETTES.get(section_type, list(BlockType))

        # Core blocks
        core_types = [BlockType.PARAGRAPH, BlockType.TITLE, BlockType.CHART,
                      BlockType.BULLET_LIST, BlockType.TEXT_CHART_ROW, BlockType.SPACER]
        core_blocks = [b for b in available_blocks if b in core_types]

        # Special blocks
        special_blocks = [b for b in available_blocks if b not in core_types]

        st.markdown("**" + ("الكتل الأساسية" if is_arabic else "Core Blocks") + ":**")
        for block_type in core_blocks:
            icon = get_block_icon(block_type)
            name = get_block_name(block_type)

            if st.button(f"{icon} {name}", use_container_width=True,
                        key=f"add_{block_type.value}_{section_name}"):
                content, metadata = get_default_block_content(block_type)
                manager.add_block(block_type, content, metadata)
                st.rerun()

        if special_blocks:
            st.markdown("---")
            st.markdown("**" + ("كتل خاصة" if is_arabic else "Special Blocks") + ":**")
            for block_type in special_blocks:
                icon = get_block_icon(block_type)
                name = get_block_name(block_type)

                if st.button(f"{icon} {name}", use_container_width=True,
                            key=f"add_{block_type.value}_{section_name}"):
                    content, metadata = get_default_block_content(block_type)
                    manager.add_block(block_type, content, metadata)
                    st.rerun()

        # Page info
        st.markdown("---")
        page_breaks = manager.get_page_breaks()
        total_pages = len(page_breaks) + 1
        total_height = manager.get_total_height()
        st.info(f"📄 ~{total_pages} " + ("صفحات" if is_arabic else "pages") + f"\n📏 {total_height}px")

    # ===== BLOCK LIST (Left side) =====
    with col_blocks:
        st.markdown("### " + ("📚 الكتل" if is_arabic else "📚 Content Blocks"))

        if not manager.blocks:
            st.info("" + ("لا توجد كتل. أضف كتلة من اللوحة الجانبية." if is_arabic else "No blocks yet. Add blocks from the palette."))
        else:
            page_breaks = manager.get_page_breaks()
            current_page = 1

            for idx, block in enumerate(manager.blocks):
                # Page break indicator
                if idx in page_breaks:
                    st.markdown(f"---\n**📄 " + ("صفحة" if is_arabic else "Page") + f" {current_page}** " + ("تنتهي" if is_arabic else "ends") + f" | **" + ("صفحة" if is_arabic else "Page") + f" {current_page + 1}** " + ("تبدأ" if is_arabic else "starts") + "\n---")
                    current_page += 1

                # Render block card
                render_block_card(manager, idx, block, section_name, is_arabic)


def render_block_card(manager: BlockManager, idx: int, block: Block, section_name: str, is_arabic: bool):
    """Render a single block as an editable card"""

    icon = get_block_icon(block.type)
    name = get_block_name(block.type)

    with st.container(border=True):
        # Header row
        col_info, col_actions = st.columns([3, 2])

        with col_info:
            st.markdown(f"**{icon} {name}** | ~{block.estimated_height}px")

        with col_actions:
            col_up, col_down, col_del = st.columns(3)

            with col_up:
                if idx > 0:
                    if st.button("↑", key=f"up_{idx}_{section_name}", use_container_width=True):
                        manager.move_block(idx, idx - 1)
                        st.rerun()

            with col_down:
                if idx < len(manager.blocks) - 1:
                    if st.button("↓", key=f"down_{idx}_{section_name}", use_container_width=True):
                        manager.move_block(idx, idx + 1)
                        st.rerun()

            with col_del:
                if st.button("🗑️", key=f"del_{idx}_{section_name}", use_container_width=True):
                    manager.remove_block(idx)
                    st.rerun()

        # Block content editor (expandable)
        with st.expander("✏️ " + ("تعديل" if is_arabic else "Edit"), expanded=False):
            render_block_editor_form(manager, idx, block, section_name, is_arabic)


def render_block_editor_form(manager: BlockManager, idx: int, block: Block, section_name: str, is_arabic: bool):
    """Render edit form for a specific block type"""

    if block.type == BlockType.PARAGRAPH:
        new_content = st.text_area(
            "المحتوى" if is_arabic else "Content",
            value=block.content,
            height=150,
            key=f"edit_para_{idx}_{section_name}"
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            font_size = st.number_input(
                "حجم الخط" if is_arabic else "Font Size",
                value=block.metadata.get("font_size", 10),
                min_value=8, max_value=20,
                key=f"fs_{idx}_{section_name}"
            )
        with col2:
            bold = st.checkbox(
                "عريض" if is_arabic else "Bold",
                value=block.metadata.get("bold", False),
                key=f"bold_{idx}_{section_name}"
            )
        with col3:
            color_options = ["black", "ecesteal", "textblue", "textpurple", "textgreen"]
            current_color = block.metadata.get("color", "black")
            color_idx = color_options.index(current_color) if current_color in color_options else 0
            color = st.selectbox(
                "اللون" if is_arabic else "Color",
                color_options,
                index=color_idx,
                key=f"color_{idx}_{section_name}"
            )

        if st.button("💾 " + ("تحديث" if is_arabic else "Update"), key=f"update_para_{idx}_{section_name}", type="primary"):
            manager.update_block(idx, content=new_content, metadata={"font_size": font_size, "bold": bold, "color": color})
            st.success("✅")
            st.rerun()

    elif block.type == BlockType.TITLE:
        new_content = st.text_input(
            "نص العنوان" if is_arabic else "Title Text",
            value=block.content,
            key=f"edit_title_{idx}_{section_name}"
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            level = st.selectbox(
                "المستوى" if is_arabic else "Level",
                [1, 2, 3],
                index=[1, 2, 3].index(block.metadata.get("level", 1)),
                key=f"lvl_{idx}_{section_name}"
            )
        with col2:
            color_options = ["ecestitle", "textblue", "textpurple", "textgreen", "black"]
            current_color = block.metadata.get("color", "ecestitle")
            color_idx = color_options.index(current_color) if current_color in color_options else 0
            color = st.selectbox(
                "اللون" if is_arabic else "Color",
                color_options,
                index=color_idx,
                key=f"tcolor_{idx}_{section_name}"
            )
        with col3:
            underline = st.checkbox(
                "تسطير" if is_arabic else "Underline",
                value=block.metadata.get("underline", False),
                key=f"uline_{idx}_{section_name}"
            )

        if st.button("💾 " + ("تحديث" if is_arabic else "Update"), key=f"update_title_{idx}_{section_name}", type="primary"):
            manager.update_block(idx, content=new_content, metadata={"level": level, "color": color, "underline": underline})
            st.success("✅")
            st.rerun()

    elif block.type == BlockType.CHART:
        st.markdown("**" + ("الرسم الحالي" if is_arabic else "Current Chart") + ":**")

        # Show current chart if exists
        chart_path = os.path.join(IMAGES_DIR, block.content)
        if os.path.exists(chart_path):
            st.image(chart_path, width=250)
        else:
            st.warning(f"Image not found: {block.content}")

        # Chart selector
        if os.path.exists(IMAGES_DIR):
            charts = sorted([f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            if charts:
                current_chart = block.content if block.content in charts else charts[0]
                selected_chart = st.selectbox(
                    "اختر رسم" if is_arabic else "Select Chart",
                    charts,
                    index=charts.index(current_chart) if current_chart in charts else 0,
                    key=f"chart_{idx}_{section_name}"
                )

                if st.button("💾 " + ("تحديث" if is_arabic else "Update"), key=f"update_chart_{idx}_{section_name}", type="primary"):
                    manager.update_block(idx, content=selected_chart)
                    st.success("✅")
                    st.rerun()
            else:
                st.warning("No charts found in images/charts folder")

    elif block.type == BlockType.BULLET_LIST:
        items = block.content if isinstance(block.content, list) else []

        st.markdown("**" + ("عناصر القائمة" if is_arabic else "List Items") + ":**")

        new_items = []
        for i, item in enumerate(items):
            new_item = st.text_input(
                f"Item {i+1}",
                value=item,
                key=f"item_{idx}_{i}_{section_name}",
                label_visibility="collapsed"
            )
            new_items.append(new_item)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ " + ("إضافة عنصر" if is_arabic else "Add Item"), key=f"add_item_{idx}_{section_name}"):
                new_items.append("New item")
                manager.update_block(idx, content=new_items)
                st.rerun()

        with col2:
            if st.button("💾 " + ("تحديث" if is_arabic else "Update"), key=f"update_list_{idx}_{section_name}", type="primary"):
                # Filter empty items
                new_items = [item for item in new_items if item.strip()]
                manager.update_block(idx, content=new_items)
                st.success("✅")
                st.rerun()

    elif block.type == BlockType.TEXT_CHART_ROW:
        content = block.content if isinstance(block.content, dict) else {"text": "", "chart_file": "ch1.png"}

        new_text = st.text_area(
            "النص" if is_arabic else "Text Content",
            value=content.get("text", ""),
            height=100,
            key=f"tcr_text_{idx}_{section_name}"
        )

        # Chart selector
        if os.path.exists(IMAGES_DIR):
            charts = sorted([f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            if charts:
                current_chart = content.get("chart_file", "ch1.png")
                new_chart = st.selectbox(
                    "الرسم" if is_arabic else "Chart",
                    charts,
                    index=charts.index(current_chart) if current_chart in charts else 0,
                    key=f"tcr_chart_{idx}_{section_name}"
                )

                if st.button("💾 " + ("تحديث" if is_arabic else "Update"), key=f"update_tcr_{idx}_{section_name}", type="primary"):
                    manager.update_block(idx, content={"text": new_text, "chart_file": new_chart})
                    st.success("✅")
                    st.rerun()

    elif block.type == BlockType.HIGHLIGHT_BOX:
        sections = block.content if isinstance(block.content, list) else []

        st.markdown("**" + ("أقسام الصندوق" if is_arabic else "Box Sections") + ":**")

        new_sections = []
        for i, section in enumerate(sections):
            st.markdown(f"--- Section {i+1} ---")

            title = st.text_input(
                "العنوان" if is_arabic else "Title",
                value=section.get("title", ""),
                key=f"hb_title_{idx}_{i}_{section_name}"
            )

            color_options = ["textblue", "textpurple", "textgreen", "black"]
            current_color = section.get("color", "textblue")
            color = st.selectbox(
                "اللون" if is_arabic else "Color",
                color_options,
                index=color_options.index(current_color) if current_color in color_options else 0,
                key=f"hb_color_{idx}_{i}_{section_name}"
            )

            content = st.text_area(
                "المحتوى" if is_arabic else "Content",
                value=section.get("content", ""),
                height=80,
                key=f"hb_content_{idx}_{i}_{section_name}"
            )

            new_sections.append({"title": title, "color": color, "content": content})

        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ " + ("إضافة قسم" if is_arabic else "Add Section"), key=f"add_hb_section_{idx}_{section_name}"):
                new_sections.append({"title": "New Section:", "color": "textblue", "content": "-- Content"})
                manager.update_block(idx, content=new_sections)
                st.rerun()

        with col2:
            if st.button("💾 " + ("تحديث" if is_arabic else "Update"), key=f"update_hb_{idx}_{section_name}", type="primary"):
                manager.update_block(idx, content=new_sections)
                st.success("✅")
                st.rerun()

    elif block.type == BlockType.PAGE_SETUP:
        content = block.content if isinstance(block.content, dict) else {}

        # Background selector
        bg_options = ["exc_bg.png", "con_bg.png", "mc_bg.png"]
        current_bg = content.get("background", "con_bg.png")
        background = st.selectbox(
            "الخلفية" if is_arabic else "Background",
            bg_options,
            index=bg_options.index(current_bg) if current_bg in bg_options else 1,
            key=f"ps_bg_{idx}_{section_name}"
        )

        page_number = st.number_input(
            "رقم الصفحة" if is_arabic else "Page Number",
            value=content.get("page_number", 1),
            min_value=1,
            key=f"ps_page_{idx}_{section_name}"
        )

        # Geometry
        st.markdown("**" + ("الهوامش" if is_arabic else "Margins") + ":**")
        geometry = content.get("geometry", {"left": "2cm", "right": "1.5cm", "top": "3cm", "bottom": "2.5cm"})

        col1, col2 = st.columns(2)
        with col1:
            left = st.text_input("Left", value=geometry.get("left", "2cm"), key=f"ps_left_{idx}_{section_name}")
            top = st.text_input("Top", value=geometry.get("top", "3cm"), key=f"ps_top_{idx}_{section_name}")
        with col2:
            right = st.text_input("Right", value=geometry.get("right", "1.5cm"), key=f"ps_right_{idx}_{section_name}")
            bottom = st.text_input("Bottom", value=geometry.get("bottom", "2.5cm"), key=f"ps_bottom_{idx}_{section_name}")

        if st.button("💾 " + ("تحديث" if is_arabic else "Update"), key=f"update_ps_{idx}_{section_name}", type="primary"):
            manager.update_block(idx, content={
                "background": background,
                "page_number": page_number,
                "geometry": {"left": left, "right": right, "top": top, "bottom": bottom}
            })
            st.success("✅")
            st.rerun()

    elif block.type == BlockType.SUBHEADER_LEGEND:
        content = block.content if isinstance(block.content, dict) else {"text": "", "legend_image": "arrow.png"}

        new_text = st.text_area(
            "النص" if is_arabic else "Text",
            value=content.get("text", ""),
            height=60,
            key=f"shl_text_{idx}_{section_name}"
        )

        legend_image = st.text_input(
            "صورة الدليل" if is_arabic else "Legend Image",
            value=content.get("legend_image", "arrow.png"),
            key=f"shl_img_{idx}_{section_name}"
        )

        if st.button("💾 " + ("تحديث" if is_arabic else "Update"), key=f"update_shl_{idx}_{section_name}", type="primary"):
            manager.update_block(idx, content={"text": new_text, "legend_image": legend_image})
            st.success("✅")
            st.rerun()

    elif block.type == BlockType.SPACER:
        size_options = ["0.5em", "1em", "1.5em", "2em"]
        current_size = block.metadata.get("size", "1em")
        size = st.selectbox(
            "الحجم" if is_arabic else "Size",
            size_options,
            index=size_options.index(current_size) if current_size in size_options else 1,
            key=f"spacer_size_{idx}_{section_name}"
        )

        if st.button("💾 " + ("تحديث" if is_arabic else "Update"), key=f"update_spacer_{idx}_{section_name}", type="primary"):
            manager.update_block(idx, metadata={"size": size})
            st.success("✅")
            st.rerun()

    else:
        st.info("Editor not available for this block type")


# ==========================================
# 4. SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    # User Info Section
    st.markdown(f"""
        <div style='background: var(--card-bg); padding: 1rem; border-radius: 8px;
                    border: 1px solid var(--border-color); margin-bottom: 1rem;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <div style='color: var(--accent-blue); font-weight: 600;'>
                        👤 {current_user}
                    </div>
                    <div style='color: var(--text-secondary); font-size: 0.8rem;'>
                        {current_role.upper()}
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Logout Button
    if st.button("🚪 Logout", use_container_width=True):
        audit_logger.log(current_user, "logout", {})
        # Clear session state
        st.session_state['authenticated'] = False
        st.session_state['username'] = None
        st.session_state['role'] = None
        st.rerun()

    st.markdown("---")

    st.image("https://via.placeholder.com/200x60/262730/4facfe?text=ECES+Barometer", width='stretch')

    st.markdown("""
        <div style='text-align: center; padding: 0.5rem 0; margin-bottom: 0.5rem;'>
            <h3 style='color: #3b82f6; font-weight: 600; font-size: 1.5rem; margin: 0;'>
                ECES Barometer
            </h3>
        </div>
    """, unsafe_allow_html=True)

    # --- LANGUAGE TOGGLE ---
    st.markdown("### 🌍 Language / اللغة")
    selected_lang = st.radio(
        "Select Language",
        ["English", "Arabic"],
        index=0 if st.session_state['language'] == 'English' else 1,
        label_visibility="collapsed",
        horizontal=True
    )
    
    # Update state and rerun if changed to load correct file maps
    if selected_lang != st.session_state['language']:
        st.session_state['language'] = selected_lang
        st.session_state['pdf_ready'] = False # Reset PDF status
        st.rerun()

    st.markdown("---")
    st.markdown("### Control Center")

    # Base navigation options
    base_nav_english = ["📝 Report Sections", "⚙️ Report Variables", "📊 Chart Manager", "🚀 Finalize & Publish"]
    base_nav_arabic = ["📝 أقسام التقرير", "⚙️ متغيرات التقرير", "📊 إدارة الرسوم البيانية", "🚀 إنهاء ونشر"]

    # Add admin panel for admin users
    if current_role == "admin":
        nav_options = {
            "English": base_nav_english + ["👥 User Management"],
            "Arabic": base_nav_arabic + ["👥 إدارة المستخدمين"]
        }
    else:
        nav_options = {
            "English": base_nav_english,
            "Arabic": base_nav_arabic
        }
    
    # Map Arabic selections back to English logic keys
    nav_map = dict(zip(nav_options["Arabic"], nav_options["English"]))

    # Store navigation options for use outside sidebar
    st.session_state['nav_options'] = nav_options
    st.session_state['nav_map'] = nav_map

    st.markdown("---")
    if is_arabic:
        st.info("💡 **تلميح:** 'المعاينة' تقوم بتجميع القسم الحالي فقط.")
    else:
        st.info("💡 **Tip:** 'Preview' compiles the current section only.")

    st.markdown("---")
    st.markdown("### 🔄 Factory Reset")

    reset_help = "استعادة الملفات الأصلية" if is_arabic else "Restore original templates"

    with st.expander(reset_help, expanded=False):
        col_reset1, col_reset2 = st.columns(2)

        with col_reset1:
            if st.button("Reset Current File", use_container_width=True, key="reset_current"):
                if 'current_section_name' in locals():
                    filename = os.path.basename(SECTION_MAP.get(st.session_state.get('current_section_name', '')))
                    success, msg = factory_reset(target=filename)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.info("Open a section first to reset it.")

        with col_reset2:
            if st.button("Reset All", use_container_width=True, type="primary", key="reset_all_trigger"):
                # Confirmation via session state
                st.session_state['confirm_reset_all'] = True
                st.rerun()

        # Confirmation dialog
        if st.session_state.get('confirm_reset_all'):
            st.warning("⚠️ This will restore ALL files to original state!")
            col_yes, col_no = st.columns(2)

            with col_yes:
                if st.button("✓ Confirm", use_container_width=True, key="confirm_yes"):
                    success, msg = factory_reset(target="all")
                    st.session_state['confirm_reset_all'] = False
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

            with col_no:
                if st.button("✗ Cancel", use_container_width=True, key="confirm_no"):
                    st.session_state['confirm_reset_all'] = False
                    st.rerun()

    # Password Change Section
    st.markdown("---")
    st.markdown("### 🔑 Change Password" if not is_arabic else "### 🔑 تغيير كلمة المرور")

    with st.expander("Update your password" if not is_arabic else "تحديث كلمة المرور", expanded=False):
        with st.form("change_password_form"):
            current_pw = st.text_input("Current Password" if not is_arabic else "كلمة المرور الحالية", type="password")
            new_pw = st.text_input("New Password" if not is_arabic else "كلمة المرور الجديدة", type="password")
            confirm_pw = st.text_input("Confirm New Password" if not is_arabic else "تأكيد كلمة المرور", type="password")

            if st.form_submit_button("Update Password" if not is_arabic else "تحديث كلمة المرور", use_container_width=True):
                # Verify current password
                user = auth_manager.authenticate(current_user, current_pw)
                if not user:
                    st.error("Current password is incorrect" if not is_arabic else "كلمة المرور الحالية غير صحيحة")
                elif len(new_pw) < 8:
                    st.error("New password must be at least 8 characters" if not is_arabic else "كلمة المرور الجديدة يجب أن تكون 8 أحرف على الأقل")
                elif new_pw != confirm_pw:
                    st.error("New passwords do not match" if not is_arabic else "كلمة المرور الجديدة غير متطابقة")
                else:
                    success, msg = auth_manager.change_password(current_user, new_pw)
                    if success:
                        audit_logger.log(current_user, "change_password", {})
                        st.success("Password updated successfully!" if not is_arabic else "تم تحديث كلمة المرور بنجاح!")
                    else:
                        st.error(msg)

# ==========================================
# HORIZONTAL NAVIGATION (MAIN CONTENT)
# ==========================================
nav_options = st.session_state.get('nav_options', {
    "English": ["📝 Report Sections", "⚙️ Report Variables", "📊 Chart Manager", "🚀 Finalize & Publish"],
    "Arabic": ["📝 أقسام التقرير", "⚙️ متغيرات التقرير", "📊 إدارة الرسوم البيانية", "🚀 إنهاء ونشر"]
})
nav_map = st.session_state.get('nav_map', {})

# Add admin panel if user is admin
if current_role == "admin":
    if "👥 User Management" not in nav_options["English"]:
        nav_options["English"].append("👥 User Management")
        nav_options["Arabic"].append("👥 إدارة المستخدمين")
        nav_map["👥 إدارة المستخدمين"] = "👥 User Management"

# Initialize selected navigation
if 'selected_nav' not in st.session_state:
    st.session_state['selected_nav'] = nav_options[st.session_state['language']][0]

# Horizontal navigation tabs
nav_cols = st.columns(len(nav_options[st.session_state['language']]))
for i, (col, nav_item) in enumerate(zip(nav_cols, nav_options[st.session_state['language']])):
    with col:
        is_selected = st.session_state['selected_nav'] == nav_item
        btn_type = "primary" if is_selected else "secondary"
        if st.button(nav_item, use_container_width=True, type=btn_type, key=f"nav_{i}"):
            st.session_state['selected_nav'] = nav_item
            st.rerun()

# Get the normalized view name
selected_view_display = st.session_state['selected_nav']
selected_view = nav_map.get(selected_view_display, selected_view_display)

st.markdown("---")

# ==========================================
# 5. VIEW: REPORT SECTIONS
# ==========================================
if selected_view == "📝 Report Sections":
    header_text = "📝 محرر المحتوى والمعاينة" if is_arabic else "📝 Content Editor & Preview"
    st.markdown(f"## {header_text}")

    # Initialize editor mode in session state
    if 'editor_mode' not in st.session_state:
        st.session_state['editor_mode'] = 'block'  # Default to block editor

    # Section Selector and Editor Mode Toggle
    col_sel, col_mode, col_info = st.columns([2, 1, 2])

    with col_sel:
        lbl = "اختر القسم" if is_arabic else "Select Section"
        section_keys = list(SECTION_MAP.keys())
        current_section_name = st.selectbox(lbl, section_keys)

    with col_mode:
        mode_lbl = "وضع المحرر" if is_arabic else "Editor Mode"
        editor_mode = st.radio(
            mode_lbl,
            ["🧱 Block", "📝 Legacy"],
            index=0 if st.session_state['editor_mode'] == 'block' else 1,
            horizontal=True,
            label_visibility="collapsed"
        )
        st.session_state['editor_mode'] = 'block' if editor_mode == "🧱 Block" else 'legacy'

    current_file_path = os.path.join(BASE_DIR, SECTION_MAP[current_section_name])

    # Check if file exists, if not create empty
    if not os.path.exists(current_file_path):
        save_file(current_file_path, "% New Section")

    with col_info:
        st.markdown(f"""
        <div style="padding-top: 5px;">
            <span style="background:#262730; padding: 5px 10px; border-radius:5px; border:1px solid #383b42;">
                📄 <code>{os.path.basename(current_file_path)}</code> | {st.session_state['language']}
            </span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ===== BLOCK EDITOR MODE =====
    if st.session_state['editor_mode'] == 'block':
        # Get section type
        section_type = SECTION_TYPE_MAP.get(current_section_name, SectionType.ANALYSIS_OVERALL)
        editor_key = f"block_editor_{current_section_name}_{st.session_state.get('language', 'en')}"

        # Split view: Editor left, Preview right
        col_editor, col_preview = st.columns([1, 1])

        with col_editor:
            st.markdown("### " + ("📝 محرر الكتل" if is_arabic else "📝 Block Editor"))

            # Action buttons row
            col_save, col_reload = st.columns(2)
            with col_save:
                if st.button("💾 " + ("حفظ" if is_arabic else "Save"), type="primary", use_container_width=True, key=f"save_block_{current_section_name}"):
                    if editor_key in st.session_state:
                        manager = st.session_state[editor_key]["manager"]
                        latex_output = manager.generate_latex()
                        save_file(current_file_path, latex_output)
                        st.toast("✅ " + ("تم الحفظ" if is_arabic else "Saved!"))
                        audit_logger.log(
                            st.session_state.get('username', 'unknown'),
                            "save_file",
                            {"filepath": os.path.relpath(current_file_path, BASE_DIR), "editor": "block"}
                        )

            with col_reload:
                if st.button("🔄 " + ("إعادة تحميل" if is_arabic else "Reload"), use_container_width=True, key=f"reload_block_{current_section_name}"):
                    # Force reload from file
                    if editor_key in st.session_state:
                        del st.session_state[editor_key]
                    st.rerun()

            # Render block editor (without its own save button)
            render_block_editor(current_section_name, section_type, current_file_path)

        with col_preview:
            st.markdown("### " + ("👁️ معاينة" if is_arabic else "👁️ Preview"))

            btn_prev_txt = "👁️ Generate Preview" if not is_arabic else "👁️ إنشاء معاينة"
            if st.button(btn_prev_txt, type="primary", use_container_width=True, key=f"preview_block_{current_section_name}"):
                # Get current content from the block manager
                if editor_key in st.session_state:
                    manager = st.session_state[editor_key]["manager"]
                    current_draft_latex = manager.generate_latex()

                    status_txt = "جاري تجميع ملف المعاينة..." if is_arabic else "Compiling Preview..."
                    with st.status(status_txt, expanded=True) as status:
                        pdf_path, error_msg = generate_preview(current_draft_latex)

                        if pdf_path and os.path.exists(pdf_path):
                            status.update(label="Ready!", state="complete", expanded=False)
                            display_pdf(pdf_path)
                        else:
                            status.update(label="Failed", state="error")
                            st.error("⚠️ LaTeX Compilation Error")
                            with st.expander("Error Details", expanded=True):
                                st.code(error_msg, language="tex")

    # ===== LEGACY EDITOR MODE =====
    else:
        raw_content = load_file(current_file_path)
        blocks = parse_latex_blocks(raw_content)

        col_editor, col_preview = st.columns([1, 1])

        # --- EDITOR ---
        with col_editor:
            st.subheader("Edit Content" if not is_arabic else "تحرير المحتوى")

            with st.container(height=800):
                with st.form(f"edit_form_{current_section_name}"):
                    edited_blocks = []
                    for idx, block in enumerate(blocks):
                        if block['type'] == 'code':
                            edited_blocks.append(block)
                        else:
                            h = max(100, len(block['content']) // 1.5)
                            new_text = st.text_area(
                                f"##",
                                value=block['content'],
                                height=int(h),
                                label_visibility="collapsed",
                                key=f"{st.session_state['language']}_{current_section_name}_{idx}"
                            )
                            edited_blocks.append({'type': 'text', 'content': new_text})
                            st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)

                    st.markdown("---")
                    btn_save_txt = "💾 حفظ الملف" if is_arabic else "💾 Save to File"
                    save_clicked = st.form_submit_button(btn_save_txt, type="primary", use_container_width=True)

            # Reconstruct content OUTSIDE form so preview can access it
            current_draft_latex = reconstruct_latex(edited_blocks)

            if save_clicked:
                save_file(current_file_path, current_draft_latex)
                st.toast(f"✅ Saved {current_section_name}")

        # --- PREVIEW ---
        with col_preview:
            st.subheader("Live Preview" if not is_arabic else "المعاينة الحية")

            # Preview button - OUTSIDE form, above preview area
            btn_prev_txt = "👁️ Generate Preview" if not is_arabic else "👁️ إنشاء معاينة"
            if st.button(btn_prev_txt, use_container_width=True, type="primary", key=f"preview_{current_section_name}"):
                st.session_state['preview_clicked'] = True
                st.rerun()

            preview_container = st.empty()

            # Check if preview was triggered
            if st.session_state.get('preview_clicked'):
                status_txt = "جاري تجميع ملف المعاينة..." if is_arabic else "Compiling Preview..."
                with st.status(status_txt, expanded=True) as status:
                    pdf_path, error_msg = generate_preview(current_draft_latex)

                    if pdf_path and os.path.exists(pdf_path):
                        status.update(label="Ready!", state="complete", expanded=False)
                        with preview_container.container():
                            display_pdf(pdf_path)
                        st.session_state['preview_clicked'] = False
                    else:
                        status.update(label="Failed", state="error")
                        st.error("⚠️ LaTeX Compilation Error")
                        with st.expander("Error Details", expanded=True):
                            st.code(error_msg, language="tex")
            else:
                preview_container.info("Click Preview / اضغط على المعاينة")

# ==========================================
# 6. VIEW: VARIABLES
# ==========================================
elif selected_view == "⚙️ Report Variables":
    header = "⚙️ الإعدادات العامة (Variables)" if is_arabic else "⚙️ Global Configuration"
    st.markdown(f"## {header}")
    
    st.markdown(f"""
    <div class="css-card">
    Current Configuration File: <code>{active_config['config']}</code>
    </div>
    """, unsafe_allow_html=True)

    if os.path.exists(CONFIG_FILE):
        raw_config = load_file(CONFIG_FILE)
        pattern = re.compile(r'\\newcommand\{\\(\w+)\}\{(.*?)\}')
        matches = pattern.findall(raw_config)
        
        with st.form("config_form"):
            updates = {}
            cols = st.columns(2)
            # RTL adjustment for inputs
            
            for i, (key, val) in enumerate(matches):
                col = cols[i % 2]
                with col:
                    updates[key] = st.text_input(f"Value for: {key}", value=val)
            
            st.markdown("---")
            btn_txt = "💾 تحديث المتغيرات" if is_arabic else "💾 Update Variables"
            if st.form_submit_button(btn_txt, type="primary"):
                new_config = raw_config
                for key, val in updates.items():
                    safe_val = val.replace('\\', '\\\\')
                    regex_replace = r'(\\newcommand\{\\' + key + r'\}\{)(.*?)(\})'
                    new_config = re.sub(regex_replace, r'\g<1>' + safe_val + r'\g<3>', new_config)
                
                save_file(CONFIG_FILE, new_config)
                st.toast("Updated!", icon="⚙️")
                st.rerun()
    else:
        st.error(f"{active_config['config']} not found.")

# ==========================================
# 7. VIEW: CHART MANAGER (Shared)
# ==========================================
elif selected_view == "📊 Chart Manager":
    header = "📊 إدارة الرسوم البيانية" if is_arabic else "📊 Chart Management"
    st.markdown(f"## {header}")
    
    if os.path.exists(IMAGES_DIR):
        files = sorted([f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(".png")])
        cols = st.columns(3)
        for idx, filename in enumerate(files):
            col = cols[idx % 3]
            filepath = os.path.join(IMAGES_DIR, filename)
            with col:
                with st.container(border=True):
                    st.markdown(f"**{filename}**")
                    st.image(filepath, width='stretch')
                    lbl = "استبدال" if is_arabic else "Replace"
                    uploaded = st.file_uploader(f"{lbl} {filename}", type=["png"], key=filename)
                    if uploaded:
                        with open(filepath, "wb") as f:
                            f.write(uploaded.getbuffer())
                        # Log chart upload
                        audit_logger.log(
                            st.session_state.get('username', 'unknown'),
                            "upload_chart",
                            {
                                "filename": filename,
                                "size_bytes": uploaded.size
                            }
                        )
                        st.success(f"Updated {filename}")
                        st.rerun()

# ==========================================
# 8. VIEW: COMPILE FINAL
# ==========================================
elif selected_view == "🚀 Finalize & Publish":
    header = "🚀 إنهاء ونشر التقرير" if is_arabic else "🚀 Compile Final Report"
    st.markdown(f"## {header}")
    
    c1, c2 = st.columns([2, 1])
    target_main = active_config["main"]
    
    with c1:
        msg = f"""
        <div class="css-card">
        <b>Target File: {target_main}</b><br>
        Using <b>XeLaTeX</b> engine to support {st.session_state['language']} fonts and layout.
        </div>
        """
        st.markdown(msg, unsafe_allow_html=True)
        
        btn_txt = "بدء التجميع الكامل" if is_arabic else "Generate Full PDF"
        
        if st.button(btn_txt, type="primary"):
            with st.status("Processing..." if not is_arabic else "جاري المعالجة...", expanded=True) as status:
                try:
                    # IMPORTANT: Arabic needs xelatex
                    cmd = ["xelatex", "-interaction=nonstopmode", target_main]

                    st.write("Running xelatex (Pass 1)...")
                    result1 = subprocess.run(cmd, cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                    st.write("Running xelatex (Pass 2 for ToC)...")
                    result2 = subprocess.run(cmd, cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    
                    expected_pdf = target_main.replace(".tex", ".pdf")
                    if os.path.exists(os.path.join(BASE_DIR, expected_pdf)):
                        # Log successful compilation
                        audit_logger.log(
                            st.session_state.get('username', 'unknown'),
                            "generate_pdf",
                            {
                                "language": st.session_state.get('language', 'Unknown'),
                                "main_file": target_main,
                                "success": True
                            }
                        )
                        status.update(label="Success!", state="complete", expanded=False)
                        st.session_state['pdf_ready'] = True
                        st.session_state['final_pdf_name'] = expected_pdf
                    else:
                        # Log failed compilation
                        # Parse log file for detailed errors
                        log_file = target_main.replace(".tex", ".log")
                        error_details = parse_latex_log(os.path.join(BASE_DIR, log_file))

                        audit_logger.log(
                            st.session_state.get('username', 'unknown'),
                            "generate_pdf",
                            {
                                "language": st.session_state.get('language', 'Unknown'),
                                "main_file": target_main,
                                "success": False,
                                "error": error_details[:500] if error_details else "Unknown"
                            }
                        )
                        status.update(label="Compilation Failed", state="error")
                        st.error("PDF was not created. See error details below.")

                        # Show detailed errors in expandable section
                        with st.expander("📋 Compilation Error Details", expanded=True):
                            st.code(error_details, language="text")
                except Exception as e:
                    status.update(label="Error", state="error")
                    st.error(str(e))

    with c2:
        if st.session_state.get('pdf_ready'):
            final_name = st.session_state.get('final_pdf_name', 'output.pdf')
            pdf_path = os.path.join(BASE_DIR, final_name)
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📥 Download PDF" if not is_arabic else "📥 تحميل التقرير",
                    data=f,
                    file_name=final_name,
                    mime="application/pdf",
                    type="primary",
                    width='stretch'
                )

# ==========================================
# 9. VIEW: USER MANAGEMENT (Admin Only)
# ==========================================
elif selected_view == "👥 User Management":
    if current_role != "admin":
        st.error("Access Denied: Admin privileges required" if not is_arabic else "الوصول مرفوض: يتطلب صلاحيات المسؤول")
        st.stop()

    header = "👥 إدارة المستخدمين" if is_arabic else "👥 User Management"
    st.markdown(f"## {header}")

    # Three tabs
    tab1, tab2, tab3 = st.tabs([
        "➕ Create User" if not is_arabic else "➕ إنشاء مستخدم",
        "📋 Manage Users" if not is_arabic else "📋 إدارة المستخدمين",
        "📊 Activity Log" if not is_arabic else "📊 سجل النشاط"
    ])

    # --- TAB 1: CREATE USER ---
    with tab1:
        st.markdown("### Create New User" if not is_arabic else "### إنشاء مستخدم جديد")

        with st.form("create_user_form"):
            col1, col2 = st.columns(2)

            with col1:
                new_username = st.text_input(
                    "Username" if not is_arabic else "اسم المستخدم",
                    placeholder="lowercase, alphanumeric",
                    help="Letters, numbers, and underscore only"
                )
                new_password = st.text_input(
                    "Password" if not is_arabic else "كلمة المرور",
                    type="password",
                    help="Minimum 8 characters"
                )

            with col2:
                new_role = st.selectbox(
                    "Role" if not is_arabic else "الدور",
                    ["user", "admin"],
                    help="Admin can manage users and access all features"
                )
                password_confirm = st.text_input(
                    "Confirm Password" if not is_arabic else "تأكيد كلمة المرور",
                    type="password"
                )

            st.markdown("---")
            create_btn = st.form_submit_button(
                "Create User" if not is_arabic else "إنشاء المستخدم",
                type="primary",
                use_container_width=True
            )

            if create_btn:
                # Validation
                if not new_username or not new_password:
                    st.error("Username and password are required" if not is_arabic else "اسم المستخدم وكلمة المرور مطلوبان")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters" if not is_arabic else "كلمة المرور يجب أن تكون 8 أحرف على الأقل")
                elif new_password != password_confirm:
                    st.error("Passwords do not match" if not is_arabic else "كلمات المرور غير متطابقة")
                elif not new_username.replace('_', '').isalnum():
                    st.error("Username must be alphanumeric (underscore allowed)" if not is_arabic else "اسم المستخدم يجب أن يكون أبجدي رقمي")
                else:
                    # Create user
                    success, message = auth_manager.create_user(
                        new_username.lower(),
                        new_password,
                        new_role,
                        current_user
                    )

                    if success:
                        audit_logger.log(
                            current_user,
                            "create_user",
                            {"new_user": new_username, "role": new_role}
                        )
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")

    # --- TAB 2: MANAGE USERS ---
    with tab2:
        st.markdown("### User List" if not is_arabic else "### قائمة المستخدمين")

        users = auth_manager.get_all_users()

        if not users:
            st.info("No users found" if not is_arabic else "لم يتم العثور على مستخدمين")
        else:
            for user in users:
                with st.expander(
                    f"{'🟢' if user['is_active'] else '🔴'} {user['username']} ({user['role']})",
                    expanded=False
                ):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"""
                        **Username:** `{user['username']}`
                        **Role:** {user['role']}
                        **Status:** {'✅ Active' if user['is_active'] else '❌ Inactive'}
                        **Created:** {user['created_at'][:10]}
                        **Created By:** {user['created_by']}
                        **Last Login:** {user['last_login'][:10] if user['last_login'] else 'Never'}
                        """)

                    with col2:
                        # Actions
                        st.markdown("**Actions:**" if not is_arabic else "**الإجراءات:**")

                        # Prevent self-modification
                        if user['username'] == current_user:
                            st.info("Cannot modify your own account" if not is_arabic else "لا يمكن تعديل حسابك")
                        else:
                            # Deactivate/Activate
                            if user['is_active']:
                                if st.button(
                                    f"🔒 Deactivate {user['username']}" if not is_arabic else f"🔒 تعطيل {user['username']}",
                                    key=f"deactivate_{user['username']}"
                                ):
                                    success, msg = auth_manager.update_user_status(
                                        user['username'], False
                                    )
                                    if success:
                                        audit_logger.log(
                                            current_user,
                                            "deactivate_user",
                                            {"target_user": user['username']}
                                        )
                                        st.success(msg)
                                        st.rerun()
                            else:
                                if st.button(
                                    f"🔓 Activate {user['username']}" if not is_arabic else f"🔓 تفعيل {user['username']}",
                                    key=f"activate_{user['username']}"
                                ):
                                    success, msg = auth_manager.update_user_status(
                                        user['username'], True
                                    )
                                    if success:
                                        audit_logger.log(
                                            current_user,
                                            "activate_user",
                                            {"target_user": user['username']}
                                        )
                                        st.success(msg)
                                        st.rerun()

                            # Reset Password
                            with st.form(f"reset_pw_{user['username']}"):
                                new_pw = st.text_input(
                                    "New Password" if not is_arabic else "كلمة المرور الجديدة",
                                    type="password",
                                    key=f"newpw_{user['username']}"
                                )
                                if st.form_submit_button("🔑 Reset Password" if not is_arabic else "🔑 إعادة تعيين كلمة المرور"):
                                    if len(new_pw) < 8:
                                        st.error("Password must be at least 8 characters" if not is_arabic else "كلمة المرور يجب أن تكون 8 أحرف على الأقل")
                                    else:
                                        success, msg = auth_manager.change_password(
                                            user['username'], new_pw
                                        )
                                        if success:
                                            audit_logger.log(
                                                current_user,
                                                "reset_password",
                                                {"target_user": user['username']}
                                            )
                                            st.success(msg)

    # --- TAB 3: ACTIVITY LOG ---
    with tab3:
        st.markdown("### Recent Activity" if not is_arabic else "### النشاط الأخير")

        # Filter options
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            log_limit = st.selectbox("Show entries:" if not is_arabic else "عرض الإدخالات:", [50, 100, 200, 500], index=1)
        with col_filter2:
            filter_user = st.selectbox(
                "Filter by user:" if not is_arabic else "تصفية حسب المستخدم:",
                ["All"] + [u['username'] for u in users]
            )
        with col_filter3:
            filter_action = st.selectbox(
                "Filter by action:" if not is_arabic else "تصفية حسب الإجراء:",
                ["All", "login", "logout", "save_file", "generate_pdf",
                 "factory_reset", "create_user", "upload_chart"]
            )

        # Get logs
        logs = audit_logger.get_recent_logs(limit=log_limit)

        # Apply filters
        if filter_user != "All":
            logs = [log for log in logs if log['username'] == filter_user]
        if filter_action != "All":
            logs = [log for log in logs if log['action'] == filter_action]

        # Reverse to show newest first
        logs = list(reversed(logs))

        if not logs:
            st.info("No activity logs found" if not is_arabic else "لم يتم العثور على سجلات نشاط")
        else:
            # Display as table
            st.markdown(f"**Showing {len(logs)} entries**" if not is_arabic else f"**عرض {len(logs)} إدخال**")

            for log in logs:
                timestamp = log['timestamp'][:19].replace('T', ' ')
                action_emoji = {
                    'login': '🔓',
                    'logout': '🔒',
                    'save_file': '💾',
                    'generate_pdf': '📄',
                    'generate_preview': '👁️',
                    'factory_reset': '🔄',
                    'create_user': '➕',
                    'upload_chart': '📊',
                    'deactivate_user': '🔒',
                    'activate_user': '🔓',
                    'reset_password': '🔑',
                    'change_password': '🔑'
                }.get(log['action'], '📝')

                with st.expander(
                    f"{action_emoji} {timestamp} | {log['username']} | {log['action']}",
                    expanded=False
                ):
                    st.json(log['details'])