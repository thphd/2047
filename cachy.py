import cachetools, cachetools.func, time, threading, traceback
from flaskthreads import AppContextThread
from flaskthreads.thread_helpers import has_app_context, _app_ctx_stack, APP_CONTEXT_ERROR
from flask import g

import concurrent.futures
from concurrent.futures.thread import _threads_queues

import functools

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

tpe = TPEMod(max_workers=256)

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
        # tsr()
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
        if state==idle and past < self.ttr:
            return self.a
        elif state==dispatching:
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


tmg = tm()
def update_tmg():
    global tmg
    while 1:
        tmg = tm()
        time.sleep(0.2)
tpe.submit(update_tmg)

def StaleBufferFunctional(f, ttr=10, ttl=1800):
    global tmg

    a = None
    tspttr = 0
    tspttl = 0

    l = threading.Lock()
    state = empty

    def update_t():
        nonlocal tspttl,tspttr
        tspttr = tmg+ttr
        tspttl = tmg+ttl

    def refresh_threaded():
        nonlocal a,state
        # tsr()
        try:
            res = f()
        except Exception as e:
            traceback.print_exc()
            with l:
                state = idle
        else:
            with l:
                state = idle
                a = res
                update_t()

    def dispatch_refresh():
        tpe.submit(refresh_threaded)

    def get():
        nonlocal a,state,tspttl,tspttr

        # past = tm() - ts

        # we couldn't afford expensive locking everytime, so
        if state==idle and tmg < tspttr:
            # return a
            pass

        elif state==dispatching:
            # return a
            pass
        else:
            with l:
                # cache is empty
                if state == empty:
                    a = f()
                    update_t()
                    state = idle

                # cache is not empty, no dispatch on the way
                elif state == idle:

                    # is cache fresh?
                    if tmg > tspttl:
                        # too old.
                        a = f()
                        update_t()

                    elif tmg > tspttr:
                        # kinda old
                        state = dispatching
                        dispatch_refresh()

                    # # cache is fresh
                    # else:
                    #     pass

                # elif self.state == 'dispatching':
                #     pass
                # else:
                #     pass

        return a
    return get


if 1 and __name__ == '__main__':
    from commons_static import timethis

    def by33():return random.random()+random.random()*111
    sb = StaleBuffer(by33, 15, 1000)

    sbf = StaleBufferFunctional(by33)

    timethis('$by33()')
    timethis('$sb.get()')
    timethis('$sbf()')


if 0 and __name__ == '__main__':
    def kg():
        j = 1
        def k():
            nonlocal j
            j+=1
            time.sleep(1)
            return j
        return k

    sb = StaleBuffer(kg(), ttr=1, ttl=6)
    sbf = StaleBufferFunctional(kg(), ttr=1, ttl=6)
    for i in range(10):
        print('old',sb.get(), sb.state)
        print('new',sbf())
        time.sleep(0.3)

    print('stalebuf test end')

def stale_cache_old(ttr=3, ttl=6, maxsize=128):
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

def stale_cache(ttr=3, ttl=6, maxsize=128):
    def stale_cache_wrapped(f):

        @functools.lru_cache(maxsize=maxsize)
        def get_stale_buffer(*a, **kw):
            return StaleBufferFunctional(
                lambda:f(*a, **kw),
                ttr=ttr,
                ttl=ttl,
            )

        def stale_cache_inner(*a, **kw):
            return get_stale_buffer(*a, **kw)()

        return stale_cache_inner

    return stale_cache_wrapped

if 1 and __name__ == '__main__':
    from commons_static import timethis

    print('00000'*5)

    @stale_cache_old()
    def by33():return random.random()+random.random()*111

    @stale_cache()
    def by34():return random.random()+random.random()*111

    timethis('$by33()')
    timethis('$by34()')

if 0 and __name__ == '__main__':

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
    @stale_cache2(ttr=1.5)
    def a2(i):
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
    @stale_cache2(ttr=3)
    def b2(n):
        global k
        k+=1
        time.sleep(.7)
        return k*n

    for i in range(20):
        print('old',a(3.5), b(6))
        print('new',a2(3.5), b2(6))
        time.sleep(0.4)
