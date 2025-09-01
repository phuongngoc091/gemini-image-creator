import streamlit as st
import google.generativeai as genai
from PIL import Image
import json

# --- Cấu hình trang và tiêu đề ---
st.set_page_config(layout="wide", page_title="Trợ lý Sáng tạo Video AI")
st.title("🎬 Trợ lý Sáng tạo Video AI")
st.caption("Tạo kịch bản video chi tiết từ ý tưởng đơn giản của bạn.")

# --- CÁC KHUÔN MẪU PROMPT (TEMPLATES) ---

# Khuôn mẫu cho Option 1 (Tải ảnh lên)
IMAGE_TO_VIDEO_TEMPLATE = """
Initial Frame: Use the provided image of {subject_description}.

Animation:
- Movement: Animate the subject to {core_action}.
- Speech: {dialogue_section}
- Gesture: While speaking or moving, the subject makes a natural gesture, such as {gesture}.
- Continued Movement: After the main action, the subject continues their action naturally to complete the scene.

Visual Effects: Maintain the atmosphere, lighting, and environmental effects from the original image. Ensure effects like {visual_effects} are animated and consistent throughout the 8-second clip.

Audio: {audio_section}
"""

# Khuôn mẫu cho Option 2 (Chỉ có ý tưởng)
TEXT_TO_VIDEO_TEMPLATE = """
Scene Description: A cinematic, ultra-detailed, 8k, photorealistic shot of {subject_description}. The setting is {setting_description}. The lighting is dramatic and fits the mood.

Animation:
- Movement: Animate the subject to {core_action}.
- Speech: {dialogue_section}
- Gesture: While speaking or moving, the subject makes a natural gesture, such as {gesture}.
- Continued Movement: After the main action, the subject continues their action naturally to complete the scene.

Visual Effects: The atmosphere is {mood}. Create realistic environmental effects like {visual_effects} for the 8-second clip.

Audio: {audio_section}
"""

