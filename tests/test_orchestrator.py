import unittest
from lifeos.agents.orchestrator import Orchestrator

class TestOrchestrator(unittest.TestCase):
    def test_task_add_route(self):
        orch = Orchestrator()
        # Use a fake user id and force deterministic behavior
        result = orch.handle_user("u1", "Add task: Write report by Friday")
        self.assertIn("intent", result)
        self.assertEqual(result["intent"], "task.add")
        self.assertIn("task_id", result)

    def test_unknown_route(self):
        orch = Orchestrator()
        result = orch.handle_user("u1", "Tell me a joke")
        self.assertEqual(result.get("route"), "none")

if __name__ == '__main__':
    unittest.main()
