#!/usr/bin/env python3
"""
Скрипт для миграции базы данных - добавление таблицы файлов
"""

from __init__ import app, db

def migrate_files_table():
    """Создает таблицу для файлов сниппетов"""
    with app.app_context():
        print("Создание таблицы snippet_file...")
        db.create_all()
        print("✅ Таблица snippet_file создана успешно!")

if __name__ == '__main__':
    migrate_files_table()