# app.py
import streamlit as st
import google.generativeai as genai
from PIL import Image
import json, re
from typing import Any, Dict

# ==============================
# PAGE & CSS
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
      width: 100%;
  }
  .stButton > button:hover { background-color: #0056b3; color: white; }

  /* Inputs */
  .stTextArea textarea, .stTextInput input {
      background-color: #ffffff; border: 1px solid #d1d1d6; border-radius: 12px; padding: 10px;
  }
  .stTextArea textarea:focus, .stTextInput input:focus {
      border-color: #007aff; box-shadow: 0 0 0 2px rgba(0,122,255,.2);
  }

  /* Safe styling cho selectbox */
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
# CONSTANTS & HELPERS
# ==============================
STYLE_OPTIONS = [
    "Chân thực (Photorealistic)",
    "Hoạt hình 3D Pixar (3D Pixar)",
    "Anime Nhật Bản (Anime)",
    "Tranh màu nước (Watercolor)",
    "Phim tài liệu (Documentary)",
    "Phim cũ (Vintage Film)",
]
DEFAULT_STYLE = STYLE_OPTIONS[0]

def style_to_en(label: str) -> str:
    m = re.search(r"\(([^)]+)\)", label)
    return m.group(1).strip() if m else label.strip()

def safe_json_loads(raw: str) -> Dict[str, Any]:
    """Parse JSON dù model có trả kèm markdown/quote lạ."""
    t = raw.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, flags=re.DOTALL|re.IGNORECASE)
    if m: t = m.group(1)
    t = t.replace("\u200b", "").translate({ord("“"): '"', ord("”"): '"', ord("‘"): "'", ord("’"): "'"})
    t = re.sub(r",\s*([}\]])", r"\1", t)
    s, e = t.find("{"), t.rfind("}")
    if s != -1 and e > s: t = t[s:e+1]
    return json.loads(t)

# ==============================
# PROMPT TEMPLATES (nâng cấp điện ảnh)
# ==============================
IMAGE_TO_VIDEO_TEMPLATE = """
Style: {style}
Initial Frame: Use the provided image of {subject_description}.
Performance Direction: {performance_direction}
Beats: {beats}
Action Design: {action_design}
Shot List: {shot_list}
Camera & Lens: {camera_motion} | Lens: {lens} | Aperture: {aperture} | Shutter: {shutter} | Focus Pulling: {focus_pulling}
Lighting & Grade: {lighting} | Color grade: {color_grade}
Environment FX: {environment_fx}
VFX: Maintain the original atmosphere. Animate effects like {visual_effects}. Avoid: {negative_cues}
Speed & Ramps: {speed_ramping}
Continuity: {continuity_anchors}
Sound Design: {sound_design}
Audio: {audio_section}
Post: {postprocessing}
Technical: duration {duration}s | aspect ratio {aspect_ratio} | fps {fps} | motion intensity {motion_intensity}
""".strip()

TEXT_TO_VIDEO_TEMPLATE = """
Style: {style}
Scene: A cinematic, 8k shot of {subject_description} in {setting_description}. Mood: {mood}.
Performance Direction: {performance_direction}
Beats: {beats}
Action Design: {action_design}
Shot List: {shot_list}
Camera & Lens: {camera_motion} | Lens: {lens} | Aperture: {aperture} | Shutter: {shutter} | Focus Pulling: {focus_pulling}
Lighting & Grade: {lighting} | Color grade: {color_grade}
Environment FX: {environment_fx}
VFX: Create realistic effects like {visual_effects}. Avoid: {negative_cues}
Speed & Ramps: {speed_ramping}
Continuity: {continuity_anchors}
Sound Design: {sound_design}
Audio: {audio_section}
Post: {postprocessing}
Technical: duration {duration}s | aspect ratio {aspect_ratio} | fps {fps} | motion intensity {motion_intensity}
""".strip()

