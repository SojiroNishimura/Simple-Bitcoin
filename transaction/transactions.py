from time import time


class Transaction:
    """
    送金可能なコインの総額を記録できるように、過去のトランザクションでの自分宛てへの送金記録と
    他のアドレスへの送金済み金額をinputsとoutputsのペアで管理する
    """
    
    def __init__(self, inputs, outputs):
        self.inputs = inputs
        self.outputs = outputs
        self.timestamp = time()
        self.t_type = 'basic'

    def to_dict(self):
        d = {
            'inputs': list(map(TransactionInput.to_dict, self.inputs)),
            'outputs': list(map(TransactionOutput.to_dict, self.outputs)),
            'timestamp': self.timestamp,
            't_type': self.t_type
        }
        return d

    def is_enough_inputs(self, fee):
        total_in = sum(i.transaction['outputs'][i.output_index]['value'] for i in self.inputs)
        total_out = sum(int(o.value) for o in self.outputs) + int(fee)
        delta = total_in - total_out

        # Inputsの合計がOutpusの合計以上であることを確認する
        if delta >= 0:
            return True
        else:
            return False

    def compute_change(self, fee):
        total_in = sum(i.transaction['outputs'][i.output_index]['value'] for i in self.inputs)
        total_out = sum(int(o.value) for o in self.outputs) + int(fee)
        delta = total_in - total_out
        return delta


class TransactionOutput:

    def __init__(self, recipient_address, value):
        self.recipient = recipient_address
        self.value = value

    def to_dict(self):
        d = {
            'recipient': self.recipient,
            'value': self.value,
        }
        return d


class TransactionInput:

    def __init__(self, transaction, output_index):
        self.transaction = transaction
        self.output_index = output_index

    def to_dict(self):
        d = {
            'transaction': self.transaction,
            'output_index': self.output_index,
        }
        return d


class CoinbaseTransaction(Transaction):
    """
    Coinbaseトランザクションは例外的にInputを持たない
    """

    def __init__(self, recipient_address, value=30):
        self.inputs = []
        self.outputs = [TransactionOutput(recipient_address, value)]
        self.timestamp = time()
        self.t_type = 'coinbase_transaction'

    def to_dict(self):
        d = {
            'inputs': [],
            'outputs': list(map(TransactionOutput.to_dict, self.outputs)),
            'timestamp': self.timestamp,
            't_type': self.t_type,
        }
        return d


class EngravedTransaction:
    """
    value以外に任意のメッセージをTransactionに付加できる拡張Transactionタイプ
    """
    def __init__(self, sender, sender_alt_name, message, icon_url=None, reply_to=None, original_reply_to=None):
        self.sender = sender
        self.sender_alt_name = sender_alt_name
        self.icon = icon_url
        self.message = message
        self.timestamp = time()
        self.reply_to = reply_to
        self.original_reply_to = original_reply_to
        self.content_id = sender + str(self.timestamp)
        self.t_type = 'engraved'

    def to_dict(self):
        d = {
            'sender': self.sender,
            'sender_alt_name': self.sender_alt_name,
            'icon': self.icon,
            'timestamp': self.timestamp,
            'message': self.message,
            'reply_to': self.reply_to,
            'original_reply_to': self.original_reply_to,
            'id': self.content_id,
            't_type': self.t_type,
        }
        return d
