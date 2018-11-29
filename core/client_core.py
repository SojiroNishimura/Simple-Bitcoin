import socket
import pickle

from blockchain.blockchain_manager import BlockchainManager
from blockchain.block_builder import BlockBuilder
from p2p.connection_manager_4edge import ConnectionManager4Edge
from p2p.my_protocol_message_store import MessageStore
from p2p.my_protocol_message_handler import MyProtocolMessageHandler
from p2p.message_manager import (
    MessageManager,
    MSG_REQUEST_FULL_CHAIN,
    RSP_FULL_CHAIN,
    MSG_ENHANCED,
)


STATE_INIT = 0
STATE_ACTIVE = 1
STATE_SHUTTING_DOWN = 2


class ClientCore:
    def __init__(self, my_port=50082, core_host=None, core_port=None, callback=None, mpmh_callback=None):
        self.client_state = STATE_INIT
        print('Initializing ClientCore...')
        self.my_ip = self.__get_myip()
        print('Server IP address is set to ...', self.my_ip)
        self.my_port = my_port
        self.my_core_host = core_host
        self.my_core_port = core_port
        self.cm = ConnectionManager4Edge(self.my_ip, my_port, core_host, core_port, self.__handle_message)
        self.mpmh = MyProtocolMessageHandler()
        self.mpm_store = MessageStore()
        self.mpmh_callback = mpmh_callback

        self.bb = BlockBuilder()
        my_genesis_block = self.bb.generate_genesis_block()
        self.bm = BlockchainManager(my_genesis_block.to_dict())
        self.callback = callback

    def start(self):
        self.client_state = STATE_ACTIVE
        self.cm.start()
        self.cm.connect_to_core_node()

    def shutdown(self):
        self.client_state = STATE_SHUTTING_DOWN
        print('Shutdown edge node...')
        self.cm.connection_close()

    def get_my_current_state(self):
        return self.client_state

    def get_my_protocol_messages(self):
        return self.mpm_store.get_list()

    def get_my_blockchain(self):
        return self.bm.get_my_blockchain()

    def __client_api(self, request, message):
        if request == 'pass_message_to_client_application':
            print('Client Core API: pass_message_to_client_application')
            self.mpm_store.add(msg)
            self.mpmh_callback(message)
        elif request == 'api_type':
            return 'client_core_api'
        else:
            print('not implemented api was used')

    def __handle_message(self, msg):
        """
            ConnectionManager4Edgeに引き渡すコールバックの中身。
        """
        print(msg)
        if msg[2] == RSP_FULL_CHAIN:
            # TODO: ブロックチェーン送信要求に応じて返却されたブロックチェーンを検証する処理を呼び出す
            new_block_chain = pickle.loads(msg[4].encode('utf8'))
            result, pool_4_orphan_blocks = self.bm.resolve_conflicts(new_block_chain)
            print('blockchain received from central', result)
            if result is not None:
                self.prev_block_hash = result
                print('Calling callback')
                self.callback()
            else:
                print('Received blockchain is useless...')
        elif msg[2] == MSG_ENHANCED:
            # P2P Network を単なるトランスポートして使っているアプリケーションが独自拡張したメッセージはここで処理する。
            # SimpleBitcoin としてはこの種別は使わない
            self.mpmh.handle_message(msg[4], self.__client_api)


    def send_message_to_my_core_node(self, msg_type, msg):
        msgtxt = self.cm.get_message_text(msg_type, msg)
        self.cm.send_msg((self.my_core_host, self.my_core_port), msgtxt)

    def send_req_full_chain_to_my_core_node(self):
        print('send_req_full_chain_to_my_core_node was called')
        new_message = self.cm.get_message_text(MSG_REQUEST_FULL_CHAIN)
        self.cm.send_msg((self.my_core_host, self.my_core_port), new_message)

    def __get_myip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
