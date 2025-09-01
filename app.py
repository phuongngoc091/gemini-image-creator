import streamlit as st
import google.generativeai as genai
from PIL import Image
from io import BytesIO

# --- Cấu hình trang và tiêu đề ---
st.set_page_config(layout="wide", page_title="Trình tạo ảnh AI Sử thi")
st.title("🎨 Trình tạo ảnh AI Sử thi")

# --- PROMPT MẪU ĐÃ CẬP NHẬT ---
# Đây là prompt mẫu chi tiết do bạn cung cấp.
# Ý tưởng của người dùng sẽ được chèn vào vị trí {user_prompt}.
BASE_PROMPT_TEMPLATE = """
A hyperrealistic cinematic scene of {user_prompt}. The figure's uniform is worn yet dignified, with determination in their serious expression. Behind them, the silhouettes of people appear blurred and hazy, representing the united strength of the nation. The atmosphere is intense and patriotic, with dramatic lighting, dust and sunlight filtering through the air, creating a historic and monumental mood. Ultra-detailed, photorealistic, 8K resolution, cinematic composition, dark yet hopeful tones.
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
except Exception as e:
    st.error(f"Lỗi cấu hình API Key: {e}")
    st.stop()

# --- Bố cục 2 cột ---
col1, col2 = st.columns([1, 3])

# --- CỘT TRÁI (Bảng điều khiển) ---
with col1:
    st.subheader("🖼️ Bảng điều khiển")
    uploaded_file = st.file_uploader(
        "Tải ảnh lên (tùy chọn)",
        type=["png", "jpg", "jpeg"],
        help="Tải lên một ảnh để AI tham khảo hoặc chỉnh sửa theo mô tả của bạn."
    )
    if uploaded_file is not None:
        image_to_display = Image.open(uploaded_file)
        st.image(image_to_display, caption="Ảnh đã tải lên", use_column_width=True)
    aspect_ratio = st.selectbox(
        "📐 Tỉ lệ ảnh",
        ("Tự động", "16:9 (Ngang)", "1:1 (Vuông)", "4:5 (Dọc)", "9:16 (Dọc cao)")
    )

# --- CỘT PHẢI (Prompt và Kết quả) ---
with col2:
    st.subheader("✨ Sáng tạo")
    with st.form("prompt_form"):
        user_prompt = st.text_area(
            "📝 Nhập ý tưởng chính của bạn:",
            height=200,
            placeholder="Ví dụ: a Vietnamese soldier standing proudly in front of a large red flag with a golden star. Beside him is a heavy tank, symbolizing strength and liberation"
        )
        submitted = st.form_submit_button("Tạo ảnh")

    if submitted:
        if not user_prompt:
            st.warning("Vui lòng nhập ý tưởng của bạn.")
        else:
            # --- TẠO PROMPT CHÍNH THỨC ---
            # Kết hợp prompt mẫu với mô tả của người dùng
            final_prompt = BASE_PROMPT_TEMPLATE.format(user_prompt=user_prompt)

            # Hiển thị prompt chính thức cho người dùng xem
            with st.expander("🔍 Xem prompt chính thức được gửi đến AI"):
                st.write(final_prompt)

            with st.spinner("AI đang sáng tạo, vui lòng chờ..."):
                try:
                    content_parts = []
                    if uploaded_file is not None:
                        uploaded_image = Image.open(uploaded_file)
                        content_parts.append(uploaded_image)
                    
                    # Sử dụng final_prompt thay vì user_prompt
                    content_parts.append(final_prompt) 

                    model = genai.GenerativeModel(model_name="gemini-2.5-flash")
                    response = model.generate_content(
                        content_parts,
                        generation_config={"response_mime_type": "image/jpeg"}
                    )
                    image_data = response.parts[0].blob.data
                    generated_image = Image.open(BytesIO(image_data))
                    st.image(generated_image, caption="Ảnh tạo ra", use_column_width=True)
                    st.download_button(
                        label="Tải ảnh xuống",
                        data=image_data,
                        file_name="generated_image.jpg",
                        mime="image/jpeg"
                    )
                except Exception as e:
                    st.error(f"Rất tiếc, đã xảy ra lỗi: {e}")
