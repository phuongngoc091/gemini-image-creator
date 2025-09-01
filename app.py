import streamlit as st
import google.generativeai as genai
from PIL import Image
from io import BytesIO

# --- Cấu hình trang web ---
st.set_page_config(
    page_title="Trình tạo ảnh AI bằng Gemini",
    page_icon="🎨",
    layout="wide"
)

# --- Giao diện chính ---
st.title("🎨 Trình tạo ảnh AI bằng Gemini 1.5 Flash")
st.write("Mô tả ý tưởng của bạn thành lời văn, AI sẽ biến nó thành hình ảnh!")

# --- Phần cấu hình API Key ở thanh bên (sidebar) ---
with st.sidebar:
    st.header("Cấu hình")
    # Lấy API Key từ Streamlit secrets, một cách an toàn
    try:
        # Hướng dẫn người dùng cách deploy để có st.secrets
        # Đây là cách tốt nhất khi deploy
        google_api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("Đã tìm thấy API Key!", icon="✅")
    except (FileNotFoundError, KeyError):
        # Nếu không có secret, yêu cầu người dùng nhập thủ công
        st.warning("Không tìm thấy API Key trong Secrets. Vui lòng nhập thủ công bên dưới.", icon="⚠️")
        google_api_key = st.text_input("Nhập Google API Key của bạn:", type="password")

# Kiểm tra nếu API key chưa được cung cấp
if not google_api_key:
    st.info("Vui lòng nhập API Key của bạn ở thanh bên để bắt đầu.")
    st.stop()

# Cấu hình API của Google
try:
    genai.configure(api_key=google_api_key)
except Exception as e:
    st.error(f"Lỗi cấu hình API Key: {e}")
    st.stop()


# --- Form nhập liệu ---
with st.form("image_form"):
    prompt = st.text_area(
        "📝 **Nhập mô tả cho bức ảnh (bằng tiếng Anh để có kết quả tốt nhất):**",
        height=150,
        placeholder="A cat astronaut riding a rocket through the rings of Saturn, oil painting style"
    )
    submitted = st.form_submit_button("✨ Tạo ảnh")

# --- Xử lý khi người dùng nhấn nút ---
if submitted:
    if not prompt:
        st.warning("Vui lòng nhập mô tả cho ảnh.")
    else:
        # Hiển thị spinner trong khi chờ tạo ảnh
        with st.spinner("🤖 AI đang sáng tạo, vui lòng chờ trong giây lát..."):
            try:
                # Chọn model và gọi API
                model = genai.GenerativeModel(model_name="gemini-1.5-flash")
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "image/jpeg"}
                )

                # Xử lý và hiển thị ảnh
                image_data = response.parts[0].blob.data
                image = Image.open(BytesIO(image_data))

                st.success("Tạo ảnh thành công!", icon="🎉")
                st.image(image, caption=f"Ảnh tạo từ mô tả: '{prompt}'", use_column_width=True)

                # Thêm nút tải xuống
                st.download_button(
                    label="Tải ảnh xuống",
                    data=image_data,
                    file_name=f"{prompt[:30].replace(' ', '_')}.jpg",
                    mime="image/jpeg"
                )

            except Exception as e:
                st.error(f" Rất tiếc, đã xảy ra lỗi: {e}")
                st.error("Nguyên nhân có thể do yêu cầu của bạn vi phạm chính sách an toàn hoặc API key không hợp lệ. Vui lòng thử lại với một mô tả khác.")
