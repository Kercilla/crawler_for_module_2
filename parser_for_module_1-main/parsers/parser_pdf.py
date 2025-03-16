import PyPDF2
from pdf2image import convert_from_path
import pytesseract
import tabula

class PDFProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.is_valid = self._validate_pdf_syntax()
        self.text_content = self._extract_text()
        self.ocr_text = self._extract_text_from_images()
        self.tables = self._extract_tables()

    def _validate_pdf_syntax(self):
        """Проверка целостности"""
        try:
            with open(self.file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                if reader.is_encrypted:
                    raise ValueError("Файл зашифрован")
                for page in reader.pages:
                    page.extract_text()
            return True
        except Exception as e:
            print(f"Ошибка структуры PDF: {e}")
            return False

    def _extract_text(self):
        """Извлечение текста"""
        if not self.is_valid:
            return ""
        text = ""
        with open(self.file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text.strip()

    def _extract_text_from_images(self, dpi=300, lang="rus+eng"):
        """Извлечение такста (OCR)"""
        if not self.is_valid:
            return ""
        images = convert_from_path(self.file_path, dpi=dpi)
        return "\n".join(
            pytesseract.image_to_string(img, lang=lang) for img in images
        ).strip()

    def _extract_tables(self):
        """Извлечение таблиц"""
        if not self.is_valid:
            return []
        try:
            return tabula.read_pdf(
                self.file_path,
                pages="all",
                multiple_tables=True,
                java_options="-Dfile.encoding=UTF8"
            )
        except Exception as e:
            print(f"Ошибка извлечения таблиц: {e}")
            return []

    def print_results(self):
        print(f"Статус: {'Валиден' if self.is_valid else 'Ошибка структуры'}")
        
        print("\nТекст документа:")
        print(self.text_content[:500] + "\n..." if len(self.text_content) > 500 else self.text_content)
        
        print("\nТекст с документа (OCR):")
        print(self.ocr_text[:500] + "\n..." if len(self.ocr_text) > 500 else self.ocr_text)
        
        print("\nТаблицыиз докумета:")
        for i, table in enumerate(self.tables, 1):
            print(f"Таблица {i}:")
            print(table.head().to_string() if not table.empty else "Пустая таблица")