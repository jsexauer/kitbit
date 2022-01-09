import datetime
from collections import defaultdict

import flask
from dataclasses import dataclass

from kitbit.protocol import *


class DetectorInfo:
    def __init__(self, detector_uuid: str, name = None):
        self.detector_uuid = detector_uuid
        self.name = name or detector_uuid
        self.last_observation = datetime.datetime.now()
        self.errors: List[ErrorMessage] = []

class CatInfo:
    def __init__(self, name, service_id):
        self.name = name
        self.service_id = service_id

class KitbitServer:

    def __init__(self):
        self.app = flask.Flask('KitbitServer')
        self.app.route(r'/kitbit/api', methods=['POST'])(self.endpoint_api)

        self.detectors: Dict[str, DetectorInfo] = defaultdict(lambda: DetectorInfo('???'))
        self.errors: List[ErrorMessage] = []

        self.cats = [
            CatInfo("Juan", "01a20071376e6677637178"),
        ]

        self.rpc_methods = {}

        self.rpc_methods['get_config'] = self.api_get_config
        self.rpc_methods['observation'] = self.api_observation
        self.rpc_methods['error'] = self.api_error



    def endpoint_api(self):
        try:
            envelope = flask.request.json
            method = envelope.get('method', 'NO METHOD')
            params = envelope.get('params', {})

            result = self.rpc_methods[method](**params)

            return {
                'result': flask.jsonify(result),
            }
        except Exception as ex:
            self.errors.append(ErrorMessage.from_last_exception())
            return flask.jsonify({
                'error': {
                    'message': str(ex)
                }
            })

    def api_get_config(self):
        cats = {c.service_id: c.name for c in self.cats}
        return ConfigMessage(cats)

    def api_observation(self, **params):
        obs = ScanObservationMessage(**params)
        detector = self.detectors[obs.detector_uuid]
        detector.last_observation = datetime.datetime.now()

        # TODO: record observation
        for cat, rssi in obs.cat_rssi.items():
            print(cat, rssi)

    def api_error(self, detector_uuid, error):
        err = ErrorMessage(**error)
        print('***** REMOTE ERROR *****')
        print(err.traceback)
        print('************************')

        self.detectors[detector_uuid].errors.append(err)

if __name__ == '__main__':
    KitbitServer().app.run('0.0.0.0', 5058)