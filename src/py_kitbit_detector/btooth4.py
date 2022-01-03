# Temporary file to test bluetooth detection


import datetime
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
        print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
        for (adtype, desc, value) in dev.getScanData():
            print("  %s = %s" % (desc, value))



if __name__ == '__main__':
    print_devices()