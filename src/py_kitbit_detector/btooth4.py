# Temporary file to test bluetooth detection


import datetime
import time

from bluepy.btle import Scanner, DefaultDelegate
from time import sleep


class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            pass
            # print("Discovered device", dev.addr)
        elif isNewData:
            pass
            # print("Received new data from", dev.addr)


def print_devices():
    scanner = Scanner().withDelegate(ScanDelegate())
    devices = scanner.scan(2.0)

    for dev in devices:
        print_device(dev)

def print_device(dev):
    print("Device %s (%s)       RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
    for (adtype, desc, value) in dev.getScanData():
        print("  %s = %s" % (desc, value))


def scan_for_kitbit():
    scanner = Scanner().withDelegate(ScanDelegate())
    while True:
        print('-'*80)
        print(datetime.datetime.now())
        devices = scanner.scan(2.0)
        for dev in devices:
            for (adtype, desc, value) in dev.getScanData():
                if desc == "Complete Local Name" and value == "TY":
                    print_device(dev)
        time.sleep(60)


if __name__ == '__main__':
    scan_for_kitbit()