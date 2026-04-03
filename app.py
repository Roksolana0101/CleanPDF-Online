import streamlit as st
from PIL import Image, JpegImagePlugin, PdfImagePlugin
import numpy as np
import tempfile
import os
import pypdfium2 as pdfium

# Явно ініціалізуємо плагіни Pillow, щоб не було KeyError: 'JPEG'
Image.init()

st.set_page_config(page_title="Clean PDF", page_icon="📄", layout="centered")

st.title("📄 Clean PDF — оптимізатор PDF для друку")
st.write("Завантаж PDF — я автоматично обріжу поля, вирівняю контент і зберу сторінки у форматі A4.")

uploaded = st.file_uploader("Завантаж PDF", type=["pdf"])


def ensure_rgb(np_img: np.ndarray) -> np.ndarray:
    """Гарантує, що зображення має 3 канали RGB."""
    if len(np_img.shape) == 2:
        return np.stack([np_img] * 3, axis=-1)

    if len(np_img.shape) == 3 and np_img.shape[2] == 4:
        return np_img[:, :, :3]

    return np_img


def crop_content(img: np.ndarray) -> np.ndarray:
    """Обрізає білі поля навколо контенту."""
    img = ensure_rgb(img)

    gray = np.mean(img, axis=2).astype(np.uint8)
    mask = gray < 250
    coords = np.argwhere(mask)

    if coords.size == 0:
        return img

    y1, x1 = coords.min(axis=0)
    y2, x2 = coords.max(axis=0)

    # +1, щоб не зрізати крайній піксель
    cropped = img[y1:y2 + 1, x1:x2 + 1]

    if cropped.size == 0:
        return img

    return cropped


if uploaded:
    with st.spinner("⏳ Оптимізую PDF... Це може зайняти 5–15 секунд..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_input:
            temp_input.write(uploaded.read())
            input_path = temp_input.name

        output_path = "optimized_for_print.pdf"

        # Параметри A4 при 300 dpi
        A4_W, A4_H = 2480, 3508
        MARGIN = 120
        SPACING = 80

        # === 1. Конвертація PDF у зображення ===
        pdf = pdfium.PdfDocument(input_path)
        images = []

        for page_number in range(len(pdf)):
            page = pdf.get_page(page_number)
            pil_image = page.render(scale=2).to_pil()
            np_image = np.array(pil_image)
            images.append(ensure_rgb(np_image))

        # === 2. Обрізання контенту ===
        cropped_pages = [crop_content(img) for img in images]

        # === 3. Формування сторінок A4 ===
        a4_pages = []
        current = np.full((A4_H, A4_W, 3), 255, dtype=np.uint8)
        y = MARGIN

        for img in cropped_pages:
            if img.size == 0 or img.shape[0] == 0 or img.shape[1] == 0:
                continue

            # Масштабуємо під ширину A4 з урахуванням полів
            available_width = A4_W - 2 * MARGIN
            scale = available_width / img.shape[1]

            new_w = max(1, int(img.shape[1] * scale))
            new_h = max(1, int(img.shape[0] * scale))

            resized = np.array(Image.fromarray(img).resize((new_w, new_h), Image.LANCZOS))
            resized = ensure_rgb(resized)

            # Якщо не влазить по висоті — нова сторінка
            if y + new_h + MARGIN > A4_H:
                a4_pages.append(Image.fromarray(current).convert("RGB"))
                current = np.full((A4_H, A4_W, 3), 255, dtype=np.uint8)
                y = MARGIN

            # Безпечна вставка в межах сторінки
            insert_h = min(new_h, current.shape[0] - y)
            insert_w = min(new_w, current.shape[1] - MARGIN)

            if insert_h > 0 and insert_w > 0:
                current[y:y + insert_h, MARGIN:MARGIN + insert_w] = resized[:insert_h, :insert_w]
                y += insert_h + SPACING

        # Додаємо останню сторінку, тільки якщо вона не порожня
        if y > MARGIN or not a4_pages:
            a4_pages.append(Image.fromarray(current).convert("RGB"))

        # Страховка: якщо раптом нічого не зібралось
        if not a4_pages:
            blank = Image.fromarray(np.full((A4_H, A4_W, 3), 255, dtype=np.uint8)).convert("RGB")
            a4_pages = [blank]

        # === 4. Збереження у PDF ===
        # Явно конвертуємо всі сторінки в RGB
        pdf_pages = [img.convert("RGB") for img in a4_pages]

        pdf_pages[0].save(
            output_path,
            format="PDF",
            save_all=True,
            append_images=pdf_pages[1:]
        )

        # === 5. Кнопка завантаження ===
        with open(output_path, "rb") as f:
            pdf_bytes = f.read()

    st.success("✅ Готово! PDF оптимізовано.")
    st.download_button(
        "⬇️ Завантажити оптимізований PDF",
        data=pdf_bytes,
        file_name="optimized_for_print.pdf",
        mime="application/pdf"
    )

    # Прибираємо тимчасовий вхідний файл
    try:
        os.remove(input_path)
    except Exception:
        pass
