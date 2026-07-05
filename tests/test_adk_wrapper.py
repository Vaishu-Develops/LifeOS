import unittest
from lifeos.agents.adk_wrapper import ADKClient

class TestADKClient(unittest.TestCase):
    def test_fallback_classification(self):
        client = ADKClient()
        # Force fallback by ensuring ADK is not available
        client._has_adk = False
        intent = client.classify_intent("Add task buy milk")
        self.assertEqual(intent, "task.add")

    def test_adk_json_response_parsing(self):
        client = ADKClient()
        # Simulate ADK agent available and returning a JSON string
        client._has_adk = True
        client._agent = object()
        def fake_call(prompt):
            return '{"intent": "task.list", "confidence": 0.92}'
        client._call_agent = fake_call
        intent = client.classify_intent("Show my tasks")
        self.assertEqual(intent, "task.list")

if __name__ == '__main__':
    unittest.main()
