import unittest
from unittest.mock import Mock, patch

from qd_core.client.cookie_utils import CookieSession
from tornado import httpclient, httputil


class TestCookieSession(unittest.TestCase):
    def setUp(self):
        self.cookie_session = CookieSession()

    def test_extract_cookies_to_jar(self):
        # Mock the request and response objects
        headers = httputil.HTTPHeaders({"Set-Cookie": "test_name=test_value; Expires=Wed, 21 Oct 2015 07:28:00 GMT"})
        mock_request = httpclient.HTTPRequest(
            url="test-url",
            headers=headers,
        )
        mock_response = httpclient.HTTPResponse(
            request=mock_request,
            code=200,
            headers=headers,
        )
        # Call the method and check if cookies are extracted correctly
        with patch("qd_core.client.cookie_utils.logger_cookiejar.debug") as mock_debug:
            self.cookie_session.extract_cookies_to_jar(mock_request, mock_response)
            mock_debug.assert_called()  # Ensure debug logging was attempted

        # Check if the cookie is in the jar (mocking actual cookie extraction logic)
        self.assertIn("test_name", self.cookie_session)

    def test_make_cookies(self):
        # Prepare headers for testing
        headers = {
            "Set-Cookie": "name=value; Expires=Wed, 21 Oct 2015 07:28:00 GMT",
            "Set-Cookie2": "name2=value2; Version=1",
        }

        # Test the method
        cookies = self.cookie_session.make_cookies(Mock(), headers)
        self.assertIsInstance(cookies, list)  # Ensure a list of cookies is returned
        # Additional checks can be added based on expected cookie attributes
        self.assertEqual(len(cookies), 2)

    def test_from_json_and_to_json(self):
        # Prepare sample JSON data representing a cookie
        json_data = [{"name": "test_name", "value": "test_value"}]

        # Test from_json
        self.cookie_session.from_json(json_data)
        self.assertEqual(self.cookie_session["test_name"], "test_value")

        # Test to_json
        json_output = self.cookie_session.to_json()
        self.assertEqual(json_output, json_data)

    def test_get_item(self):
        # Add a cookie to the session
        self.cookie_session.set("key", "value")
        self.assertEqual(self.cookie_session["key"], "value")

    def test_to_dict(self):
        # Add cookies to the session
        self.cookie_session.set("key1", "value1")
        self.cookie_session.set("key2", "value2")
        dict_output = self.cookie_session.to_dict()
        self.assertEqual(dict_output, {"key1": "value1", "key2": "value2"})

    # Additional tests can be written for other methods like get_cookie_header, etc.


if __name__ == "__main__":
    unittest.main()
