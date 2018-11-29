class UTXOManager:
    
    def __init__(self, address):
        print('Initializing UTXOManager...')
        self.my_address = address
        self.utxo_txs = []
        self.my_balance = 0

    def is_sbc_transaction(self, tx):
        """
        暗号通貨用のTransactionかそれ以外かを判定する
        タプルでTransactions種別も返す
        """
        print('is_sbc_transaction was called', tx['t_type'])
        tx_t = tx['t_type']

        t_basic = 'basic'
        t_coinbase = 'coinbase_transaction'
        unknown = 'unknown'

        if tx_t != t_basic:
            if tx_t != t_coinbase:
                return False, unknown
            else:
                return True, t_coinbase
        else:
            return True, t_basic

    def extract_utxos(self, txs):
        """
        与えられたTransaction群の中からUTXOとして利用可能なもののみを抽出して保存する
        """
        print('extract_utxos was called!')
        outputs = []
        inputs = []
        idx = 0
        for t in txs:
            for txout in t['outputs']:
                recipient = txout['recipient']
                if recipient == self.my_address:
                    outputs.append(t)
            for txin in t['inputs']:
                t_in_txin = txin['transaction']
                idx = txin['output_index']
                o_recipient = t_in_txin['outputs'][idx]['recipient']
                if o_recipient == self.my_address:
                    inputs.append(t)

        if outputs is not []:
            for o in outputs:
                if inputs is not []:
                    for i in inputs:
                        for i_i in i['inputs']:
                            if o == i_i['transaction']:
                                outputs.remove(o)
                else:
                    break
        else:
            print('No Transaction for UTXO')
            return

        self._set_my_utxo_txs(outputs)

    def _set_my_utxo_txs(self, txs):
        print('_set_my_utxo_txs was called')
        self.utxo_txs = []

        for t in txs:
            self.put_utxo_tx(t)

    def put_utxo_tx(self, tx):
        """
        UTXOトランザクションの追加。TransactionそのものとTransaction内で自分宛てのoutputが格納されている
        インデックスのタプルとして保存する
        """
        print('put_utxo_tx was called')
        idx = 0
        for txout in tx['outputs']:
            if txout['recipient'] == self.my_address:
                self.utxo_txs.append((tx, idx))
            else:
                idx += 1

        self._compute_my_balance()

    def get_utxo_tx(self, idx):
        return self.utxo_txs[idx]

    def remove_utxo_tx(self, tx):
        self.utxo_txs.remove(tx)
        self._compute_my_balance()

    def _compute_my_balance(self):
        print('_compute_my_balance was called')
        balance = 0
        txs = self.utxo_txs
        for t in txs:
            for txout in t[0]['outputs']:
                print('txout: ', txout)
                if txout['recipient'] == self.my_address:
                    balance += txout['value']

        self.my_balance = balance
