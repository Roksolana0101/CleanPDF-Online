import streamlit as st
from pdf2image import convert_from_path
import cv2
import numpy as np
from PIL import Image
import tempfile

st.set_page_config(page_title="Clean PDF", page_icon="📄")

st.title("📄 Clean PDF — Обрізання полів та оптимізація")
st.write("Завантаж PDF — я очищу поля, вирівняю контент та створю ідеальний файл для друку.")

uploaded = st.file_uploader("Завантаж PDF", type=["pdf"])

if uploaded:
    # зберігаємо PDF у тимчасовий файл
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
        temp.write(uploaded.read())
        input_path = temp.name

    st.info("⏳ Обробка PDF...")

    # конвертуємо PDF → зображення
    pages = convert_from_path(input_path, dpi=300)

    processed_images = []

    for page in pages:
        img = np.array(page)

        # перетворюємо в градації сірого
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # знаходження тексту (бінаризація)
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

        # пошук контурів
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            x, y, w, h = cv2.boundingRect(np.vstack(contours))
            cropped = img[y:y+h, x:x+w]
        else:
            cropped = img

        processed_images.append(cropped)

    # створення "колажу" як довгої сторінки
    widths = [img.shape[1] for img in processed_images]
    max_w = max(widths)
    heights = [img.shape[0] for img in processed_images]
    total_h = sum(heights)

    final = np.ones((total_h + 50, max_w + 50, 3), dtype=np.uint8) * 255

    y_offset = 25
    for img in processed_images:
        h, w, _ = img.shape
        final[y_offset:y_offset+h, 25:25+w] = img
        y_offset += h + 25

    # перетворюємо назад у PDF
    final_image = Image.fromarray(final)
    output_path = "optimized.pdf"
    final_image.save(output_path, "PDF", resolution=300)

    with open(output_path, "rb") as f:
        st.success("✅ Готово! PDF оптимізовано.")
        st.download_button("⬇️ Завантажити PDF", f, file_name="optimized.pdf")
