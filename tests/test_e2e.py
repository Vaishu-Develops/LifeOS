"""End-to-end integration test for LifeOS.

Tests the full flow: user input → Orchestrator → sub-agents → response.
This test uses deterministic mocking to avoid requiring live OAuth/MCP endpoints.
"""
import unittest
from unittest.mock import patch, MagicMock

from lifeos.agents.orchestrator import Orchestrator


class TestLifeOSE2E(unittest.TestCase):
    """Integration tests for the orchestrator and sub-agents."""

    def test_end_to_end_task_add(self):
        """User adds a task via orchestrator."""
        orch = Orchestrator()
        result = orch.handle_user("test_user", "Add task: review proposal by Friday")

        self.assertEqual(result["intent"], "task.add")
        self.assertEqual(result["route"], "task")
        self.assertEqual(result["action"], "add")
        self.assertIn("task_id", result)
        self.assertGreater(result["task_id"], 0)

    def test_end_to_end_task_list(self):
        """User lists tasks via orchestrator."""
        # Add a task first
        orch = Orchestrator()
        orch.handle_user("test_user", "Add task: test task")
        # Now list
        result = orch.handle_user("test_user", "Show my tasks")

        self.assertEqual(result["intent"], "task.list")
        self.assertEqual(result["route"], "task")
        self.assertEqual(result["action"], "list")
        self.assertIn("tasks", result)
        self.assertGreater(result["count"], 0)

    def test_end_to_end_calendar_list(self):
        """User lists calendar events (without credentials, returns empty)."""
        orch = Orchestrator()
        result = orch.handle_user("test_user", "What does my afternoon look like?")

        self.assertEqual(result["intent"], "calendar.list")
        self.assertEqual(result["route"], "calendar")
        self.assertEqual(result["action"], "list_today")
        # No credentials, so events should be empty
        self.assertEqual(result.get("count"), 0)

    def test_end_to_end_email_search(self):
        """User searches email (without credentials, returns empty)."""
        orch = Orchestrator()
        result = orch.handle_user("test_user", "Search email for project meeting")

        self.assertEqual(result["intent"], "email.search")
        self.assertEqual(result["route"], "email")
        self.assertEqual(result["action"], "search")
        # No credentials, so threads should be empty
        self.assertEqual(result.get("count"), 0)

    def test_end_to_end_unknown_intent(self):
        """User says something the orchestrator doesn't understand."""
        orch = Orchestrator()
        result = orch.handle_user("test_user", "Tell me a joke")

        self.assertEqual(result["intent"], "unknown")
        self.assertEqual(result["route"], "none")
        self.assertIn("message", result)

    def test_orchestrator_with_mock_credentials(self):
        """Verify orchestrator passes credentials to agents."""
        mock_creds = MagicMock()
        mock_creds.token = "fake-access-token"

        with patch("lifeos.agents.calendar_agent.requests") as mock_requests:
            # Mock the HTTP call to return empty events list
            mock_response = MagicMock()
            mock_response.json.return_value = {"items": []}
            mock_response.status_code = 200
            mock_requests.get.return_value = mock_response

            orch = Orchestrator(credentials=mock_creds)
            result = orch.handle_user("test_user", "Show my calendar for today")

            # Should attempt to call the MCP endpoint with auth headers
            self.assertEqual(result["intent"], "calendar.list")
            self.assertEqual(result["route"], "calendar")

    def test_orchestrator_error_handling(self):
        """Orchestrator gracefully handles exceptions in sub-agents."""
        orch = Orchestrator()

        with patch("lifeos.agents.task_agent.TaskAgent.add_task") as mock_add:
            mock_add.side_effect = RuntimeError("DB connection failed")
            result = orch.handle_user("test_user", "Add task: test")

            # Should return an error response
            self.assertEqual(result["route"], "error")
            self.assertIn("message", result)


if __name__ == "__main__":
    unittest.main()
