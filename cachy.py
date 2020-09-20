import cachetools, cachetools.func, time, threading, traceback

hashkey = cachetools.keys.hashkey
tm = time.monotonic

Lock = threading.Lock

# buffer that refreshes in the bkgnd
class StaleBuffer:
    # f returns what we want to serve
    def __init__(self, f, ttr=5, ttl=10): # time to refresh / time to live
        self.a = None

        self.ts = tm()
        self.l = Lock()
        self.state = 'empty'

        self.f = f

        self.ttr = ttr
        self.ttl = ttl
        assert ttl>ttr

    def dispatch_refresh(self):
        def wrapper():
            try:
                r = self.f()
            except Exception as e:
                traceback.print_exc()
            else:
                self.l.acquire()
                self.state = 'nodispatch'
                self.a = r
                self.ts = tm()
                self.l.release()

        t = threading.Thread(target=wrapper, daemon=True)
        t.start()

    def get(self):
        ttl = self.ttl
        ttr = self.ttr
        f = self.f
        now = tm()

        # we couldn't afford expensive locking everytime, so
        if self.state=='nodispatch' and now - self.ts < ttr:
            return self.a

        self.l.acquire()

        try:
            # cache is empty
            if self.state == 'empty':
                self.a = f()
                self.ts = now
                self.state = 'nodispatch'

            # cache is not empty, no dispatch on the way
            elif self.state == 'nodispatch':
                # is fresh?
                now = now
                if now - self.ts>ttl:
                    # too old.
                    self.a = f()
                    self.ts = now

                elif now - self.ts>ttr:
                    # kinda old
                    self.dispatch_refresh()
                    self.state = 'dispatching'
                    # use the stale version

                else:
                    # data is fresh
                    pass

            # cache is not empty, dispatch on the way
            elif self.state == 'dispatching':
                # return the stale version until dispatch finishes
                pass

        except Exception as e:
            self.l.release()
            raise e
        else:
            r = self.a
            self.l.release()
        return r

if __name__ == '__main__':
    j = 1
    def k():
        global j
        j+=1
        time.sleep(2)
        return j

    sb = StaleBuffer(k, ttr=3, ttl=6)
    for i in range(20):
        print(sb.get(), sb.state)
        time.sleep(0.5)

def stale_cache(ttr=3, ttl=6, maxsize=128):
    def wrapper(f):

        @cachetools.func.lru_cache(maxsize=maxsize)
        def get_stale_buffer(*a, **kw):
            def sbw():
                return f(*a, **kw)

            sb = StaleBuffer(sbw, ttr=ttr, ttl=ttl)
            return sb

        def inner(*a, **kw):
            sb = get_stale_buffer(*a, **kw)
            return sb.get()

        return inner
    return wrapper

if __name__ == '__main__':

    j = 1
    k = 1

    @stale_cache()
    def a(i):
        global j
        j+=1
        time.sleep(1)
        return i*j

    @stale_cache()
    def b(n):
        global k
        k+=1
        time.sleep(1.5)
        return k*n

    for i in range(20):
        print(a(3.5), b(6))
        time.sleep(0.4)
