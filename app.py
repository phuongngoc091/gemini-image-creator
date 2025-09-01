# app.py
import streamlit as st
import google.generativeai as genai
from PIL import Image
import json, re, unicodedata, random
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

def strip_diacritics(text: str) -> str:
    if not isinstance(text, str): return text
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def canonicalize_names(data: Dict[str, Any]) -> Dict[str, Any]:
    """Tên riêng không dấu cho mọi field TRỪ dialogue."""
    keys = [
        "subject_description","core_action","setting_description","mood",
        "camera_motion","lens","aperture","shutter","focus_pulling","lighting",
        "performance_direction","beats","action_design","shot_list","environment_fx",
        "color_grade","speed_ramping","continuity_anchors","visual_effects",
        "negative_cues","voice_type","gesture","sound_design","postprocessing"
    ]
    for k in keys:
        if k in data and isinstance(data[k], str):
            data[k] = strip_diacritics(data[k])
    return data

def has_speech_intent(text: str) -> bool:
    t = (text or "").lower()
    cues = [
        "lời thoại","thoại","nói","chào","hỏi","trả lời","đối thoại","thuyết minh",
        "voice","voiceover","voice over","nói chuyện","gọi","hét","la","phỏng vấn",
        "trò chuyện","đối đáp","đàm thoại","conversation","interview","debate"
    ]
    return any(cue in t for cue in cues)

def has_multi_dialogue_intent(text: str) -> bool:
    """Ý tưởng có vẻ là hội thoại giữa nhiều người?"""
    t = (text or "").lower()
    cues = [
        "đối thoại","nói chuyện với nhau","trò chuyện","hỏi đáp","đối đáp",
        "phỏng vấn","phỏng vấn nhau","conversation","interview","debate",
        "hội thoại","trao đổi"
    ]
    return any(cue in t for cue in cues)

def craft_dialogue(user_idea_vi: str) -> str:
    t = user_idea_vi.lower()
    if any(k in t for k in ["thầy","cô","giáo viên"]) and any(k in t for k in ["học sinh","lớp","lớp học"]):
        return random.choice([
            "Chào các em, hôm nay chúng ta bắt đầu bài học nhé!",
            "Xin chào các em, chúc cả lớp một buổi học hiệu quả!",
            "Chào các em, hôm nay thầy cô có bài học rất thú vị!"
        ])
    if "giới thiệu" in t:
        return "Xin chào mọi người, mình là Phuong Ngoc, rất vui được đồng hành cùng các bạn!"
    if "chào" in t:
        return "Xin chào mọi người, chúng ta bắt đầu nhé!"
    return "Chào mọi người, mình bắt đầu được chứ?"

def normalize_speaker(name: str) -> str:
    return strip_diacritics(name or "").strip() or "Speaker"

def safe_json_loads(raw: str) -> Dict[str, Any]:
    t = raw.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, flags=re.DOTALL|re.IGNORECASE)
    if m: t = m.group(1)
    t = t.replace("\u200b","").translate({ord("“"): '"', ord("”"): '"', ord("‘"): "'", ord("’"): "'"})
    t = re.sub(r",\s*([}\]])", r"\1", t)
    s, e = t.find("{"), t.rfind("}")
    if s != -1 and e > s: t = t[s:e+1]
    return json.loads(t)

# ==============================
# PROMPT TEMPLATES
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

