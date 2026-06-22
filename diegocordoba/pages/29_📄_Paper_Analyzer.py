import streamlit as st
import os
import fitz  # PyMuPDF
from anthropic import Anthropic

# Ensure project root is on path
import sys
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from lib.auth_gate import require_auth
from lib.mode_gate import show_mode_banner

require_auth()
show_mode_banner()

st.set_page_config(
    page_title="Paper Analyzer | PRIMEnergeia",
    page_icon="📄",
    layout="wide"
)

# Premium CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
.main { background-color: #050810; color: #e0e6ed; font-family: 'Inter', sans-serif; }
.metric-card {
    background: linear-gradient(135deg, #0d1520, #111b2a);
    border: 1px solid rgba(0, 209, 255, 0.25);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("# 📄 Paper Analyzer: Deep Reading")
st.markdown("Upload scientific PDFs to automatically extract Mathematical Formulations (HJB), Methodologies, and Key Conclusions using Anthropic Claude.")

# --- Logic: PDF Extraction ---
def extract_text_from_pdf(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# --- Logic: Anthropic Call ---
@st.cache_data(show_spinner=False)
def analyze_paper_in_depth(paper_text):
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    prompt = f"""You are a senior computational physicist and stochastic control expert at PRIMEnergeia.
Please perform an in-depth reading of the following scientific paper.

Extract and structure your response as follows:
1. **Abstract & Summary**: A brief summary of the paper's main goal.
2. **Mathematical Formulation (HJB & PDEs)**: Extract any Hamilton-Jacobi-Bellman equations, stochastic differential equations, or core mathematical models discussed. Format them in LaTeX.
3. **Methodology**: How did the authors solve or approach the problem?
4. **Key Conclusions**: What are the main takeaways?
5. **Relevance to PRIMEnergeia**: How can this be applied to energy dispatch, battery optimization, or optimal control?

Paper Text:
---
{paper_text}
---
"""
    try:
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=2500,
            system=[{"type": "text", "text": "You are a senior computational physicist.", "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
        )
        return response.content[0].text
    except Exception as e:
        return f"Error connecting to Anthropic API: {e}"

# --- UI ---
uploaded_file = st.file_uploader("Upload a PDF paper", type=["pdf"])

if uploaded_file is not None:
    if "paper_text" not in st.session_state or st.session_state.get("uploaded_filename") != uploaded_file.name:
        with st.spinner("Extracting text from PDF..."):
            st.session_state.paper_text = extract_text_from_pdf(uploaded_file.read())
            st.session_state.uploaded_filename = uploaded_file.name
            st.session_state.messages = [] # Reset chat history
            
    st.success(f"PDF loaded successfully: {uploaded_file.name} ({len(st.session_state.paper_text)} characters)")

    tab1, tab2 = st.tabs(["📊 Deep Analysis", "💬 Paper Chat"])
    
    with tab1:
        if st.button("🚀 Run In-Depth Analysis"):
            with st.spinner("Analyzing paper with Claude... this might take a minute."):
                analysis_result = analyze_paper_in_depth(st.session_state.paper_text)
                st.session_state.analysis_result = analysis_result
        
        if "analysis_result" in st.session_state:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.markdown(st.session_state.analysis_result)
            st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("### Chat with the Paper")
        
        # Display chat messages
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
        # Chat input
        if prompt := st.chat_input("Ask a specific question about the mathematical model or methodology..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
                
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                with st.spinner("Thinking..."):
                    try:
                        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
                        
                        # Build context
                        system_prompt = "You are a helpful AI assistant analyzing a scientific paper. Use the following paper text to answer user questions.\n\nPaper Text:\n" + st.session_state.paper_text
                        
                        api_messages = [{"role": m["role"], "content": [{"type": "text", "text": m["content"]}]} for m in st.session_state.messages]
                        
                        response = client.messages.create(
                            model="claude-opus-4-8",
                            max_tokens=1500,
                            system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                            messages=api_messages,
                            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
                        )
                        full_response = response.content[0].text
                        message_placeholder.markdown(full_response)
                        st.session_state.messages.append({"role": "assistant", "content": full_response})
                    except Exception as e:
                        st.error(f"Error during chat: {e}")
