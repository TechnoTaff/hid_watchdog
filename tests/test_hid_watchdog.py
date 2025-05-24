# -*- coding: utf-8 -*-
"""Unit tests for hid_watchdog."""

# Standard library imports for path manipulation first
import os
import sys

# Path manipulation code to allow local imports
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.join(_CURRENT_DIR, "..")
sys.path.insert(0, _PARENT_DIR)

# Other standard library imports
import unittest
from unittest.mock import patch, MagicMock, call 
import logging
import binascii

# Local application/library specific imports
from hid_watchdog import WatchDog
from hid_watchdog import cli

# Keep logging disabled for most tests unless specifically testing logging output
# logging.disable(logging.CRITICAL)


class TestWatchDogClass(unittest.TestCase):
    """Test cases for the WatchDog class."""

    def setUp(self):
        """Set up test fixtures, including log capture."""
        logging.disable(logging.NOTSET)  # Enable logging for capture
        self.logger = logging.getLogger("hid_watchdog.hid_watchdog")
        self.log_capture = []

        class ListHandler(logging.Handler):
            def __init__(self, log_list_capture):
                super().__init__()
                self.log_list_capture = log_list_capture

            def emit(self, record):
                self.log_list_capture.append(self.format(record))

        self.list_handler = ListHandler(self.log_capture)
        formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
        self.list_handler.setFormatter(formatter)
        self.logger.addHandler(self.list_handler)
        self.logger.setLevel(logging.DEBUG)

    def tearDown(self):
        """Tear down test fixtures."""
        self.logger.removeHandler(self.list_handler)
        # logging.disable(logging.CRITICAL)

    @patch("hid_watchdog.hid_watchdog.hid")
    def test_init_successful(self, mock_hid_module):
        """Test WatchDog successful initialization."""
        mock_device_instance = MagicMock()
        mock_device_instance.product = "TestProduct"
        mock_device_instance.write = MagicMock()
        mock_device_instance.read = MagicMock()
        mock_device_instance.close = MagicMock()

        mock_hid_module.enumerate.return_value = [
            {
                "product_id": 1234,
                "vendor_id": 5678,
                "path": b"some_path",
                "serial_number": "SN123",
            }
        ]
        mock_hid_module.Device.return_value = mock_device_instance

        wd = WatchDog(wd_product_id=1234, wd_vendor_id=5678, timeout=160)

        self.assertIsNotNone(wd.watchdog_device)
        mock_hid_module.enumerate.assert_called_once()
        mock_hid_module.Device.assert_called_once_with(path=b"some_path")

        expected_payload = bytearray(64)
        expected_payload[0] = int((160 / 10) + 12)
        mock_device_instance.write.assert_called_once_with(
            bytes(expected_payload)
        )

        # E501: Wrapped log_msg1 (line 79/80 from previous report)
        log_msg1 = (
            "INFO:hid_watchdog.hid_watchdog:Found TestProduct (SN123) at "
            f"{str(b'some_path')}"
        )
        self.assertIn(log_msg1, self.log_capture)
        log_msg_set = (
            "INFO:hid_watchdog.hid_watchdog:Watchdog set to 160 seconds."
        )
        self.assertIn(log_msg_set, self.log_capture)

    @patch("hid_watchdog.hid_watchdog.hid")
    def test_init_device_not_found(self, mock_hid_module):
        """Test WatchDog initialization when device is not found."""
        mock_hid_module.enumerate.return_value = []  # No devices found

        wd = WatchDog(wd_product_id=1234, wd_vendor_id=5678)

        self.assertIsNone(wd.watchdog_device)
        mock_hid_module.enumerate.assert_called_once()
        mock_hid_module.Device.assert_not_called()
        # E501: Wrapped err_log (line 87/88 from previous report)
        err_log = (
            "ERROR:hid_watchdog.hid_watchdog:Could not locate ST "
            "Microelectronics Watchdog USBHID Device"
        )
        self.assertIn(err_log, self.log_capture)

    def test_init_invalid_timeout(self):
        """Test WatchDog initialization with invalid timeout."""
        with self.assertRaises(Exception) as context:
            WatchDog(timeout=165)
        self.assertTrue(
            "Timeout values must be divisible by 10" in str(context.exception)
        )

    @patch("hid_watchdog.hid_watchdog.hid.Device")
    def test_sendStatus_device_none(self, mock_hid_device_class):
        """Test sendStatus when WatchDog device is not initialized."""
        with patch("hid_watchdog.hid_watchdog.hid.enumerate", return_value=[]):
            wd = WatchDog()

        self.assertIsNone(wd.watchdog_device)
        wd.sendStatus()

        # E501: Wrapped warn_log (line 151/153 from report)
        warn_log = (
            "WARNING:hid_watchdog.hid_watchdog:Watchdog device not "
            "available. Cannot send status."
        )
        self.assertIn(warn_log, self.log_capture)

    @patch("hid_watchdog.hid_watchdog.hid.enumerate")
    @patch("hid_watchdog.hid_watchdog.hid.Device")
    def test_sendStatus_successful(
        self, mock_device_constructor, mock_enumerate
    ):
        """Test successful sendStatus call."""
        mock_device_instance = MagicMock()
        mock_device_instance.write = MagicMock()
        mock_device_instance.read = MagicMock(return_value=b"\x01\x02")

        mock_enumerate.return_value = [
            {"product_id": 1, "vendor_id": 1, "path": b"path"}
        ]
        mock_device_constructor.return_value = mock_device_instance

        wd = WatchDog(wd_product_id=1, wd_vendor_id=1, timeout=10)
        wd.sendStatus()

        mock_device_instance.write.assert_called_with(wd.bytebits)
        self.assertEqual(mock_device_instance.write.call_count, 2)
        mock_device_instance.read.assert_called_once_with(2, timeout=2000)

        expected_hex = binascii.hexlify(b"\x01\x02").decode()
        # E261 fix: Ensure comment (if any) is well spaced or remove.
        # E501: Wrapped debug_log (line 100 E261, line 130/131 E501 from report)
        debug_log = (  # Corrected spacing for potential E261
            f"DEBUG:hid_watchdog.hid_watchdog:Watchdog response: {expected_hex}"
        )
        self.assertIn(debug_log, self.log_capture)

    @patch("hid_watchdog.hid_watchdog.hid.enumerate")
    @patch("hid_watchdog.hid_watchdog.hid.Device")
    def test_sendStatus_read_failure(
        self, mock_device_constructor, mock_enumerate
    ):
        """Test sendStatus with a read failure."""
        mock_device_instance = MagicMock()
        mock_device_instance.write = MagicMock()
        mock_device_instance.read = MagicMock(return_value=b"")

        mock_enumerate.return_value = [
            {"product_id": 1, "vendor_id": 1, "path": b"path"}
        ]
        mock_device_constructor.return_value = mock_device_instance

        wd = WatchDog(wd_product_id=1, wd_vendor_id=1, timeout=10)
        wd.sendStatus()

        mock_device_instance.write.assert_called_with(wd.bytebits)
        mock_device_instance.read.assert_called_once_with(2, timeout=2000)
        self.assertIn(
            "ERROR:hid_watchdog.hid_watchdog:Could not read from Watchdog",
            self.log_capture,
        )

    def test_close_device_none(self):
        """Test close when WatchDog device is not initialized."""
        with patch("hid_watchdog.hid_watchdog.hid.enumerate", return_value=[]):
            wd = WatchDog()

        self.assertIsNone(wd.watchdog_device)
        wd.close()
        # E501: Wrapped debug_log (line 157/159 from report)
        debug_log = (
            "DEBUG:hid_watchdog.hid_watchdog:Watchdog device not "
            "available. Nothing to close."
        )
        self.assertIn(debug_log, self.log_capture)

    @patch("hid_watchdog.hid_watchdog.hid.enumerate")
    @patch("hid_watchdog.hid_watchdog.hid.Device")
    def test_close_successful(self, mock_device_constructor, mock_enumerate):
        """Test successful close call."""
        mock_device_instance = MagicMock()
        mock_device_instance.close = MagicMock()

        mock_enumerate.return_value = [
            {"product_id": 1, "vendor_id": 1, "path": b"path"}
        ]
        mock_device_constructor.return_value = mock_device_instance

        wd = WatchDog(wd_product_id=1, wd_vendor_id=1, timeout=10)
        wd.close()

        mock_device_instance.close.assert_called_once()
        self.assertIn(
            "WARNING:hid_watchdog.hid_watchdog:Closing Watchdog device",
            self.log_capture,
        )


