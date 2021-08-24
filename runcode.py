from pytio import Tio, TioRequest, TioFile
import subprocess, sys, inspect

from cachetools.func import *
from commons_static import *

class CorrectedTioRequest(TioRequest):
    '''
    the author of pytio package did not fully test his code.
    full of bugs.
    '''

    def append_binary_file(self, name:str, content:bytes):
        self._bytes += b'F'+bytes(name, 'utf-8')+b'\x00'  \
            + str(len(content)).encode('utf-8') + b'\x00'  \
            + content + b'\x00'

@lru_cache(maxsize=128)
def run_python_code(code, stdin=b'', online=True):
    use_tio = online

    def sanitize(s): return s.replace(b'\r\n',b'\n')

    if use_tio:
        tio = Tio()
        request = CorrectedTioRequest(lang='python3', code=code)
        request.append_binary_file('.input.tio', stdin)

        print(f'sending tio request...({len(stdin)})')
        response = tio.send(request)
        print(f'got tio response')

        res = iif(isinstance(response._result, bytes),
            response._result, b'')

        err = iif(isinstance(response._error, bytes),
            response._error, b'')

    else:
        res = subprocess.run([sys.executable,
            '-Wignore','-I','-X', 'utf8', '-c', code],
            input=stdin,
            capture_output=True)

        err = res.stderr
        res = res.stdout

    return sanitize(res), sanitize(err)

if __name__ == '__main__':
    if 1:
        res, err = run_python_code(
            'a = int(input()); print(a,a*2)', b'33', online=False)
        k = res+err
        print(k.decode('utf-8')+'(eof)local', len(k))

        res, err = run_python_code(
            'a = int(input()); print(a,a*2)', b'33', online=True)
        k = res+err
        print(k.decode('utf-8')+'(eof)online', len(k))

def run_method_remotely(c, mname, args:tuple):
    import base64,pickle

    remote_code = '''
import base64,pickle,sys
packed = sys.stdin.buffer.read()
packed = base64.b64decode(packed)
c, mname, args = pickle.loads(packed)
print(c, mname, args)

res = c.__getattr__(mname)(*args)
res = base64.b64encode(pickle.dumps(res))
sys.stdout.buffer.write(res)
print(res)
'''

    pickled = base64.b64encode(pickle.dumps((c, mname, args)))
    print('input pickled', pickled)

    out, err = run_python_code(remote_code, stdin=pickled, online=False)

    print(out.decode('utf8'))
    print(err.decode('utf8'))

# run_method_remotely(k,'double',(3,))
