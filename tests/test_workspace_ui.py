import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from blueprint.workspace_ui import (
    SECTION_PREVIEWS,
    _can_answer_from_section,
    _dedupe_boundary,
    _display_text,
    _enrich_foundation_from_idea,
    _instant_foundation,
    _local_chat_answer,
    _open_workspace_view,
    _projected_score,
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

    def test_common_section_questions_take_the_instant_grounded_path(self):
        self.assertTrue(
            _can_answer_from_section(
                "What are the strongest competitor gaps?",
                "competitor_intelligence",
                {"competitors": [{"name": "Example"}]},
            )
        )
        self.assertFalse(
            _can_answer_from_section(
                "Combine the competitor, customer, and market findings into a new positioning strategy with trade-offs",
                "competitor_intelligence",
                {"competitors": [{"name": "Example"}]},
            )
        )

    def test_verdict_projection_is_bounded_and_conditional(self):
        self.assertEqual(60, _projected_score(48, 3))
        self.assertEqual(100, _projected_score(96, 5))
        self.assertIsNone(_projected_score(None, 3))


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
    def test_foundation_display_normalizes_lists_and_repeated_audience_text(self):
        self.assertEqual("No major constraint", _display_text(["No major constraint"]))
        self.assertEqual(
            "Small businesses; Independent dental clinics",
            _dedupe_boundary("Small businesses; Independent dental clinics — Independent dental clinics"),
        )

    def test_running_age_uses_the_latest_durable_task_timestamp(self):
        stamp = (datetime.now(timezone.utc) - timedelta(seconds=215)).isoformat()

        age = _running_age_seconds({"updated_at": stamp})

        self.assertIsNotNone(age)
        self.assertGreaterEqual(age, 210)
        self.assertLess(age, 225)

    def test_running_age_is_unknown_for_missing_or_malformed_state(self):
        self.assertIsNone(_running_age_seconds(None))
        self.assertIsNone(_running_age_seconds({"updated_at": "not-a-timestamp"}))

    def test_every_workspace_section_has_an_informative_waiting_preview(self):
        self.assertIn("jobs", SECTION_PREVIEWS["customer_demand"][1])
        self.assertIn("Direct, indirect", SECTION_PREVIEWS["competitor_intelligence"][1])
        self.assertIn("beachhead", SECTION_PREVIEWS["market_economics"][1])

    def test_foundation_can_be_structured_without_web_or_model_latency(self):
        context = {
            "project": {
                "constraints": {
                    "onboarding_answers": {
                        "target_customer": ["Busy professionals"],
                        "goal": "Validate demand",
                        "hours_per_week": 6,
                        "money_available": 0,
                    }
                }
            }
        }
        fake_streamlit = SimpleNamespace(session_state={})
        with patch("blueprint.workspace_ui.st", fake_streamlit):
            result = _instant_foundation(context, "A fitness tracker for busy professionals")

        self.assertEqual("foundation", result["module_key"])
        self.assertIn("Busy professionals", result["target_user_boundary"])
        self.assertTrue(result["assumptions"])
        self.assertTrue(result["risks"])

    def test_foundation_recovers_explicit_audience_from_the_idea(self):
        result = _enrich_foundation_from_idea(
            {
                "target_user_boundary": "Not identified — founder input required.",
                "assumptions": ["A user must be chosen."],
                "unknowns": ["The first target customer segment is not yet specific enough to test."],
                "success_definition": "Not sure:",
            },
            "A privacy-first fitness tracker for busy professionals that supports realistic habits",
        )

        self.assertIn("busy professionals", result["target_user_boundary"])
        self.assertFalse(result["unknowns"])
        self.assertIn("measurable", result["success_definition"])


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


class ParallelResearchWorkflowTests(unittest.TestCase):
    def test_parallel_runner_filters_non_uuid_source_labels_before_rpc(self):
        root = Path(__file__).resolve().parents[1]
        workflow = json.loads(
            (root / "backend" / "n8n" / "BP-STAGE1-ASYNC-01-research-runner.json").read_text(
                encoding="utf-8"
            )
        )
        prepare = next(node for node in workflow["nodes"] if node["name"] == "Prepare Durable Observation")

        self.assertIn("durableEvidenceIds", prepare["parameters"]["jsCode"])
        self.assertIn("uuid.test(id)", prepare["parameters"]["jsCode"])

    def test_scheduler_dispatches_selected_research_without_waiting(self):
        root = Path(__file__).resolve().parents[1]
        workflow = json.loads(
            (root / "backend" / "n8n" / "BP-SCHED-01-eligible-task-scheduler.json").read_text(
                encoding="utf-8"
            )
        )
        dispatch = next(node for node in workflow["nodes"] if node["name"] == "Dispatch Parallel Specialist Runner")

        self.assertFalse(dispatch["parameters"]["options"]["waitForSubWorkflow"])

    def test_stage1_uses_the_validated_fast_model_for_bounded_extraction(self):
        root = Path(__file__).resolve().parents[1]
        workflow = json.loads(
            (root / "backend" / "n8n" / "BP-STAGE1-01-research-specialist.json").read_text(
                encoding="utf-8"
            )
        )
        prepare = next(node for node in workflow["nodes"] if node["name"] == "Prepare Grounded Specialist Analysis")
        analyst = next(node for node in workflow["nodes"] if node["name"] == "Nebius — Bounded Stage 1 Analyst")
        code = prepare["parameters"]["jsCode"]

        self.assertIn("Qwen/Qwen3-30B-A3B-Instruct-2507", code)
        self.assertIn("exactly 5 concise objects", code)
        self.assertIn("evidence.slice(0,6)", code)
        self.assertIn("slice(0,900)", code)
        self.assertEqual(90000, analyst["parameters"]["options"]["timeout"])


if __name__ == "__main__":
    unittest.main()
