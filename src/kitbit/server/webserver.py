import datetime
import os
import sqlite3
import uuid
from collections import defaultdict, deque
from typing import *

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

@dataclass
class Location:
    floor: int
    room: str
    detail: Optional[str] = None

    def __str__(self):
        result = f"{self.floor}F - {self.room}"
        if self.detail is not None:
            result += f" - {self.detail}"
        return result

    @property
    def id(self):
        return hash(self.__str__())


class KitbitServer:

    def __init__(self):
        this_folder = Path(__file__).parent
        self.app = flask.Flask('KitbitServer', template_folder=str(this_folder / 'templates'))
        self.app.route(r'/kitbit')(self.endpoint_home)
        self.app.route(r'/kitbit/config')(self.endpoint_config)
        self.app.route(r'/kitbit/config/url/tesla')(self.endpoint_config_tesla)
        self.app.route(r'/kitbit/config/url/octopi')(self.endpoint_config_octopi)
        self.app.route(r'/kitbit/config/url/rpi4')(self.endpoint_config_rpi4)
        self.app.route(r'/kitbit/config/url/laptop')(self.endpoint_config_laptop)
        self.app.route(r'/kitbit/config/period/<i>')(self.endpoint_config_period)
        self.app.route(r'/kitbit/train')(self.endpoint_train)
        self.app.route(r'/kitbit/train/<location_id>')(self.endpoint_train_record)
        self.app.route(r'/kitbit/api', methods=['POST'])(self.endpoint_api)

        self.config_url = f"http://{gethostname()}:5058/kitbit/api"
        self.config_sampling_period = 30

        self.errors: List[ErrorMessage] = []
        self.detectors: Dict[str, DetectorInfo] = defaultdict(lambda: DetectorInfo())

        # Manually setup by each detector
        self.detectors['DETECTOR_74c12192'] = DetectorInfo("F1_FrontRoom", "rpi0wh")
        self.detectors['DETECTOR_238260ce'] = DetectorInfo("F1_Couch", "rpi4")
        self.detectors['DETECTOR_762876f7'] = DetectorInfo("F1_DiningRoom", "gardenpi")
        self.detectors['DETECTOR_3b81b2ca'] = DetectorInfo("F2_Hallway", "rpi0w2")
        self.detectors['DETECTOR_1bbda189'] = DetectorInfo("F2_BackBedroom", "rpi0w")
        self.detectors['DETECTOR_1f35bcd8'] = DetectorInfo("F3_3dPrinter", "octopi")

        self.locations = [
            Location(1, "Sun Room"),
            Location(1, "Sun Room", "Perch"),
            Location(1, "Parlor"),
            Location(1, "Living Room"),
            Location(1, "Living Room", "Yellow Chair"),
            Location(1, "Living Room", "Couch"),
            Location(1, "Kitchen"),
            Location(1, "Kitchen", "Food Bowl"),
            Location(1, "Dining Room"),
            Location(1, "Deck"),

            Location(2, "Hallway"),
            Location(2, "Front Bedroom"),
            Location(2, "Middle Bedroom"),
            Location(2, "Middle Bedroom", "Litter Box"),
            Location(2, "Bathroom"),
            Location(2, "Back Bedroom"),

            Location(3, "Staircase"),
            Location(3, "Office"),
            Location(3, "Printer Room"),

            Location(0, "Front of Basement"),
            Location(0, "Back of Basement"),
        ]


        self.cats: Dict[str, CatInfo] = {
            "Juan": CatInfo("Juan", "01a20071376e6677637178"),
        }

        self.rpc_methods = {}

        self.rpc_methods['get_config'] = self.api_get_config
        self.rpc_methods['observation'] = self.api_observation
        self.rpc_methods['error'] = self.api_error

        # Initilize database
        basedir = os.path.dirname(__file__)
        self.db_fp = os.path.join(basedir, 'kitbit_data.db')
        cols = {
            'data_id': 'text',
            'timestamp': 'text',
            'location': 'str',
        }

        for d in self.detectors.values():
            cols[d.name] = 'real'
        sql = "create table if not exists training_data (\n"
        for c, dtype in cols.items():
            sql += f"  {c} {dtype},"
        sql = sql[:-1]
        sql += ")"
        print(sql)
        sqlite3.connect(self.db_fp).cursor().execute(sql)


    def endpoint_home(self):
        context = {
            'cats': self.cats.values(),
            'detectors': self.detectors,
            'errors': self.errors,
        }
        return flask.render_template('kitbit_server_home.html', **context)


    def endpoint_train_record(self, location_id):
        location = [l for l in self.locations if l.id == int(location_id)][0]
        data = {
            'data_id': str(uuid.uuid4())[:6],
            'timestamp': datetime.datetime.now().replace(microsecond=0, second=0),
            'location': str(location),
        }

        for d in self.detectors.values():
            if d.is_stale:
                raise Exception("all sensors must be online")
            data[d.name] = d.last_5_min_observation("Juan")[0].rssi

        sql = f"insert into training_data ({','.join([c for c in data.keys()])}) " \
              f"values ({','.join(['?' for c in data.keys()])})"
        db = sqlite3.connect(self.db_fp)
        cur = db.cursor()
        cur.execute(sql, tuple(data.values()))
        db.commit()
        db.close()
        return flask.redirect(flask.url_for(r"endpoint_home"))

    def endpoint_train(self):
        return flask.render_template('kitbit_server_train.html',
                                     locations = self.locations)


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
    def endpoint_config_laptop(self):
        self.config_url = f"http://jason-laptop:5058/kitbit/api"
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