META_PROMPT_FOR_GEMINI = """
You are a film director AI. Turn a short Vietnamese idea into a production-ready JSON for a video model.

HARD REQUIREMENTS
- OUTPUT: A single valid JSON object only (no markdown, no preface).
- LANGUAGE: All values MUST be in ENGLISH, EXCEPT "dialogue" which MUST remain in VIETNAMESE.
- If something is missing, pick cinematic defaults (avoid nulls).

FIELDS (keys)
- subject_description, core_action, setting_description, mood
- dialogue (VIETNAMESE, max ~8s)
- camera_motion, lens (e.g. "35mm"), aperture ("f/2.8"), shutter ("1/100"), focus_pulling
- lighting, performance_direction, beats (comma-separated micro-beats)
- action_design (stunts/choreo/vehicle dynamics), shot_list (key shots as a concise list)
- environment_fx (rain, smoke, debris, reflections), color_grade (e.g., teal-orange high contrast)
- speed_ramping (when to ramp speed/slow-mo), continuity_anchors (objects or lines that persist between shots)
- visual_effects, negative_cues (avoid artifacts: extra limbs/flicker/etc.)
- voice_type, gesture, sound_design, postprocessing
- duration (2–8), aspect_ratio ("16:9"|"9:16"|"1:1"|"21:9"), fps (24|25|30), motion_intensity ("low"|"medium"|"high")

CREATIVE PROCESS
- Read the user's idea and selected style: "{style}".
- Infer genre and push cinematic specificity (for action: clear geography, momentum, cause-effect, stunt notes).
- Keep "dialogue" in VIETNAMESE; everything else in ENGLISH.

User Idea (Vietnamese): "{user_idea}"
""".strip()

# ==============================
# SESSION STATE (đừng init uploaded_image để khỏi xung đột)
# ==============================
if "final_prompt" not in st.session_state: st.session_state.final_prompt = ""
if "user_idea" not in st.session_state: st.session_state.user_idea = ""
if "style" not in st.session_state: st.session_state.style = DEFAULT_STYLE

def reset_form():
    """Callback: xoá sạch state rồi để Streamlit tự rerun."""
    st.session_state.pop("uploaded_image", None)
    st.session_state["user_idea"] = ""
    st.session_state["final_prompt"] = ""
    st.session_state["style"] = DEFAULT_STYLE
    # KHÔNG gọi st.rerun() trong callback

# ==============================
# SIDEBAR: API KEY
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

# ==============================
# GEMINI: JSON-only + schema mở rộng
# ==============================
RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "subject_description": {"type": "string"},
        "core_action": {"type": "string"},
        "setting_description": {"type": "string"},
        "mood": {"type": "string"},
        "dialogue": {"type": "string"},
        "camera_motion": {"type": "string"},
        "lens": {"type": "string"},
        "aperture": {"type": "string"},
        "shutter": {"type": "string"},
        "focus_pulling": {"type": "string"},
        "lighting": {"type": "string"},
        "performance_direction": {"type": "string"},
        "beats": {"type": "string"},
        "action_design": {"type": "string"},
        "shot_list": {"type": "string"},
        "environment_fx": {"type": "string"},
        "color_grade": {"type": "string"},
        "speed_ramping": {"type": "string"},
        "continuity_anchors": {"type": "string"},
        "visual_effects": {"type": "string"},
        "negative_cues": {"type": "string"},
        "voice_type": {"type": "string"},
        "gesture": {"type": "string"},
        "sound_design": {"type": "string"},
        "postprocessing": {"type": "string"},
        "duration": {"type": "number"},
        "aspect_ratio": {"type": "string"},
        "fps": {"type": "number"},
        "motion_intensity": {"type": "string"},
    },
}

try:
    genai.configure(api_key=google_api_key)
    gemini_model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config={
            "temperature": 0.7,           # giữ chất lượng ổn định hơn
            "max_output_tokens": 2048,
            "response_mime_type": "application/json",
            "response_schema": RESPONSE_SCHEMA,
        },
    )
except Exception as e:
    st.error(f"Lỗi cấu hình API Key: {e}")
    st.stop()

