import streamlit as st
import fitz
import cv2
import numpy as np
import tempfile

st.set_page_config(page_title="Clean PDF", page_icon="📄", layout="centered")

st.title("📄 Clean PDF — оптимізатор PDF для друку")
st.write("Завантаж PDF — я автоматично обріжу поля, вирівняю текст і створю чистий файл для друку.")

uploaded = st.file_uploader("Завантаж PDF", type=["pdf"])

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
        temp.write(uploaded.read())
        input_path = temp.name

    OUTPUT_FILE = "optimized_for_print.pdf"

    CM_TO_PT = 28.35
    MARGIN = int(CM_TO_PT * 1.0)
    SPACING = int(CM_TO_PT * 0.8)

    A4_WIDTH, A4_HEIGHT = 3508, 2480

    doc = fitz.open(input_path)
    processed = []

    for i in range(len(doc)):
        pix = doc[i].get_pixmap(matrix=fitz.Matrix(3, 3))
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

        if img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)

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

    output = fitz.open()
    page_img = np.ones((A4_HEIGHT, A4_WIDTH, 3), dtype=np.uint8) * 255
    y_cursor = MARGIN

    def add_page(image):
        img_bytes = cv2.imencode(".png", image)[1].tobytes()
        h, w, _ = image.shape
        page = output.new_page(width=w, height=h)
        page.insert_image(fitz.Rect(0, 0, w, h), stream=img_bytes)

    for img in processed:
        max_width = A4_WIDTH - 2 * MARGIN
        scale = max_width / img.shape[1]
        img = cv2.resize(img, (int(img.shape[1] * scale), int(img.shape[0] * scale)))

        h, w, _ = img.shape

        if y_cursor + h + MARGIN > A4_HEIGHT:
            add_page(page_img)
            page_img = np.ones((A4_HEIGHT, A4_WIDTH, 3), dtype=np.uint8) * 255
            y_cursor = MARGIN

        page_img[y_cursor:y_cursor+h, MARGIN:MARGIN+w] = img
        y_cursor += h + SPACING

    add_page(page_img)

    output.save(OUTPUT_FILE)
    output.close()

    with open(OUTPUT_FILE, "rb") as f:
        st.download_button(
            "⬇️ Завантажити оптимізований PDF",
            f,
            file_name=OUTPUT_FILE,
            mime="application/pdf"
        )
