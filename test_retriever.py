
import unittest
from retriever import retrieve_context


class TestRetriever(unittest.TestCase):
    def setUp(self):
        self.files = [
            {
                "path": "main.py",
                "content": (
                    "def main():\n"
                    "    start_server()\n"
                    "    print('started')"
                ),
            },
            {
                "path": "database.py",
                "content": (
                    "def connect_database():\n"
                    "    return create_connection()"
                ),
            },
        ]

    def test_finds_relevant_file(self):
        results = retrieve_context(
            self.files, "Where is the database connection?"
        )
        self.assertTrue(results)
        self.assertEqual(results[0]["path"], "database.py")

    def test_includes_line_numbers(self):
        results = retrieve_context(self.files, "database connection")
        self.assertEqual(results[0]["start_line"], 1)
        self.assertIn("connect_database", results[0]["content"])

    def test_returns_empty_for_unmatched_question(self):
        results = retrieve_context(self.files, "quantum spaceship")
        self.assertEqual(results, [])

    def test_rejects_invalid_top_k(self):
        with self.assertRaises(ValueError):
            retrieve_context(self.files, "database", top_k=0)


if __name__ == "__main__":
    unittest.main()
