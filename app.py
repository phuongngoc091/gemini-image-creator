# app.py
import streamlit as st
import google.generativeai as genai
from PIL import Image
import json

# ==============================
# CẤU HÌNH TRANG & CSS
# ==============================
st.set_page_config(layout="wide", page_title="Viết prompt tạo video với phuongngoc091")

APPLE_STYLE_CSS = """
<style>
    body, .stApp { background-color: #f0f2f5; color: #000000; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    h1, h2, h3 { font-weight: 600; }
    .stApp > header { background-color: transparent; }
    /* Button mặc định */
    .stButton > button {
        background-color: #007aff; color: white; border: none; border-radius: 12px;
        padding: 10px 24px; transition: all 0.2s ease-in-out; font-weight: 500;
    }
    .stButton > button:hover { background-color: #0056b3; color: white; }
    /* Button xám (container phải có class custom-gray-btn) */
    .custom-gray-btn .stButton > button {
        background-color: #e9e9eb; color: #000000;
    }
    .custom-gray-btn .stButton > button:hover {
        background-color: #d1d1d6; color: #000000;
    }
    /* Input */
    .stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #ffffff; border: 1px solid #d1d1d6; border-radius: 12px; padding: 10px;
    }
    .stTextArea textarea:focus, .stTextInput input:focus, .stSelectbox div[data-baseweb="select"] > div:focus-within {
        border-color: #007aff; box-shadow: 0 0 0 2px rgba(0, 122, 255, 0.2);
    }
    .stFileUploader { background-color: #ffffff; border: 2px dashed #d1d1d6; border-radius: 12px; padding: 8px; }
    .stSidebar { background-color: #f0f2f5; border-right: 1px solid #d1d1d6; }
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f0f2f5;
        color: #8a8a8a; text-align: center; padding: 10px; font-size: 14px;
    }
</style>
"""
st.markdown(APPLE_STYLE_CSS, unsafe_allow_html=True)

# ==============================
# HẰNG SỐ & TEMPLATE
# ==============================
STYLE_OPTIONS = [
    "Chân thực (Photorealistic)",
    "Hoạt hình 3D Pixar",
    "Anime Nhật Bản",
    "Tranh màu nước",
    "Phim tài liệu",
    "Phim cũ",
]
DEFAULT_STYLE = STYLE_OPTIONS[0]

IMAGE_TO_VIDEO_TEMPLATE = """
Style: {style}
Initial Frame: Use the provided image of {subject_description}.
Animation: Animate the subject to {core_action}.
Camera Motion: {camera_motion}.
Speech: {dialogue_section}
Visual Effects: Maintain the original atmosphere. Animate effects like {visual_effects}.
Audio: {audio_section}
""".strip()

