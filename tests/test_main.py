import unittest


class MainImportTests(unittest.TestCase):
    def test_import_main_without_api_key_does_not_raise(self):
        import main

        self.assertTrue(hasattr(main, "weather_agent"))


if __name__ == "__main__":
    unittest.main()
