import json


class MyProtocolMessageHandler(object):
    def __init__(self):
        print('Initializing MyProtocolMessageHandler...')

    def handle_message(self, msg):
        msg = json.loads(msg)
        print('MyProtocolMessageHandler received ', msg)
        return
