import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class StreamlitNavigationTest(unittest.TestCase):
    def test_home_hides_home_icon_and_catalog_hides_catalog_icon(self):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app" / "app.py"
        app = AppTest.from_file(str(app_path)).run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        home_keys = [button.key for button in app.button]
        self.assertNotIn("nav_Home", home_keys)
        self.assertIn("nav_Catalog", home_keys)

        next(button for button in app.button if button.key == "nav_Catalog").click()
        app.run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        catalog_keys = [button.key for button in app.button]
        self.assertIn("nav_Home", catalog_keys)
        self.assertNotIn("nav_Catalog", catalog_keys)


if __name__ == "__main__":
    unittest.main()