class TestCli(unittest.TestCase):
    """Test cases for the CLI functionality."""

    def setUp(self):
        """Set up test fixtures for CLI tests."""
        self.logger = logging.getLogger("hid_watchdog")
        self.log_capture = []

        class ListHandler(logging.Handler):
            def __init__(self, log_list_capture):
                super().__init__()
                self.log_list_capture = log_list_capture

            def emit(self, record):
                self.log_list_capture.append(self.format(record))

        self.list_handler = ListHandler(self.log_capture)
        formatter = logging.Formatter(
            "%(asctime)-15s %(filename)s %(message)s"
        )
        self.list_handler.setFormatter(formatter)
        self.logger.addHandler(self.list_handler)
        self.logger.setLevel(logging.DEBUG)

        self.patch_sys_exit = patch("sys.exit")
        self.mock_sys_exit = self.patch_sys_exit.start()

    def tearDown(self):
        """Tear down test fixtures for CLI tests."""
        self.logger.removeHandler(self.list_handler)
        self.patch_sys_exit.stop()
        self.log_capture = []

    @patch("hid_watchdog.cli.WatchDog")
    @patch("hid_watchdog.cli.sleep")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_default_args(
        self, mock_parse_args, mock_sleep, mock_watchdog_class
    ):
        """Test CLI main function with default arguments."""
        mock_wd_instance = MagicMock()
        mock_wd_instance.watchdog_device = True
        mock_wd_instance.sendStatus = MagicMock()
        mock_watchdog_class.return_value = mock_wd_instance

        mock_args = MagicMock()
        mock_args.pid = 22352
        mock_args.vid = 1155
        mock_args.timeout = 160
        mock_args.frequency = 9
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        mock_sleep.side_effect = [None, None, KeyboardInterrupt]

        with self.assertRaises(KeyboardInterrupt):
            cli.main(mock_args)

        # E501: Wrapped arguments (line 222/225 from report)
        mock_watchdog_class.assert_called_once_with(
            wd_product_id=22352,
            wd_vendor_id=1155,
            timeout=160
        )
        self.assertTrue(mock_wd_instance.sendStatus.call_count > 0)
        mock_sleep.assert_any_call(9)

    @patch("hid_watchdog.cli.WatchDog")
    @patch("hid_watchdog.cli.sleep")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_custom_args_debug(
        self, mock_parse_args, mock_sleep, mock_watchdog_class
    ):
        """Test CLI main function with custom arguments and debug flag."""
        mock_wd_instance = MagicMock()
        mock_wd_instance.watchdog_device = True
        mock_wd_instance.sendStatus = MagicMock()
        mock_watchdog_class.return_value = mock_wd_instance

        mock_args = MagicMock()
        mock_args.pid = 1111
        mock_args.vid = 2222
        mock_args.timeout = 60
        mock_args.frequency = 5
        mock_args.debug = True
        mock_parse_args.return_value = mock_args

        mock_sleep.side_effect = [KeyboardInterrupt]

        cli_logger = logging.getLogger("hid_watchdog")

        with self.assertRaises(KeyboardInterrupt):
            cli.main(mock_args)

        # E501: Wrapped arguments (line 239/242 from report)
        mock_watchdog_class.assert_called_once_with(
            wd_product_id=1111,
            wd_vendor_id=2222,
            timeout=60
        )
        mock_sleep.assert_called_once_with(5)
        self.assertEqual(cli_logger.getEffectiveLevel(), logging.DEBUG)

    @patch("hid_watchdog.cli.WatchDog")
    @patch("hid_watchdog.cli.sleep")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_device_init_failure(
        self, mock_parse_args, mock_sleep, mock_watchdog_class
    ):
        """Test CLI main function when WatchDog device initialization fails."""
        mock_wd_instance = MagicMock()
        mock_wd_instance.watchdog_device = None
        mock_watchdog_class.return_value = mock_wd_instance

        mock_args = MagicMock()
        mock_args.pid = 123
        mock_args.vid = 456
        mock_args.timeout = 100
        mock_args.frequency = 10
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        cli.main(mock_args)

        mock_watchdog_class.assert_called_once_with(
            wd_product_id=123, wd_vendor_id=456, timeout=100
        )
        self.mock_sys_exit.assert_called_once_with(1)

        found_critical_log = False
        for record_str in self.log_capture:
            if (
                "CRITICAL" in record_str
                and "Watchdog device not found. Exiting." in record_str
            ):
                found_critical_log = True
                break
        # E501: Wrapped assertion message (line 343 from report)
        msg = "Critical log for device not found was not captured."
        self.assertTrue(found_critical_log, msg)

    @patch("hid_watchdog.cli.WatchDog")
    @patch("hid_watchdog.cli.sys")
    def test_get_shutdown_handler(self, mock_sys, mock_watchdog_class):
        """Test the shutdown handler function."""
        mock_wd_instance = MagicMock()
        mock_wd_instance.close = MagicMock()

        handler = cli.get_shutdown_handler("Test shutdown", mock_wd_instance)
        handler(None, None)

        mock_wd_instance.close.assert_called_once()
        mock_sys.exit.assert_called_once_with(0)


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    unittest.main()
