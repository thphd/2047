import shutil, os, tarfile
from commons import *

dir = os.path.abspath('./dump/')

basename = '2047backup_'+time_iso_now().replace(':','').replace('-','')
basename_p = basename.replace('backup_', 'backup_publish_')

print('working on', dir)

# https://stackoverflow.com/a/38883728
tar = tarfile.open(basename+'.tar',"w")
tar.add('dump')
tar.close()

def accept(fn):
    nope = 'conversations histories messages logs passwords invitations'.split(' ')
    # for obvious reasons
    for k in nope:
        if k in fn:
            return False
    return True

tar = tarfile.open(basename_p+'.tar',"w")
tar.add('dump', filter=lambda x: x if accept(x.name) else None)
tar.close()
