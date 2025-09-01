import streamlit as st
import google.generativeai as genai
from PIL import Image
import json

# --- CẤU HÌNH TRANG VÀ CSS ---
st.set_page_config(layout="wide", page_title="Viết prompt tạo video với phuongngoc091")

# CSS để có giao diện sạch sẽ, tối giản
APPLE_STYLE_CSS = """
<style>
    /* ... (Toàn bộ CSS giữ nguyên như cũ) ... */
    body, .stApp { background-color: #f0f2f5; color: #000000; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    h1, h2, h3 { font-weight: 600; }
    .stApp > header { background-color: transparent; }
    .stButton > button {
        background-color: #007aff; color: white; border: none; border-radius: 12px;
        padding: 10px 24px; transition: all 0.2s ease-in-out; font-weight: 500;
    }
    .stButton > button:hover { background-color: #0056b3; color: white; }
    .stButton:has(button:contains("Làm mới")) > button { background-color: #e9e9eb; color: #000000; }
    .stButton:has(button:contains("Làm mới")) > button:hover { background-color: #d1d1d6; }
    .stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #ffffff; border: 1px solid #d1d1d6; border-radius: 12px; padding: 10px;
    }
    .stTextArea textarea:focus, .stTextInput input:focus, .stSelectbox div[data-baseweb="select"] > div:focus-within {
        border-color: #007aff; box-shadow: 0 0 0 2px rgba(0, 122, 255, 0.2);
    }
    .stFileUploader { background-color: #ffffff; border: 2px dashed #d1d1d6; border-radius: 12px; }
    .stSidebar { background-color: #f0f2f5; border-right: 1px solid #d1d1d6; }
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f0f2f5;
        color: #8a8a8a; text-align: center; padding: 10px; font-size: 14px;
    }
</style>
"""
st.markdown(APPLE_STYLE_CSS, unsafe_allow_html=True)

# --- KHỞI TẠO SESSION STATE ---
if 'final_prompt' not in st.session_state:
    st.session_state.final_prompt = ""

# --- TIÊU ĐỀ ---
st.title("Viết prompt tạo video với phuongngoc091")
st.caption("Biến ý tưởng đơn giản của bạn thành một kịch bản video chi tiết.")

# --- CÁC KHUÔN MẪU PROMPT ---
IMAGE_TO_VIDEO_TEMPLATE = """
Style: {style}
Initial Frame: Use the provided image of {subject_description}.
Animation: Animate the subject to {core_action}.
Camera Motion: {camera_motion}.
Speech: {dialogue_section}
Visual Effects: Maintain the original atmosphere. Animate effects like {visual_effects}.
Audio: {audio_section}
"""
TEXT_TO_VIDEO_TEMPLATE = """
Style: {style}
Scene Description: A cinematic, 8k, photorealistic shot of {subject_description} in {setting_description}. The mood is {mood}.
Animation: Animate the subject to {core_action}.
Camera Motion: {camera_motion}.
Speech: {dialogue_section}
Visual Effects: Create realistic effects like {visual_effects}.
Audio: {audio_section}
"""
META_PROMPT_FOR_GEMINI = """
You are a creative director AI. Your primary task is to convert a simple user idea (in Vietnamese) into a detailed cinematic prompt for a video AI model.

**CRITICAL OUTPUT REQUIREMENTS:**
1.  **LANGUAGE:** All JSON values MUST be in ENGLISH, with only ONE exception. This includes proper nouns like names and places, which should be transliterated or translated appropriately (e.g., "Thầy giáo Phương Ngọc" should become "Teacher Phuong Ngoc").
2.  **EXCEPTION FOR DIALOGUE:** The value for the "dialogue" field MUST remain in its original VIETNAMESE.
3.  **FORMAT:** The entire final output MUST be a single, clean JSON object. Do not add any explanatory text before or after the JSON block.

**CREATIVE PROCESS:**
-   Analyze the user's idea and the chosen `{style}`.
-   Envision the scene and add creative details for subject, setting, mood, lighting, and camera work.
-   Rewrite dialogue in VIETNAMESE to be concise (under 8s). If none, the "dialogue" field should be an empty string.
-   Translate descriptive elements to English.
-   Construct a JSON object with all required fields.

**STYLE DIRECTIVE:** The user has selected the style: "{style}".

**Analyze the user's idea below and generate the JSON output, strictly following all critical requirements.**
User Idea: "{user_idea}"
"""

# --- Cấu hình API Key ---
with st.sidebar:
    st.header("Cấu hình")
    try:
        google_api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("API Key đã được kết nối.", icon="✅")
    except (FileNotFoundError, KeyError):
        st.warning("Không tìm thấy API Key.", icon="⚠️")
        google_api_key = st.text_input("Nhập Google API Key:", type="password", label_visibility="collapsed")

