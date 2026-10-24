
import unittest
from unittest.mock import patch, Mock

from local_llm import ask_gemma


class TestLocalLLM(unittest.TestCase):
    def test_rejects_empty_question(self):
        with self.assertRaises(ValueError):
            ask_gemma(" ")

    def test_returns_model_answer(self):
        mock_response = Mock()
        mock_response.json.return_value = {
            "message": {"content": "The entry point is main.py."}
        }
        mock_response.raise_for_status.return_value = None

        with patch("local_llm.requests.post", return_value=mock_response):
            answer = ask_gemma("Where is the entry point?")

        self.assertEqual(answer, "The entry point is main.py.")


if __name__ == "__main__":
    unittest.main()
