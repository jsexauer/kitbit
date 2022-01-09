import flask

class KitbitServer:

    def __init__(self):
        self.app = flask.Flask('KitbitServer')
        self.app.route(r'/kitbit/api', methods=['POST'])(self.endpoint_api)



    def endpoint_api(self):
        envelope = flask.request.json
        method = envelope.get('method', 'NO METHOD')
        params = envelope.get('params', {})

        if method == 'observation':
            self.endpoint_api_observation(**params)
        elif method == '':
            self.endpoint_api_error(**params)

        return flask.Response()

    def endpoint_api_observation(self, cat: str, rssi: float):
        print(cat, rssi)

    def endpoint_api_error(self, tb: str, ex: str):
        print('***** REMOTE ERROR *****')
        print(ex)
        print(tb)

if __name__ == '__main__':
    KitbitServer().app.run('0.0.0.0', 5058)