# ==============================
# UI
# ==============================
st.title("Viết prompt tạo video với phuongngoc091")
st.caption("Biến ý tưởng đơn giản của bạn thành một kịch bản video chi tiết.")

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

    with st.expander("Tùy chọn nâng cao (kỹ thuật)", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            duration = st.number_input("Thời lượng (s)", min_value=2, max_value=8, value=8, step=1)
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

    # ---- 2 NÚT NGANG HÀNG ----
    bcol1, bcol2 = st.columns([1, 1])
    with bcol1:
        submitted = st.button("Tạo kịch bản", key="btn_create", use_container_width=True)
    with bcol2:
        # dùng callback để tránh StreamlitAPIException
        st.button("Làm mới", key="btn_reset", use_container_width=True, on_click=reset_form)

    # ==========================
    # XỬ LÝ TẠO PROMPT
    # ==========================
    if submitted:
        if not user_idea.strip():
            st.warning("Vui lòng nhập ý tưởng của bạn.")
        else:
            style_en = style_to_en(selected_style)
            final_style_for_model = "Derived from the provided image" if uploaded_file else style_en

            with st.spinner("Đạo diễn AI đang phân tích và sáng tạo..."):
                try:
                    request_for_gemini = META_PROMPT_FOR_GEMINI.format(
                        user_idea=user_idea.strip(),
                        style=final_style_for_model
                    )
                    response = gemini_model.generate_content(request_for_gemini)
                    raw = (response.text or "").strip()
                    if not raw:
                        st.error("Lỗi: AI không trả về nội dung.")
                        st.stop()

                    try:
                        extracted = safe_json_loads(raw)
                    except Exception:
                        st.error("Lỗi: Không tìm thấy JSON hợp lệ trong phản hồi của AI.")
                        with st.expander("Xem dữ liệu thô từ AI"):
                            st.code(raw)
                        st.stop()

                    g = lambda k, d: extracted.get(k, d)
                    prompt_data = {
                        "subject_description": g("subject_description", "a subject"),
                        "core_action": g("core_action", "a simple action"),
                        "setting_description": g("setting_description", "a location"),
                        "dialogue": g("dialogue", ""),
                        "mood": g("mood", "neutral"),
                        "camera_motion": g("camera_motion", "dynamic tracking with gentle push-in"),
                        "lens": g("lens", "35mm"),
                        "aperture": g("aperture", "f/2.8"),
                        "shutter": g("shutter", "1/100"),
                        "focus_pulling": g("focus_pulling", "rack focus on key beats"),
                        "lighting": g("lighting", "soft key light with warm rim; motivated practicals"),
                        "performance_direction": g("performance_direction", "grounded intensity; clear eyelines"),
                        "beats": g("beats", "establishing, escalation, close-quarters, payoff"),
                        "action_design": g("action_design", "clean geography; believable physics; near-misses and swerves"),
                        "shot_list": g("shot_list", "wide establishing; low-angle tracking; OTS; insert of throttle; hero close-up"),
                        "environment_fx": g("environment_fx", "sparks, smoke wisps, wet asphalt reflections"),
                        "color_grade": g("color_grade", "teal-orange with high contrast"),
                        "speed_ramping": g("speed_ramping", "90–110% micro ramps; one 60% slow-mo hero beat"),
                        "continuity_anchors": g("continuity_anchors", "neon billboard on left; cracked taxi windshield"),
                        "visual_effects": g("visual_effects", "heat haze, light streaks"),
                        "negative_cues": g("negative_cues", "flicker, extra limbs, deformed hands, melting textures"),
                        "voice_type": g("voice_type", "gritty male voice"),
                        "gesture": g("gesture", "firm grip, head tilt"),
                        "sound_design": g("sound_design", "engine roar, tire squeal, Doppler police sirens, metal clanks, rising adrenaline music"),
                        "postprocessing": g("postprocessing", "subtle film grain; gentle vignette"),
                        "duration": duration,
                        "aspect_ratio": aspect_ratio,
                        "fps": fps,
                        "motion_intensity": motion_intensity,
                    }

                    prompt_data["style"] = "In the style of the provided image" if uploaded_file else style_en

                    if prompt_data["dialogue"]:
                        prompt_data["audio_section"] = f'Generate natural Vietnamese speech, spoken by {prompt_data["voice_type"]}.'
                    else:
                        prompt_data["audio_section"] = "No speech; only ambience and foley."

                    template = IMAGE_TO_VIDEO_TEMPLATE if uploaded_file else TEXT_TO_VIDEO_TEMPLATE
                    st.session_state.final_prompt = template.format(**prompt_data)

                    st.rerun()  # ngoài callback: rerun để show kết quả ngay

                except Exception as e:
                    st.error("Đã xảy ra lỗi khi tạo kịch bản. Vui lòng thử lại.")
                    with st.expander("Chi tiết kỹ thuật"):
                        st.exception(e)

# ==============================
# OUTPUT
# ==============================
if st.session_state.final_prompt:
    st.divider()
    st.subheader("Kịch bản Prompt chi tiết")
    st.text_area(
        "Prompt (tiếng Anh) đã được tối ưu cho AI:",
        value=st.session_state.final_prompt,
        height=430
    )

# ==============================
# FOOTER
# ==============================
st.markdown('<div class="footer">Thiết kế bởi: phuongngoc091 | 0932 468 218</div>', unsafe_allow_html=True)
