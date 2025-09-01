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

  /* Buttons */
  .stButton > button {
      background-color: #007aff; color: white; border: none; border-radius: 12px;
      padding: 10px 24px; transition: all 0.2s ease-in-out; font-weight: 500;
  }
  .stButton > button:hover { background-color: #0056b3; color: white; }
  .custom-gray-btn .stButton > button { background-color: #e9e9eb; color: #000000; }
  .custom-gray-btn .stButton > button:hover { background-color: #d1d1d6; color: #000000; }

  /* Text inputs */
  .stTextArea textarea, .stTextInput input {
      background-color: #ffffff; border: 1px solid #d1d1d6; border-radius: 12px; padding: 10px;
  }
  .stTextArea textarea:focus, .stTextInput input:focus {
      border-color: #007aff; box-shadow: 0 0 0 2px rgba(0,122,255,.2);
  }

  /* ✅ Safe styling cho selectbox (không động > div) */
  .stSelectbox [data-baseweb="select"] {
      background-color: #ffffff; border: 1px solid #d1d1d6; border-radius: 12px;
  }
  .stSelectbox [data-baseweb="select"]:focus-within {
      border-color: #007aff; box-shadow: 0 0 0 2px rgba(0,122,255,.2);
  }
  .stSelectbox [data-baseweb="select"] * { color: #000000; }

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
Performance Direction: {performance_direction}
Beats: {beats}
Camera & Lens: {camera_motion} | Lens: {lens} | Aperture: {aperture} | Shutter: {shutter}
Lighting: {lighting}
VFX: Maintain the original atmosphere. Animate effects like {visual_effects}. Avoid: {negative_cues}
Sound Design: {sound_design}
Audio: {audio_section}
Technical: duration {duration}s | aspect ratio {aspect_ratio} | fps {fps} | motion intensity {motion_intensity}
""".strip()

TEXT_TO_VIDEO_TEMPLATE = """
Style: {style}
Scene: A cinematic, 8k shot of {subject_description} in {setting_description}. Mood: {mood}.
Performance Direction: {performance_direction}
Beats: {beats}
Camera & Lens: {camera_motion} | Lens: {lens} | Aperture: {aperture} | Shutter: {shutter}
Lighting: {lighting}
VFX: Create realistic effects like {visual_effects}. Avoid: {negative_cues}
Sound Design: {sound_design}
Audio: {audio_section}
Technical: duration {duration}s | aspect ratio {aspect_ratio} | fps {fps} | motion intensity {motion_intensity}
""".strip()

META_PROMPT_FOR_GEMINI = """
You are a film director AI. Convert a short Vietnamese idea into a production-ready JSON for a video generation model.

HARD REQUIREMENTS:
- OUTPUT: A single valid JSON object only. No preface, no markdown.
- LANGUAGE: All values MUST be in ENGLISH, EXCEPT the "dialogue" field which MUST remain in VIETNAMESE.
- If a field is unknown, choose a sensible cinematic default (do not leave null).

FIELDS TO PRODUCE (keys):
- subject_description, core_action, setting_description, mood
- dialogue (VIETNAMESE, under 8 seconds total)
- camera_motion, lens (e.g., "35mm"), aperture (e.g., "f/2.8"), shutter (e.g., "1/100")
- lighting, performance_direction, beats (comma-separated micro-beats)
- visual_effects, negative_cues
- voice_type, gesture, sound_design
- duration (2–8), aspect_ratio ("16:9" | "9:16" | "1:1" | "21:9"), fps (24 | 25 | 30), motion_intensity ("low" | "medium" | "high")

CREATIVE PROCESS:
- Read the user's idea and selected style: "{style}".
- Expand into a cinematic plan with clear camera, lighting, performance, and beats.
- Keep "dialogue" in VIETNAMESE; everything else in ENGLISH.

User Idea (Vietnamese): "{user_idea}"
""".strip()

# ==============================
# SESSION STATE (KHÔNG init uploaded_image để tránh xung đột)
# ==============================
if "final_prompt" not in st.session_state:
    st.session_state.final_prompt = ""
if "user_idea" not in st.session_state:
    st.session_state.user_idea = ""
if "style" not in st.session_state:
    st.session_state.style = DEFAULT_STYLE

def reset_form():
    """Xoá toàn bộ dữ liệu form. Callback tự rerun, không gọi st.rerun() ở đây."""
    st.session_state.pop("uploaded_image", None)  # quan trọng: xoá key file_uploader, không gán None
    st.session_state["user_idea"] = ""
    st.session_state["final_prompt"] = ""
    st.session_state["style"] = DEFAULT_STYLE

# ==============================
# SIDEBAR: API Key
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

# Khởi tạo model
try:
    genai.configure(api_key=google_api_key)
    gemini_model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config={"temperature": 0.8, "max_output_tokens": 2048},
    )
except Exception as e:
    st.error(f"Lỗi cấu hình API Key: {e}")
    st.stop()

# ==============================
# UI CHÍNH
# ==============================
st.title("Viết prompt tạo video với phuongngoc091")
st.caption("Biến ý tưởng đơn giản của bạn thành một kịch bản video chi tiết.")

col1, col2 = st.columns([1, 2], gap="large")

with col1:
    st.subheader("Ý tưởng hình sang video")
    uploaded_file = st.file_uploader(
        "Tải ảnh lên (tùy chọn)",
        type=["png", "jpg", "jpeg"],
        key="uploaded_image"   # có key để reset bằng pop()
    )
    if uploaded_file:
        try:
            st.image(Image.open(uploaded_file), caption="Khung hình khởi đầu", use_container_width=True)
        except Exception:
            st.warning("Không hiển thị được ảnh vừa tải. Vui lòng thử ảnh khác.")
    st.image("https://ia600905.us.archive.org/0/items/Donate_png/1111111.jpg", caption="Donate", width=250)

with col2:
    st.subheader("Ý tưởng của bạn")

    # Tùy chọn kỹ thuật
    with st.expander("Tùy chọn nâng cao (kỹ thuật)", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            duration = st.number_input("Thời lượng (s)", min_value=2, max_value=8, value=5, step=1)
        with c2:
            aspect_ratio = st.selectbox("Tỷ lệ khung", ["16:9", "9:16", "1:1", "21:9"], index=0)
        with c3:
            fps = st.selectbox("FPS", [24, 25, 30], index=0)
        with c4:
            motion_intensity = st.selectbox("Độ mạnh chuyển động", ["low", "medium", "high"], index=1)

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
        with st.container():
            st.markdown('<div class="custom-gray-btn">', unsafe_allow_html=True)
            st.button("Làm mới", use_container_width=True, on_click=reset_form)
            st.markdown("</div>", unsafe_allow_html=True)

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

                    if not getattr(response, "text", None) or not response.text.strip():
                        st.error("Lỗi: AI không trả về nội dung. Yêu cầu của bạn có thể đã bị chặn.")
                        st.stop()

                    raw_text = response.text.strip()
                    start_index = raw_text.find("{")
                    end_index = raw_text.rfind("}") + 1
                    if start_index == -1 or end_index <= start_index:
                        st.error("Lỗi: Không tìm thấy JSON hợp lệ trong phản hồi của AI.")
                        with st.expander("Xem dữ liệu thô từ AI"):
                            st.code(raw_text)
                        st.stop()

                    response_text = raw_text[start_index:end_index]
                    extracted_data = json.loads(response_text)

                    def _get(k, default): return extracted_data.get(k, default)

                    prompt_data = {
                        "subject_description": _get("subject_description", "a subject"),
                        "core_action": _get("core_action", "a simple action"),
                        "setting_description": _get("setting_description", "a location"),
                        "dialogue": _get("dialogue", ""),
                        "mood": _get("mood", "neutral"),
                        "visual_effects": _get("visual_effects", "subtle particles"),
                        "negative_cues": _get("negative_cues", "flicker, artifacts, extra limbs, deformed hands"),
                        "voice_type": _get("voice_type", "a warm voice"),
                        "gesture": _get("gesture", "natural gesture"),
                        "camera_motion": _get("camera_motion", "gentle push-in"),
                        "lens": _get("lens", "35mm"),
                        "aperture": _get("aperture", "f/2.8"),
                        "shutter": _get("shutter", "1/100"),
                        "lighting": _get("lighting", "soft key light with warm rim"),
                        "performance_direction": _get("performance_direction", "subtle smile, confident posture"),
                        "beats": _get("beats", "establishing, action, close-up, resolve"),
                        "duration": duration,
                        "aspect_ratio": aspect_ratio,
                        "fps": fps,
                        "motion_intensity": motion_intensity,
                    }

                    prompt_data["style"] = "In the style of the provided image" if uploaded_file else final_style

                    if prompt_data["dialogue"]:
                        prompt_data["audio_section"] = f'Generate natural Vietnamese speech, spoken by {prompt_data["voice_type"]}.'
                    else:
                        prompt_data["audio_section"] = "No speech; only ambience and foley."

                    prompt_data["sound_design"] = _get(
                        "sound_design",
                        "subtle room tone, soft footsteps, light music bed"
                    )

                    template = IMAGE_TO_VIDEO_TEMPLATE if uploaded_file else TEXT_TO_VIDEO_TEMPLATE
                    st.session_state.final_prompt = template.format(**prompt_data)

                    # ngoài callback -> rerun để hiển thị kết quả ngay
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
            height=380
        )

# ==============================
# FOOTER
# ==============================
st.markdown('<div class="footer">Thiết kế bởi: phuongngoc091 | 0932 468 218</div>', unsafe_allow_html=True)
