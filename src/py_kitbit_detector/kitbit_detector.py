import datetime
import time
from typing import *

import requests
import traceback

from bluepy.btle import Scanner, DefaultDelegate


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


class KitbitConfig:
    def __init__(self):
        self.api_url = r"http://tesla:5058/kitbit/api"

        self.cat_service_datas = {
            '01a20071376e6677637178': 'Juan'
        }



class KitbitDetector:

    def __init__(self):
        self.scanner = Scanner().withDelegate(ScanDelegate())
        self.config = KitbitConfig()


    def call_api(self, method: str, params: Dict):
        requests.post(self.config.api_url,
                      json={
                          'method': method,
                          'params': params
                      })

    def main_loop(self):
        while True:
            try:
                self.scan()
            except Exception as ex:
                self.call_api('error', {
                    'tb': traceback.format_exc(),
                    'ex': str(ex)
                })
            time.sleep(15)



    def scan(self):
        devices = self.scanner.scan(2.0)
        for dev in devices:
            for (adtype, desc, value) in dev.getScanData():
                if desc == "16b Service Data":
                    try:
                        cat = self.config.cat_service_datas[value]
                    except KeyError:
                        continue
                    self.call_api('observation', {
                        'cat': cat,
                        'rssi': dev.rssi
                    })
                    print(f"Saw {cat} with at rssi={dev.rssi} dB")

if __name__ == '__main__':
    KitbitDetector().main_loop()