# hid-watchdog

This is a simple service to communicate with cheap USB WatchDog timers that create a USB-HID device:

![USB HID "v5" Watchdog Timer](docs/usb-hid-watchdog-v5.jpg)

## Install

### Installation on Ubuntu

Create your VirtualEnv, activate it.

```
$ pip install -r requirements.txt 
```
This will install the `hidapi` Python package and any other necessary dependencies listed in `requirements.txt`.

You will still need to install the underlying C library on your operating system for `hidapi` to interface with the USB-HID device:

```
apt install libhidapi-hidraw0
```

Alternatively you may be able to use "libhidapi-libusb0" but I didn't have any success with this.

### Installation on CentOS

Same as for Ubuntu, except for last step

```
yum install hidapi
```
