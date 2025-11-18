import streamlit as st
import pdfplumber
import numpy as np
from PIL import Image
import io

# Конфігурація сторінки
st.set_page_config(page_title="Clean PDF", page_icon="📄", layout="centered")
st.title("📄 Clean PDF — автоматичне очищення PDF для друку")

uploaded = st.file_uploader("Завантаж PDF", type=["pdf"])

# Константи
CM_TO_PX = 118   # 1 см = 118 px при 300 dpi
MARGIN = int(1.0 * CM_TO_PX)
SPACING = int(0.8 * CM_TO_PX)

# A4 — вертикально
A4_WIDTH, A4_HEIGHT = 2480, 3508


# ✂️ Обрізання білих полів
def crop_white(img: Image.Image):
    gray = img.convert("L")
    arr = np.array(gray)

    mask = arr < 240  # темні / не-білі пікселі
    coords = np.argwhere(mask)

    if coords.size == 0:
        return img

    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0) + 1
    return img.crop((x0, y0, x1, y1))


# ➕ Додаємо сторінку у PDF (через Pillow)
def save_page_to_pdf(canvas, pdf_list):
    buf = io.BytesIO()
    canvas.save(buf, format="PDF")
    pdf_list.append(buf.getvalue())


if uploaded:
    st.info("⌛ Обробка PDF, зачекай кілька секунд...")

    pdf_pages = []
    fragments = []

    # 🟦 1. Вичитуємо PDF і конвертуємо кожну сторінку в картинку
    with pdfplumber.open(uploaded) as pdf:
        for page in pdf.pages:
            img = page.to_image(resolution=300).original
            pil_img = Image.fromarray(img)

            cropped = crop_white(pil_img)
            fragments.append(cropped)

    # 🟦 2. Створюємо чистий аркуш
    canvas = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), "white")
    y_cursor = MARGIN

    # 🟦 3. Розкладка блоків по листу
    for block in fragments:
        max_width = A4_WIDTH - 2 * MARGIN
        ratio = max_width / block.width

        resized = block.resize((max_width, int(block.height * ratio)))

        if y_cursor + resized.height + MARGIN > A4_HEIGHT:
            save_page_to_pdf(canvas, pdf_pages)
            canvas = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), "white")
            y_cursor = MARGIN

        canvas.paste(resized, (MARGIN, y_cursor))
        y_cursor += resized.height + SPACING

    save_page_to_pdf(canvas, pdf_pages)

    # 🟦 4. Об'єднуємо PDF-сторінки
    final_pdf = b"".join(pdf_pages)

    # 🟦 5. Даємо кнопку на завантаження
    st.success("Готово! Завантажуй оптимізований PDF 👇")
    st.download_button(
        "⬇️ Завантажити PDF",
        final_pdf,
        file_name="optimized_for_print.pdf",
        mime="application/pdf",
    )
