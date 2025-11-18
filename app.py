import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
import tempfile
import io

st.set_page_config(page_title="Clean PDF", page_icon="📄", layout="centered")

st.title("📄 Clean PDF — проста онлайн-версія")
st.write(
    "Ця веб-версія створює **чисту копію PDF** (без метаданих, службових елементів). "
    "Просунута версія з обрізанням полів працює у локальному скрипті `clean_pdf.py` на Mac."
)

uploaded_file = st.file_uploader("Завантаж PDF-файл", type=["pdf"])

if uploaded_file is not None:
    # Показати ім’я файлу
    st.info(f"Файл: **{uploaded_file.name}**")

    if st.button("✨ Очистити PDF та створити нову копію"):
        try:
            # Тимчасово зберігаємо завантажений файл
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                input_path = tmp.name

            # Читаємо PDF
            reader = PdfReader(input_path)
            writer = PdfWriter()

            # Копіюємо сторінки один-в-один
            for page in reader.pages:
                writer.add_page(page)

            # Очищаємо метадані (щоб файл був "чистішим")
            writer.add_metadata({})

            # Записуємо в пам’ять (BytesIO), а не на диск
            output_stream = io.BytesIO()
            writer.write(output_stream)
            output_stream.seek(0)

            st.success("✅ Готово! Створено новий PDF-файл.")

            st.download_button(
                label="⬇️ Завантажити очищений PDF",
                data=output_stream,
                file_name="cleaned.pdf",
                mime="application/pdf",
            )

        except Exception as e:
            st.error(f"❌ Сталася помилка при обробці PDF: {e}")
else:
    st.write("⬆️ Будь ласка, завантаж PDF-файл для початку.")
