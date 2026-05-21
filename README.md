# CodeHub — платформа для обмена сниппетами
# https://docs.google.com/presentation/d/12TRpFxFd9AUcaeNl3srbBxSSf9XHsYgL6KCrwgFsEww/edit?slide=id.p1#slide=id.p1 ccылка на перзентацию
# https://vlad2233.pythonanywhere.com ссылка на сайт
Flask-приложение для публикации и обсуждения учебных сниппетов кода (в т.ч. по теме вредоносного ПО и анализа).

## Возможности

- Создание сниппетов с несколькими файлами (до 20), ссылками на проекты, тегами и категориями
- Модерация: новые и отредактированные сниппеты проходят проверку перед публикацией
- Повторная отправка на модерацию после отклонения с комментарием к исправлениям
- Комментарии с вложенностью, голосованием и жалобами
- Лайки и дизлайки на сниппетах и комментариях
- Уникальные просмотры (по пользователю или IP)
- Страница «Горячие» — топ по лайкам за последние 7 дней
- Поиск и фильтрация; сортировка по дате, лайкам, просмотрам
- Скачивание файлов сниппета по отдельности или ZIP-архивом
- Подсветка синтаксиса (highlight.js)
- Публичный REST API для списка одобренных сниппетов

Данные хранятся в **SQLite** (`instance/main.db`) через **SQLAlchemy**.

## Требования

- **Python** 3.10 или новее (проверено на 3.11–3.13)
- **pip** для установки зависимостей из `requirements.txt`

## Установка и запуск

### Windows (PowerShell)

**1. Перейдите в папку проекта**

```powershell
cd "путь\к\итоговый проэкт"
```

**2. Создайте и активируйте виртуальное окружение**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Если PowerShell блокирует скрипты, один раз выполните (от имени текущего пользователя):

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

При успешной активации в начале строки появится префикс `(venv)`.

**3. Установите зависимости**

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**4. Подготовьте папку для аватарок (опционально, для загрузки фото в профиле)**

```powershell
New-Item -ItemType Directory -Force -Path static\avatars
```

**5. Запустите приложение**

```powershell
python run.py
```

Откройте в браузере: **vlad2233.pythonanywhere.com**

Остановка сервера: `Ctrl+C` в том же окне терминала.

---

### Linux / macOS

```bash
cd /путь/к/итоговый\ проэкт
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
mkdir -p static/avatars
python run.py
```

Сайт: **vlad2233.pythonanywhere.com**

---

### Альтернативный запуск

Точка входа та же логика, что в `run.py`:

```bash
python __init__.py
```

Рекомендуется использовать **`python run.py`** — в нём явно вызываются `db.create_all()` и инициализация категорий перед стартом сервера.

## Первый вход

1. Зарегистрируйтесь: **vlad2233.pythonanywhere.com/register**
2. Войдите под созданным логином: **vlad2233.pythonanywhere.com/login**

Готовых учётных записей в проекте нет — их нужно создать при регистрации.

### Назначение администратора

Права админа нужны для модерации (`/admin/moderate`) и статистики (`/admin/stats`). В корне проекта с активированным `venv` выполните:

```powershell
python
```

В открывшейся консоли Python:

```python
from __init__ import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = User(
        username='admin',
        password=generate_password_hash('надёжный_пароль'),
        admin=True,
    )
    db.session.add(admin)
    db.session.commit()
```

Чтобы выдать права уже зарегистрированному пользователю, найдите его в БД и установите `user.admin = True`, затем `db.session.commit()`.

## Структура проекта

```
__init__.py          — приложение Flask, модели, маршруты, API
run.py               — запуск сервера (рекомендуется)
requirements.txt     — зависимости Python
templates/           — HTML-шаблоны (Jinja2)
static/avatars/      — загруженные аватары (создаётся при установке)
instance/main.db     — база SQLite (создаётся при первом запуске)
```

## Зависимости

| Пакет | Назначение |
|--------|------------|
| Flask | Веб-приложение, шаблоны, маршруты |
| Flask-Login | Сессии и `current_user` |
| Flask-SQLAlchemy | ORM, SQLite |
| Flask-WTF | Защита форм (CSRF) |
| Werkzeug | Хеширование паролей |
| SQLAlchemy | Ядро ORM |

Полный список версий — в `requirements.txt`.

## REST API

Базовый URL: `http://127.0.0.1:5000`

| Метод | URL | Описание |
|--------|-----|----------|
| GET | `/api/snippets` | Список одобренных сниппетов (пагинация: `?page=2`, по 20 на страницу) |

Пример ответа — JSON-массив объектов с полями: `id`, `title`, `author`, `category`, `tags`, `views`, `likes`, `created_at`.

Эндпоинта для одного сниппета по ID в текущей версии нет — детали доступны в веб-интерфейсе (`/post/<id>`).

## База данных

- Файл: `instance/main.db`
- При первом запуске через `run.py` вызываются `db.create_all()` и `init_categories()` (стандартные категории: Web, Python, Malware Analysis и др.)
- Основные модели: `User`, `CodeSnippet`, `Category`, `Tag`, `Comment`, `Vote`, `Report`, `Notification`, `SnippetFile`, `SnippetLink`, `SnippetView`
- Полный сброс: удалите `instance/main.db` и перезапустите приложение

## Стек

- Python 3, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF
- SQLite
- Bootstrap 5, highlight.js (CDN)
- Jinja2
