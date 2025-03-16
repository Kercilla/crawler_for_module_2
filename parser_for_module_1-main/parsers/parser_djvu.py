import subprocess
import pytesseract
from PIL import Image
import os

class DJVUProcessor:
    def __init__(self, file_path, lang="rus+eng"):
        self.file_path = file_path
        self.lang = lang
        self.is_valid = self._validate_dependencies()
        self.text_content = self._extract_text()
        self.ocr_text = self._extract_text_ocr() if not self.text_content else ""
        self.metadata = self._extract_metadata()
        self.image_count = 0

    def _validate_dependencies(self):
        """Проверка наличия необходимых утилит"""
        required_tools = ["djvutxt", "ddjvu"]
        missing = []
        for tool in required_tools:
            try:
                subprocess.run([tool, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except FileNotFoundError:
                missing.append(tool)
        if missing:
            print(f"Ошибка: не найдены утилиты: {', '.join(missing)}")
            return False
        return True

    def _extract_text(self):
        """Извлечение текста"""
        if not self.is_valid:
            return ""
        try:
            result = subprocess.run(
                ["djvutxt", self.file_path],
                capture_output=True,
                text=True,
                encoding="utf-8"
            )
            return result.stdout.strip()
        except Exception as e:
            print(f"Ошибка извлечения текста: {e}")
            return ""

    def _extract_text_ocr(self):
        """Извлечение текста с изображений"""
        if not self.is_valid:
            return ""
        temp_image = "temp.tiff"
        try:
            subprocess.run(["ddjvu", "-format=tiff", self.file_path, temp_image], check=True)
            text = pytesseract.image_to_string(Image.open(temp_image), lang=self.lang)
            return text.strip()
        except Exception as e:
            print(f"OCR ошибка: {e}")
            return ""
        finally:
            if os.path.exists(temp_image):
                os.remove(temp_image)

    def _extract_metadata(self):
        """Получение метаданных"""
        if not self.is_valid:
            return ""
        try:
            result = subprocess.run(
                ["djvudump", self.file_path],
                capture_output=True,
                text=True,
                encoding="utf-8"
            )
            return result.stdout
        except Exception as e:
            print(f"Ошибка извлечения метаданных: {e}")
            return ""

    def print_results(self):
        print(f"Статус: {'Валиден' if self.is_valid else 'Ошибка зависимостей'}")
        
        print("\nТекст документа:")
        print(self.text_content[:500] + "\n..." if len(self.text_content) > 500 else self.text_content)
        
        if self.ocr_text:
            print("\nТекст документа (OCR):")
            print(self.ocr_text[:500] + "\n..." if len(self.ocr_text) > 500 else self.ocr_text)
            
        print("\nМетаданные:")
        print(self.metadata[:500] + "\n..." if len(self.metadata) > 500 else self.metadata)