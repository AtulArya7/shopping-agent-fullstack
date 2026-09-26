import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import database
import main
import shopping_agent
from fastapi.testclient import TestClient
from user_context import current_user_id


class ShoppingFeaturesTest(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.db_path = handle.name
        database.DB_PATH = self.db_path
        shopping_agent.DB_PATH = self.db_path
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.executescript(
                """
                CREATE TABLE products (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT,
                    price REAL, description TEXT, is_organic INTEGER DEFAULT 0
                );
                CREATE TABLE reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER,
                    rating REAL, reviewer_name TEXT, review_text TEXT
                );
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL,
                    product_name TEXT NOT NULL, price REAL NOT NULL,
                    ordered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                INSERT INTO products VALUES
                    (1, 'Whole Wheat Bread', 'bread', 4.99, 'Fresh whole-grain bread', 0);
                """
            )
            connection.commit()
        database.migrate_database()
        os.environ["ADMIN_PASSWORD"] = "test-admin-password"
        main.SESSIONS.clear()
        self.client = TestClient(main.app)
        self.atul = self._register("Atul", "atul@example.com")
        self.nikhil = self._register("Nikhil", "nikhil@example.com")

    def tearDown(self):
        self.client.close()
        os.unlink(self.db_path)

    def _register(self, name, email):
        response = self.client.post(
            "/api/auth/register",
            json={"name": name, "email": email, "password": "secure-pass-123"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    @staticmethod
    def headers(account):
        return {"Authorization": f"Bearer {account['token']}"}

    def test_login_rejects_wrong_password(self):
        response = self.client.post(
            "/api/auth/login",
            json={"email": "atul@example.com", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 401)

    def test_orders_are_isolated_between_users(self):
        context_token = current_user_id.set(self.atul["user"]["id"])
        try:
            shopping_agent.checkout.invoke({"product_id": 1})
        finally:
            current_user_id.reset(context_token)

        atul_orders = self.client.get(
            "/api/orders/me", headers=self.headers(self.atul)
        ).json()["orders"]
        nikhil_orders = self.client.get(
            "/api/orders/me", headers=self.headers(self.nikhil)
        ).json()["orders"]
        self.assertEqual(len(atul_orders), 1)
        self.assertEqual(atul_orders[0]["product_name"], "Whole Wheat Bread")
        self.assertEqual(nikhil_orders, [])

    def test_preferences_are_isolated_between_users(self):
        self.client.put(
            "/api/preferences/me",
            headers=self.headers(self.atul),
            json={"key": "max_price", "value": "20"},
        )
        atul = self.client.get(
            "/api/preferences/me", headers=self.headers(self.atul)
        ).json()["preferences"]
        nikhil = self.client.get(
            "/api/preferences/me", headers=self.headers(self.nikhil)
        ).json()["preferences"]
        self.assertEqual(atul[0]["preference_value"], "20")
        self.assertEqual(nikhil, [])

    def test_chat_session_cannot_be_used_by_another_user(self):
        session_id = self.client.post(
            "/api/session/new", headers=self.headers(self.atul)
        ).json()["session_id"]
        response = self.client.post(
            "/api/chat",
            headers=self.headers(self.nikhil),
            json={"session_id": session_id, "message": "Show bread"},
        )
        self.assertEqual(response.status_code, 404)

    def test_guardrail_rejects_off_topic_before_agent(self):
        session_id = self.client.post(
            "/api/session/new", headers=self.headers(self.atul)
        ).json()["session_id"]
        with patch.object(main, "run_agent") as mocked_agent:
            response = self.client.post(
                "/api/chat",
                headers=self.headers(self.atul),
                json={"session_id": session_id, "message": "Explain black holes"},
            )
        self.assertIn("only help with shopping", response.json()["response"])
        mocked_agent.assert_not_called()

    def test_admin_can_add_product_but_regular_auth_cannot(self):
        product = {
            "name": "Sourdough Bread", "category": "bread", "price": 6.5,
            "description": "Naturally fermented loaf", "is_organic": False,
        }
        denied = self.client.post(
            "/api/admin/products", headers=self.headers(self.atul), json=product
        )
        allowed = self.client.post(
            "/api/admin/products",
            headers={"X-Admin-Password": "test-admin-password"},
            json=product,
        )
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(allowed.status_code, 200)


if __name__ == "__main__":
    unittest.main()
