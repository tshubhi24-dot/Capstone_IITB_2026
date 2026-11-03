import unittest

from analystdesk.chat_context import build_chat_question


class ChatContextTests(unittest.TestCase):
    def test_new_question_does_not_use_previous_context(self):
        question = "What about 2023?"
        context = [{"question": "Compare Microsoft and Alphabet.", "answer": "Prior answer."}]

        self.assertEqual(build_chat_question(question, "new", context), question)

    def test_follow_up_includes_recent_context(self):
        context = [
            {"question": f"Question {i}", "answer": f"Answer {i}"}
            for i in range(4)
        ]

        result = build_chat_question("What about 2023?", "follow_up", context)

        self.assertIn("Question 1", result)
        self.assertIn("Question 2", result)
        self.assertIn("Question 3", result)
        self.assertNotIn("Question 0", result)
        self.assertIn("Current follow-up question: What about 2023?", result)

    def test_follow_up_without_context_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "before asking a follow-up"):
            build_chat_question("What about 2023?", "follow_up", [])

    def test_unknown_question_mode_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Choose either"):
            build_chat_question("Question", "unknown", [])


if __name__ == "__main__":
    unittest.main()