# === META PROMPT (JSON-only, nhiều nhân vật khi cần) ===
META_PROMPT_FOR_GEMINI = """
You are a film director AI. Turn a short Vietnamese idea into a production-ready JSON for a video model.

HARD REQUIREMENTS
- OUTPUT: A single valid JSON object only (no markdown, no preface).
- LANGUAGE: All values MUST be in ENGLISH, EXCEPT "dialogue" and "dialogue_lines[].line_vi" which MUST remain in VIETNAMESE.
- Only output a NON-EMPTY "dialogue" if the user's idea clearly implies speech
  (mentions cues like: lời thoại/thoại/nói/chào/hỏi/trả lời/đối thoại/thuyết minh/voice...).
- If the idea implies **two or more people talking to each other** (dialogue, interview, conversation, debate),
  prefer "dialogue_lines" array with items:
  { speaker: ASCII (no Vietnamese diacritics), line_vi: VIETNAMESE text, voice_tone: short English tone hint }.
- Names must be ASCII without Vietnamese diacritics, e.g., "Teacher Phuong Ngoc".

FIELDS (keys)
- subject_description, core_action, setting_description, mood
- dialogue (optional, single-line VIETNAMESE) OR
- dialogue_lines (optional, array of lines as specified above)
- camera_motion, lens ("35mm"), aperture ("f/2.8"), shutter ("1/100"), focus_pulling
- lighting, performance_direction, beats
- action_design, shot_list, environment_fx, color_grade
- speed_ramping, continuity_anchors, visual_effects, negative_cues
- voice_type, gesture, sound_design, postprocessing
- duration (2–8), aspect_ratio ("16:9"|"9:16"|"1:1"|"21:9"), fps (24|25|30), motion_intensity ("low"|"medium"|"high")

CREATIVE PROCESS
- Read the user's idea and selected style: "{style}".
- If there are multiple speakers, keep total dialogue under ~8 seconds and split lines clearly.
- Keep all non-dialogue values in ENGLISH; keep dialogue content in VIETNAMESE.

User Idea (Vietnamese): "{user_idea}"
""".strip()

# ==============================
# SESSION STATE
# ==============================
if "final_prompt" not in st.session_state: st.session_state.final_prompt = ""
if "user_idea" not in st.session_state: st.session_state.user_idea = ""
if "style" not in st.session_state: st.session_state.style = DEFAULT_STYLE

