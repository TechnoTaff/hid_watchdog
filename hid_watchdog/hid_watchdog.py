# -*- coding: utf-8 -*-
"""Main module."""

from ctypes import create_string_buffer
import logging
import hid

class WatchDog:
    def __init__(self, wd_product_id=22352, wd_vendor_id=1155, timeout=160):
        if timeout % 10 != 0:
            raise Exception('Timeout values must be divisible by 10')
        # device expects 64 byte payload with 1st byte as timeout
        self.bytebits = create_string_buffer(64)
        self.bytebits[0] = int((timeout / 10) + 12)
        try:
            hid_dev = next(hid_dev for hid_dev in hid.enumerate()
                           if (hid_dev['product_id'] == wd_product_id
                               and hid_dev['vendor_id'] == wd_vendor_id))
        except StopIteration:
            logging.error(
                'Could not locate ST Microelectronics Watchdog USBHID Device')
            self.watchdog_device = None
            return
        if hid_dev:
            self.watchdog_device = hid.Device(path=hid_dev['path'])
            logging.info(f'Found {self.watchdog_device.product} ({str(hid_dev["serial_number"])}) at {str(hid_dev["path"])}')
            self.watchdog_device.write(self.bytebits)
            logging.info(f'Watchdog set to {timeout} seconds.')

    def sendStatus(self):
        logging.debug('Sending \'Server Alive\' Packet to Watchdog timer')
        self.watchdog_device.write(self.bytebits)
        logging.debug('Reading Status Packet from Watchdog')
        outbuff = self.watchdog_device.read(2, timeout=2000)
        if len(outbuff) == 0:
            print('Could not read from Watchdog')
        #print(binascii.hexlify(bytearray(self.watchdog_device.read(2,timeout=2000))))

    def close(self):
        logging.warning('Closing Watchdog device')
        self.watchdog_device.close()
