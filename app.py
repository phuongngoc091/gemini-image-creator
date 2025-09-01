import streamlit as st
import google.generativeai as genai
from PIL import Image
import json

# --- CẤU HÌNH TRANG VÀ CSS CHO GIAO DIỆN CYBERPUNK ---
st.set_page_config(layout="wide", page_title="AI Video Scripting Core")

# CSS để thay đổi giao diện
CYBERPUNK_CSS = """
<style>
    /* Nền và font chữ chính */
    body, .stApp {
        background-color: #0d0221; /* Nền tím than đậm */
        color: #f0f2f6;
        font-family: 'Courier New', Courier, monospace;
    }

    /* Tiêu đề chính */
    h1 {
        color: #00f6ff; /* Cyan neon */
        text-shadow: 0 0 10px #00f6ff, 0 0 20px #00f6ff;
    }

    /* Tiêu đề phụ */
    h2, h3 {
        color: #ff00ff; /* Magenta neon */
        border-bottom: 2px solid #ff00ff;
        padding-bottom: 5px;
    }

    /* Nút bấm */
    .stButton > button {
        background-color: transparent;
        color: #00f6ff;
        border: 2px solid #00f6ff;
        border-radius: 0px;
        transition: all 0.3s ease-in-out;
    }
    .stButton > button:hover {
        background-color: #00f6ff;
        color: #0d0221;
        box-shadow: 0 0 15px #00f6ff;
    }
    
    /* Ô nhập liệu */
    .stTextArea textarea, .stTextInput input {
        background-color: #1a0a38;
        color: #f0f2f6;
        border: 1px solid #ff00ff;
        border-radius: 0px;
    }

    /* Box tải file lên */
    .stFileUploader {
        background-color: #1a0a38;
        border: 2px dashed #ff00ff;
        border-radius: 0px;
    }
    
    /* Thanh sidebar */
    .stSidebar {
        background-color: #1a0a38;
    }
    
    /* Dòng footer */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #1a0a38;
        color: #8a8a8a;
        text-align: center;
        padding: 10px;
        border-top: 1px solid #ff00ff;
    }
</style>
"""
st.markdown(CYBERPUNK_CSS, unsafe_allow_html=True)

# --- TIÊU ĐỀ ---
st.title(">> AI VIDEO SCRIPTING CORE_")
st.caption("Initializing prompt amplification sequence...")

# --- CÁC KHUÔN MẪU PROMPT (KHÔNG THAY ĐỔI) ---
IMAGE_TO_VIDEO_TEMPLATE = """
Initial Frame: Use the provided image of {subject_description}.
Animation: Animate the subject to {core_action}.
Speech: {dialogue_section}
Visual Effects: Maintain the original atmosphere. Animate effects like {visual_effects}.
Audio: {audio_section}
"""
TEXT_TO_VIDEO_TEMPLATE = """
Scene Description: A cinematic, 8k, photorealistic shot of {subject_description} in {setting_description}. The mood is {mood}.
Animation: Animate the subject to {core_action}.
Speech: {dialogue_section}
Visual Effects: Create realistic effects like {visual_effects}.
Audio: {audio_section}
"""
META_PROMPT_FOR_GEMINI = """
Analyze the user's Vietnamese video idea. Extract key information and translate it to English.
Rewrite the dialogue in Vietnamese to be concise (under 8 seconds).
Output a clean JSON object.

User Idea: "{user_idea}"

JSON fields:
- "subject_description": (Translate to English) The main subject.
- "core_action": (Translate to English) The main action.
- "setting_description": (Translate to English) The location.
- "dialogue": (Keep and rewrite in Vietnamese) The speech.
- "mood": (Translate to English) The feeling of the scene.
- "visual_effects": (Translate to English) Visual effects.
- "voice_type": (Translate to English) e.g., 'a warm female voice'.
"""

# --- Cấu hình API Key ở thanh bên (sidebar) ---
with st.sidebar:
    st.header("SYSTEM CONFIG_")
    try:
        google_api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("API Key Status: CONNECTED", icon="✅")
    except (FileNotFoundError, KeyError):
        st.warning("API Key: NOT FOUND. Please input manually.", icon="⚠️")
        google_api_key = st.text_input("INPUT API KEY:", type="password")

