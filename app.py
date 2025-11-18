import streamlit as st
import fitz
import cv2
import numpy as np
import tempfile
from PIL import Image

st.set_page_config(page_title="Clean PDF", page_icon="📄", layout="centered")

st.title("📄 Clean PDF — оптимізатор PDF для друку")
st.write("Завантаж PDF — я автоматично обріжу поля, вирівняю текст і створю чистий файл для друку.")

uploaded = st.file_uploader("Завантаж PDF", type=["pdf"])

if uploaded:
    # тимчасовий файл
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
        temp.write(uploaded.read())
        input_path = temp.name

    OUTPUT_FILE = "optimized_for_print.pdf"

    CM_TO_PT = 28.35
    MARGIN = int(CM_TO_PT * 1.0)
    SPACING = int(CM_TO_PT * 0.8)

    # A4 у високій якості
    A4_WIDTH, A4_HEIGHT = 3508, 2480

    # 1️⃣ Читаємо PDF
    doc = fitz.open(input_path)
    processed = []

    for i in range(len(doc)):
        pix = doc[i].get_pixmap(matrix=fitz.Matrix(3, 3))
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

        # конвертація RGBA → RGB
        if img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)

        # обрізання полів
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            x, y, w, h = cv2.boundingRect(np.vstack(contours))
            cropped = img[y:y+h, x:x+w]
        else:
            cropped = img

        processed.append(cropped)

    doc.close()

    # 2️⃣ Формуємо вихідний PDF
    output = fitz.open()
    page_canvas = np.ones((A4_HEIGHT, A4_WIDTH, 3), dtype=np.uint8) * 255
    y_cursor = MARGIN

    def add_page_to_pdf(canvas):
        """Вставляє зібрану сторінку у PDF файл"""
        pil_img = Image.fromarray(canvas.astype(np.uint8))
        img_bytes = pil_img.tobytes("raw", "RGB")

        page = output.new_page(width=pil_img.width, height=pil_img.height)
        page.insert_image(
            fitz.Rect(0, 0, pil_img.width, pil_img.height),
            stream=pil_img.tobytes(),
            keep_proportion=False
        )

    # 3️⃣ Розміщення блоків на аркуші
    for img in processed:
        max_width = A4_WIDTH - 2 * MARGIN
        scale = max_width / img.shape[1]
        img = cv2.resize(img, (int(img.shape[1] * scale), int(img.shape[0] * scale)))

        h, w, _ = img.shape

        # новий аркуш, якщо не влазить
        if y_cursor + h + MARGIN > A4_HEIGHT:
            add_page_to_pdf(page_canvas)
            page_canvas = np.ones((A4_HEIGHT, A4_WIDTH, 3), dtype=np.uint8) * 255
            y_cursor = MARGIN

        page_canvas[y_cursor:y_cursor+h, MARGIN:MARGIN+w] = img
        y_cursor += h + SPACING

    # додаємо фінальний аркуш
    add_page_to_pdf(page_canvas)

    output.save(OUTPUT_FILE)
    output.close()

    # кнопка завантажити
    with open(OUTPUT_FILE, "rb") as f:
        st.download_button(
            "⬇️ Завантажити оптимізований PDF",
            f,
            file_name=OUTPUT_FILE,
            mime="application/pdf"
        )
