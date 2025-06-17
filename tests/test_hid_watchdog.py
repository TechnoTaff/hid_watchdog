import unittest
from unittest.mock import patch, MagicMock, call, mock_open
import logging
import sys
import os
import binascii

# Add the parent directory to sys.path to allow imports from hid_watchdog module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hid_watchdog import WatchDog
from hid_watchdog import cli

# Keep logging disabled for most tests, enable for specific logging tests if necessary
# logging.disable(logging.CRITICAL)

class TestWatchDogClass(unittest.TestCase):

    def setUp(self):
        # Reset logging level for each test to capture logs
        logging.disable(logging.NOTSET)
        # Create a logger instance to capture log messages
        self.logger = logging.getLogger('hid_watchdog.hid_watchdog') # Target the logger used in WatchDog
        self.log_capture = []

        # Custom handler to capture log records
        class ListHandler(logging.Handler):
            def __init__(self, log_list):
                super().__init__()
                self.log_list = log_list
            def emit(self, record):
                self.log_list.append(self.format(record))
        
        self.list_handler = ListHandler(self.log_capture)
        # Use a basic formatter, or match the application's formatter if important
        formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s') 
        self.list_handler.setFormatter(formatter)
        self.logger.addHandler(self.list_handler)
        self.logger.setLevel(logging.DEBUG) # Capture all levels from DEBUG upwards

    def tearDown(self):
        # Clean up the handler and disable logging again if needed
        self.logger.removeHandler(self.list_handler)
        # logging.disable(logging.CRITICAL) # Or whatever default state you want
        self.log_capture = []


    @patch('hid_watchdog.hid_watchdog.hid')
    def test_init_successful(self, mock_hid_module):
        mock_device_instance = MagicMock()
        mock_device_instance.product = "TestProduct"
        mock_device_instance.write = MagicMock()
        mock_device_instance.read = MagicMock()
        mock_device_instance.close = MagicMock()

        mock_hid_module.enumerate.return_value = [{
            'product_id': 1234,
            'vendor_id': 5678,
            'path': b'some_path',
            'serial_number': 'SN123'
        }]
        mock_hid_module.Device.return_value = mock_device_instance

        wd = WatchDog(wd_product_id=1234, wd_vendor_id=5678, timeout=160)

        self.assertIsNotNone(wd.watchdog_device)
        mock_hid_module.enumerate.assert_called_once()
        mock_hid_module.Device.assert_called_once_with(path=b'some_path')
        
        expected_payload = bytearray(64)
        expected_payload[0] = int((160 / 10) + 12)
        mock_device_instance.write.assert_called_once_with(bytes(expected_payload))
        
        # Check log messages
        # Need to enable logging capture for this
        self.assertIn(f'INFO:hid_watchdog.hid_watchdog:Found TestProduct (SN123) at {str(b"some_path")}', self.log_capture)
        self.assertIn('INFO:hid_watchdog.hid_watchdog:Watchdog set to 160 seconds.', self.log_capture)


    @patch('hid_watchdog.hid_watchdog.hid')
    def test_init_device_not_found(self, mock_hid_module):
        mock_hid_module.enumerate.return_value = [] # No devices found

        wd = WatchDog(wd_product_id=1234, wd_vendor_id=5678)

        self.assertIsNone(wd.watchdog_device)
        mock_hid_module.enumerate.assert_called_once()
        mock_hid_module.Device.assert_not_called()
        self.assertIn('ERROR:hid_watchdog.hid_watchdog:Could not locate ST Microelectronics Watchdog USBHID Device', self.log_capture)

    def test_init_invalid_timeout(self):
        with self.assertRaises(Exception) as context:
            WatchDog(timeout=165)
        self.assertTrue('Timeout values must be divisible by 10' in str(context.exception))

    @patch('hid_watchdog.hid_watchdog.hid.Device') # Mock Device directly for sendStatus
    def test_sendStatus_device_none(self, mock_hid_device_class):
        # First, initialize WatchDog so that self.watchdog_device is None
        with patch('hid_watchdog.hid_watchdog.hid.enumerate', return_value=[]):
            wd = WatchDog()
        
        self.assertIsNone(wd.watchdog_device) # Ensure device is None
        wd.sendStatus() # Call sendStatus

        # Verify warning log
        self.assertIn("WARNING:hid_watchdog.hid_watchdog:Watchdog device not available. Cannot send status.", self.log_capture)


    @patch('hid_watchdog.hid_watchdog.hid.enumerate')
    @patch('hid_watchdog.hid_watchdog.hid.Device')
    def test_sendStatus_successful(self, mock_device_constructor, mock_enumerate):
        mock_device_instance = MagicMock()
        mock_device_instance.write = MagicMock()
        mock_device_instance.read = MagicMock(return_value=b'\x01\x02') # Sample 2-byte buffer

        mock_enumerate.return_value = [{'product_id': 1, 'vendor_id': 1, 'path': b'path'}]
        mock_device_constructor.return_value = mock_device_instance
        
        wd = WatchDog(wd_product_id=1, wd_vendor_id=1, timeout=10)
        wd.sendStatus()

        mock_device_instance.write.assert_called_with(wd.bytebits) # called once in init, once in sendStatus
        self.assertEqual(mock_device_instance.write.call_count, 2)
        mock_device_instance.read.assert_called_once_with(2, timeout=2000)
        
        expected_hex = binascii.hexlify(b'\x01\x02').decode()
        self.assertIn(f"DEBUG:hid_watchdog.hid_watchdog:Watchdog response: {expected_hex}", self.log_capture)

    @patch('hid_watchdog.hid_watchdog.hid.enumerate')
    @patch('hid_watchdog.hid_watchdog.hid.Device')
    def test_sendStatus_read_failure(self, mock_device_constructor, mock_enumerate):
        mock_device_instance = MagicMock()
        mock_device_instance.write = MagicMock()
        mock_device_instance.read = MagicMock(return_value=b'') # Empty buffer

        mock_enumerate.return_value = [{'product_id': 1, 'vendor_id': 1, 'path': b'path'}]
        mock_device_constructor.return_value = mock_device_instance

        wd = WatchDog(wd_product_id=1, wd_vendor_id=1, timeout=10)
        wd.sendStatus()

        mock_device_instance.write.assert_called_with(wd.bytebits)
        mock_device_instance.read.assert_called_once_with(2, timeout=2000)
        self.assertIn("ERROR:hid_watchdog.hid_watchdog:Could not read from Watchdog", self.log_capture)


    def test_close_device_none(self):
        with patch('hid_watchdog.hid_watchdog.hid.enumerate', return_value=[]):
            wd = WatchDog()
        
        self.assertIsNone(wd.watchdog_device)
        wd.close()
        self.assertIn("DEBUG:hid_watchdog.hid_watchdog:Watchdog device not available. Nothing to close.", self.log_capture)


    @patch('hid_watchdog.hid_watchdog.hid.enumerate')
    @patch('hid_watchdog.hid_watchdog.hid.Device')
    def test_close_successful(self, mock_device_constructor, mock_enumerate):
        mock_device_instance = MagicMock()
        mock_device_instance.close = MagicMock()

        mock_enumerate.return_value = [{'product_id': 1, 'vendor_id': 1, 'path': b'path'}]
        mock_device_constructor.return_value = mock_device_instance

        wd = WatchDog(wd_product_id=1, wd_vendor_id=1, timeout=10)
        wd.close()

        mock_device_instance.close.assert_called_once()
        self.assertIn("WARNING:hid_watchdog.hid_watchdog:Closing Watchdog device", self.log_capture)


