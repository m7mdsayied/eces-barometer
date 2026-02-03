import streamlit as st
import os
import re
import subprocess
import base64
import shutil

# ==========================================
# 1. CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    layout="wide",
    page_title="ECES Barometer Suite",
    page_icon="📊",
    initial_sidebar_state="expanded"
)

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
    with open(filepath, 'w', encoding='utf-8') as f: f.write(content)

def display_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        st.error("Preview file not found.")
        return
    with open(pdf_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}#toolbar=0&navpanes=0&scrollbar=0" width="100%" height="800" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# ==========================================
# 3. COMPILER & TOOLS
# ==========================================
def parse_latex_log(log_path):
    if not os.path.exists(log_path): return "Log file not found."
    errors = []
    try:
        with open(log_path, "r", encoding="latin-1", errors='ignore') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if line.startswith("!"):
                context = lines[i:i+3] 
                errors.append("".join(context).strip())
    except:
        return "Could not parse log."
    return "\n\n".join(errors) if errors else "Unknown error. Check syntax."

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
        subprocess.run(["xelatex", "-interaction=nonstopmode", preview_tex], cwd=BASE_DIR, stdout=subprocess.DEVNULL)
        
        if os.path.exists(preview_pdf):
            return preview_pdf, None
        else:
            error_msg = parse_latex_log(os.path.join(BASE_DIR, preview_log))
            return None, error_msg
    except Exception as e:
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
# 4. SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
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
    
    nav_options = {
        "English": ["📝 Report Sections", "⚙️ Report Variables", "📊 Chart Manager", "🚀 Finalize & Publish"],
        "Arabic": ["📝 أقسام التقرير", "⚙️ متغيرات التقرير", "📊 إدارة الرسوم البيانية", "🚀 إنهاء ونشر"]
    }
    
    # Map Arabic selections back to English logic keys
    nav_map = dict(zip(nav_options["Arabic"], nav_options["English"]))
    
    selected_view_display = st.radio(
        "Navigation",
        nav_options[st.session_state['language']],
        label_visibility="collapsed"
    )
    
    # Normalize view variable
    selected_view = nav_map.get(selected_view_display, selected_view_display)
    
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

# ==========================================
# 5. VIEW: REPORT SECTIONS
# ==========================================
if selected_view == "📝 Report Sections":
    header_text = "📝 محرر المحتوى والمعاينة" if is_arabic else "📝 Content Editor & Preview"
    st.markdown(f"## {header_text}")
    
    # Section Selector
    section_keys = list(SECTION_MAP.keys())
    col_sel, col_info = st.columns([1, 2])
    with col_sel:
        lbl = "اختر القسم" if is_arabic else "Select Section"
        current_section_name = st.selectbox(lbl, section_keys)
    
    current_file_path = os.path.join(BASE_DIR, SECTION_MAP[current_section_name])
    
    # Check if file exists, if not create empty
    if not os.path.exists(current_file_path):
        save_file(current_file_path, "% New Section")
    
    raw_content = load_file(current_file_path)
    blocks = parse_latex_blocks(raw_content)
    
    with col_info:
        st.markdown(f"""
        <div style="padding-top: 25px;">
            <span style="background:#262730; padding: 5px 10px; border-radius:5px; border:1px solid #383b42;">
                File: <code>{os.path.basename(current_file_path)}</code> | Mode: <b>{st.session_state['language']}</b>
            </span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
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
                    subprocess.run(cmd, cwd=BASE_DIR, stdout=subprocess.DEVNULL)
                    
                    st.write("Running xelatex (Pass 2 for ToC)...")
                    subprocess.run(cmd, cwd=BASE_DIR, stdout=subprocess.DEVNULL)
                    
                    expected_pdf = target_main.replace(".tex", ".pdf")
                    if os.path.exists(os.path.join(BASE_DIR, expected_pdf)):
                        status.update(label="Success!", state="complete", expanded=False)
                        st.session_state['pdf_ready'] = True
                        st.session_state['final_pdf_name'] = expected_pdf
                    else:
                        status.update(label="Compilation Failed", state="error")
                        st.error("PDF was not created. Check logs.")
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