from __future__ import annotations

import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from blueprint.auth import AUTH_STATE_KEY, clear_local_session, get_auth_session, sign_in, sign_in_anonymously
from blueprint.backend import (
    ask_research,
    load_recent_blueprints,
    normalize_research_selection,
    preview_research_rerun,
    resolve_research_rerun,
    resolve_founder_checkpoint,
    start_blueprint,
)
from blueprint.config import AppConfig


CONFIG = AppConfig(
    supabase_url="https://example.supabase.co",
    supabase_publishable_key="public-test-key",
    n8n_start_webhook_url="https://n8n.example.test/webhook/blueprint/start",
    request_timeout_seconds=10,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class AuthenticationTests(unittest.TestCase):
    def test_anonymous_sign_in_creates_owner_isolated_session_without_identity_fields(self):
        state = {}
        response = FakeResponse(200, {
            "access_token": "guest-access", "refresh_token": "guest-refresh", "expires_in": 3600,
            "user": {"id": "guest-owner-1", "is_anonymous": True},
        })
        with patch("blueprint.auth.st.session_state", state), patch(
            "blueprint.auth.requests.post", return_value=response
        ) as request:
            session = sign_in_anonymously(CONFIG)

        self.assertEqual(session["user"]["id"], "guest-owner-1")
        self.assertEqual(request.call_args.kwargs["json"], {})
        self.assertNotIn("email", request.call_args.kwargs["json"])
    def test_sign_in_stores_real_supabase_session(self):
        state = {}
        response = FakeResponse(
            200,
            {
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_in": 3600,
                "user": {"id": "owner-1", "email": "founder@example.com"},
            },
        )
        with patch("blueprint.auth.st.session_state", state), patch(
            "blueprint.auth.requests.post", return_value=response
        ) as request:
            session = sign_in(" founder@example.com ", "password123", CONFIG)

        self.assertEqual(session["user"]["id"], "owner-1")
        self.assertEqual(state[AUTH_STATE_KEY]["access_token"], "access")
        self.assertEqual(
            request.call_args.kwargs["headers"]["apikey"],
            "public-test-key",
        )
        self.assertEqual(request.call_args.kwargs["json"]["email"], "founder@example.com")

    def test_expired_session_that_cannot_refresh_is_cleared(self):
        state = {
            AUTH_STATE_KEY: {
                "access_token": "expired",
                "refresh_token": "refresh",
                "expires_at": int(time.time()) - 1,
                "user": {"id": "owner-1"},
            },
            "backend_project_id": "project-1",
        }
        with patch("blueprint.auth.st.session_state", state), patch(
            "blueprint.auth.refresh_auth_session", return_value=None
        ):
            self.assertIsNone(get_auth_session())
        self.assertNotIn(AUTH_STATE_KEY, state)
        self.assertNotIn("backend_project_id", state)

    def test_clear_local_session_removes_blueprint_owner_state(self):
        state = {AUTH_STATE_KEY: {"access_token": "x"}, "backend_run_id": "run-1", "unrelated": 1}
        with patch("blueprint.auth.st.session_state", state):
            clear_local_session()
        self.assertEqual(state, {"unrelated": 1})


class BackendContractTests(unittest.TestCase):
    def test_research_selection_normalizes_and_deduplicates(self):
        self.assertEqual(
            normalize_research_selection(["Competitor research", "competitor_intelligence"]),
            ["competitor_intelligence"],
        )

    def test_empty_selection_defaults_to_all_three(self):
        self.assertEqual(
            set(normalize_research_selection([])),
            {"customer_demand", "competitor_intelligence", "market_economics"},
        )

    def test_start_blueprint_sends_owner_jwt_boundary_payload(self):
        profile = SimpleNamespace(
            idea="A cited founder research workspace",
            goal="startup",
            success_definition="Find ten paying customers",
            target_customer="Solo founders",
            hours_per_week=10,
            money_available=2000,
            launch_timeline="Within 3 months",
            current_work="Customer conversations",
            constraints=["Full-time job"],
            location="India",
        )
        answers = {
            "research_selection": ["Customer research", "Market research"],
            "industry": "Founder tools",
        }
        response = FakeResponse(202, {"ok": True, "project_id": "project-1", "run_id": "run-1"})
        with patch("blueprint.backend._authenticated_request", return_value=response) as request:
            result = start_blueprint(profile, answers, idempotency_key="stable-key-001", config=CONFIG)

        payload = request.call_args.kwargs["json"]
        self.assertEqual(result["run_id"], "run-1")
        self.assertEqual(payload["idempotency_key"], "stable-key-001")
        self.assertEqual(payload["requested_research"], ["customer_demand", "market_economics"])
        self.assertEqual(payload["constraints"]["onboarding_answers"], answers)

    def test_recent_blueprints_attach_only_latest_run_per_project(self):
        projects = [
            {"id": "project-1", "idea_text": "First"},
            {"id": "project-2", "idea_text": "Second"},
        ]
        runs = [
            {"id": "run-new", "project_id": "project-1", "status": "RESEARCHING"},
            {"id": "run-old", "project_id": "project-1", "status": "PARTIAL"},
        ]
        with patch("blueprint.backend._supabase_table_select", side_effect=[projects, runs]):
            result = load_recent_blueprints(CONFIG)
        self.assertEqual(result[0]["latest_run"]["id"], "run-new")
        self.assertIsNone(result[1]["latest_run"])

    def test_ask_research_uses_sibling_authenticated_webhook(self):
        response = FakeResponse(200, {"status": "ANSWERED", "answer": "Grounded answer", "citations": []})
        with patch("blueprint.backend._authenticated_request", return_value=response) as request:
            result = ask_research("What did we learn?", project_id="project-1", run_id="run-1", config=CONFIG)
        self.assertEqual(result["status"], "ANSWERED")
        self.assertEqual(request.call_args.args[1], "https://n8n.example.test/webhook/blueprint/chat")
        self.assertFalse(request.call_args.kwargs["json"]["confirmed_command"])

    def test_checkpoint_resolution_uses_resume_webhook_with_current_run_context(self):
        response = FakeResponse(202, {"ok": True, "status": "PLANNING", "planning_mode": "PROVE_AND_DESIGN"})
        state = {
            "backend_project_id": "project-1", "backend_run_id": "run-1",
            "backend_bundle": {
                "snapshot": {"run": {"profile_version": 2}},
                "research_context": {"project": {"idea_text": "A founder evidence workspace"}},
                "blueprint": {"current_version": {"blueprint": {"starting_position": {"goal": {"type": "PAID_CUSTOMERS"}}}}},
            },
            "dialog_answers": {"research_selection": ["Customer research", "Competitor research", "Market research"]},
        }
        with patch("blueprint.backend.st.session_state", state), patch(
            "blueprint.backend.load_config", return_value=CONFIG
        ), patch("blueprint.backend._authenticated_request", return_value=response) as request:
            result = resolve_founder_checkpoint("checkpoint-1", 4, "PROCEED")

        self.assertEqual(result["status"], "PLANNING")
        self.assertEqual(request.call_args.args[1], "https://n8n.example.test/webhook/blueprint/checkpoint")
        self.assertEqual(request.call_args.kwargs["json"]["requested_research"], ["customer_demand", "competitor_intelligence", "market_economics"])

    def test_rerun_is_preview_then_explicit_resolution(self):
        preview_response = FakeResponse(200, {"ok": True, "status": "NEEDS_CONFIRMATION", "rerun_request_id": "rr-1"})
        resolve_response = FakeResponse(202, {"ok": True, "status": "QUEUED", "run_id": "run-2"})
        with patch("blueprint.backend._authenticated_request", side_effect=[preview_response, resolve_response]) as request:
            preview = preview_research_rerun(
                "market_economics",
                project_id="project-1",
                source_run_id="run-1",
                idempotency_key="rerun-key-001",
                config=CONFIG,
            )
            resolved = resolve_research_rerun("rr-1", 3, "APPROVE", config=CONFIG)
        self.assertEqual(preview["status"], "NEEDS_CONFIRMATION")
        self.assertEqual(resolved["run_id"], "run-2")
        self.assertEqual(request.call_args_list[0].args[1], "https://n8n.example.test/webhook/blueprint/rerun")
        self.assertEqual(request.call_args_list[1].kwargs["json"]["command"], "APPROVE")


if __name__ == "__main__":
    unittest.main()
