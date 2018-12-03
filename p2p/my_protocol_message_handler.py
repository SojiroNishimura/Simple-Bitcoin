import json


SEND_TO_ALL_PEER = 'send_message_to_all_peer'
SEND_TO_ALL_EDGE = 'send_message_to_all_edge'
SEND_TO_THIS_ADDRESS = 'send_message_to_this_pubkey_address'

PASS_TO_CLIENT_APP = 'pass_message_to_client_application'


class MyProtocolMessageHandler(object):
    def __init__(self):
        print('Initializing MyProtocolMessageHandler...')

    def handle_message(self, msg, api, is_core):
        msg = json.loads(msg)
        my_api = api('api_type', None)
        print('my_api: ', my_api)
        
        if my_api == 'server_core_api':
            if msg['message_type'] == 'cipher_message':
                print('received cipher message!')
                target_address = msg['recipient']
                result = api(SEND_TO_THIS_ADDRESS, (target_address, json.dumps(msg)))
                if result == None:
                    if not is_core:
                        api(SEND_TO_ALL_PEER, json.dumps(msg))
            else:
                print('Bloadcasting ...', json.dumps(msg))
                if not is_core:
                    # Coreノード以外からのメッセージの場合は他のCoreノードにブロードキャストする
                    api(SEND_TO_ALL_PEER, json.dumps(msg))
                api(SEND_TO_ALL_EDGE, json.dumps(msg))
        else:
            print('MyProtocolMessageHandler received ', msg)
            api(PASS_TO_CLIENT_APP, msg)

        return
