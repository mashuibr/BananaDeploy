import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

# Add tools directory to path to import deploy
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools')))
import deploy

class TestDeployHistory(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create dummy history files
        self.staging_history = [
            {"timestamp": "2023-01-01T10:00:00Z", "service": "backend", "version": "v1.0.0", "status": "success", "deployed_by": "alice"},
            {"timestamp": "2023-01-02T10:00:00Z", "service": "frontend", "version": "v1.1.0-password-supersecret", "status": "success", "deployed_by": "bob"}
        ]
        self.prod_history = [
            {"timestamp": "2023-01-05T10:00:00Z", "service": "backend", "version": "v1.0.0", "status": "success", "deployed_by": "charlie"}
        ]
        
        with open(".deploy_history_staging.json", "w") as f:
            json.dump(self.staging_history, f)
            
        with open(".deploy_history_production.json", "w") as f:
            json.dump(self.prod_history, f)

    def tearDown(self):
        os.chdir(self.original_cwd)
        for f in os.listdir(self.test_dir):
            os.remove(os.path.join(self.test_dir, f))
        os.rmdir(self.test_dir)

    def test_redact_secrets(self):
        self.assertEqual(deploy.redact_secrets("token=mysecrettoken123"), "token=***REDACTED***")
        self.assertEqual(deploy.redact_secrets("v1.0-password:  supersecret"), "v1.0-password=***REDACTED***")
        self.assertEqual(deploy.redact_secrets("Bearer abcdef1234567"), "Bearer=***REDACTED***")
        self.assertEqual(deploy.redact_secrets("normal_version_string"), "normal_version_string")

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_list_deployments_json(self, mock_stdout):
        deploy.list_deployments("staging", output_format="json")
        output = mock_stdout.getvalue()
        data = json.loads(output)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["operator"], "alice")
        self.assertEqual(data[0]["environment"], "staging")
        # Check redaction worked
        self.assertEqual(data[1]["version"], "v1.1.0-password=***REDACTED***")

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_list_deployments_all_envs(self, mock_stdout):
        # Only tests that all environments are aggregated
        deploy.list_deployments("all", output_format="json")
        output = mock_stdout.getvalue()
        data = json.loads(output)
        
        # We only created staging and production histories in our dummy setup,
        # but ENVIRONMENTS has development, staging, production.
        # development will just return []
        self.assertEqual(len(data), 3)
        envs_found = set(d["environment"] for d in data)
        self.assertEqual(envs_found, {"staging", "production"})
        
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_list_deployments_filter_service(self, mock_stdout):
        deploy.list_deployments("all", service="frontend", output_format="json")
        output = mock_stdout.getvalue()
        data = json.loads(output)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["service"], "frontend")

if __name__ == '__main__':
    unittest.main()
