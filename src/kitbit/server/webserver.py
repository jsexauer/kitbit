import datetime
from collections import defaultdict, deque

import flask
from dataclasses import dataclass, field
from pathlib import Path
from socket import gethostname

from kitbit.protocol import *

@dataclass
class ObservationInfo:
    detector: str
    beacon: str
    rssi: Optional[float]
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)


class DetectorInfo:
    def __init__(self, name = '???', host='???'):
        self.name = name
        self.host = host
        self.last_observation = datetime.datetime(1970,1,1)
        self.last_configuration = datetime.datetime(1970,1,1)
        self.errors: List[ErrorMessage] = []
        self.recent_observations: Deque[ObservationInfo] = deque(maxlen=10)

    def last_5_min_observation(self, beacon: str) -> List[ObservationInfo]:
        """List of observations within the last 5 minutes"""
        result = []
        ref = datetime.datetime.now()
        for i in range(5):
            start = ref - datetime.timedelta(minutes=i)
            end = ref - datetime.timedelta(minutes=i+1)
            in_range = [o for o in self.recent_observations if start > o.timestamp >= end and o.beacon == beacon]
            if len(in_range) > 0:
                result.append(in_range[0])
            else:
                result.append(ObservationInfo(detector=self.name, beacon=beacon, rssi=None, timestamp=start))
        return result

    @property
    def is_stale(self):
        return self.last_observation <= datetime.datetime.now() - datetime.timedelta(minutes=2)


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
        self.app.route(r'/kitbit/config')(self.endpoint_config)
        self.app.route(r'/kitbit/config/url/tesla')(self.endpoint_config_tesla)
        self.app.route(r'/kitbit/config/url/octopi')(self.endpoint_config_octopi)
        self.app.route(r'/kitbit/config/url/rpi4')(self.endpoint_config_rpi4)
        self.app.route(r'/kitbit/config/period/<i>')(self.endpoint_config_period)
        self.app.route(r'/kitbit/api', methods=['POST'])(self.endpoint_api)

        self.config_url = f"http://{gethostname()}:5058/kitbit/api"
        self.config_sampling_period = 30

        self.errors: List[ErrorMessage] = []
        self.detectors: Dict[str, DetectorInfo] = defaultdict(lambda: DetectorInfo())

        # Manually setup by each detector
        self.detectors['DETECTOR_1bbda189'] = DetectorInfo("Back Bedroom", "rpi0w")
        self.detectors['DETECTOR_1f35bcd8'] = DetectorInfo("3rd floor - 3d Printer", "octopi")
        self.detectors['DETECTOR_762876f7'] = DetectorInfo("Dining Room", "gardenpi")
        self.detectors['DETECTOR_74c12192'] = DetectorInfo("Front Room", "rpi0wh")
        self.detectors['DETECTOR_3b81b2ca'] = DetectorInfo("Hallway", "rpi0w2")
        self.detectors['DETECTOR_238260ce'] = DetectorInfo("Couch", "rpi4")


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


    def endpoint_config(self):
        return flask.render_template('kitibt_server_config.html',
                                     config_url = self.config_url,
                                     config_sampling_period = self.config_sampling_period)
    def endpoint_config_tesla(self):
        self.config_url = f"http://tesla:5058/kitbit/api"
        return self.endpoint_config()
    def endpoint_config_rpi4(self):
        self.config_url = f"http://rpi4:5058/kitbit/api"
        return self.endpoint_config()
    def endpoint_config_octopi(self):
        self.config_url = f"http://octopi:5058/kitbit/api"
        return self.endpoint_config()
    def endpoint_config_period(self, i):
        self.config_sampling_period = int(i)
        return self.endpoint_config()

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
        self.detectors[detector_uuid].last_configuration = datetime.datetime.now()

        cats = {c.service_id: c.name for c in self.cats.values()}
        return ConfigMessage(cats,
                             sampling_period=self.config_sampling_period,
                             api_uri=self.config_url,).to_dict()

    def api_observation(self, **params):
        obs = ScanObservationMessage(**params)
        detector = self.detectors[obs.detector_uuid]
        detector.last_observation = datetime.datetime.now()

        # TODO: record observation
        for cat, rssi in obs.cat_rssi.items():
            self.cats[cat].last_seen_timestamp = datetime.datetime.now()
            self.cats[cat].last_seen_detector = detector.name
            detector.recent_observations.append(ObservationInfo(
                detector=detector.name,
                beacon=cat,
                rssi=rssi
            ))
            print(cat, detector.name, rssi)

    def api_error(self, detector_uuid, error):
        err = ErrorMessage(**error)
        print('***** REMOTE ERROR *****')
        print(err.traceback)
        print('************************')

        self.detectors[detector_uuid].errors.append(err)

if __name__ == '__main__':
    KitbitServer().app.run('0.0.0.0', 5058)