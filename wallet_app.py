import os
import sys
import binascii
import json
import pprint
import base64
import copy

from tkinter import *
from tkinter import messagebox
from tkinter import filedialog
from tkinter.ttk import Button, Style
from tkinter import ttk

from core.client_core import ClientCore as Core
from utils.key_manager import KeyManager
from utils.rsa_util import RSAUtil
from utils.aes_util import AESUtil
from transaction.utxo_manager import UTXOManager
from transaction.transactions import Transaction
from transaction.transactions import TransactionInput
from transaction.transactions import TransactionOutput
from transaction.transactions import CoinbaseTransaction
from transaction.transactions import EngravedTransaction
from p2p.message_manager import (
    MSG_NEW_TRANSACTION,
    MSG_ENHANCED,
)


class SimpleBC_Gui(Frame):
    
    def __init__(self, parent, my_port, c_host, c_port):
        Frame.__init__(self, parent)
        self.parent = parent
        self.parent.protocol('WM_DELETE_WINDOW', self.quit)
        self.coin_balance = StringVar(self.parent, '0')
        self.status_message = StringVar(self.parent, 'No coin to be sent')
        self.c_core = None
        self.initApp(my_port, c_host, c_port)
        self.setupGUI()

    def quit(self, event=None):
        self.c_core.shutdown()
        self.parent.destroy()

    def initApp(self, my_port, c_host, c_port):
        print('SimpleBitcoin client is now activating...: ')
        self.km = KeyManager()
        self.um = UTXOManager(self.km.my_address())
        self.rsa_util = RSAUtil()

        self.c_core = Core(my_port, c_host, c_port, self.update_callback, self.get_message_callback)
        self.c_core.start(self.km.my_address())

        # テスト用
        t1 = CoinbaseTransaction(self.km.my_address())
        t2 = CoinbaseTransaction(self.km.my_address())
        t3 = CoinbaseTransaction(self.km.my_address())

        transactions = []
        transactions.append(t1.to_dict())
        transactions.append(t2.to_dict())
        transactions.append(t3.to_dict())

        self.um.extract_utxos(transactions)
        self.update_balance()

    def display_info(self, title, info):
        f = Tk()
        label = Label(f, text=title)
        label.pack()
        info_area = Text(f, width=70, height=50)
        info_area.insert(INSERT, info)
        info_area.pack()

    def update_status(self, info):
        self.status_message.set(info)

    def update_balance(self):
        bal = str(self.um.my_balance)
        self.coin_balance.set(bal)

    def get_message_callback(self, target_message):
        print('get_message_callback was called!')

        if target_message['message_type'] == 'cipher_message':
            try:
                encrypted_key = base64.b64decode(binascii.unhexlify(target_message['enc_key']))
                print('encrypted_key: ', encrypted_key)
                decrypted_key = self.km.decrypt_with_private_key(encrypted_key)
                print('decrypted_key: ', binascii.hexlify(decrypted_key).decode('ascii'))

                aes_util = AESUtil()
                decrypted_message = aes_util.decrypt_with_key(base64.b64decode(binascii.unhexlify(target_message['body'])), decrypted_key)
                print(decrypted_message.decode('utf-8'))
                """
                現状使わないが一応メッセージを作っておく
                message = {
                    'from': binascii.unhexlify(target_message['sender']),
                    'message': decrypted_message.decode('utf-8'),
                }
                message_4display = pprint.pformat(message, indent=2)
                """
                messagebox.showwarning('You received an instant encrypted message!', decrypted_message.decode('utf-8'))
            except Exception as e:
                print(e, 'error occured')
        elif target_message['message_type'] == 'engraved':
            sender_name = target_message['sender_alt_name']
            msg_body = base64.b64decode(binascii.unhexlify(target_message['message'])).decode('utf-8')
            timestamp = datetime.datetime.fromtimestamp(int(target_message['timestamp']))
            messagebox.showwarning(
                'You received a new engraved message!',
                '{} :\n {} \n {}'.format(sender_name, msg_body, timestamp))

    def update_callback(self):
        print('update_callback was called!')
        s_transactions = self.c_core.get_stored_transactions_from_bc()
        print(s_transactions)
        self.um.extract_utxos(s_transactions)
        self.update_balance()

    def create_menu(self):
        top = self.winfo_toplevel()
        self.menuBar = Menu(top)
        top['menu'] = self.menuBar

        self.subMenu = Menu(self.menuBar, tearoff=0)
        self.menuBar.add_cascade(label='Menu', menu=self.subMenu)
        self.subMenu.add_command(label='Show My Address', command=self.show_my_address)
        self.subMenu.add_command(label='Load my Keys', command=self.load_my_keys)
        self.subMenu.add_command(label='Update Blockchain', command=self.update_block_chain)
        self.subMenu.add_separator()
        self.subMenu.add_command(label='Quit', command=self.quit)

        self.subMenu2 = Menu(self.menuBar, tearoff=0)
        self.menuBar.add_cascade(label='Settings', menu=self.subMenu2)
        self.subMenu2.add_command(label='Renew my Keys', command=self.renew_my_keypairs)
        self.subMenu2.add_command(label='Connection Info', command=self.edit_conn_info)

        self.subMenu3 = Menu(self.menuBar, tearoff=0)
        self.menuBar.add_cascade(label='Advance', menu=self.subMenu3)
        self.subMenu3.add_command(label='Send Encrypted Instant Message', command=self.send_instant_message)
        self.subMenu3.add_command(label='Show logs', command=self.open_log_window)
        self.subMenu3.add_command(label='Show Blockchain', command=self.show_my_block_chain)
        self.subMenu3.add_command(label='Engrave Message', command=self.engrave_message)

    def show_my_address(self):
        f = Tk()
        label = Label(f, text='My Address')
        label.pack()
        key_info = Text(f, width=70, height=10)
        my_address = self.km.my_address()
        key_info.insert(INSERT, my_address)
        key_info.pack()

    def show_input_dialog_for_key_loading(self):

        def load_my_keys():
            f2 = Tk()
            f2.withdraw()
            fTyp = [('', '*.pem')]
            iDir = os.path.abspath(os.path.dirname(__file__))
            messagebox.showinfo('Load key pair', 'please choose your key file')
            f_name = filedialog.askopenfilename(filetypes=fTyp, initialdir=iDir)

            try:
                file = open(f_name)
                data = file.read()
                target = binascii.unhexlify(data)
                # TODO: 鍵ペアが不正時などの異常系処理を追加すべき
                self.km.import_key_pair(target, p_phrase.get())
            except Exception as e:
                print(e)
            finally:
                # TODO: 保有コインの再確認処理を入れる
                file.close()
                f.destroy()
                f2.destroy()
                self.um = utxm.UTXOManager(self.km.my_address())
                self.um.my_balance = 0
                self.update_balance()

        f = Tk()
        label0 = Label(f, text='Please enter pass phrase for hyour key pair')
        frame1 = ttk.Frame(f)
        label1 = ttk.Label(frame1, text='Pass Phrase:')

        p_phrase = StringVar()

        entry1 = ttk.Entry(frame1, textvariable=p_phrase)
        button1 = ttk.Button(frame1, text='Load', command=load_my_keys)

        label0.grid(row=0, column=0, sticky=(N,E,S,W))
        frame1.grid(row=1, column=0, sticky=(N,E,S,W))
        label1.grid(row=2, column=0, sticky=E)
        entry1.grid(row=2, column=1, sticky=W)
        button1.grid(row=3, column=1, sticky=W)

    def load_my_keys(self):
        pass

    def update_block_chain(self):
        self.c_core.send_req_full_chain_to_my_core_node()

    def renew_my_keypairs(self):
        # TODO: 新規アドレスになるので所有コインを0に更新する
        def save_my_pem():
            self.km = KeyManager()
            my_pem = self.km.export_key_pair(p_phrase.get())
            my_pem_hex = binascii.hexlify(my_pem).decode('ascii')

            path = 'my_key_pair.pem'
            f1 = open(path, 'a')
            f1.write(my_pem_hex)
            f1.close()
            f.destroy()
            self.um = UTXOManager(self.km.my_address())
            self.um.my_balance = 0
            self.update_balance()

        f = Tk()
        f.title('New Key Gene')
        label0 = Label(f, text='Please enter pass phrase for your new key pair')
        frame1 = ttk.Frame(f)
        label1 = ttk.Label(frame1, text='Pass Phrase:')

        p_phrase = StringVar()

        entry1 = ttk.Entry(frame1, textvariable=p_phrase)
        button1 = ttk.Button(frame1, text='Generate', command=save_my_pem)

        label0.grid(row=0, column=0, sticky=(N,E,S,W))
        frame1.grid(row=1, column=0, sticky=(N,E,S,W))
        label1.grid(row=2, column=0, sticky=E)
        entry1.grid(row=2, column=1, sticky=W)
        button1.grid(row=3, column=1, sticky=W)


    def edit_conn_info(self):
        # Coreノードへの接続情報の編集
        pass
        
    def open_log_window(self):
        pass

    def show_my_block_chain(self):
        mychain = self.c_core.get_my_blockchain()
        if mychain is not None:
            mychain_str = pprint.pformat(mychain, indent=2)
            self.display_info('Current Blockchain', mychain_str)
        else:
            self.display_info('Warning', 'Currently Blockchain is empty...')

    def setupGUI(self):
        self.parent.bind('<Control-q>', self.quit)
        self.parent.title('SimpleBitcoin GUI')
        self.pack(fill=BOTH, expand=1)

        self.create_menu()

        lf = LabelFrame(self, text='Current Balance')
        lf.pack(side=TOP, fill='both', expand='yes', padx=7, pady=7)

        lf2 = LabelFrame(self, text='')
        lf2.pack(side=BOTTOM, fill='both', expand='yes', padx=7, pady=7)

        # 保有コインの総額表示用ラベル
        self.balance = Label(lf, textvariable=self.coin_balance, font='Helvetica 20')
        self.balance.pack()

        # 送信先公開鍵
        self.label = Label(lf2, text='Recipient Address:')
        self.label.grid(row=0, pady=5)

        self.recipient_pubkey = Entry(lf2, bd=2)
        self.recipient_pubkey.grid(row=0, column=1, pady=5)

        # 送金額
        self.label2 = Label(lf2, text='Amount to pay: ')
        self.label2.grid(row=1, pady=5)

        self.amountBox = Entry(lf2, bd=2)
        self.amountBox.grid(row=1, column=1, pady=5, sticky='NSEW')

        # 手数料
        self.label3 = Label(lf2, text='Fee (Optional): ')
        self.label3.grid(row=2, pady=5)

        self.feeBox = Entry(lf2, bd=2)
        self.feeBox.grid(row=2, column=1, pady=5, sticky='NSEW')

        # レイアウト調整
        self.label4 = Label(lf2, text='')
        self.label4.grid(row=3, pady=5)

        # 送金実行ボタン
        self.sendBtn = Button(lf2, text='\nSend Coin(s)\n', command=self.sendCoins)
        self.sendBtn.grid(row=4, column=1, sticky='NSEW')

        # 画面下部ステータスバー
        stbar = Label(self.winfo_toplevel(), textvariable=self.status_message, bd=1, relief=SUNKEN, anchor=W)
        stbar.pack(side=BOTTOM, fill=X)

    def sendCoins(self):
        sendAtp = int(self.amountBox.get())
        recipientKey = self.recipient_pubkey.get()
        sendFee = int(self.feeBox.get())

        utxo_len = len(self.um.utxo_txs)

        if not sendAtp:
            messagebox.showwarning('Warning', 'Please enter the Amount to pay.')
        elif len(recipientKey) <= 1:
            messagebox.showwarning('Warning', 'Please enter the Recipient Address.')
        elif not sendFee:
            sendFee = 0
        else:
            result = messagebox.askyesno('Confirmation', 'Sending {} SimpleBitcoins to :\n {}'.format(sendAtp, recipientKey))

        if result:
            if utxo_len > 0:
                print('Sending {} SimpleBitcoins to reciever:\n {}'.format(sendAtp, recipientKey))
            else:
                messagebox.showwarning('Short of coin.', 'Not enough coin to be sent...')
                return

            utxo, idx = self.um.get_utxo_tx(0)

            t = Transaction(
                [TransactionInput(utxo, idx)],
                [TransactionOutput(recipientKey, sendAtp)]
            )

            counter = 1

            # TransactionInputが送金額に達するまでUTXOを収集しTransactionを完成させる
            while t.is_enough_inputs(sendFee) is not True:
                new_utxo, new_idx = self.um.get_utxo_tx(counter)
                t.inputs.append(TransactionInput(new_utxo, new_idx))
                counter += 1
                if counter > len(self.um.utxo_txs):
                    messagebox.showwarning('Short of Coinn.', 'Not enough coin to be sent...')
                    break

            if t.is_enough_inputs(sendFee) is True:
                # お釣り用Transactionを生成
                change = t.compute_change(sendFee)
                t.outputs.append(TransactionOutput(self.km.my_address(), change))

                to_be_signed = json.dumps(t.to_dict(), sort_keys=True)
                signed = self.km.compute_digital_signature(to_be_signed)
                new_tx = json.loads(to_be_signed)
                new_tx['signature'] = signed
                tx_strings = json.dumps(new_tx)
                self.c_core.send_message_to_my_core_node(MSG_NEW_TRANSACTION, tx_strings)
                print('signed new_tx: ', tx_strings)

                self.um.put_utxo_tx(t.to_dict())

                to_be_deleted = 0
                del_list = []
                while to_be_deleted < counter:
                    del_tx = self.um.get_utxo_tx(to_be_deleted)
                    del_list.append(del_tx)
                    to_be_deleted += 1

                for dx in del_list:
                    self.um.remove_utxo_tx(dx)

        self.amountBox.delete(0, END)
        self.feeBox.delete(0, END)
        self.recipient_pubkey.delete(0, END)
        self.update_balance()

    def engrave_message(self):
        """
        ブロックチェーンにTwitter風のメッセージを格納する
        """
        def send_e_message():
            new_message = {}
            msg_txt = entry.get().encode('utf-8')

            msg = EngravedTransaction(self.km.my_address(),
                                        'Testman',
                                        binascii.hexlify(base64.b64encode(msg_txt)).decode('ascii'))

            to_be_signed = json.dumps(msg.to_dict(), sort_keys=True)
            signed = self.km.compute_digital_signature(to_be_signed)
            new_tx = json.loads(to_be_signed)
            new_tx['signature'] = signed
            tx_strings = json.dumps(new_tx)
            self.c_core.send_message_to_my_core_node(MSG_NEW_TRANSACTION, tx_strings)

            new_tx2 = copy.deepcopy(new_tx)
            new_tx2['message_type'] = 'engraved'
            tx_strings2 = json.dumps(new_tx2)
            self.c_core.send_message_to_my_core_node(MSG_ENHANCED, tx_strings2)
            f.destroy()

        f = Tk()
        f.title('Engrave New Message')
        label0 = Label(f, text='Any idea?')
        frame1 = ttk.Frame(f)
        label = ttk.Label(frame1, text='Message:')
        entry = ttk.Entry(frame1, width=30)
        button1 = ttk.Button(frame1, text='Engrave this on Blockchain', command=send_e_message)

        label0.grid(row=0, column=0, sticky=(N,E,S,W))
        frame1.grid(row=1,column=0,sticky=(N,E,S,W))
        label.grid(row=2,column=0,sticky=E)
        entry.grid(row=2,column=1,sticky=W)
        button1.grid(row=3,column=1,sticky=W)

    def send_instant_message(self):
        def send_message():
            r_pkey = entry1.get()
            print('pubkey', r_pkey)
            new_message = {}
            aes_util = AESUtil()
            cipher_txt = aes_util.encrypt(entry2.get())
            new_message['message_type'] = 'cipher_message'
            new_message['recipient'] = r_pkey
            new_message['sender'] = self.km.my_address()
            new_message['body'] = binascii.hexlify(base64.b64encode(cipher_txt)).decode('ascii')

            key = aes_util.get_aes_key()
            encrypted_key = self.rsa_util.encrypt_with_pubkey(key, r_pkey)
            print('encrypted_key: ', encrypted_key[0])
            new_message['enc_key'] = binascii.hexlify(base64.b64encode(encrypted_key[0])).decode('ascii')
            msg_type = MSG_ENHANCED
            message_strings = json.dumps(new_message)
            self.c_core.send_message_to_my_core_node(msg_type, message_strings)
            f.destroy()

        f = Tk()
        f.title('New Message')
        label0 = Label(f, text='Please input recipient address and message')
        frame1 = ttk.Frame(f)
        label1 = ttk.Label(frame1, text='Recipient')
        pkey = StringVar()
        entry1 = ttk.Entry(frame1, textvariable=pkey)
        label2 = ttk.Label(frame1, text='Message: ')
        message = StringVar()
        entry2 = ttk.Entry(frame1, textvariable=message)
        button1 = ttk.Button(frame1, text='Send Message', command=send_message)

        label0.grid(row=0, column=0, sticky=(N,E,S,W))
        frame1.grid(row=1, column=0, sticky=(N,E,S,W))
        label1.grid(row=2, column=0, sticky=E)
        entry1.grid(row=2, column=1, sticky=W)
        label2.grid(row=3, column=0, sticky=E)
        entry2.grid(row=3, column=1, sticky=W)
        button1.grid(row=4, column=1, sticky=W)



def main(my_port, c_host, c_port):
    root = Tk()
    app = SimpleBC_Gui(root, my_port, c_host, c_port)
    root.mainloop()


if __name__ == '__main__':
    args = sys.argv

    if len(args) == 4:
        my_port = int(args[1])
        c_host = args[2]
        c_port = int(args[3])
    else:
        print('Param Error')
        print('$ wallet_app.py <my_port> <core_node_ip_address> <core_node_port_num>')
        quit()

    main(my_port, c_host, c_port)
    main()
