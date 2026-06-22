import unittest
import json
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure core is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.web_intelligence import WebIntelligenceTools

class TestWebIntelligenceTools(unittest.TestCase):
    
    @patch('core.web_intelligence.requests.request')
    def test_execute_raw_http(self, mock_request):
        # Mock response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://example.com"
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_resp.text = "<html><body><h1>Hello Dr. Prime</h1></body></html>"
        mock_resp.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
        
        mock_request.return_value = mock_resp
        
        result = WebIntelligenceTools.execute_raw_http("https://example.com")
        
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["text"], "<html><body><h1>Hello Dr. Prime</h1></body></html>")
        
    def test_evaluate_xpath_or_css(self):
        html = "<html><body><div id='data'>Secret 123</div></body></html>"
        result = WebIntelligenceTools.evaluate_xpath_or_css(html, "#data")
        self.assertEqual(len(result), 1)
        self.assertIn("Secret 123", result[0])
        
    def test_regex_extractor(self):
        text = "Contact me at dr.prime@primenergeia.com or support@primenergeia.com."
        emails = WebIntelligenceTools.regex_extractor(text, r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        self.assertEqual(len(emails), 2)
        self.assertIn("dr.prime@primenergeia.com", emails)
        
    def test_dom_skeleton_viewer(self):
        html = "<html><head><script>alert('x');</script></head><body><div>Text</div></body></html>"
        skeleton = WebIntelligenceTools.dom_skeleton_viewer(html)
        self.assertNotIn("alert", skeleton)
        self.assertNotIn("Text", skeleton)
        self.assertIn("div", skeleton)

if __name__ == "__main__":
    unittest.main()
