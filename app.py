import streamlit as st
import google.generativeai as genai
from PIL import Image
import json

# --- Cấu hình trang và tiêu đề ---
st.set_page_config(layout="wide", page_title="Trợ lý Sáng tạo Video AI")
st.title("🎬 Trợ lý Sáng tạo Video AI")
st.caption("Tạo kịch bản video chi tiết từ ý tưởng đơn giản của bạn.")

# --- CÁC KHUÔN MẪU PROMPT (TEMPLATES) ---
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

# --- SIÊU PROMPT DÀNH CHO "BIÊN KỊCH AI" (PHIÊN BẢN ĐƠN GIẢN HÓA) ---
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
        st.success("Đã tìm thấy API Key!", icon="✅")
    except (FileNotFoundError, KeyError):
        st.warning("Không tìm thấy API Key trong Secrets. Vui lòng nhập thủ công.", icon="⚠️")
        google_api_key = st.text_input("Nhập Google API Key của bạn:", type="password")

if not google_api_key:
    st.error("Vui lòng nhập API Key của bạn để bắt đầu.")
    st.stop()

try:
    genai.configure(api_key=google_api_key)
    gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash")
except Exception as e:
    st.error(f"Lỗi cấu hình API Key: {e}")
    st.stop()

# --- Giao diện ứng dụng ---
col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("🖼️ Đầu vào")
    uploaded_file = st.file_uploader("Tải ảnh lên (cho tùy chọn Ảnh -> Video)", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        st.image(Image.open(uploaded_file), caption="Khung hình khởi đầu", use_column_width=True)

with col2:
    st.subheader("💡 Ý tưởng của bạn")
    with st.form("prompt_form"):
        user_idea = st.text_area("Nhập ý tưởng video bằng tiếng Việt:", height=200, placeholder="Ví dụ: một cô gái đi trên Cầu Vàng có tuyết rơi và nói 'Chào mọi người! Tuyết rơi đẹp không?'")
        submitted = st.form_submit_button("Tạo kịch bản Prompt")

    if submitted and user_idea:
        with st.spinner("🤖 Biên kịch AI đang phân tích..."):
            try:
                # Bước 1: Gọi AI để trích xuất JSON
                request_for_gemini = META_PROMPT_FOR_GEMINI.format(user_idea=user_idea)
                response = gemini_model.generate_content(request_for_gemini)
                response_text = response.text.replace("```json", "").replace("```", "").strip()
                extracted_data = json.loads(response_text)

                # Bước 2: Gán giá trị an toàn
                prompt_data = {
                    'subject_description': extracted_data.get('subject_description', 'a scene'),
                    'core_action': extracted_data.get('core_action', 'an action'),
                    'setting_description': extracted_data.get('setting_description', 'a location'),
                    'dialogue': extracted_data.get('dialogue', ''),
                    'mood': extracted_data.get('mood', 'neutral'),
                    'visual_effects': extracted_data.get('visual_effects', 'none'),
                    'voice_type': extracted_data.get('voice_type', 'a voice')
                }

                # Xử lý phần lời thoại
                if prompt_data['dialogue']:
                    prompt_data['dialogue_section'] = f"Animate the subject's mouth to synchronize with the speech: \"{prompt_data['dialogue']}\"."
                    prompt_data['audio_section'] = f"Generate natural-sounding Vietnamese speech, spoken by {prompt_data['voice_type']}."
                else:
                    prompt_data['dialogue_section'] = "No dialogue."
                    prompt_data['audio_section'] = "No speech audio, only ambient sounds."

                # Bước 3: Lắp ráp prompt
                template = IMAGE_TO_VIDEO_TEMPLATE if uploaded_file else TEXT_TO_VIDEO_TEMPLATE
                final_prompt = template.format(**prompt_data)

                # Hiển thị kết quả
                st.divider()
                st.subheader("🎬 Kịch bản Prompt chi tiết (Tiếng Anh)")
                st.text_area("Prompt cuối cùng:", value=final_prompt, height=400)

            except Exception as e:
                st.error(f"Đã xảy ra lỗi: {e}")
                st.write("Dữ liệu thô từ AI (để gỡ lỗi):", response_text)

    elif submitted:
        st.warning("Vui lòng nhập ý tưởng của bạn.")
