import datetime
from collections import defaultdict

import flask
from dataclasses import dataclass
from pathlib import Path

from kitbit.protocol import *


class DetectorInfo:
    def __init__(self, detector_uuid: str, name = None):
        self.name = name or detector_uuid
        self.last_observation = datetime.datetime(1970,1,1)
        self.last_configuration = datetime.datetime(1970,1,1)
        self.errors: List[ErrorMessage] = []

class CatInfo:
    def __init__(self, name, service_id):
        self.name = name
        self.service_id = service_id
        self.last_seen_timestamp = datetime.datetime(1970,1,1)
        self.last_seen_detector = 'None'


class KitbitServer:

    def __init__(self):
        this_folder = Path(__file__).parent
        self.app = flask.Flask('KitbitServer', template_folder=str(this_folder / 'templates'))
        self.app.route(r'/kitbit')(self.endpoint_home)
        self.app.route(r'/kitbit/api', methods=['POST'])(self.endpoint_api)

        self.errors: List[ErrorMessage] = []
        self.detectors: Dict[str, DetectorInfo] = defaultdict(lambda: DetectorInfo('???'))
        self.detectors['DETECTOR_6c348178-9748-4901-bfb0-5ddf4bd57250'] = DetectorInfo("rpi0w2")


        self.cats: Dict[str, CatInfo] = {
            "Juan": CatInfo("Juan", "01a20071376e6677637178"),
        }

        self.rpc_methods = {}

        self.rpc_methods['get_config'] = self.api_get_config
        self.rpc_methods['observation'] = self.api_observation
        self.rpc_methods['error'] = self.api_error


    def endpoint_home(self):

        context = {
            'cats': self.cats.values(),
            'detectors': self.detectors,
            'errors': self.errors,
        }


        return flask.render_template('kitbit_server_home.html', **context)

    def endpoint_api(self):
        try:
            envelope = flask.request.json
            method = envelope.get('method', 'NO METHOD')
            params = envelope.get('params', {})

            result = self.rpc_methods[method](**params)

            return flask.jsonify({
                'result': result,
            })
        except Exception as ex:
            self.errors.append(ErrorMessage.from_last_exception())
            return flask.jsonify({
                'error': {
                    'message': str(ex)
                }
            })

    def api_get_config(self, detector_uuid):
        self.detectors[detector_uuid].last_observation = datetime.datetime.now()

        cats = {c.service_id: c.name for c in self.cats.values()}
        return ConfigMessage(cats).to_dict()

    def api_observation(self, **params):
        obs = ScanObservationMessage(**params)
        detector = self.detectors[obs.detector_uuid]
        detector.last_observation = datetime.datetime.now()

        # TODO: record observation
        for cat, rssi in obs.cat_rssi.items():
            self.cats[cat].last_seen_timestamp = datetime.datetime.now()
            self.cats[cat].last_seen_detector = detector.name
            print(cat, rssi)

    def api_error(self, detector_uuid, error):
        err = ErrorMessage(**error)
        print('***** REMOTE ERROR *****')
        print(err.traceback)
        print('************************')

        self.detectors[detector_uuid].errors.append(err)

if __name__ == '__main__':
    KitbitServer().app.run('0.0.0.0', 5058)