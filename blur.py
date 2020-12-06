# let's randomize things a bit

import subprocess as sp

def get_ts_of(n):
    compro = sp.run(
            ("git show @{"
                +str(n)
                +"} --pretty='%cI' --no-patch --no-notes").split(' ')
            ,
            capture_output=True,
        )
    b = compro.stdout
    b = b.decode('ascii').strip().replace("'",'')
    return dfs(b)

from commons import *

t0 = get_ts_of(0)
t1 = get_ts_of(1)

print('last commit is at', t0)
print('last commit before is at', t1)

td = t0-t1

assert td > dttd(seconds=0)
totals = td.total_seconds()

print('delta is', totals)

import random

while 1:
    sec = random.randint(-totals, -(totals//2))

    print('add', sec, 'seconds')
    nt = t0 + dttd(seconds=sec)

    print('proposed time is', nt)

    if nt>t1:
        print('pass')
        break
    else:
        print('proposed time smaller than commit before, try again...')
        continue

# nt is proposed time
import os
os.environ['GIT_COMMITTER_DATE'] = str(nt)

command = f'''git commit --amend --no-edit --date "{str(nt).replace(' ','T')}"'''

print(command)

sp.run(command.split(' '))
