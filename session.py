# because flask session is a total disaster

from itsdangerous import Signer
import os,json,base64
from base64 import b64encode,b64decode

def get_secret():
    fn = 'secret.bin'
    if os.path.exists(fn):
        f = open(fn, 'rb');r = f.read();f.close()
    else:
        r = os.urandom(32)
        f = open(fn, 'wb');f.write(r);f.close()
    return r

secret = get_secret()
signer = Signer(secret)

def sign(s):
    return signer.sign(s.encode('utf-8'))

def unsign(s):
    try:
        u = signer.unsign(s)
        u = u.decode('utf-8')
    except Exception as e:
        return '{}'
    else:
        return u

# rough implementation of JSON Web Signature (JWS)
def signj(j):
    return signer.sign(
        b64encode(json.dumps(j).encode('utf-8'))
    )

def unsignj(s):
    try:
        r = json.loads(
            b64decode(signer.unsign(s.encode('utf-8'))).decode('utf-8')
        )
    except Exception as e:
        # print('unsignjerr', e)
        return {}
    else:
        return r

from flask import request, g

def save_session(resp):
    print('save_session', signj(g.session))
    resp.set_cookie(
        key='session',
        value=signj(g.session),
        max_age=86400*31,
        httponly=True,
        samesite='strict',
    )

def load_session():
    return unsignj(request.cookies.get('session', default={}))

if __name__ == '__main__':
    a = sign('helloworld')
    print(a)
    b = unsign(a)
    print(b)
    c = unsign(a+b'j')
    print(unsign(c))

    d = signj({1:2})
    e = unsignj(d)
    print(d)
    print(e)
