import re,random,os


# RNG
import secrets
def get_salt(length):
    # return random.randbytes(length)
    # return secrets.token_bytes(length)
    return os.urandom(length)

# compression
# pip install python-snappy
import snappy

if __name__ == '__main__':
    toc = b"jim"
    compressed = snappy.compress(toc)
    print('comp',len(toc),len(compressed),)
    print(snappy.uncompress(compressed))

    toc = toc * 20
    compressed = snappy.compress(toc)
    print('comp',len(toc),len(compressed), type(compressed))

# use compression only if gets smaller.
def compress(p):
    checksize(p)
    c = snappy.compress(p)
    return (c if len(c) < len(p) else p)

def checksize(ba):
    if len(ba) > 1024:
        raise Exception('input too large (we have to protect our servers)')

def decompress(c):
    checksize(c)
    try:
        dec = snappy.uncompress(c)
        if len(dec) > len(c):
            return dec
        else:
            return c
    except Exception as e:
        # print(e)
        return c

if __name__ == '__main__':
    def cd(b):
        cc = compress(b)
        p = decompress(cc)
        print(len(b), len(cc), len(p))
        print('equal:', 'yes' if p==b else 'no', f'ratio:{len(cc)/len(b):.3f}')

    cd(b'asdf')
    cd(b'asdf'*20)
    hard = bytes([i%256 for i in range(1000)])
    cd(hard)
    cd('中国'.encode('utf8'))
    cd('中国'.encode('utf8')*20)
    # cd('0'.encode('utf8')*20000000)
    # maximum compression ratio of snappy seems to be 0.047(a bit over 20x)
    # memory exhaustion seems not a problem

    tries = 10000
    succ = 0
    for i in range(tries):
        b = get_salt(8)
        try:
            p = snappy.decompress(b)
            succ+=1
        except Exception as e:
            pass
            # print(e)
            # print(b[0:20])
    print(f'{succ}/{tries} successed')


    tries = 1000
    succ = 0
    for i in range(tries):
        b = get_salt(32)
        if decompress(compress(b)) == b:
            succ+=1
        else:
            print(b)
    print(f'{succ}/{tries} successed')


# chinese characters ranked by frequency
# obtained from https://lingua.mtsu.edu/chinese-computing/statistics/char/list.php?Which=MO
from junda import forward, backward

# SinoBase1024
# represent every byte(0-255) with a number within 0-1023
def sb1024_encode(ba):
    checksize(ba)
    out  = []
    for b in ba:
        verted = b + random.randint(0,3) * 256
        out.append(forward[verted])
    return ''.join(out)

def sb1024_decode(ca):
    checksize(ca)
    out = []
    for c in ca:
        if sb1024_is_occupied(c):
            out.append(backward[c] % 256)
    return bytes(out)

# determine whether c is within the 1024 character set
def sb1024_is_occupied(c):
    return (c in backward) and (backward[c] < 1024)

def pf(*a):
    la = len(a)

    toprint = []
    if la>=2:
        g = a[0]
        toprint.append(g)
        for i in a[1:]:
            g = i(g)
            toprint.append(g)
    print(*toprint)

# encryption
# pip install cryptography
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305 as cc2p1

from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import ChaCha20 as cc2

def cc2p1_enc(key, plain, nonce):
    cipher = cc2p1(key)
    ct = cipher.encrypt(nonce=nonce, data=plain, associated_data=None)
    return ct

def cc2p1_dec(key, ct, nonce):
    cipher = cc2p1(key)
    plain = cipher.decrypt(nonce=nonce, data=ct, associated_data=None)
    return plain

# here we chose chacha20 WITHOUT authentication because:
# 1. authentication costs 16 bytes
# 2. no one can prove what your plaintext really is

def cc2_enc(key, plain, nonce):
    alg = cc2(key, nonce)
    cipher = Cipher(alg, mode=None)
    encryptor = cipher.encryptor()
    ct = encryptor.update(plain)
    return ct

def cc2_dec(key, ct, nonce):
    alg = cc2(key, nonce)
    cipher = Cipher(alg, mode=None)
    decryptor = cipher.decryptor()
    plain = decryptor.update(ct)
    return plain

if __name__ == '__main__':
    somekey = os.urandom(32)
    nonce = os.urandom(12)
    ct = cc2p1_enc(somekey, b'abcde', nonce)
    plain = cc2p1_dec(somekey, ct, nonce)
    print(plain)

    nonce = os.urandom(16)
    ct = cc2_enc(somekey, b'dorbie', nonce)
    plain = cc2_dec(somekey, ct, nonce)
    print(plain)


from functools import lru_cache

# conversion between unicode string and bytes

# always choose the shortest encoding. useful when
# input consists of many chinese characters.

def string_to_bytes(string):
    utf8 = string.encode('utf8')
    try:
        gbk = string.encode('gbk')
        ba = utf8 if len(utf8)<=len(gbk) else gbk
    except Exception as e:
        ba = utf8
    ba = compress(ba)
    return ba

def bytes_to_string(ba):
    # !!! DoS attack vector
    ba = decompress(ba)
    try:
        utf8 = ba.decode('utf8')
        return utf8
    except:
        return ba.decode('gbk')

