import unittest

from blueprint.workspace_ui import _local_chat_answer


class WorkspaceChatFallbackTests(unittest.TestCase):
    def test_basic_foundation_question_has_plain_language_answer(self):
        answer = _local_chat_answer(
            "What is foundation?",
            "foundation",
            {},
            ("running", "Researching"),
        )

        self.assertIn("problem hypothesis", answer)
        self.assertNotEqual("UNKNOWN", answer.strip().upper())

    def test_next_step_question_returns_actionable_sequence(self):
        answer = _local_chat_answer(
            "What should I do next?",
            "foundation",
            {},
            ("running", "Researching"),
        )

        self.assertIn("safest next moves", answer)
        self.assertIn("1.", answer)

    def test_unstarted_section_fails_closed_instead_of_inventing(self):
        answer = _local_chat_answer(
            "What did the research prove?",
            "customer_demand",
            {},
            ("locked", "Needs Gate 1 decision"),
        )

        self.assertIn("has not produced an accepted result", answer)
        self.assertIn("will not invent", answer)


if __name__ == "__main__":
    unittest.main()