if not google_api_key:
    st.error("FATAL ERROR: API Key is required to initialize.")
    st.stop()

try:
    genai.configure(api_key=google_api_key)
    gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash")
except Exception as e:
    st.error(f"API CONFIGURATION FAILED: {e}")
    st.stop()

# --- Giao diện ứng dụng ---
col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("UPLINK_")
    uploaded_file = st.file_uploader("Drag & Drop Image (Optional: Image -> Video)", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        st.image(Image.open(uploaded_file), caption="[Initial Frame Buffer]", use_column_width=True)

with col2:
    st.subheader("IDEA INPUT_")
    
    # Sử dụng session_state để quản lý nội dung ô text
    if 'user_idea' not in st.session_state:
        st.session_state.user_idea = ""

    user_idea = st.text_area(
        "Input video concept (Vietnamese):",
        height=200,
        placeholder="e.g., một cô gái đi trên Cầu Vàng có tuyết rơi và nói 'Chào mọi người! Tuyết rơi đẹp không?'",
        key="user_idea_input" # Đặt key để truy cập
    )
    
    # Form chứa các nút bấm
    form_col1, form_col2 = st.columns([1, 1])
    with form_col1:
        submitted = st.button("EXECUTE SCRIPT_")
    with form_col2:
        # Nút làm mới, xóa nội dung và chạy lại app
        if st.button("CLEAR INPUT_"):
            st.session_state.user_idea = ""
            st.rerun()

    if submitted and user_idea:
        with st.spinner("AI CORE: Analyzing and creating script..."):
            response_text = ""
            try:
                request_for_gemini = META_PROMPT_FOR_GEMINI.format(user_idea=user_idea)
                response = gemini_model.generate_content(request_for_gemini)

                if not response.text or not response.text.strip():
                    st.error("AI RESPONSE ERROR: No content returned. The request may have been blocked for safety or policy reasons. Please try a different idea.")
                    st.stop()

                response_text = response.text.replace("```json", "").replace("```", "").strip()
                extracted_data = json.loads(response_text)

                prompt_data = {
                    'subject_description': extracted_data.get('subject_description', 'a scene'),
                    'core_action': extracted_data.get('core_action', 'an action'),
                    'setting_description': extracted_data.get('setting_description', 'a location'),
                    'dialogue': extracted_data.get('dialogue', ''),
                    'mood': extracted_data.get('mood', 'neutral'),
                    'visual_effects': extracted_data.get('visual_effects', 'none'),
                    'voice_type': extracted_data.get('voice_type', 'a voice')
                }

                if prompt_data['dialogue']:
                    prompt_data['dialogue_section'] = f"Animate the subject's mouth to synchronize with the speech: \"{prompt_data['dialogue']}\"."
                    prompt_data['audio_section'] = f"Generate natural-sounding Vietnamese speech, spoken by {prompt_data['voice_type']}."
                else:
                    prompt_data['dialogue_section'] = "No dialogue."
                    prompt_data['audio_section'] = "No speech audio, only ambient sounds."

                template = IMAGE_TO_VIDEO_TEMPLATE if uploaded_file else TEXT_TO_VIDEO_TEMPLATE
                final_prompt = template.format(**prompt_data)

                st.divider()
                st.subheader("FINAL PROMPT SCRIPT_")
                st.text_area("Optimized output for video model:", value=final_prompt, height=400)

            except json.JSONDecodeError:
                st.error("JSON DECODING FAILED: AI did not return valid JSON. Please try again with a clearer idea.")
                st.write("Raw data from AI (for debugging):", response_text)
            except Exception as e:
                st.error(f"UNEXPECTED ERROR: {e}")

    elif submitted:
        st.warning("WARNING: Idea input field is empty.")

# --- FOOTER ---
st.markdown('<div class="footer">thiết kế bởi phuongngoc091 | 0932 468 218</div>', unsafe_allow_html=True)
