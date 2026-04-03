import streamlit as st
from PIL import Image
import numpy as np
import tempfile
import pypdfium2 as pdfium

st.set_page_config(page_title="Clean PDF", page_icon="📄", layout="centered")

st.title("📄 Clean PDF — оптимізатор PDF для друку")
st.write("Завантаж PDF — я автоматично обріжу поля, вирівняю текст і зберу розділи на сторінках А4.")

uploaded = st.file_uploader("Завантаж PDF", type=["pdf"])

if uploaded:

    with st.spinner("⏳ Оптимізую PDF... Це може зайняти 5–10 секунд..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
            temp.write(uploaded.read())
            input_path = temp.name

        OUTPUT_FILE = "optimized_for_print.pdf"

        # Параметри
        A4_W, A4_H = 2480, 3508  # А4 у пікселях (300 dpi)
        MARGIN = 120             # поля
        SPACING = 80             # відступ між секціями

        # === 1. Конвертація PDF у зображення ===
        pdf = pdfium.PdfDocument(input_path)
        images = []

        for page_number in range(len(pdf)):
            page = pdf.get_page(page_number)
            pil_image = page.render(scale=2).to_pil()  # 2 = 300 dpi
            images.append(np.array(pil_image))

        # === 2. Обрізання контенту ===
        cropped_pages = []
        for img in images:
            gray = np.mean(img, axis=2).astype(np.uint8)
            mask = gray < 250
            coords = np.argwhere(mask)

            if coords.size == 0:
                cropped_pages.append(img)
                continue

            y1, x1 = coords.min(axis=0)
            y2, x2 = coords.max(axis=0)
            cropped = img[y1:y2, x1:x2]
            cropped_pages.append(cropped)

        # === 3. Формування сторінок А4 ===
        a4_pages = []
        current = np.full((A4_H, A4_W, 3), 255, dtype=np.uint8)
        y = MARGIN

        for img in cropped_pages:
            # Масштабування
            scale = (A4_W - 2*MARGIN) / img.shape[1]
            new_w = int(img.shape[1] * scale)
            new_h = int(img.shape[0] * scale)
            resized = np.array(Image.fromarray(img).resize((new_w, new_h)))

            # Якщо не влазить — нова сторінка
            if y + new_h + MARGIN > A4_H:
                a4_pages.append(Image.fromarray(current))
                current = np.full((A4_H, A4_W, 3), 255, dtype=np.uint8)
                y = MARGIN

            # Вставка на сторінку
insert_h = min(new_h, current.shape[0] - y)
insert_w = min(new_w, current.shape[1] - MARGIN)

current[y:y+insert_h, MARGIN:MARGIN+insert_w] = resized[:insert_h, :insert_w]
y += insert_h + SPACING

        # Додати останню сторінку
        a4_pages.append(Image.fromarray(current))

        # === 4. Збереження у PDF ===
        a4_pages[0].save(
            OUTPUT_FILE, 
            save_all=True, 
            append_images=a4_pages[1:]
        )

    st.success("✅ Готово! PDF оптимізовано.")

    # === 5. Кнопка завантаження ===
    with open(OUTPUT_FILE, "rb") as f:
        st.download_button(
            "⬇️ Завантажити оптимізований PDF",
            f,
            file_name=OUTPUT_FILE,
            mime="application/pdf"
        )
