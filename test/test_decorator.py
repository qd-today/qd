import logging
import unittest
from unittest.mock import MagicMock

from qd_core.config import get_settings
from qd_core.utils.decorator import log_and_raise_error


class TestLogAndRaiseError(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.logger = MagicMock(spec=logging.Logger)
        self.error_message_format = "An error occurred: %s"
        self.normal_function_result = "Normal Function Result"

    def test_decorator_with_exception_raised(self):
        @log_and_raise_error(self.logger, self.error_message_format, raise_exception=True)
        def function_that_raises():
            raise ValueError("Test Exception")

        with self.assertRaises(ValueError):
            function_that_raises()

        self.logger.log.assert_called_once_with(
            logging.ERROR, self.error_message_format, "Test Exception", exc_info=get_settings().log.traceback_print
        )

    def test_decorator_without_exception_raised(self):
        @log_and_raise_error(self.logger, self.error_message_format, raise_exception=False)
        def function_that_raises():
            raise ValueError("Test Exception")

        result = function_that_raises()

        self.assertIsNone(result)
        self.logger.log.assert_called_once_with(
            logging.ERROR, self.error_message_format, "Test Exception", exc_info=get_settings().log.traceback_print
        )

    async def test_async_decorator_with_exception_raised(self):
        @log_and_raise_error(self.logger, self.error_message_format, raise_exception=True)
        async def async_function_that_raises():
            raise ValueError("Test Exception")

        with self.assertRaises(ValueError):
            await async_function_that_raises()

        self.logger.log.assert_called_once_with(
            logging.ERROR, self.error_message_format, "Test Exception", exc_info=get_settings().log.traceback_print
        )

    async def test_async_decorator_without_exception_raised(self):
        @log_and_raise_error(self.logger, self.error_message_format, raise_exception=False)
        async def async_function_that_raises():
            raise ValueError("Test Exception")

        result = await async_function_that_raises()

        self.assertIsNone(result)
        self.logger.log.assert_called_once_with(
            logging.ERROR, self.error_message_format, "Test Exception", exc_info=get_settings().log.traceback_print
        )

    def test_decorator_without_exception(self):
        @log_and_raise_error(self.logger, self.error_message_format, raise_exception=True)
        def normal_function():
            return self.normal_function_result

        result = normal_function()

        self.assertEqual(result, self.normal_function_result)
        self.logger.log.assert_not_called()

    async def test_async_decorator_without_exception(self):
        @log_and_raise_error(self.logger, self.error_message_format, raise_exception=True)
        async def async_normal_function():
            return self.normal_function_result

        result = await async_normal_function()

        self.assertEqual(result, self.normal_function_result)
        self.logger.log.assert_not_called()


if __name__ == "__main__":
    unittest.main()
