import cachetools, cachetools.func, time, threading, traceback
from flaskthreads import AppContextThread
from flaskthreads.thread_helpers import has_app_context, _app_ctx_stack, APP_CONTEXT_ERROR
from flask import g

import concurrent.futures
from concurrent.futures.thread import _threads_queues

def get_context(): return _app_ctx_stack.top if has_app_context() else None

class TPEMod(concurrent.futures.ThreadPoolExecutor):
    def submit(self, fn, *a, **kw):
        context = get_context()
        def fnwrapper(*aa, **akw):
            if context:
                with context:
                    return fn(*aa, **akw)
            else:
                return fn(*aa, **akw)

        res = super().submit(fnwrapper, *a, **kw)
        _threads_queues.clear() # hack to stop joining from preventing ctrl-c
        return res

tpe = TPEMod(max_workers=128)

class AppContextThreadMod(threading.Thread):
    """Implements Thread with flask AppContext."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_ctx = get_context()

    def run(self):
        if self.app_ctx:
            with self.app_ctx:
                super().run()
        else:
            super().run()

Thread = AppContextThreadMod

# hashkey = cachetools.keys.hashkey
tm = time.monotonic

empty = 0
idle = 1
dispatching = 2

import time, random
ts = time.sleep
rr = random.random

def tsr():ts(rr()*.1)

# buffer that refreshes in the bkgnd
class StaleBuffer:

    # f returns what we want to serve
    def __init__(self, f, ttr=5, ttl=10): # time to refresh / time to live
        self.a = None

        self.ts = tm()
        self.l = threading.Lock()
        self.state = empty

        self.f = f

        self.ttr = ttr
        self.ttl = ttl
        assert ttl>ttr

    def refresh_threaded(self):
        tsr()
        try:
            r = self.f()
        except Exception as e:
            traceback.print_exc()
            with self.l:
                self.state = idle
        else:
            with self.l:
                self.state = idle
                self.a = r
                self.ts = tm()

    def dispatch_refresh(self):
        tpe.submit(self.refresh_threaded)

        # t = Thread(target=self.refresh_threaded, daemon=True)
        # t.start()

    def get(self):
        # ttl = self.ttl
        # ttr = self.ttr
        # f = self.f

        # last = self.ts
        # now = tm()
        # past = now - last
        past = tm() - self.ts
        state = self.state


        # we couldn't afford expensive locking everytime, so
        if state==idle and past < self.ttr or state==dispatching:
            return self.a

        else:
            with self.l:
                # cache is empty
                if state == empty:
                    self.a = self.f()
                    self.ts = tm()
                    self.state = idle

                # cache is not empty, no dispatch on the way
                elif state == idle:
                    # is cache fresh?
                    if past > self.ttl:
                        # too old.
                        self.a = self.f()
                        self.ts = tm()

                    elif past > self.ttr:
                        # kinda old
                        self.state = dispatching
                        self.dispatch_refresh()

                    # # cache is fresh
                    # else:
                    #     pass

                # elif self.state == 'dispatching':
                #     pass
                # else:
                #     pass

                return self.a


if __name__ == '__main__':
    j = 1
    def k():
        global j
        j+=1
        time.sleep(1)
        return j

    sb = StaleBuffer(k, ttr=1, ttl=6)
    for i in range(10):
        print(sb.get(), sb.state)
        time.sleep(0.3)

    print('stalebuf test end')

def stale_cache(ttr=3, ttl=6, maxsize=128):
    def stale_cache_wrapper(f):

        @cachetools.func.lru_cache(maxsize=maxsize)
        def get_stale_buffer(*a, **kw):
            def sbw():
                return f(*a, **kw)

            sb = StaleBuffer(sbw, ttr=ttr, ttl=ttl)
            return sb

        def stale_cache_inner(*a, **kw):
            sb = get_stale_buffer(*a, **kw)
            return sb.get()

        return stale_cache_inner
    return stale_cache_wrapper

if __name__ == '__main__':

    def return3():
        return 31234019374194

    future = tpe.submit(return3)
    print(future.result())

    j = 1
    k = 1

    @stale_cache(ttr=1.5)
    def a(i):
        global j
        j+=1
        time.sleep(.5)
        return i*j

    @stale_cache(ttr=3)
    def b(n):
        global k
        k+=1
        time.sleep(.7)
        return k*n

    for i in range(20):
        print(a(3.5), b(6))
        time.sleep(0.4)