# --- SIÊU PROMPT DÀNH CHO "BIÊN KỊCH AI" (PHIÊN BẢN NÂNG CẤP) ---
META_PROMPT_FOR_GEMINI = """
You are an expert creative director and scriptwriter for a cutting-edge text-to-video AI model. Your task is to transform a user's simple idea (in Vietnamese) into a rich, detailed, and technically precise cinematic prompt in English.

**Analyze the user's idea by following these steps:**
1.  **Deconstruct the core elements:** Identify the main subject, the core action, and the setting from the user's idea.
2.  **Envision the scene:** Based on the core elements, creatively imagine the mood, lighting, and cinematic style. Think like a director. What would make this scene powerful?
3.  **Process the dialogue:**
    - If dialogue exists, rewrite it to be impactful and concise (under 8 seconds). Keep it in the original Vietnamese.
    - If no dialogue exists, leave the dialogue field empty.
4.  **Translate and Structure:** Translate all descriptive elements into fluent, evocative English. Keep the dialogue in Vietnamese. Structure the final output as a single, clean JSON object.

**Here is an example of the quality I expect:**
-   **User's simple idea (Vietnamese):** "cô gái đi trên Cầu Vàng có tuyết rơi và nói 'Chào mọi người! Tuyết rơi đẹp không?'"
-   **Your high-quality JSON output:**
    {
        "subject_description": "a young Vietnamese woman with a graceful walk, wearing a warm, elegant coat",
        "core_action": "walking forward along the iconic Golden Bridge in Da Nang, moving directly towards the camera",
        "setting_description": "the Golden Bridge in Da Nang, Vietnam, uniquely covered in a gentle, magical snowfall",
        "dialogue": "Chào mọi người! Tuyết rơi ở Cầu Vàng, đẹp siêu thực luôn!",
        "tone": "friendly and slightly amazed",
        "language": "Vietnamese",
        "voice_type": "a warm, gentle female voice",
        "gesture": "raising a hand to catch a falling snowflake, with a sense of wonder",
        "visual_effects": "realistic falling snow, soft and ambient light reflecting off the golden structure",
        "mood": "magical, serene, and wondrous"
    }

**Now, analyze the following user's idea and generate the JSON output based on the same high standard.**

User's Idea: "{user_idea}"
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
    uploaded_file = st.file_uploader(
        "Tải ảnh lên (cho tùy chọn Ảnh -> Video)",
        type=["png", "jpg", "jpeg"]
    )
    if uploaded_file is not None:
        image_to_display = Image.open(uploaded_file)
        st.image(image_to_display, caption="Khung hình khởi đầu", use_column_width=True)

with col2:
    st.subheader("💡 Ý tưởng của bạn")
    with st.form("prompt_form"):
        user_idea = st.text_area(
            "Nhập ý tưởng video bằng tiếng Việt:",
            height=200,
            placeholder="Ví dụ: một cô gái đi trên Cầu Vàng có tuyết rơi và nói 'Chào mọi người! Tuyết rơi đẹp không?'"
        )
        submitted = st.form_submit_button("Tạo kịch bản Prompt")

    if submitted:
        if not user_idea:
            st.warning("Vui lòng nhập ý tưởng của bạn.")
        else:
            with st.spinner("🤖 Biên kịch AI đang phân tích và sáng tạo..."):
                try:
                    # Bước 1: Gửi yêu cầu phân tích đến Gemini
                    request_for_gemini = META_PROMPT_FOR_GEMINI.format(user_idea=user_idea)
                    response = gemini_model.generate_content(request_for_gemini)
                    
                    # Trích xuất và làm sạch JSON từ phản hồi
                    response_text = response.text.replace("```json", "").replace("```", "").strip()
                    extracted_data = json.loads(response_text)

                    # Bước 2: Lắp ráp prompt cuối cùng
                    final_prompt = ""
                    if uploaded_file is not None:
                        # Option 1: Có ảnh
                        template = IMAGE_TO_VIDEO_TEMPLATE
                    else:
                        # Option 2: Chỉ có text
                        template = TEXT_TO_VIDEO_TEMPLATE
                    
                    # Xử lý phần lời thoại và âm thanh để có thể ẩn đi nếu không có
                    if extracted_data.get("dialogue"):
                        extracted_data['dialogue_section'] = f"Animate the subject's mouth to synchronize with the speech: \"{extracted_data['dialogue']}\"."
                        extracted_data['audio_section'] = f"Generate natural-sounding {extracted_data['language']} speech for the dialogue, spoken by a {extracted_data['voice_type']} with a {extracted_data['tone']} tone."
                    else:
                        extracted_data['dialogue_section'] = "No dialogue."
                        extracted_data['audio_section'] = "No speech audio, only ambient sounds matching the scene."

                    # Đoạn code mới linh hoạt hơn
                    try:
                        final_prompt = template.format(
                            subject_description=extracted_data.get('subject_description', 'a person in a scene'),
                            core_action=extracted_data.get('core_action', 'performing an action'),
                            setting_description=extracted_data.get('setting_description', 'an interesting setting'),
                            dialogue_section=extracted_data.get('dialogue_section', 'No dialogue.'),
                            audio_section=extracted_data.get('audio_section', 'No speech audio.'),
                            gesture=extracted_data.get('gesture', 'a natural gesture'),
                            visual_effects=extracted_data.get('visual_effects', 'cinematic effects'),
                            mood=extracted_data.get('mood', 'an interesting mood')
                        )
                    except KeyError as e:
                        st.error(f"Lỗi: AI đã không trả về đủ các trường dữ liệu cần thiết. Vui lòng thử lại. Trường bị thiếu: {e}")
                        st.stop() # Dừng thực thi nếu có lỗi nghiêm trọng
                    # Hiển thị kết quả
                    st.divider()
                    st.subheader("🎬 Kịch bản Prompt chi tiết (Tiếng Anh)")
                    st.info("Đây là prompt đã được tối ưu để gửi đến AI tạo video (như Veo).")
                    st.text_area("Prompt cuối cùng:", value=final_prompt, height=400)

                except json.JSONDecodeError:
                    st.error("Lỗi: AI không trả về định dạng JSON hợp lệ. Vui lòng thử lại với ý tưởng rõ ràng hơn.")
                    st.write("Dữ liệu thô từ AI:", response_text)
                except Exception as e:
                    st.error(f"Đã xảy ra lỗi không mong muốn: {e}")
