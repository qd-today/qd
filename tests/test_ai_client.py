"""Tests for libs.ai_client (HAR preprocessing & response parsing)."""
import unittest


class TestPreprocessHar(unittest.TestCase):
    def _make_entry(self, url, method="GET", mime="application/json", body=""):
        return {
            "request": {
                "method": method,
                "url": url,
                "headers": [
                    {"name": "Content-Type", "value": "application/json"},
                    {"name": "User-Agent", "value": "x"},  # 应被过滤
                ],
                "cookies": [{"name": "session", "value": "abc"}],
                "postData": {"mimeType": "application/json", "text": body},
            },
            "response": {
                "status": 200,
                "content": {"mimeType": mime, "text": "ok"},
            },
        }

    def test_filters_static_resources(self):
        from libs.ai_client import preprocess_har
        har = {
            "log": {
                "entries": [
                    self._make_entry("https://x.com/a.js", mime="application/javascript"),
                    self._make_entry("https://x.com/style.css", mime="text/css"),
                    self._make_entry("https://x.com/img.png", mime="image/png"),
                    self._make_entry("https://x.com/api/sign", method="POST"),
                ]
            }
        }
        out = preprocess_har(har, max_entries=10)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["url"], "https://x.com/api/sign")
        self.assertEqual(out[0]["method"], "POST")

    def test_filters_analytics(self):
        from libs.ai_client import preprocess_har
        har = {
            "log": {
                "entries": [
                    self._make_entry("https://www.google-analytics.com/collect"),
                    self._make_entry("https://api.x.com/check_in", method="POST"),
                ]
            }
        }
        out = preprocess_har(har, max_entries=10)
        urls = [e["url"] for e in out]
        self.assertNotIn("https://www.google-analytics.com/collect", urls)
        self.assertIn("https://api.x.com/check_in", urls)

    def test_keeps_relevant_headers_only(self):
        from libs.ai_client import preprocess_har
        har = {"log": {"entries": [self._make_entry("https://x.com/api/sign", "POST")]}}
        out = preprocess_har(har, max_entries=10)
        names = {h["name"].lower() for h in out[0]["headers"]}
        self.assertIn("content-type", names)
        self.assertNotIn("user-agent", names)

    def test_max_entries_limit(self):
        from libs.ai_client import preprocess_har
        har = {
            "log": {
                "entries": [
                    self._make_entry(f"https://x.com/api/n{i}", "POST")
                    for i in range(50)
                ]
            }
        }
        out = preprocess_har(har, max_entries=5)
        self.assertEqual(len(out), 5)

    def test_post_methods_prioritized(self):
        from libs.ai_client import preprocess_har
        har = {
            "log": {
                "entries": [
                    self._make_entry("https://x.com/list", "GET"),
                    self._make_entry("https://x.com/sign", "POST"),
                ]
            }
        }
        out = preprocess_har(har, max_entries=10)
        # POST 应排在前面
        self.assertEqual(out[0]["method"], "POST")


class TestParseAIResponse(unittest.TestCase):
    def test_plain_json(self):
        from libs.ai_client import parse_ai_response
        result = parse_ai_response('{"sitename": "x", "entries": []}')
        self.assertEqual(result["sitename"], "x")

    def test_markdown_wrapped(self):
        from libs.ai_client import parse_ai_response
        result = parse_ai_response('```json\n{"sitename": "y", "entries": []}\n```')
        self.assertEqual(result["sitename"], "y")

    def test_with_extra_text(self):
        from libs.ai_client import parse_ai_response
        result = parse_ai_response(
            'Here is the result:\n{"sitename": "z", "entries": []}\nThanks.'
        )
        self.assertEqual(result["sitename"], "z")

    def test_invalid_json_raises(self):
        from libs.ai_client import AIClientError, parse_ai_response
        with self.assertRaises(AIClientError):
            parse_ai_response("not json at all")


class TestAIResultToHar(unittest.TestCase):
    def test_basic_conversion(self):
        from libs.ai_client import ai_result_to_har
        result = {
            "sitename": "Demo",
            "entries": [
                {
                    "method": "POST",
                    "url": "https://api.demo.com/sign",
                    "headers": [
                        {"name": "Content-Type", "value": "application/json"}
                    ],
                    "body": '{"action":"sign"}',
                    "reason": "POST 路径含 sign",
                }
            ],
        }
        har = ai_result_to_har(result)
        self.assertEqual(len(har["log"]["entries"]), 1)
        e = har["log"]["entries"][0]
        self.assertEqual(e["request"]["method"], "POST")
        self.assertEqual(e["request"]["url"], "https://api.demo.com/sign")
        self.assertIn("postData", e["request"])
        self.assertEqual(e["request"]["postData"]["text"], '{"action":"sign"}')

    def test_empty_entries(self):
        from libs.ai_client import ai_result_to_har
        har = ai_result_to_har({"entries": []})
        self.assertEqual(har["log"]["entries"], [])


class TestAIClientDisabled(unittest.TestCase):
    def test_disabled_when_no_key(self):
        from libs.ai_client import AIClient
        client = AIClient(api_key="")
        self.assertFalse(client.enabled)


if __name__ == "__main__":
    unittest.main()
