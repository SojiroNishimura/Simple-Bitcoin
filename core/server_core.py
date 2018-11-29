import socket
import threading
import json
import pickle
import time
import copy

from blockchain.blockchain_manager import BlockchainManager
from blockchain.block_builder import BlockBuilder
from transaction.transaction_pool import TransactionPool
from transaction.utxo_manager import UTXOManager
from transaction.transactions import CoinbaseTransaction
from utils.key_manager import KeyManager
from utils.rsa_util import RSAUtil
from p2p.connection_manager import ConnectionManager
from p2p.my_protocol_message_handler import MyProtocolMessageHandler
from p2p.my_protocol_message_store import MessageStore
from p2p.message_manager import (
    MessageManager,
    MSG_NEW_TRANSACTION,
    MSG_NEW_BLOCK,
    MSG_REQUEST_FULL_CHAIN,
    RSP_FULL_CHAIN,
    MSG_ENHANCED,
)


STATE_INIT = 0
STATE_STANDBY = 1
STATE_CONNECTED_TO_CENTRAL = 2
STATE_SHUTTING_DOWN = 3

CHECK_INTERVAL = 10


class ServerCore:
    def __init__(self, my_port=50082, core_node_host=None, core_node_port=None, passphrase=None):
        self.server_state = STATE_INIT
        print('Initializing server...')
        self.my_ip = self.__get_myip()
        print('Server IP address is set to ...', self.my_ip)
        self.my_port = my_port
        self.cm = ConnectionManager(self.my_ip, self.my_port, self.__handle_message)
        self.mpm = MyProtocolMessageHandler()
        self.core_node_host = core_node_host
        self.core_node_port = core_node_port
        self.mpm_store = MessageStore()

        self.bb = BlockBuilder()
        self.flag_stop_block_build = False
        self.is_bb_running = False
        my_genesis_block = self.bb.generate_genesis_block()
        self.bm = BlockchainManager(my_genesis_block.to_dict())
        self.prev_block_hash = self.bm.get_hash(my_genesis_block.to_dict())
        self.tp = TransactionPool()

        self.km = KeyManager(None, passphrase)
        self.rsa_util = RSAUtil()
        self.um = UTXOManager(self.km.my_address())

    def start(self):
        self.server_state = STATE_STANDBY
        self.cm.start()

        self.bb_timer = threading.Timer(CHECK_INTERVAL, self.__generate_block_with_tp)
        self.bb_timer.start()

    def join_network(self):
        if self.core_node_host is not None:
            self.server_state = STATE_CONNECTED_TO_CENTRAL
            self.cm.join_network(self.core_node_host, self.core_node_port)
        else:
            print('This server is running as Genesis Core Node...')

    def shutdown(self):
        self.server_state = STATE_SHUTTING_DOWN
        print('Shutdown server...')
        self.cm.connection_close()

    def get_my_current_state(self):
        return self.server_state

    def get_all_chains_for_resolve_conflict(self):
        print('get_all_chains_for_resolve_conflict was called')
        new_message = self.cm.get_message_text(MSG_REQUEST_FULL_CHAIN)
        self.cm.send_msg_to_all_peer(new_message)

    def __generate_block_with_tp(self):
        print('Thread for generate_block_with_tp started!')
        while not self.flag_stop_block_build:
            self.is_bb_running = True
            prev_hash = copy.copy(self.prev_block_hash)
            result = self.tp.get_stored_transactions()
            if len(result) == 0:
                print('Transaction Pool is empty...')
                break

            new_tp = self.bm.remove_useless_transaction(result)
            self.tp.renew_my_transactions(new_tp)
            if len(new_tp) == 0:
                break

            # ブロック生成報酬としてリスト先頭に自分宛てのCoinbaseTransactionを追加する
            total_fee = self.tp.get_total_fee_from_tp()
            # TODO: 動作確認のため一時的に固定値を使用する
            total_fee += 30

            my_coinbase_t = CoinbaseTransaction(self.km.my_address(), total_fee)
            transactions_4_block = copy.deepcopy(new_tp)
            transactions_4_block.insert(0, my_coinbase_t.to_dict())
            new_block = self.bb.generate_new_block(transactions_4_block, prev_hash)

            # ブロックの追加可否チェック
            if new_block.to_dict()['previous_block'] == self.prev_block_hash:
                self.bm.set_new_block(new_block.to_dict())
                self.prev_block_hash = self.bm.get_hash(new_block.to_dict())
                msg_new_block = self.cm.get_message_text(MSG_NEW_BLOCK, json.dumps(new_block.to_dict()))
                self.cm.send_msg_to_all_peer(msg_new_block)
                # ブロック生成成功時はTransactionPoolをクリアする
                index = len(new_tp)
                self.tp.clear_my_transactions(index)
                break
            else:
                print('Bad block. It seems someone already win the PoW.')
                break

        print('Current Blockchain is ...', self.bm.chain)
        print('Current prev_block_hash is ...', self.prev_block_hash)
        self.flag_stop_block_build = False
        self.is_bb_running = False
        self.bb_timer = threading.Timer(CHECK_INTERVAL, self.__generate_block_with_tp)
        self.bb_timer.start()

    def __core_api(self, request, message):
        msg_type = MSG_ENHANCED

        if request == 'send_message_to_all_peer':
            new_message = self.cm.get_message_text(msg_type, message)
            self.cm.send_msg_to_all_peer(new_message)
            return 'ok'
        elif request == 'send_message_to_all_edge':
            new_message = self.cm.get_message_text(msg_type, message)
            self.cm.send_msg_to_all_edge(new_message)
            return 'ok'
        elif request == 'api_type':
            return 'server_core_api'

    def __handle_message(self, msg, is_core, peer=None):
        if peer != None:
            if msg[2] == MSG_REQUEST_FULL_CHAIN:
                print('Send our latest blockchain for reply to : ', peer)
                mychain = self.bm.get_my_blockchain()
                chain_data = pickle.dumps(mychain, 0).decode()
                new_message = self.cm.get_message_text(RSP_FULL_CHAIN, chain_data)
                self.cm.send_msg(peer, new_message)
        else:
            if msg[2] == MSG_NEW_TRANSACTION:
                new_transaction = json.loads(msg[4])
                print('received new_transaction', new_transaction)
                is_sbc_t, _ = self.um.is_sbc_transaction(new_transaction)
                current_transactions = self.tp.get_stored_transactions()
                if new_transaction in current_transactions:
                    print('this is already pooled transaction: ', new_transaction)
                    return

                if not is_sbc_t:
                    print('this is not SimpleBitcoin transaction: ', new_transaction)
                    is_verified = self.rsa_util.verify_general_transaction_sig(new_transaction)
                    if not is_verified:
                        print('Transaction Verification Error')
                        return
                else:
                    # テスト用に最初のブロックだけ未知のCoinbaseTransactionを許可する暫定処置
                    if self.bm.get_my_chain_length() != 1:
                        checked = self._check_availability_of_transaction(new_transaction)
                        if not checked:
                            print('Transaction Verification Error')
                            return
                    self.tp.set_new_transaction(new_transaction)

                if not is_core:
                    new_message = self.cm.get_message_text(MSG_NEW_TRANSACTION, json.dumps(new_transaction))
                    self.cm.send_msg_to_all_peer(new_message)
            elif msg[2] == MSG_NEW_BLOCK:
                if not is_core:
                    print('block received from unknown')
                    return

                # 新規ブロックを検証し正当なものであればブロックチェーンに追加する
                new_block = json.loads(msg[4])
                print('new_block: ', new_block)
                if self.bm.is_valid_block(self.prev_block_hash, new_block):
                    # ブロック生成中なら処理を止める
                    if self.is_bb_running:
                        self.flag_stop_block_build = True
                    self.prev_block_hash = self.bm.get_hash(new_block)
                    self.bm.set_new_block(new_block)
                    new_tp = self.bm.remove_useless_transaction(result)
                    self.tp.renew_my_transactions(new_tp)
                else:
                    # ブロックとして不正ではないがVerifyにコケる場合は自分がorphanブロックを生成している可能性がある
                    self.get_all_chains_for_resolve_conflict()
            elif msg[2] == RSP_FULL_CHAIN:
                if not is_core:
                    print('blockchain received from unknown')
                    return

                # ブロックチェーン送信要求に応じて返却されたブロックチェーンを検証し、有効なものか
                # 検証した上で自分の持つチェーンと比較し優位な方を今後のブロックチェーンとして有効化する
                new_block_chain = pickle.loads(msg[4].encode('utf8'))
                print(new_block_chain)
                result, pool_4_orphan_blocks = self.bm.resolve_conflicts(new_block_chain)
                print('blockchain received from central')
                if result is not None:
                    self.prev_block_hash = result
                    if len(pool_4_orphan_blocks) != 0:
                        # orphanブロック群の中にあった未処理扱いのTransactionをTransactionPoolに戻す
                        new_transactions = self.bm.get_transactions_from_orphan_blocks(pool_4_orphan_blocks)
                        for t in new_transactions:
                            self.tp.set_new_transaction(t)
                else:
                    print('Received blockchain is useless...')
            elif msg[2] == MSG_ENHANCED:
                print('received enhanced message', msg[4])
                current_messages = self.mpm_store
                has_same = False
                if not msg[4] in current_messages:
                    self.mpm_store.append(msg[4])
                    self.mpm.handle_message(msg[4], self.__core_api)

    def _check_availability_of_transaction(self, transaction):
        """
        Transactionに含まれているTransactionInputの有効性(二重使用)を検証する
        """
        v_result, used_outputs = self.rsa_util.verify_sbc_transactions_sig(transaction)

        if v_result is not True:
            print('signature verification error on new transaction')
            return False

        for used_o in used_ouputs:
            print('used_o', used_o)
            bm_v_result = self.bm.has_this_output_in_my_chain(used_o)
            tp_v_result = self.tp.has_this_output_in_my_tp(used_o)
            bm_v_result2 = self.bm.is_valid_output_in_my_chain(used_o)
            if bm_v_result:
                print('This TransactionOutput is already used', used_o)
                return False
            if tp_v_result:
                print('This TransactionOutput is already stored in the TransactionPool', used_o)
                return False
            if bm_v_result2 is not True:
                print('This TransactionOutput is unknown', used_o)
                return False

        return True

    def _check_availability_of_transaction_in_block(self, transaction):
        v_result, used_outputs = self.km.verify_sbc_transactions_sig(transaction)
        if v_result is not True:
            print('signature verification error on new transaction')
            return False

        for used_o in used_outputs:
            print('used_o: ', used_o)
            bm_v_result = self.bm.has_this_output_in_my_chain(used_o)
            bm_v_result2 = self.bm.is_valid_output_in_my_chain(used_o)
            if bm_v_result2 is not True:
                print('This TransactionOutput is unknown', used_o)
                return False
            if bm_v_result:
                print('This TransactionOutput is already used', used_o)
                return False

        return True

    def get_total_fee_on_block(self, block):
        print('get_total_fee_on_block was called')
        transactions = block['transactions']
        result = 0
        for t in transactions:
            t = json.loads(t)
            is_sbc_t, t_type = self.um.is_sbc_transaction(t)
            if t_type == 'basic':
                total_in = sum(i['transaction']['outputs'][i['output_index']]['value'] for i in t['inputs'])
                total_out = sum(o['value'] for o in t['outputs'])
                delta = total_in - total_out
                result += delta

        return result

    def check_transactions_in_new_block(self, block):
        """
        ブロック内のTransactionに不正がないか確認する
        """
        fee_for_block = self.get_total_fee_on_block(block)
        fee_for_block += 30 # FIXME: 一旦固定値にしておく
        print('fee_for_block: ', fee_for_block)

        transactions = block['transactions']

        counter = 0

        for t in transactions:
            t = json.loads(t)
            # basic, coinbase_transaction以外はスルー
            is_sbc_t, t_type = self.um.is_sbc_transaction(t)
            if is_sbc_t:
                if t_type == 'basic':
                    if self._check_availability_of_transaction_in_block(t) is not True:
                        print('Bad Block. Having invalid Transaction')
                        return False
                elif t_type == 'coinbase_transaction':
                    if counter != 0:
                        print('Coinbase Transaction is only for BlockBuilder')
                        return False
                    else:
                        insentive = t['outputs'][0]['value']
                        print('insentive', insentive)
                        if insentive != fee_for_block:
                            print('Invalid value in fee for CoinbaseTransaction', insentive)
                            return False
            else:
                is_verified = self.rsa_util.verify_general_transaction_sig(t)
                if not is_verified:
                    return False

        print('ok. this block is acceptable')
        return True

    def __get_myip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]

