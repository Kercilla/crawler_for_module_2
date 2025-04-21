# Модуль 2: Разработка поискового робота 

## Описание проекта

Проект поискового робота для сбора и обработки данных с ресурсов Web 1.0/Web 2.0

## Структура репозитория
```
├── crawlers                      # Папка с поисковыми роботами
  ├── web1_crawler.py             # Поисковый робот по Web 1.0
  ├── web2_telegram_crawler.py    # Поисковый робот по Web 2.0 (Telegram)
├── parsers                       # Папка с парсерами
  ├── parser_html.py              # Парсер html-страниц из первого модуля
├── utils
  ├── robots_checker.py           # Скрипт с проверкой правил
├── README.md                     # Описание проекта
├── auth.py                       # Скрипт для авторизации API Telegram
├── main.py                       # Основной скрипт обработки 
├── requirements.txt              # Список зависимостей для Python
```

## Запуск проекта

### Создание виртуального окружения

```bash
conda create -n py-crawler python=3.9
```

### Установка зависимостей 

Для установки необходимых зависимостей выполните следующую команду:

```bash
pip install -r requirements.txt
```

### Запуск скрипта

Для запуска поискового робота используйте команду:

по Web 1.0:

```bash
python main.py web1 --domain $DOMAIN
```

По Web 2.0:

```bash
python main.py web2
```

### API Telegram

- Регистрируем и создаем приложение [my.telegram.org](https://my.telegram.org/)
- Получаем API_ID и API_HASH
- Создаем файл .env в корне и записываем в него полученные ключи:
```
API_ID = ""
API_HASH = ""
PHONE_NUMBER = ""
```
