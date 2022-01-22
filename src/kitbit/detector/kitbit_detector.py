import os.path
import time
from typing import *
from uuid import uuid4

import requests
import traceback

from bluepy.btle import Scanner, DefaultDelegate, BTLEManagementError

from kitbit.protocol import *




class KitbitDetector:

    def __init__(self):
        self.scanner = Scanner().withDelegate(ScanDelegate())
        basedir = os.path.dirname(__file__)

        # Read in last good config if possible
        self.detector_config_fp = os.path.join(basedir, 'detector_config.txt')
        if os.path.isfile(self.detector_config_fp):
            self.config = ConfigMessage.from_json(open(self.detector_config_fp).read())
        else:
            self.config: ConfigMessage = ConfigMessage({})
        self.last_config = datetime.datetime(1970,1,1)

        # Read in the detector uuid, creating a new one if needed
        detector_uuid_fp = os.path.join(basedir, 'detector_uuid.txt')
        if not os.path.isfile(detector_uuid_fp):
            with open(detector_uuid_fp, 'w') as fh:
                fh.write('DETECTOR_' + str(uuid4())[:8])
        self.detector_uuid = open(detector_uuid_fp).read().strip()

    def call_api(self, method: str, message: Dict):
        response = requests.post(self.config.api_uri,
                      json={
                          'method': method,
                          'params': message
                      })
        response_json: Dict = response.json()

        if 'result' in response_json.keys():
            return response_json['result']
        raise RpcServerException(response_json['error']['message'])

    def main_loop(self):

        while True:
            try:
                if datetime.datetime.now() - self.last_config > datetime.timedelta(minutes=5):
                    # Every 5 minutes update the config incase polling frequency or API endpoint change
                    self.config = ConfigMessage.from_dict(
                        self.call_api('get_config', {'detector_uuid': self.detector_uuid}))
                    self.last_config = datetime.datetime.now()

                    # Save updated config
                    with open(self.detector_config_fp, 'w') as fh:
                        fh.write(self.config.to_json())

                # Now that we are sure we have the latest config, do a scan
                self.scan()
            except Exception as ex:
                try:
                    self.call_api('error', {
                        'detector_uuid': self.detector_uuid,
                        'error': ErrorMessage.from_last_exception().to_dict()
                    })
                except Exception as ex2:
                    print(f"*** ERROR SENDING ERROR TO SERVER: {ex2}\nFOR\n{ex}")



            time.sleep(self.config.sampling_period)



    def scan(self):
        scan_successful = False
        for n in range(3):
            try:
                devices = self.scanner.scan(2.0)
                scan_successful = True
            except BTLEManagementError:
                # May fail to acquire scan if someone else is trying to use the BT scanner at the same time
                # Wait a moment and try again
                time.sleep(2)
        if not scan_successful:
            raise Exception(f"Unable to scan after 3 attempts")

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


    def print_all_devices(self):
        # List all BLE devices found.  Used for figuring out the identifying information of a BLE beacon
        devices = self.scanner.scan(2.0)

        print('='*80)
        print(f"At {datetime.datetime.now()}:")
        for dev in devices:
            print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
            for (adtype, desc, value) in dev.getScanData():
                print("  %s = %s" % (desc, value))
        print('=' * 80)



class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            pass # print("Discovered device", dev.addr)
        elif isNewData:
            pass # print("Received new data from", dev.addr)


class RpcServerException(Exception):
    pass

if __name__ == '__main__':
    KitbitDetector().main_loop()