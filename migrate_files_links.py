#!/usr/bin/env python3
"""
Миграция для добавления поддержки загрузки файлов и ссылок на проекты
"""

import sqlite3
from datetime import datetime

def migrate_database():
    conn = sqlite3.connect('instance/main.db')
    cursor = conn.cursor()
    
    try:
        print("Начинаем миграцию базы данных...")
        
        # Добавляем новые поля в таблицу snippet_file
        print("Добавляем новые поля в таблицу snippet_file...")
        
        # Проверяем, существуют ли уже новые поля
        cursor.execute("PRAGMA table_info(snippet_file)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'file_type' not in columns:
            cursor.execute("ALTER TABLE snippet_file ADD COLUMN file_type VARCHAR(20) DEFAULT 'text'")
            print("✓ Добавлено поле file_type")
        
        if 'file_size' not in columns:
            cursor.execute("ALTER TABLE snippet_file ADD COLUMN file_size INTEGER")
            print("✓ Добавлено поле file_size")
        
        if 'mime_type' not in columns:
            cursor.execute("ALTER TABLE snippet_file ADD COLUMN mime_type VARCHAR(100)")
            print("✓ Добавлено поле mime_type")
        
        # Создаем таблицу snippet_link
        print("Создаем таблицу snippet_link...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snippet_link (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snippet_id INTEGER NOT NULL,
                title VARCHAR(200) NOT NULL,
                url VARCHAR(500) NOT NULL,
                description TEXT,
                link_type VARCHAR(50),
                "order" INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (snippet_id) REFERENCES code_snippet (id) ON DELETE CASCADE
            )
        """)
        print("✓ Создана таблица snippet_link")
        
        # Обновляем существующие файлы, устанавливая значения по умолчанию
        print("Обновляем существующие файлы...")
        cursor.execute("""
            UPDATE snippet_file 
            SET file_size = LENGTH(content),
                mime_type = 'text/plain'
            WHERE file_size IS NULL OR mime_type IS NULL
        """)
        
        affected_rows = cursor.rowcount
        print(f"✓ Обновлено {affected_rows} существующих файлов")
        
        conn.commit()
        print("✅ Миграция успешно завершена!")
        
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()