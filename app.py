"""Небольшой учебный обработчик заявок. Некоторые сценарии реализованы с ошибками.

Тестовое задание САП КОД. Используются только синтетические данные.
"""

import sqlite3


def _prepare_db(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            external_id TEXT NOT NULL,
            customer TEXT NOT NULL,
            message TEXT NOT NULL,
            UNIQUE(source, external_id)
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL
        );
        """
    )


def _validate_event(event: dict) -> tuple[bool, str]:
    """Проверяет событие. Возвращает (валидно, причина_ошибки)."""
    fields = ["source", "external_id", "customer", "message"]
    for field in fields:
        value = event.get(field)
        if not isinstance(value, str):
            return False, f"Поле '{field}' должно быть строкой"
        if not value.strip():
            return False, f"Поле '{field}' не должно быть пустым"
    return True, ""


def process_event(event: dict, db_path: str) -> dict:
    """Принимает событие и возвращает dict со статусом и, при успехе, id заявки.

    Контракт статусов и бизнес-правила описаны в README.md.
    """
    # 1. Валидация
    is_valid, reason = _validate_event(event)
    if not is_valid:
        return {"status": "invalid", "reason": reason}

    # 2. Обрезка пробелов
    source = event["source"].strip()
    external_id = event["external_id"].strip()
    customer = event["customer"].strip()
    message = event["message"].strip()

    with sqlite3.connect(db_path) as connection:
        _prepare_db(connection)

        # 3. Проверка на дубликат
        existing = connection.execute(
            "SELECT id FROM leads WHERE source = ? AND external_id = ?",
            (source, external_id),
        ).fetchone()

        if existing:
            return {"status": "duplicate", "id": existing[0]}

        # 4. Создание новой заявки
        cursor = connection.execute(
            """
            INSERT INTO leads (source, external_id, customer, message)
            VALUES (?, ?, ?, ?)
            """,
            (source, external_id, customer, message),
        )
        lead_id = cursor.lastrowid

        # 5. Создание уведомления
        connection.execute(
            "INSERT INTO notifications (lead_id) VALUES (?)", (lead_id,)
        )
        connection.commit()
        return {"status": "created", "id": lead_id}