class TestCli(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger('hid_watchdog') # Target the CLI logger
        self.log_capture = []
        
        class ListHandler(logging.Handler):
            def __init__(self, log_list):
                super().__init__()
                self.log_list = log_list
            def emit(self, record):
                self.log_list.append(self.format(record))
        
        self.list_handler = ListHandler(self.log_capture)
        formatter = logging.Formatter('%(asctime)-15s %(filename)s %(message)s') # Match CLI format
        self.list_handler.setFormatter(formatter)
        self.logger.addHandler(self.list_handler)
        self.logger.setLevel(logging.DEBUG) # Capture all levels

        # Patch sys.exit to prevent tests from exiting
        self.patch_sys_exit = patch('sys.exit')
        self.mock_sys_exit = self.patch_sys_exit.start()

    def tearDown(self):
        self.logger.removeHandler(self.list_handler)
        self.patch_sys_exit.stop()
        self.log_capture = []


    @patch('hid_watchdog.cli.WatchDog')
    @patch('hid_watchdog.cli.sleep')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_default_args(self, mock_parse_args, mock_sleep, mock_watchdog_class):
        # Mock WatchDog instance and its watchdog_device attribute
        mock_wd_instance = MagicMock()
        mock_wd_instance.watchdog_device = True # Simulate device found
        mock_wd_instance.sendStatus = MagicMock()
        mock_watchdog_class.return_value = mock_wd_instance

        # Mock parsed arguments
        mock_args = MagicMock()
        mock_args.pid = 22352
        mock_args.vid = 1155
        mock_args.timeout = 160
        mock_args.frequency = 9
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        # Mock sleep to break the loop after a few iterations
        mock_sleep.side_effect = [None, None, KeyboardInterrupt] # Raise exception to stop infinite loop

        with self.assertRaises(KeyboardInterrupt): # Expect loop to be broken by mock_sleep
             cli.main(mock_args)

        mock_watchdog_class.assert_called_once_with(wd_product_id=22352, wd_vendor_id=1155, timeout=160)
        self.assertTrue(mock_wd_instance.sendStatus.call_count > 0) # Check if called at least once
        mock_sleep.assert_any_call(9)


    @patch('hid_watchdog.cli.WatchDog')
    @patch('hid_watchdog.cli.sleep')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_custom_args_debug(self, mock_parse_args, mock_sleep, mock_watchdog_class):
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

        # Check logging level configuration
        # We need to get the logger instance that cli.main configures
        cli_logger = logging.getLogger('hid_watchdog') # This is the parent logger name used in cli.py

        with self.assertRaises(KeyboardInterrupt):
            cli.main(mock_args)

        mock_watchdog_class.assert_called_once_with(wd_product_id=1111, wd_vendor_id=2222, timeout=60)
        mock_sleep.assert_called_once_with(5)
        
        # Verify logging level was set to DEBUG
        self.assertEqual(cli_logger.getEffectiveLevel(), logging.DEBUG)
        # And that basicConfig was called (indirectly check via a log message if possible, or by checking handlers)
        # This part is a bit tricky as basicConfig is global.
        # We can check if our handler is still there and if a debug message was logged.
        # For example, if WatchDog logged something at DEBUG level and it was captured.
        # Or check the log_capture for the format.
        # For simplicity, we assume if level is DEBUG, basicConfig was likely called with it.

    @patch('hid_watchdog.cli.WatchDog')
    @patch('hid_watchdog.cli.sleep') # Still need to mock sleep
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_device_init_failure(self, mock_parse_args, mock_sleep, mock_watchdog_class):
        mock_wd_instance = MagicMock()
        mock_wd_instance.watchdog_device = None # Simulate device NOT found
        mock_watchdog_class.return_value = mock_wd_instance

        mock_args = MagicMock()
        mock_args.pid = 123
        mock_args.vid = 456
        mock_args.timeout = 100
        mock_args.frequency = 10
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        cli.main(mock_args) # Should not loop, should exit

        mock_watchdog_class.assert_called_once_with(wd_product_id=123, wd_vendor_id=456, timeout=100)
        self.mock_sys_exit.assert_called_once_with(1)
        
        # Check for critical log message
        # Note: The logger in cli.py is 'hid_watchdog', not 'hid_watchdog.cli'
        # We need to adjust self.logger in setUp for TestCli or add another handler for 'hid_watchdog'
        # For now, let's assume the existing log capture might catch it if propagation is on.
        # A more robust way is to specifically target the 'hid_watchdog' logger.
        
        # Re-checking the logging setup for TestCli:
        # self.logger = logging.getLogger('hid_watchdog') # Correctly targets the parent logger
        
        # Check if the critical message was logged
        found_critical_log = False
        for record_str in self.log_capture:
            if "CRITICAL" in record_str and "Watchdog device not found. Exiting." in record_str:
                found_critical_log = True
                break
        self.assertTrue(found_critical_log, "Critical log for device not found was not captured.")

    @patch('hid_watchdog.cli.WatchDog') # Mock WatchDog
    @patch('hid_watchdog.cli.sys') # Mock sys to check sys.exit
    def test_get_shutdown_handler(self, mock_sys, mock_watchdog_class):
        mock_wd_instance = MagicMock()
        mock_wd_instance.close = MagicMock()
        
        # Get the handler function
        handler = cli.get_shutdown_handler("Test shutdown", mock_wd_instance)
        
        # Call the handler as if a signal was received
        handler(None, None) # signum and frame are not used by this handler
        
        mock_wd_instance.close.assert_called_once()
        # print is harder to mock if not injected. If it were logging, it'd be easier.
        # For now, we assume if close is called, the handler works.
        # To test print, you might patch 'builtins.print'
        mock_sys.exit.assert_called_once_with(0)


if __name__ == '__main__':
    # Disable all logging for tests run via __main__, except when testing logging itself.
    # Individual test methods or setUp can re-enable or capture logs.
    logging.disable(logging.CRITICAL) 
    unittest.main()
