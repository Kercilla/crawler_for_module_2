import pytest
import requests_mock
from WebPageProcessor import WebPageProcessor

@pytest.fixture
def mock_html():
    """Моковая HTML-страница для тестирования."""
    return """
    <html>
        <head>
            <meta name="description" content="Test description">
            <meta property="og:title" content="Test Title">
        </head>
        <body>
            <h1>Заголовок</h1>
            <p>Первый параграф.</p>
            <p>Второй параграф.</p>
            <img src="image1.jpg" alt="Image 1">
            <img src="image2.jpg">
            <table>
                <tr><th>Header 1</th><th>Header 2</th></tr>
                <tr><td>Data 1</td><td>Data 2</td></tr>
            </table>
            <a href="https://example.com">Example Link</a>
        </body>
    </html>
    """

@pytest.fixture
def processor(mock_html):
    """Создание экземпляра WebPageProcessor с моковым HTML."""
    with requests_mock.Mocker() as m:
        m.get("http://mock.url", text=mock_html)
        return WebPageProcessor("http://mock.url")

# Тест загрузки страницы
def test_load_page(processor):
    assert processor.soup is not None
    assert processor.soup.find("h1").text == "Заголовок"

# Тест извлечения текста
def test_extract_full_text(processor):
    expected_text = "Заголовок\nПервый параграф.\nВторой параграф."
    assert expected_text in processor.full_text

# Тест извлечения изображений
def test_extract_images(processor):
    expected_images = [
        {"src": "image1.jpg", "alt": "Image 1"},
        {"src": "image2.jpg", "alt": "No alt text"}
    ]
    assert processor.images == expected_images

# Тест извлечения таблиц
def test_extract_tables(processor):
    expected_tables = [
        {
            "headers": ["Header 1", "Header 2"],
            "rows": [["Data 1", "Data 2"]]
        }
    ]
    assert processor.tables == expected_tables

# Тест извлечения метаданных
def test_extract_meta_tags(processor):
    expected_meta_tags = {
        "description": "Test description",
        "og:title": "Test Title"
    }
    assert processor.meta_tags == expected_meta_tags

# Тест извлечения ссылок
def test_extract_links(processor):
    expected_links = [
        {"text": "Example Link", "url": "https://example.com"}
    ]
    assert processor.links == expected_links

# Тест обработки пустой страницы
def test_empty_page():
    with requests_mock.Mocker() as m:
        m.get("http://empty.url", text="")
        processor = WebPageProcessor("http://empty.url")
        assert processor.full_text == ""
        assert processor.images == []
        assert processor.tables == []
        assert processor.meta_tags == {}
        assert processor.links == []

# Тест обработки страницы без изображений
def test_no_images(mock_html):
    mock_html = """
    <html>
        <body>
            <p>Текст без изображений.</p>
        </body>
    </html>
    """
    with requests_mock.Mocker() as m:
        m.get("http://no-images.url", text=mock_html)
        processor = WebPageProcessor("http://no-images.url")
        assert processor.images == []

# Тест обработки страницы без таблиц
def test_no_tables(mock_html):
    mock_html = """
    <html>
        <body>
            <p>Текст без таблиц.</p>
        </body>
    </html>
    """
    with requests_mock.Mocker() as m:
        m.get("http://no-tables.url", text=mock_html)
        processor = WebPageProcessor("http://no-tables.url")
        assert processor.tables == []

# Тест обработки страницы без метаданных
def test_no_meta_tags(mock_html):
    mock_html = """
    <html>
        <body>
            <p>Текст без метаданных.</p>
        </body>
    </html>
    """
    with requests_mock.Mocker() as m:
        m.get("http://no-meta.url", text=mock_html)
        processor = WebPageProcessor("http://no-meta.url")
        assert processor.meta_tags == {}

# Тест обработки страницы без ссылок
def test_no_links(mock_html):
    mock_html = """
    <html>
        <body>
            <p>Текст без ссылок.</p>
        </body>
    </html>
    """
    with requests_mock.Mocker() as m:
        m.get("http://no-links.url", text=mock_html)
        processor = WebPageProcessor("http://no-links.url")
        assert processor.links == []