def reset_form():
    st.session_state.pop("uploaded_image", None)
    st.session_state["user_idea"] = ""
    st.session_state["final_prompt"] = ""
    st.session_state["style"] = DEFAULT_STYLE
    # Không gọi st.rerun() trong callback

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
# GEMINI: JSON-only + schema
# ==============================
RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "subject_description": {"type": "string"},
        "core_action": {"type": "string"},
        "setting_description": {"type": "string"},
        "mood": {"type": "string"},
        "dialogue": {"type": "string"},
        "dialogue_lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "speaker": {"type": "string"},
                    "line_vi": {"type": "string"},
                    "voice_tone": {"type": "string"}
                }
            }
        },
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
            "temperature": 0.7,
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
    uploaded_file = st.file_uploader("Tải ảnh lên (tùy chọn)", type=["png","jpg","jpeg"], key="uploaded_image")
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
        with c1: duration = st.number_input("Thời lượng (s)", min_value=2, max_value=8, value=5, step=1)
        with c2: aspect_ratio = st.selectbox("Tỷ lệ khung", ["16:9","9:16","1:1","21:9"], index=0)
        with c3: fps = st.selectbox("FPS", [24,25,30], index=0)
        with c4: motion_intensity = st.selectbox("Độ mạnh chuyển động", ["low","medium","high"], index=1)

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

    bcol1, bcol2 = st.columns([1,1])
    with bcol1:
        submitted = st.button("Tạo kịch bản", use_container_width=True)
    with bcol2:
        st.button("Làm mới", use_container_width=True, on_click=reset_form)

    if submitted:
        if not user_idea.strip():
            st.warning("Vui lòng nhập ý tưởng của bạn.")
        else:
            style_en = style_to_en(selected_style)
            final_style_for_model = "Derived from the provided image" if uploaded_file else style_en

            with st.spinner("Đạo diễn AI đang phân tích và sáng tạo..."):
                try:
                    request_for_gemini = META_PROMPT_FOR_GEMINI.format(
                        user_idea=user_idea.strip(), style=final_style_for_model
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
                        with st.expander("Xem dữ liệu thô từ AI"): st.code(raw)
                        st.stop()

                    # Chuẩn hóa tên (trừ dialogue)
                    extracted = canonicalize_names(extracted)

                    # --- Dialogue logic ---
                    speech = has_speech_intent(user_idea)
                    multi   = has_multi_dialogue_intent(user_idea)

                    dialogue_section = "No dialogue."
                    audio_section = "No speech; only ambience and foley."
                    final_dialogue_single = ""

                    if speech:
                        if multi:
                            # Ưu tiên dialogue_lines nếu có
                            lines = extracted.get("dialogue_lines") if isinstance(extracted.get("dialogue_lines"), list) else []
                            rendered, voices = [], []
                            for item in lines:
                                spk = normalize_speaker(item.get("speaker","Speaker"))
                                line_vi = (item.get("line_vi") or "").strip()
                                if not line_vi: continue
                                tone = item.get("voice_tone","").strip()
                                rendered.append(f'{spk}: "{line_vi}"')
                                voices.append(f"{spk}: {tone or 'natural'}")
                            if rendered:
                                dialogue_section = "Use the following lines exactly (Vietnamese):\n" + "\n".join(rendered)
                                audio_section = "Generate separate Vietnamese voices with these tones: " + "; ".join(voices) + "."
                            else:
                                # fallback: một câu
                                final_dialogue_single = (extracted.get("dialogue") or "").strip() or craft_dialogue(user_idea)
                        else:
                            final_dialogue_single = (extracted.get("dialogue") or "").strip() or craft_dialogue(user_idea)

                        if final_dialogue_single:
                            dialogue_section = f'Animate mouth to sync with: "{final_dialogue_single}".'
                            voice = extracted.get("voice_type", "a natural voice")
                            audio_section = f"Generate natural Vietnamese speech, spoken by {voice}."

                    # --- Build prompt data ---
                    g = lambda k, d: extracted.get(k, d)
                    prompt_data = {
                        "subject_description": g("subject_description","a subject"),
                        "core_action": g("core_action","a simple action"),
                        "setting_description": g("setting_description","a location"),
                        "mood": g("mood","neutral"),
                        "camera_motion": g("camera_motion","gentle push-in"),
                        "lens": g("lens","35mm"),
                        "aperture": g("aperture","f/2.8"),
                        "shutter": g("shutter","1/100"),
                        "focus_pulling": g("focus_pulling","rack focus on key beats"),
                        "lighting": g("lighting","soft key light with warm rim"),
                        "performance_direction": g("performance_direction","confident, kind"),
                        "beats": g("beats","establishing, action, resolve"),
                        "action_design": g("action_design","clean, believable movement"),
                        "shot_list": g("shot_list","wide establishing; mid; close-up"),
                        "environment_fx": g("environment_fx","subtle dust motes"),
                        "color_grade": g("color_grade","warm natural"),
                        "speed_ramping": g("speed_ramping","none"),
                        "continuity_anchors": g("continuity_anchors","whiteboard at back"),
                        "visual_effects": g("visual_effects","none"),
                        "negative_cues": g("negative_cues","flicker, artifacts, deformed hands"),
                        "voice_type": g("voice_type","warm mid-range male"),
                        "gesture": g("gesture","gentle nod"),
                        "sound_design": g("sound_design","classroom ambience; clear speech"),
                        "postprocessing": g("postprocessing","subtle film grain"),
                        "duration": duration,
                        "aspect_ratio": aspect_ratio,
                        "fps": fps,
                        "motion_intensity": motion_intensity,
                        "style": "In the style of the provided image" if uploaded_file else style_en,
                        "audio_section": audio_section,
                        "dialogue_section": dialogue_section,
                    }

                    template = IMAGE_TO_VIDEO_TEMPLATE if uploaded_file else TEXT_TO_VIDEO_TEMPLATE
                    st.session_state.final_prompt = template.format(**prompt_data)
                    st.rerun()

                except Exception as e:
                    st.error("Đã xảy ra lỗi khi tạo kịch bản. Vui lòng thử lại.")
                    with st.expander("Chi tiết kỹ thuật"): st.exception(e)

# ==============================
# OUTPUT (có nút copy built-in)
# ==============================
if st.session_state.final_prompt:
    st.divider()
    st.subheader("Kịch bản Prompt chi tiết")
    st.markdown("**Prompt (tiếng Anh) đã được tối ưu cho AI:**")
    st.code(st.session_state.final_prompt, language="text")  # có nút Sao chép ở góc phải

# ==============================
# FOOTER
# ==============================
st.markdown('<div class="footer">Thiết kế bởi: phuongngoc091 | 0932 468 218</div>', unsafe_allow_html=True)
