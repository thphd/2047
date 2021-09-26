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

        self.bad()

    def good(self):
        self.available = True
        ss = self.s
        good_upstreams[ss] = self
        if ss in bad_upstreams:
            del bad_upstreams[ss]

    def bad(self):
        self.available = False
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
            self.lasthit = time.monotonic()
            self.bad()
            return None

        else:
            self.lasthit = time.monotonic()
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
            continue
        else:
            return first

    return None

asleep = asyncio.sleep
async def stream(r, w, note=''):
    rateof = r.at_eof
    rread = r.read
    wdrain = w.drain
    wwrite = w.write

    nbytes = 0

    while not rateof():
        data = await rread(800000)
        # qprint(f'{note} {len(data)} bytes')
        if data:
            wwrite(data)
            await wdrain()
            nbytes+=len(data)

    await closew(w)
    qprint(f'{note} {nbytes:8d}')

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


            qprint(f'{time_iso_now()} #{colored_info(str(conn_counter))} {ads} --> {upstream.h}:{upstream.p}')

            up = stream(dr, uw, colored_up(f'#{conn_counter} >>'))
            down = stream(ur, dw, colored_down(f'#{conn_counter} <<'))

            await asyncio.gather(up, down)

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
