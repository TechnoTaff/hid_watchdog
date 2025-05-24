# -*- coding: utf-8 -*-
"""Main module."""

from ctypes import create_string_buffer
import logging
import hid
import binascii


class WatchDog:
    def __init__(self, wd_product_id=22352, wd_vendor_id=1155, timeout=160):
        if timeout % 10 != 0:
            raise Exception("Timeout values must be divisible by 10")
        #  device expects 64 byte payload with 1st byte as timeout
        self.bytebits = create_string_buffer(64)
        self.bytebits[0] = int((timeout / 10) + 12)
        try:
            hid_dev = next(
                hid_dev
                for hid_dev in hid.enumerate()
                if (
                    hid_dev["product_id"] == wd_product_id
                    and hid_dev["vendor_id"] == wd_vendor_id
                )
            )
        except StopIteration:
            logging.error(
                "Could not locate ST Microelectronics Watchdog USBHID Device"
            )
            self.watchdog_device = None
            return
        if hid_dev:
            self.watchdog_device = hid.Device(path=hid_dev["path"])
            # Explicitly using variable names as per instruction example
            prod = self.watchdog_device.product
            sn = hid_dev["serial_number"]
            p_val = str(hid_dev["path"])  # Using 'p_val'
            logging.info(f"Found {prod} ({sn}) at {p_val}")
            self.watchdog_device.write(self.bytebits)
            logging.info(f"Watchdog set to {timeout} seconds.")

    def sendStatus(self):
        if not self.watchdog_device:
            logging.warning("WD not initialized. Cannot send status.")
            return
        logging.debug("Sending 'Alive' pkt to Watchdog timer")  # W291 fix
        self.watchdog_device.write(self.bytebits)
        logging.debug("Reading Status Packet from Watchdog")
        outbuff = self.watchdog_device.read(2, timeout=2000)
        if len(outbuff) == 0:
            logging.error("Could not read from Watchdog")
        else:
            # Shortening for line 42/44 area
            response_hex = binascii.hexlify(bytearray(outbuff))
            logging.debug(f"Watchdog response: {response_hex}")

    def close(self):
        if not self.watchdog_device:
            logging.debug("Watchdog device not available. Nothing to close.")
            return
        logging.warning("Closing Watchdog device")
        self.watchdog_device.close()
