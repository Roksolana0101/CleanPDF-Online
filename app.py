import streamlit as st
import pypdfium2 as pdfium
import numpy as np
from PIL import Image
import io
import tempfile

# ---------------- Налаштування сторінки ----------------
st.set_page_config(page_title="Clean PDF Collage", page_icon="📄", layout="centered")

st.title("📄 Clean PDF — обрізання полів + колаж на A4")
st.write(
    "Завантаж PDF — я обріжу білі поля, масштабую вміст по ширині сторінки "
    "і складу кілька блоків один під одним на аркушах A4."
)

uploaded_file = st.file_uploader("Завантаж PDF-файл", type=["pdf"])

# ---------------- Налаштування колажу ----------------
# Працюємо в ландшафтній орієнтації, як у твоєму локальному скрипті
A4_WIDTH = 3508   # px при 300 dpi (≈297 мм)
A4_HEIGHT = 2480  # px при 300 dpi (≈210 мм)

# 1 см ≈ 118 px (300 dpi ≈ 118 пікселів на см)
CM_TO_PX = 118
MARGIN_CM = 1.0
SPACING_CM = 0.8  # відстань між блоками

MARGIN = int(MARGIN_CM * CM_TO_PX)    # поля з усіх боків ~1 см
SPACING = int(SPACING_CM * CM_TO_PX)  # вертикальний інтервал між секціями


def crop_whitespace(np_img: np.ndarray, threshold: int = 245) -> np.ndarray:
    """
    Обрізає білі поля навколо контенту.
    threshold — поріг «білизни»: чим менший, тим агресивніше обрізання.
    """
    # Переводимо в відтінки сірого
    if np_img.ndim == 3:
        gray = np.mean(np_img, axis=2)
    else:
        gray = np_img

    # де пікселі НЕ білі
    mask = gray < threshold

    if not mask.any():
        # Якщо взагалі нічого не знайшли (порожня сторінка) — повертаємо як є
        return np_img

    coords = np.argwhere(mask)
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0) + 1  # +1, щоб включити останній піксель

    cropped = np_img[y0:y1, x0:x1]
    return cropped


def make_collage_pages(images_np):
    """
    Приймає список кропнутих np-масивів (H, W, 3),
    складає їх по висоті на аркушах A4 з полями і відступами.
    Повертає список PIL.Image сторінок.
    """
    pages = []

    # Поточний "аркуш" як біле тло
    canvas = np.ones((A4_HEIGHT, A4_WIDTH, 3), dtype=np.uint8) * 255
    y_cursor = MARGIN
    has_content = False  # чи щось уже намальовано на поточному аркуші

    max_width = A4_WIDTH - 2 * MARGIN

    for np_img in images_np:
        h, w = np_img.shape[:2]

        # Масштабуємо під ширину (з урахуванням полів)
        scale = max_width / w
        new_w = int(w * scale)
        new_h = int(h * scale)

        pil_img = Image.fromarray(np_img)
        pil_resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
        np_resized = np.array(pil_resized)

        h2, w2 = np_resized.shape[:2]

        # Якщо не влазить по висоті — створюємо нову сторінку
        if y_cursor + h2 + MARGIN > A4_HEIGHT:
            # додаємо попередній заповнений аркуш
            if has_content:
                pages.append(Image.fromarray(canvas))

            # новий чистий аркуш
            canvas = np.ones((A4_HEIGHT, A4_WIDTH, 3), dtype=np.uint8) * 255
            y_cursor = MARGIN
            has_content = False

        # Вставляємо блок зліва, із заданим відступом
        x_pos = MARGIN
        canvas[y_cursor:y_cursor + h2, x_pos:x_pos + w2] = np_resized
        y_cursor += h2 + SPACING
        has_content = True

    # Додаємо останній аркуш, якщо там щось є
    if has_content:
        pages.append(Image.fromarray(canvas))

    return pages


if uploaded_file is not None:
    st.info(f"Файл: **{uploaded_file.name}**")

    if st.button("✨ Обробити PDF (обрізати поля + колаж)"):
        try:
            # Тимчасово записуємо PDF для pdfium
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                input_path = tmp.name

            # Відкриваємо PDF через pypdfium2
            pdf = pdfium.PdfDocument(input_path)
            processed_images = []

            # Рендеримо сторінки в зображення та обрізаємо поля
            for i in range(len(pdf)):
                page = pdf[i]
                # scale 2.0 — нормальна якість без гігантського розміру
                bitmap = page.render(scale=2.0)
                pil_img = bitmap.to_pil()
                np_img = np.array(pil_img)

                # Обрізаємо білі поля
                cropped = crop_whitespace(np_img)
                processed_images.append(cropped)

            # Робимо колажні сторінки
            collage_pages = make_collage_pages(processed_images)

            if not collage_pages:
                st.error("Не вдалося створити жодної сторінки. Можливо, PDF порожній?")
            else:
                # Записуємо у PDF в пам'ять
                pdf_bytes = io.BytesIO()
                first_page = collage_pages[0]
                if len(collage_pages) == 1:
                    first_page.save(pdf_bytes, format="PDF")
                else:
                    first_page.save(
                        pdf_bytes,
                        format="PDF",
                        save_all=True,
                        append_images=collage_pages[1:],
                    )
                pdf_bytes.seek(0)

                st.success("✅ Готово! Створено новий PDF з обрізаними полями і колажем.")
                st.download_button(
                    "⬇️ Завантажити оброблений PDF",
                    data=pdf_bytes,
                    file_name="optimized_collage.pdf",
                    mime="application/pdf",
                )

        except Exception as e:
            st.error(f"❌ Помилка під час обробки PDF: {e}")
else:
    st.write("⬆️ Завантаж PDF-файл, щоб почати.")
