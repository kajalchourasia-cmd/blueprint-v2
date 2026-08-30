import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from blueprint.workspace_ui import (
    _local_chat_answer,
    _open_workspace_view,
    _project_title,
    _running_age_seconds,
    _return_to_workspace,
)


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


class WorkspaceTitleTests(unittest.TestCase):
    def test_long_founder_idea_becomes_a_short_product_title(self):
        title = _project_title(
            "I want to build a fitness tracking app for busy professionals "
            "because they struggle to maintain consistent habits."
        )

        self.assertEqual("Fitness Tracking App", title)

    def test_unstructured_idea_title_is_bounded(self):
        title = _project_title(
            "A community-led solution that connects independent founders "
            "to trustworthy customer discovery opportunities"
        )

        self.assertLessEqual(len(title.split()), 5)


class WorkspaceRunningStateTests(unittest.TestCase):
    def test_running_age_uses_the_latest_durable_task_timestamp(self):
        stamp = (datetime.now(timezone.utc) - timedelta(seconds=215)).isoformat()

        age = _running_age_seconds({"updated_at": stamp})

        self.assertIsNotNone(age)
        self.assertGreaterEqual(age, 210)
        self.assertLess(age, 225)

    def test_running_age_is_unknown_for_missing_or_malformed_state(self):
        self.assertIsNone(_running_age_seconds(None))
        self.assertIsNone(_running_age_seconds({"updated_at": "not-a-timestamp"}))


class WorkspaceNavigationTests(unittest.TestCase):
    def test_blueprint_round_trip_restores_the_active_run_and_section(self):
        session_state = {
            "backend_project_id": "project-1",
            "backend_run_id": "run-1",
            "bp_selected_section": "competitor_intelligence",
        }
        query_params = {}

        def rerun():
            raise RuntimeError("rerun")

        fake_streamlit = SimpleNamespace(
            session_state=session_state,
            query_params=query_params,
            rerun=rerun,
        )
        with patch("blueprint.workspace_ui.st", fake_streamlit):
            with self.assertRaisesRegex(RuntimeError, "rerun"):
                _open_workspace_view("blueprint")
            self.assertEqual("blueprint", query_params["view"])
            self.assertEqual("run-1", query_params["run_id"])

            session_state["backend_run_id"] = "wrong-run"
            session_state["bp_selected_section"] = "foundation"
            with self.assertRaisesRegex(RuntimeError, "rerun"):
                _return_to_workspace()

        self.assertNotIn("view", query_params)
        self.assertEqual("run-1", session_state["backend_run_id"])
        self.assertEqual("competitor_intelligence", session_state["bp_selected_section"])


if __name__ == "__main__":
    unittest.main()
