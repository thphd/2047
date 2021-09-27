import asyncio, socket
import functools
import random, time

afi = socket.AF_INET
rr = random.random

import logging
from colors import *
from commons_static import *
from aiorun import run

async def ever():
    while 1:
        yield 1

afut = asyncio.Future

good_upstreams = {}
bad_upstreams = {}

class UpStream:
    def __init__(self, h, p):
        self.h = h
        self.p = p

        self.s = f'{h}:{p}'
        self.lasthit = time.monotonic()

        self.accumulator = 0

        self.bad()

    def accumulate(self, t):
        self.accumulator = (self.accumulator + t) * 0.95

    def good(self):
        self.available = True
        self.lasthit = time.monotonic() + self.accumulator*.1

        ss = self.s
        good_upstreams[ss] = self
        if ss in bad_upstreams:
            del bad_upstreams[ss]

    def bad(self):
        self.available = False
        self.lasthit = time.monotonic() + self.accumulator*.1

        ss = self.s
        bad_upstreams[ss] = self
        if ss in good_upstreams:
            del good_upstreams[ss]

    async def update_availability(self):
        while 1:
            if self.available == False:

                k = await self.open()
                if k is None:
                    print_err(f'failed to reach upstream {self.s}')
                    continue

                print_info(f'upstream ok {self.s}')
                ur, uw = k
                await closew(uw)

            else:
                await asleep(0.2*rr())

    async def open(self):
        try:
            conn = await make_conn(self.h, self.p)

        except ConnectionRefusedError as e:
            print_err('CRE', e)
            self.bad()
            return None

        else:
            self.good()
            return conn

upstreams = [
    UpStream('127.0.0.1', 5000),
    UpStream('127.0.0.1', 5001),
    # UpStream('127.0.0.1', 5002),
    # UpStream('127.0.0.1', 5003),
]

def make_conn(h,p):
    return asyncio.open_connection(
        h, p, family=afi,
    )

async def update_statuses():
    await asyncio.gather(*(i.update_availability() for i in upstreams))

def get_one_upstream():

    lgu = list(good_upstreams.values())
    lgu.sort(key=lambda u:u.lasthit)
    lu = len(lgu)

    if lu:
        return lgu[0]

    lbu = list(bad_upstreams.values())
    lbu.sort(key=lambda u:u.lasthit)
    lu = len(lbu)

    if lu:
        return lbu[0]

    return None

q = []

async def put_conn_in_q():
    while 1:
        if len(q) >= 40:
            await asleep(0.05)
            continue

        upstream = get_one_upstream()

        if upstream is None:
            await asleep(0)
            continue

        conn = await upstream.open()

        if conn is None:
            continue

        q.append((upstream, conn))
        # print_info(f'-> q:{len(q)}')

def get_conn_from_q():
    # print_down(f'<- q:{len(q)}')
    while len(q):
        first = q.pop(0)
        upst, conn = first
        r,w = conn
        if r.at_eof() or w.is_closing():
            print_err(f'<- q:{len(q)} (drop closed conn)')
            continue
        else:
            return first

    return None

asleep = asyncio.sleep
async def stream(r, w):
    rateof = r.at_eof
    rread = r.read
    wdrain = w.drain
    wwrite = w.write

    nbytes = 0
    firstline = None

    while not rateof():
        data = await rread(800000)
        # qprint(f'{note} {len(data)} bytes')
        if data:

            wwrite(data)
            await wdrain()
            nbytes+=len(data)

            if firstline is None:
                idx = data.find(b'\r\n')
                if idx<100:
                    firstline = data[:idx].decode('utf-8')
                else:
                    firstline = '(toolong)'
                # qprint(f'{firstline}')

    await closew(w)
    # qprint(f'{note} {nbytes:8d}')
    return nbytes, firstline

conn_counter = 0

async def closew(dw):
    dw.write_eof()
    dw.close()
    await dw.wait_closed()

async def tcp_lb_server(nretries=10):
    async def client_conn_cb(dr, dw):
        global conn_counter
        conn_counter+=1

        try:
            ts = time.monotonic()

            addr = dw.get_extra_info('peername')
            ads = f'{addr[0]}:{addr[1]}'

            retry_counter = 0
            while True:
                retry_counter+=1
                if retry_counter > nretries:
                    print_err(f'#{conn_counter} exceeded max retries')

                    await closew(dw)
                    return False

                elif retry_counter>1:
                    print_up(f'#{conn_counter} attempt #{retry_counter}')
                    await asleep(0.01*1.5**retry_counter*rr())

                k = get_conn_from_q()

                if k is None:
                    print_err(f'#{conn_counter} attempt #{retry_counter} no upstream available')
                    continue

                upstream, conn = k
                ur, uw = conn

                break

            up = stream(dr, uw)
            down = stream(ur, dw)

            cc = colored_info(f'#{str(conn_counter)}')
            cc2 = (f'#{str(conn_counter)}')
            qprint(cc,
                f'{time_iso_now()} {ads} --> {upstream.h}:{upstream.p}',
                colored_up(f'{upstream.accumulator:.3f}'))


            (upb, ufl), (dnb, dfl) = await asyncio.gather(up, down)

            elap = time.monotonic() - ts

            qprint(cc2,
                colored_up(f'{upb:7d} sent'),
                colored_info(ufl),
                colored_down(f'{dnb:7d} rcvd'),
                colored_err(f'{int(elap*1000):5d} ms'),
                colored_info(dfl))

            upstream.accumulate(elap)

        except Exception as e:
            print_err('ccc',e)

    server = await asyncio.start_server(
        client_conn_cb,
        host=lhost,
        port=lport,
    )

    async with server:
        await server.serve_forever()

lhost, lport = '0.0.0.0', 5100

async def main():
    await asyncio.gather(
        update_statuses(),
        put_conn_in_q(),
        tcp_lb_server(),
    )

run(main(), stop_on_unhandled_errors=True)
