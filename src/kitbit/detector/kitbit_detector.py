import os.path
import time
from typing import *
from uuid import uuid4

import requests
import traceback

from bluepy.btle import Scanner, DefaultDelegate

from kitbit.protocol import *

API_URL = r"http://tesla:5058/kitbit/api"


class KitbitDetector:

    def __init__(self):
        self.scanner = Scanner().withDelegate(ScanDelegate())
        self.config: ConfigMessage

        # Read in the detector uuid, creating a new one if needed
        detector_uuid_fp = 'detector_uuid.txt'
        if not os.path.isfile(detector_uuid_fp):
            with open(detector_uuid_fp, 'w') as fh:
                fh.write('DETECTOR_' + str(uuid4()))
        self.detector_uuid = open(detector_uuid_fp).read().strip()

        self.config = ConfigMessage.from_dict(self.call_api('get_config', {}))


    def call_api(self, method: str, message: Dict):
        response = requests.post(API_URL,
                      json={
                          'method': method,
                          'params': message
                      })
        return response.json()

    def main_loop(self):
        while True:
            try:
                self.scan()
            except Exception as ex:
                self.call_api('error', {
                    'detector_uuid': self.detector_uuid,
                    'error': ErrorMessage.from_last_exception().to_dict()
                })
            time.sleep(15)



    def scan(self):
        devices = self.scanner.scan(2.0)

        result = ScanObservationMessage(
            detector_uuid=self.detector_uuid,
            cat_rssi={}
        )
        for dev in devices:
            for (adtype, desc, value) in dev.getScanData():
                if desc == "16b Service Data":
                    try:
                        cat = self.config.cat_identifiers[value]
                    except KeyError:
                        continue
                    result.cat_rssi[cat] = dev.rssi
                    print(f"Saw {cat} with at rssi={dev.rssi} dB")
        self.call_api('observation', result.to_dict())



class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            pass # print("Discovered device", dev.addr)
        elif isNewData:
            pass # print("Received new data from", dev.addr)


if __name__ == '__main__':
    KitbitDetector().main_loop()