if __name__ == '__main__':
    pf('ninja', string_to_bytes, bytes_to_string)
    pf('忍者', string_to_bytes, bytes_to_string)


# Key Derivation Function
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
SHA256 = hashes.SHA256()
H = hashes.Hash

def sha256_digest(k):
    digest = H(SHA256)
    digest.update(k)
    return digest.finalize()

# since this is not for password storage we derive our key with
# one pass of SHA256
def key_derive(keybytes, salt, length=32):
    # kdf = Scrypt(
    #     salt=salt,
    #     length=length,
    #     n=4,
    #     r=32,
    #     p=1,
    # )
    # derived_key = kdf.derive(keybytes)


    kdf = PBKDF2HMAC(
        algorithm=SHA256,
        length=length,
        salt=salt,
        iterations=1,
    )
    derived_key = kdf.derive(keybytes)

    # derived_key = sha256_digest(keybytes+salt)
    # while len(derived_key)<length:
    #     derived_key += sha256_digest(derived_key)

    # print(len(derived_key))
    return derived_key[:length]

if __name__ == '__main__':
    print(key_derive(string_to_bytes('mykey'), os.urandom(8)))

# length in bytes
len_salt = 4 # 32 bit security
len_nonce = 16
len_key = 32
# len_tag = 16

# lsfpt = len_salt_from_plain_table = (0,1,2,3,4)
# ltt = len_total_table = [i+idx for idx, i in enumerate(lsfpt)]
# lsfcd = len_salt_from_ct_dict = {}
# lsmfc = len_salt_max_from_ct = 0
# for idx, i in enumerate(ltt):
#     lsfcd[i] = i-idx
#     lsmfc = max(lsmfc, i-idx)
#
# if __name__ == '__main__':
#     print(lsfpt)
#     print(ltt)
#     print(lsfcd)
#     print(lsmfc)

# def get_len_salt_from_plain(plain):
#     pl = len(plain)
#     if pl>=len(lsfpt): return lsfpt[-1]
#     return lsfpt[pl]
#
# def get_len_salt_from_ct(ct):
#     cl = len(ct)
#     if cl>=ltt[-1]: return lsmfc
#     if (cl in lsfcd):
#         return lsfcd[cl]
#     else:
#         raise Exception(f'length of ciphertext({cl}) must be one of {ltt}')

# key: unicode string
# plaintext: unicode string
# ciphertext: unicode string of chinese characters

def sb1024_cc2_str_encrypt(keystring, plaintextstring, keybytes=None, plain=None):
    keybytes = keybytes or string_to_bytes(keystring)
    plain = plain or string_to_bytes(plaintextstring)
    # salt = get_salt(get_len_salt_from_plain(plain))
    salt = get_salt(len_salt)
    dk = derived_key = key_derive(
        keybytes, salt, length=len_key+len_nonce)

    ct = cc2_enc(key=dk[:len_key], plain=plain, nonce=dk[len_key:])
    # the entropy of nonce is limited by the length of salt
    # this is okay since this is mostly for fun rather than security
    return sb1024_encode(ct + salt)

def sb1024_cc2_str_decrypt(keystring, ciphertextstring):
    ct = sb1024_decode(ciphertextstring)
    keybytes = string_to_bytes(keystring)

    # len_salt = get_len_salt_from_ct(ct)

    salt = ct[-len_salt:]
    ct = ct[:-len_salt]

    dk = derived_key = key_derive(
        keybytes, salt, length=len_key+len_nonce)
    plain = cc2_dec(key=dk[:len_key], ct=ct, nonce=dk[len_key:])
    plaintextstring = bytes_to_string(plain)
    return plaintextstring

import re
def sb1024_cc2_encryption_collider(keystring, plaintextstring, target, attempts=99,limit=1):
    keybytes = string_to_bytes(keystring)
    plain = string_to_bytes(plaintextstring)

    target_regex = []
    for idx, char in enumerate(target):
        if sb1024_is_occupied(char):
            target_regex.append(char)
    target_regex = ''.join(target_regex)

    cr = re.compile(target_regex)
    lr = len(target_regex)

    collisions = []

    for i in range(attempts):
        ct = sb1024_cc2_str_encrypt(
            None, None, keybytes=keybytes, plain=plain
        )
        if i==0 and len(ct)<lr:
            return 'target longer than ciphertext'

        result = cr.search(ct)
        if result:
            collision = cr.sub(target, ct, count=1)
            assert sb1024_cc2_str_decrypt(keystring, collision) \
                == plaintextstring
            collisions.append(collision)
            if len(collisions)>=limit:
                return collisions

    return collisions or 'nothing found'

if __name__ == '__main__':
    for i in range(12):
        pl = '吼'*i
        ci = sb1024_cc2_str_encrypt('习明泽大战姚安娜',pl)
        print('ci', ci, pl)

    print('len of ci', len(ci))
    print(sb1024_cc2_str_decrypt('习明泽大战姚安娜', ci))
    # print(sb1024_cc2_str_decrypt('习明泽大战姚安娜', ci+'大'))
    print(sb1024_cc2_str_decrypt('习明泽大战姚安娜',ci+'繁'))

    res = sb1024_cc2_encryption_collider('习明泽大战姚安娜','吼'*30,'大撒币',999,limit=2221)

    print(len(res), res[0] if len(res) else '')
