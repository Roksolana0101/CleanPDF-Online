import streamlit as st
import pypdfium2 as pdfium
import numpy as np
import cv2
from PIL import Image
import tempfile

st.set_page_config(page_title="Clean PDF", page_icon="📄")

st.title("📄 Clean PDF — Обрізання полів та оптимізація")
st.write("Завантаж PDF — я виріжу білі поля й складу сторінки у суцільний чистий документ.")

uploaded = st.file_uploader("Завантаж PDF", type=["pdf"])

if uploaded:
    # зберігаємо у тимчасовий файл
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
        temp.write(uploaded.read())
        input_pdf_path = temp.name

    st.info("⏳ Обробка PDF...")

    # відкриваємо PDF
    pdf = pdfium.PdfDocument(input_pdf_path)

    processed_images = []

    for i in range(len(pdf)):
        page = pdf[i]

        # рендер сторінки
        pil_image = page.render(scale=3).to_pil()

        img = np.array(pil_image)

        # у grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # інверсія для пошуку тексту
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

        # контури
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            x, y, w, h = cv2.boundingRect(np.vstack(contours))
            cropped = img[y:y+h, x:x+w]
        else:
            cropped = img

        processed_images.append(cropped)

    # створюємо довгий вертикальний колаж
    widths = [img.shape[1] for img in processed_images]
    heights = [img.shape[0] for img in processed_images]

    max_width = max(widths)
    total_height = sum(heights) + 30 * len(heights)

    final = np.ones((total_height, max_width, 3), dtype=np.uint8) * 255

    y_offset = 20
    for img in processed_images:
        h, w, _ = img.shape
        final[y_offset:y_offset+h, :w] = img
        y_offset += h + 20

    # зберігаємо PDF
    output_path = "optimized.pdf"
    final_image = Image.fromarray(final)
    final_image.save(output_path, "PDF", resolution=300)

    with open(output_path, "rb") as f:
        st.success("✅ Готово! PDF оптимізовано.")
        st.download_button("⬇️ Завантажити PDF", f, file_name="optimized.pdf")
