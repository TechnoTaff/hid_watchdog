# -*- coding: utf-8 -*-
"""Console script for hid_watchdog."""

__author__ = "Steve Randall"
__version__ = "0.1.0"
__license__ = "GPLv3"

import argparse
import logging
from hid_watchdog import WatchDog
from signal import signal, SIGINT, SIGTERM
from time import sleep
import sys


def get_shutdown_handler(message=None, watchdog_device=None):
    """
    Build a shutdown handler, called from the signal methods
    """
    def handler(signum, frame):
        # If we want to do anything on shutdown, such as stop motors on a robot,
        # you can add it here.
        watchdog_device.close()
        print(message)
        exit(0)
    return handler

def main(args):
    """ Main entry point of the app """
    logger = logging.getLogger('hid_watchdog')
    FORMAT = '%(asctime)-15s %(filename)s %(message)s'
    if args.debug:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO
    logger.setLevel(loglevel)
    logging.basicConfig(format=FORMAT,level=loglevel)
    wdstick = WatchDog(wd_product_id=args.pid,
                       wd_vendor_id=args.vid,
                       timeout=args.timeout)
    signal(SIGINT, get_shutdown_handler('SIGINT received',wdstick))
    signal(SIGTERM, get_shutdown_handler('SIGTERM received',wdstick))
    if wdstick.watchdog_device:
        while True:
            wdstick.sendStatus()
            sleep(args.frequency)


if __name__ == "__main__":
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser()

    # Optional argument which requires a parameter (eg. -d test)
    parser.add_argument("-p",
                        "--pid",
                        type=int,
                        action="store",
                        dest="pid",
                        default=22352,
                        help='product_id (default: 22352)')
    parser.add_argument("-v",
                        "--vid",
                        type=int,
                        action="store",
                        dest="vid",
                        default=1155,
                        help='vendor_id (default: 1155)')
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        action="store",
        dest="timeout",
        default=160,
        help="Timeout Value before reboot is forced (Default 160 seconds)")

    parser.add_argument(
        "-f",
        "--frequency",
        type=int,
        action="store",
        dest="frequency",
        default=9,
        help="Frequency to update Watchdog timer"
    )

    # Specify output of "--version"
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (version {version})".format(version=__version__))

    parser.add_argument(
        '--debug',
        action='store_true', 
        help='print debug messages to stderr'
    )


    args = parser.parse_args()
    main(args)