TEXT_TO_VIDEO_TEMPLATE = """
Style: {style}
Scene Description: A cinematic, 8k, photorealistic shot of {subject_description} in {setting_description}. The mood is {mood}.
Animation: Animate the subject to {core_action}.
Camera Motion: {camera_motion}.
Speech: {dialogue_section}
Visual Effects: Create realistic effects like {visual_effects}.
Audio: {audio_section}
""".strip()

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
""".strip()

# ==============================
# SESSION STATE
# ==============================
if "final_prompt" not in st.session_state:
    st.session_state.final_prompt = ""
if "user_idea" not in st.session_state:
    st.session_state.user_idea = ""
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None
if "style" not in st.session_state:
    st.session_state.style = DEFAULT_STYLE

def reset_form():
    """Xoá toàn bộ dữ liệu form và rerun."""
    st.session_state.user_idea = ""
    st.session_state.final_prompt = ""
    st.session_state.uploaded_image = None
    st.session_state.style = DEFAULT_STYLE
    st.rerun()

# ==============================
# SIDEBAR: Cấu hình API Key
# ==============================
with st.sidebar:
    st.header("Cấu hình")
    try:
        google_api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("API Key đã được kết nối.", icon="✅")
    except (FileNotFoundError, KeyError):
        st.warning("Không tìm thấy API Key trong secrets.", icon="⚠️")
        google_api_key = st.text_input("Nhập Google API Key:", type="password")

if not google_api_key:
    st.error("Vui lòng nhập API Key để bắt đầu.")
    st.stop()

try:
    genai.configure(api_key=google_api_key)
    gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash")
except Exception as e:
    st.error(f"Lỗi cấu hình API Key: {e}")
    st.stop()

# ==============================
# TIÊU ĐỀ
# ==============================
st.title("Viết prompt tạo video với phuongngoc091")
st.caption("Biến ý tưởng đơn giản của bạn thành một kịch bản video chi tiết.")

# ==============================
# GIAO DIỆN CHÍNH
# ==============================
col1, col2 = st.columns([1, 2], gap="large")

with col1:
    st.subheader("Ý tưởng hình sang video")
    uploaded_file = st.file_uploader(
        "Tải ảnh lên (tùy chọn)",
        type=["png", "jpg", "jpeg"],
        key="uploaded_image"
    )
    if uploaded_file:
        try:
            st.image(Image.open(uploaded_file), caption="Khung hình khởi đầu", use_container_width=True)
        except Exception:
            st.warning("Không hiển thị được ảnh vừa tải. Vui lòng thử ảnh khác.")
    st.image("https://ia600905.us.archive.org/0/items/Donate_png/1111111.jpg", caption="Donate", width=250)

with col2:
    st.subheader("Ý tưởng của bạn")

    is_style_disabled = (uploaded_file is not None)
    selected_style = st.selectbox(
        "Chọn phong cách video:",
        options=STYLE_OPTIONS,
        index=STYLE_OPTIONS.index(st.session_state.style) if st.session_state.style in STYLE_OPTIONS else 0,
        key="style",
        disabled=is_style_disabled,
        help="Khi tải ảnh lên, phong cách sẽ được phân tích từ ảnh."
    )
    if is_style_disabled:
        st.info("ℹ️ Phong cách sẽ được tự động phân tích từ hình ảnh bạn đã tải lên.")

    user_idea = st.text_area(
        "Nhập ý tưởng video bằng tiếng Việt:",
        height=210,
        placeholder="Ví dụ: Thầy giáo bước lên bục giảng, mỉm cười nói: 'Xin chào các em'",
        key="user_idea"
    )

    form_col1, form_col2 = st.columns([1, 1])
    with form_col1:
        submitted = st.button("Tạo kịch bản", use_container_width=True)
    with form_col2:
        # Bọc vào container riêng để style xám áp dụng chắc chắn
        with st.container():
            st.markdown('<div class="custom-gray-btn">', unsafe_allow_html=True)
            st.button("Làm mới", use_container_width=True, on_click=reset_form)
            st.markdown('</div>', unsafe_allow_html=True)

    # ==========================
    # XỬ LÝ TẠO PROMPT
    # ==========================
    if submitted:
        if not user_idea.strip():
            st.warning("Vui lòng nhập ý tưởng của bạn.")
        else:
            final_style = "Dựa trên phong cách của hình ảnh được cung cấp" if uploaded_file else selected_style

            with st.spinner("Đạo diễn AI đang phân tích và sáng tạo..."):
                try:
                    request_for_gemini = META_PROMPT_FOR_GEMINI.format(
                        user_idea=user_idea.strip(),
                        style=final_style
                    )
                    response = gemini_model.generate_content(request_for_gemini)

                    # Kiểm tra nội dung trả về
                    if not getattr(response, "text", None) or not response.text.strip():
                        st.error("Lỗi: AI không trả về nội dung. Yêu cầu của bạn có thể đã bị chặn.")
                        st.stop()

                    # Cố gắng cắt đúng JSON
                    raw_text = response.text.strip()
                    start_index = raw_text.find("{")
                    end_index = raw_text.rfind("}") + 1

                    if start_index == -1 or end_index <= start_index:
                        st.error("Lỗi: Không tìm thấy dữ liệu JSON hợp lệ trong phản hồi của AI.")
                        with st.expander("Xem dữ liệu thô từ AI"):
                            st.code(raw_text)
                        st.stop()

                    response_text = raw_text[start_index:end_index]

                    # Parse JSON
                    extracted_data = json.loads(response_text)

                    # Ghép dữ liệu
                    prompt_data = {
                        "subject_description": extracted_data.get("subject_description", "a scene"),
                        "core_action": extracted_data.get("core_action", "an action"),
                        "setting_description": extracted_data.get("setting_description", "a location"),
                        "dialogue": extracted_data.get("dialogue", ""),
                        "mood": extracted_data.get("mood", "neutral"),
                        "visual_effects": extracted_data.get("visual_effects", "none"),
                        "voice_type": extracted_data.get("voice_type", "a voice"),
                        "gesture": extracted_data.get("gesture", "a natural gesture"),
                        "camera_motion": extracted_data.get("camera_motion", "a stable, static shot"),
                    }

                    # Style hiển thị trong prompt
                    prompt_data["style"] = (
                        "In the style of the provided image" if uploaded_file else final_style
                    )

                    # Thoại & audio
                    if prompt_data["dialogue"]:
                        prompt_data["dialogue_section"] = f'Animate mouth to sync with: "{prompt_data["dialogue"]}".'
                        prompt_data["audio_section"] = f'Generate natural-sounding Vietnamese speech, spoken by {prompt_data["voice_type"]}.'
                    else:
                        prompt_data["dialogue_section"] = "No dialogue."
                        prompt_data["audio_section"] = "No speech audio, only ambient sounds."

                    # Chọn template theo việc có ảnh hay không
                    template = IMAGE_TO_VIDEO_TEMPLATE if uploaded_file else TEXT_TO_VIDEO_TEMPLATE
                    st.session_state.final_prompt = template.format(**prompt_data)

                    # Rerun để đảm bảo text_area kết quả hiển thị tức thì (nếu muốn có thể bỏ)
                    st.rerun()

                except json.JSONDecodeError as je:
                    st.error("Lỗi phân tích JSON từ AI. Vui lòng thử lại hoặc điều chỉnh ý tưởng.")
                    with st.expander("Chi tiết lỗi JSON"):
                        st.exception(je)
                        st.write("Phản hồi (đã cắt theo dấu ngoặc):")
                        st.code(response_text if 'response_text' in locals() else "", language="json")
                except Exception as e:
                    st.error("Đã xảy ra lỗi không mong muốn khi tạo kịch bản. Vui lòng thử lại.")
                    with st.expander("Chi tiết kỹ thuật"):
                        st.exception(e)

    # ==========================
    # HIỂN THỊ KẾT QUẢ
    # ==========================
    if st.session_state.final_prompt:
        st.divider()
        st.subheader("Kịch bản Prompt chi tiết")
        st.text_area(
            "Prompt (tiếng Anh) đã được tối ưu cho AI:",
            value=st.session_state.final_prompt,
            height=350
        )

# ==============================
# FOOTER
# ==============================
st.markdown('<div class="footer">Thiết kế bởi: phuongngoc091 | 0932 468 218</div>', unsafe_allow_html=True)
