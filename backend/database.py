"""SQLite persistence for catalog, users, sessions, orders, and preferences."""

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from typing import Any


DB_PATH = os.getenv(
    "SHOPPING_DB_PATH", os.path.join(os.path.dirname(__file__), "store.db")
)


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def migrate_database() -> None:
    """Apply additive migrations without replacing existing catalog data."""
    with closing(connect()) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS auth_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                preference_key TEXT NOT NULL,
                preference_value TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'explicit',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, preference_key),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_auth_sessions_user
                ON auth_sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_preferences_user
                ON user_preferences(user_id);
            """
        )
        order_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(orders)").fetchall()
        }
        if "user_id" not in order_columns:
            connection.execute("ALTER TABLE orders ADD COLUMN user_id INTEGER")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id, ordered_at)"
        )
        connection.commit()


def list_products() -> list[dict[str, Any]]:
    with closing(connect()) as connection:
        rows = connection.execute(
            """
            SELECT p.id, p.name, p.category, p.price, p.description, p.is_organic,
                   COALESCE(ROUND(AVG(r.rating), 2), 0) AS average_rating,
                   COUNT(r.id) AS review_count
            FROM products AS p
            LEFT JOIN reviews AS r ON r.product_id = p.id
            GROUP BY p.id
            ORDER BY p.category, p.name
            """
        ).fetchall()
    return [_serialize_product(row) for row in rows]


def get_product(product_id: int) -> dict[str, Any] | None:
    with closing(connect()) as connection:
        row = connection.execute(
            """SELECT id, name, category, price, description, is_organic
               FROM products WHERE id = ?""",
            (product_id,),
        ).fetchone()
    return _serialize_product(row) if row else None


def create_product(product: dict[str, Any]) -> dict[str, Any]:
    with closing(connect()) as connection:
        cursor = connection.execute(
            """INSERT INTO products (name, category, price, description, is_organic)
               VALUES (?, ?, ?, ?, ?)""",
            (
                product["name"], product["category"], product["price"],
                product["description"], int(product["is_organic"]),
            ),
        )
        product_id = cursor.lastrowid
        connection.commit()
    return get_product(product_id)


def update_product(product_id: int, product: dict[str, Any]) -> dict[str, Any] | None:
    with closing(connect()) as connection:
        cursor = connection.execute(
            """UPDATE products
               SET name = ?, category = ?, price = ?, description = ?, is_organic = ?
               WHERE id = ?""",
            (
                product["name"], product["category"], product["price"],
                product["description"], int(product["is_organic"]), product_id,
            ),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
    return get_product(product_id)


def delete_product(product_id: int) -> bool:
    with closing(connect()) as connection:
        connection.execute("DELETE FROM reviews WHERE product_id = ?", (product_id,))
        cursor = connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
        connection.commit()
        return cursor.rowcount > 0


def product_vocabulary() -> set[str]:
    vocabulary: set[str] = set()
    with closing(connect()) as connection:
        rows = connection.execute("SELECT name, category FROM products").fetchall()
    for row in rows:
        for value in (row["name"], row["category"]):
            if value:
                vocabulary.update(part.lower() for part in value.replace("-", " ").split())
    return {word for word in vocabulary if len(word) >= 3}


def create_user(name: str, email: str, password_hash: str) -> dict[str, Any]:
    with closing(connect()) as connection:
        cursor = connection.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name.strip(), email.strip().lower(), password_hash),
        )
        user_id = cursor.lastrowid
        connection.commit()
    return get_user_by_id(user_id)


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with closing(connect()) as connection:
        row = connection.execute(
            "SELECT id, name, email, password_hash, created_at FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with closing(connect()) as connection:
        row = connection.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def save_auth_session(token_hash: str, user_id: int, expires_at: str) -> None:
    with closing(connect()) as connection:
        connection.execute(
            "INSERT INTO auth_sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (token_hash, user_id, expires_at),
        )
        connection.commit()


def user_for_session(token_hash: str) -> dict[str, Any] | None:
    now = datetime.now(timezone.utc).isoformat()
    with closing(connect()) as connection:
        row = connection.execute(
            """
            SELECT u.id, u.name, u.email, u.created_at
            FROM auth_sessions AS s
            JOIN users AS u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ?
            """,
            (token_hash, now),
        ).fetchone()
    return dict(row) if row else None


def delete_auth_session(token_hash: str) -> None:
    with closing(connect()) as connection:
        connection.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))
        connection.commit()


def list_user_orders(user_id: int, limit: int = 50) -> list[dict[str, Any]]:
    with closing(connect()) as connection:
        rows = connection.execute(
            """
            SELECT id, product_id, product_name, price, ordered_at
            FROM orders
            WHERE user_id = ?
            ORDER BY ordered_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def order_summary(user_id: int) -> dict[str, Any]:
    with closing(connect()) as connection:
        totals = connection.execute(
            """SELECT COUNT(*) AS order_count, COALESCE(ROUND(SUM(price), 2), 0) AS total_spent
               FROM orders WHERE user_id = ?""",
            (user_id,),
        ).fetchone()
        categories = connection.execute(
            """
            SELECT p.category, COUNT(*) AS order_count,
                   COALESCE(ROUND(SUM(o.price), 2), 0) AS total_spent
            FROM orders AS o
            LEFT JOIN products AS p ON p.id = o.product_id
            WHERE o.user_id = ?
            GROUP BY p.category
            ORDER BY order_count DESC, total_spent DESC
            """,
            (user_id,),
        ).fetchall()
    return {"totals": dict(totals), "categories": [dict(row) for row in categories]}


def list_preferences(user_id: int) -> list[dict[str, Any]]:
    with closing(connect()) as connection:
        rows = connection.execute(
            """SELECT preference_key, preference_value, source, updated_at
               FROM user_preferences WHERE user_id = ? ORDER BY preference_key""",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def set_preference(user_id: int, key: str, value: str, source: str = "explicit") -> None:
    with closing(connect()) as connection:
        connection.execute(
            """
            INSERT INTO user_preferences
                (user_id, preference_key, preference_value, source, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, preference_key) DO UPDATE SET
                preference_value = excluded.preference_value,
                source = excluded.source,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, key, value, source),
        )
        connection.commit()


def delete_preference(user_id: int, key: str) -> bool:
    with closing(connect()) as connection:
        cursor = connection.execute(
            "DELETE FROM user_preferences WHERE user_id = ? AND preference_key = ?",
            (user_id, key),
        )
        connection.commit()
        return cursor.rowcount > 0


def _serialize_product(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result["is_organic"] = bool(result["is_organic"])
    return result
