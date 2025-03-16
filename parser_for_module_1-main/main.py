import argparse
from pathlib import Path
from urllib.parse import urlparse

from parsers.parser_html import WebPageProcessor 
from parsers.parser_pdf import PDFProcessor  
from parsers.parser_djvu import DJVUProcessor 
from parsers.parser_doc import DOCProcessor  
from parsers.parser_docx import DOCXProcessor 

class FileProcessor:
    def __init__(self, input_path):
        self.input_path = input_path
        self.is_url = self._is_valid_url(input_path)
        self.processor = self._get_processor()

    def _is_valid_url(self, path):
        """Проверка существования URL"""
        try:
            result = urlparse(path)
            return all([result.scheme, result.netloc])
        except:
            return False

    def _get_processor(self):
        """Выбор обработчика в зависимости от формата входа"""
        if self.is_url:
            return WebPageProcessor(self.input_path)
            
        file_path = Path(self.input_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Файл {file_path} не найден")
            
        ext = file_path.suffix.lower()
        if ext == '.html':
            return WebPageProcessor(self.input_path)
        elif ext == '.pdf':
            return PDFProcessor(self.input_path)
        elif ext == '.djvu':
            return DJVUProcessor(self.input_path)
        elif ext == '.doc':
            return DOCProcessor(self.input_path)
        elif ext == '.docx':
            return DOCXProcessor(self.input_path)
        else:
            raise ValueError(f"Формат {ext} не подходит")

    def process(self):
        """Собственно парсинг"""
        if self.processor:
            print(f"Обработка: {self.input_path}")
            self.processor.print_results()
        else:
            print("Не удалось определить тип данных")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Синтаксический анализатори html страниц, документов форматов .pdf, .doc, .docx, .djvu")
    parser.add_argument("input_path", help="Путь к файлу или URL для парсинга")
    args = parser.parse_args()

    try:
        processor = FileProcessor(args.input_path)
        processor.process()
    except Exception as e:
        print(f"Ошибка: {e}")