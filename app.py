import streamlit as st
import google.generativeai as genai
from PIL import Image
import json

# --- CẤU HÌNH TRANG VÀ CSS CHO GIAO DIỆN TỐI GIẢN ---
st.set_page_config(layout="wide", page_title="Viết prompt tạo video với phuongngoc091")

# CSS để có giao diện sạch sẽ, tối giản
APPLE_STYLE_CSS = """
<style>
    /* Font chữ và nền chính */
    body, .stApp {
        background-color: #f0f2f5; /* Nền xám rất nhạt */
        color: #000000;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
    }

    /* Tiêu đề */
    h1, h2, h3 {
        font-weight: 600;
    }
    
    /* Các thành phần chính */
    .stApp > header {
        background-color: transparent;
    }
    
    /* Nút bấm */
    .stButton > button {
        background-color: #007aff; /* Xanh dương của Apple */
        color: white;
        border: none;
        border-radius: 12px;
        padding: 10px 24px;
        transition: all 0.2s ease-in-out;
        font-weight: 500;
    }
    .stButton > button:hover {
        background-color: #0056b3;
        color: white;
    }
    /* Nút làm mới (phụ) */
    .stButton:has(button:contains("Làm mới")) > button {
        background-color: #e9e9eb;
        color: #000000;
    }
     .stButton:has(button:contains("Làm mới")) > button:hover {
        background-color: #d1d1d6;
    }

    /* Ô nhập liệu */
    .stTextArea textarea, .stTextInput input {
        background-color: #ffffff;
        border: 1px solid #d1d1d6;
        border-radius: 12px;
        padding: 10px;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
         border-color: #007aff;
         box-shadow: 0 0 0 2px rgba(0, 122, 255, 0.2);
    }

    /* Box tải file lên */
    .stFileUploader {
        background-color: #ffffff;
        border: 2px dashed #d1d1d6;
        border-radius: 12px;
    }
    
    /* Thanh sidebar */
    .stSidebar {
        background-color: #f0f2f5;
        border-right: 1px solid #d1d1d6;
    }
    
    /* Dòng footer */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f0f2f5;
        color: #8a8a8a;
        text-align: center;
        padding: 10px;
        font-size: 14px;
    }
</style>
"""
st.markdown(APPLE_STYLE_CSS, unsafe_allow_html=True)

# --- TIÊU ĐỀ ---
st.title("Trợ lý Sáng tạo Video")
st.caption("Biến ý tưởng đơn giản của bạn thành một kịch bản video chi tiết.")

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
    st.header("Cấu hình")
    try:
        google_api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("API Key đã được kết nối.", icon="✅")
    except (FileNotFoundError, KeyError):
        st.warning("Không tìm thấy API Key. Vui lòng nhập thủ công.", icon="⚠️")
        google_api_key = st.text_input("Nhập Google API Key của bạn:", type="password", label_visibility="collapsed")

if not google_api_key:
    st.error("Vui lòng nhập API Key trong thanh cấu hình để bắt đầu.")
    st.stop()

try:
    genai.configure(api_key=google_api_key)
    gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash")
except Exception as e:
    st.error(f"Lỗi cấu hình API Key: {e}")
    st.stop()

# --- Giao diện ứng dụng ---
col1, col2 = st.columns([1, 2], gap="large")

with col1:
    st.subheader("Đầu vào")
    uploaded_file = st.file_uploader("Tải ảnh lên (tùy chọn)", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        st.image(Image.open(uploaded_file), caption="Khung hình khởi đầu", use_column_width=True)

    # --- THÊM HÌNH ẢNH MỚI TẠI ĐÂY ---
    st.image(
        "https://ia600905.us.archive.org/0/items/Donate_png/1111111.jpg",
        caption="Donate"
    )

with col2:
    st.subheader("Ý tưởng của bạn")
    
    user_idea = st.text_area(
        "Nhập ý tưởng video bằng tiếng Việt:",
        height=210,
        placeholder="Ví dụ: một cô gái đi trên Cầu Vàng có tuyết rơi và nói 'Chào mọi người! Tuyết rơi đẹp không?'",
        key="user_idea_input"
    )
    
    # Các nút bấm
    form_col1, form_col2 = st.columns([1, 1])
    with form_col1:
        submitted = st.button("Tạo kịch bản", use_container_width=True)
    with form_col2:
        if st.button("Làm mới", use_container_width=True):
            st.session_state.user_idea_input = ""
            st.rerun()

    if submitted and user_idea:
        with st.spinner("AI đang phân tích và sáng tạo..."):
            response_text = ""
            try:
                request_for_gemini = META_PROMPT_FOR_GEMINI.format(user_idea=user_idea)
                response = gemini_model.generate_content(request_for_gemini)

                if not response.text or not response.text.strip():
                    st.error("Lỗi: AI không trả về nội dung. Yêu cầu của bạn có thể đã bị chặn. Vui lòng thử lại với một ý tưởng khác.")
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
                st.subheader("Kịch bản Prompt chi tiết")
                st.text_area("Prompt (tiếng Anh) đã được tối ưu cho AI tạo video:", value=final_prompt, height=350)

            except json.JSONDecodeError:
                st.error("Lỗi: AI trả về định dạng không hợp lệ. Vui lòng thử lại.")
                st.write("Dữ liệu thô từ AI (để gỡ lỗi):", response_text)
            except Exception as e:
                st.error(f"Đã xảy ra lỗi: {e}")

    elif submitted:
        st.warning("Vui lòng nhập ý tưởng của bạn.")

# --- FOOTER ---
st.markdown('<div class="footer">Thiết kế bởi: phuongngoc091 | 0932 468 218</div>', unsafe_allow_html=True)
