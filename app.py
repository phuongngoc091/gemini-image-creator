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

  /* Text inputs */
  .stTextArea textarea, .stTextInput input {
      background-color: #ffffff; border: 1px solid #d1d1d6; border-radius: 12px; padding: 10px;
  }
  .stTextArea textarea:focus, .stTextInput input:focus {
      border-color: #007aff; box-shadow: 0 0 0 2px rgba(0,122,255,.2);
  }

  /* Safe styling cho selectbox (không động > div) */
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
# CONSTANTS & TEMPLATES
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
    """Trả về phần tiếng Anh trong ngoặc. Nếu không có, trả về nguyên chuỗi."""
    m = re.search(r"\(([^)]+)\)", label)
    return m.group(1).strip() if m else label.strip()

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
# SESSION STATE
# ==============================
if "final_prompt" not in st.session_state:
    st.session_state.final_prompt = ""
if "user_idea" not in st.session_state:
    st.session_state.user_idea = ""
if "style" not in st.session_state:
    st.session_state.style = DEFAULT_STYLE

def reset_form():
    """Xoá toàn bộ dữ liệu form (không gọi st.rerun trong callback)."""
    st.session_state.pop("uploaded_image", None)
    st.session_state["user_idea"] = ""
    st.session_state["final_prompt"] = ""
    st.session_state["style"] = DEFAULT_STYLE

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
# GEMINI: force JSON + safe parser
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
        "lighting": {"type": "string"},
        "performance_direction": {"type": "string"},
        "beats": {"type": "string"},
        "visual_effects": {"type": "string"},
        "negative_cues": {"type": "string"},
        "voice_type": {"type": "string"},
        "gesture": {"type": "string"},
        "sound_design": {"type": "string"},
        "duration": {"type": "number"},
        "aspect_ratio": {"type": "string"},
        "fps": {"type": "number"},
        "motion_intensity": {"type": "string"},
    },
}

def safe_json_loads(raw: str) -> Dict[str, Any]:
    """Cố gắng parse JSON từ mọi tình huống."""
    t = raw.strip()
    # code fence
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, flags=re.DOTALL|re.IGNORECASE)
    if m:
        t = m.group(1)
    # normalize quotes / trailing commas
    t = t.replace("\u200b", "")
    t = t.translate({ord("“"): '"', ord("”"): '"', ord("‘"): "'", ord("’"): "'"})
    t = re.sub(r",\s*([}\]])", r"\1", t)
    # try cut braces if extra text
    s, e = t.find("{"), t.rfind("}")
    if s != -1 and e > s: t = t[s:e+1]
    return json.loads(t)

try:
    genai.configure(api_key=google_api_key)
    gemini_model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config={
            "temperature": 0.8,
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
    st.subheader("Ý tưởng h
