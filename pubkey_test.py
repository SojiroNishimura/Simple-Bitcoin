import Crypto
import Crypto.Random
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256


def generate_rsa_key_pair():
    random_gen = Crypto.Random.new().read
    private_key = RSA.generate(2048, random_gen)
    public_key = private_key.publickey()

    return public_key, private_key


def main():
    test_txt = 'This is test message for getting understand about digital signature'
    pubkey, privkey = generate_rsa_key_pair()

    hashed = SHA256.new(test_txt.encode('utf8')).digest()
    print('hashed: ', hashed)

    encrypto = pubkey.encrypt(test_txt.encode('utf-8'), 0)
    print('encrypto: ', encrypto)

    decrypto = privkey.decrypt(encrypto)
    print('decrypto: ', decrypto)

    if test_txt == decrypto.decode('utf-8'):
        print('test_txt and decrypto are same!')

    enc_with_priv = privkey.encrypt(hashed, 0)[0]
    print('enc_with_priv: ', enc_with_priv)

    dec_with_pub = pubkey.decrypt(enc_with_priv)
    print('dec_with_pub: ', dec_with_pub)

    if hashed == dec_with_pub:
        print('hashed and dec_with_pub are same!')

if __name__ == '__main__':
    main()
