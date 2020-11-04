from commons import *

import os, re


bkup = './backup'
l = os.listdir(bkup)

import monkeypatch

l=l.filter(lambda s:s.endswith('.tar')).map(lambda s:(s, s.split('_')[-1][:-4]))

now = dtn()
print(now, now.year, now.month)

def pd(s):
    return datetime.datetime.strptime(s, '%Y%m%dT%H%M%S')


dategroups = {}

for fn, ts in l:

    t = pd(ts)
    def endg(date):
        if date not in dategroups:
            dategroups[date] = []
        dategroups[date].append((fn, ts))

    if now - t > dttd(days=2):
        # not recent
        endg(ts[:8]) # day

    if now - t > dttd(days=90):
        # not this month
        endg(ts[:6]) # month

for k in dategroups:
    print('group', k)

    l = dategroups[k]

    l = sorted(l,key=lambda k:k[1])
    # print(l)

    for j in l[1:-1]: # no head no tail
        ffn = bkup+'/'+j[0]
        print('about to delete', ffn)
        os.remove(ffn)