if not google_api_key:
    st.error("Vui lòng nhập API Key để bắt đầu.")
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
    st.subheader("Ý tưởng hình sang video")
    uploaded_file = st.file_uploader("Tải ảnh lên (tùy chọn)", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        st.image(Image.open(uploaded_file), caption="Khung hình khởi đầu", use_container_width=True)
    st.image("https://ia600905.us.archive.org/0/items/Donate_png/1111111.jpg", caption="Donate", width=250)

with col2:
    st.subheader("Ý tưởng của bạn")
    style_options = ["Chân thực (Photorealistic)", "Hoạt hình 3D Pixar", "Anime Nhật Bản", "Tranh màu nước", "Phim tài liệu", "Phim cũ"]
    is_style_disabled = (uploaded_file is not None)
    
    selected_style = st.selectbox(
        "Chọn phong cách video:", options=style_options, index=0,
        disabled=is_style_disabled, help="Khi tải ảnh lên, phong cách sẽ được phân tích từ ảnh."
    )
    
    if is_style_disabled:
        st.info("ℹ️ Phong cách sẽ được tự động phân tích từ hình ảnh bạn đã tải lên.")

    user_idea = st.text_area(
        "Nhập ý tưởng video bằng tiếng Việt:", height=210,
        placeholder="Ví dụ: Thầy giáo bước lên bục giảng, mỉm cười nói: 'Xin chào các em'",
        key="user_idea_input"
    )
    
    form_col1, form_col2 = st.columns([1, 1])
    with form_col1:
        submitted = st.button("Tạo kịch bản", use_container_width=True)
    with form_col2:
        # --- BỎ CHỨC NĂNG DISABLED ---
        if st.button("Làm mới", use_container_width=True):
            st.session_state.user_idea = ""
            st.session_state.final_prompt = ""
            st.rerun()

    if submitted and user_idea:
        if uploaded_file:
            final_style = "Dựa trên phong cách của hình ảnh được cung cấp"
        else:
            final_style = selected_style
            
        with st.spinner("Đạo diễn AI đang phân tích và sáng tạo..."):
            response_text = ""
            try:
                request_for_gemini = META_PROMPT_FOR_GEMINI.format(user_idea=user_idea, style=final_style)
                response = gemini_model.generate_content(request_for_gemini)

                if not response.text or not response.text.strip():
                    st.error("Lỗi: AI không trả về nội dung. Yêu cầu của bạn có thể đã bị chặn.")
                    st.stop()

                start_index = response.text.find('{')
                end_index = response.text.rfind('}') + 1
                
                if start_index != -1 and end_index > start_index:
                    response_text = response.text[start_index:end_index]
                    extracted_data = json.loads(response_text)
                else:
                    st.error("Lỗi: Không tìm thấy dữ liệu JSON hợp lệ trong phản hồi của AI.")
                    st.write("Dữ liệu thô từ AI:", response.text)
                    st.stop()

                prompt_data = {
                    'subject_description': extracted_data.get('subject_description', 'a scene'),
                    'core_action': extracted_data.get('core_action', 'an action'),
                    'setting_description': extracted_data.get('setting_description', 'a location'),
                    'dialogue': extracted_data.get('dialogue', ''),
                    'mood': extracted_data.get('mood', 'neutral'),
                    'visual_effects': extracted_data.get('visual_effects', 'none'),
                    'voice_type': extracted_data.get('voice_type', 'a voice'),
                    'gesture': extracted_data.get('gesture', 'a natural gesture'),
                    'camera_motion': extracted_data.get('camera_motion', 'a stable, static shot')
                }
                
                prompt_data['style'] = final_style if not uploaded_file else "In the style of the provided image"

                if prompt_data['dialogue']:
                    prompt_data['dialogue_section'] = f"Animate mouth to sync with: \"{prompt_data['dialogue']}\"."
                    prompt_data['audio_section'] = f"Generate natural-sounding Vietnamese speech, spoken by {prompt_data['voice_type']}."
                else:
                    prompt_data['dialogue_section'] = "No dialogue."
                    prompt_data['audio_section'] = "No speech audio, only ambient sounds."

                template = IMAGE_TO_VIDEO_TEMPLATE if uploaded_file else TEXT_TO_VIDEO_TEMPLATE
                st.session_state.final_prompt = template.format(**prompt_data)

            except Exception as e:
                st.error(f"Đã xảy ra lỗi: {e}")

    elif submitted:
        st.warning("Vui lòng nhập ý tưởng của bạn.")

    # Luôn hiển thị kết quả nếu có
    if st.session_state.final_prompt:
        st.divider()
        st.subheader("Kịch bản Prompt chi tiết")
        st.text_area("Prompt (tiếng Anh) đã được tối ưu cho AI:", value=st.session_state.final_prompt, height=350)

# --- FOOTER ---
st.markdown('<div class="footer">Thiết kế bởi: phuongngoc091 | 0932 468 218</div>', unsafe_allow_html=True)
