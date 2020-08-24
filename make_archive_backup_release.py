import shutil, os, tarfile
from commons import *

dir = os.path.abspath('./dump/')

init_directory('./backup')

basename = 'backup/2047backup_'+time_iso_now().replace(':','').replace('-','')+'.tar'
basename_p = basename.replace('backup_', 'backup_publish_')

print('working on', dir)

# https://stackoverflow.com/a/38883728
tar = tarfile.open(basename,"w")
tar.add('dump')
tar.close()
print('written to', basename)

def accept(fn):
    nope = 'conversations histories messages logs passwords invitations'.split(' ')
    # for obvious reasons
    for k in nope:
        if k in fn:
            print('skip', fn)
            return False
    print('accept', fn)
    return True

tar = tarfile.open(basename_p,"w")
tar.add('dump', filter=lambda x: x if accept(x.name) else None)
tar.close()
print('written to', basename_p)

tok = open('release_token.txt','r').read().strip()
os.environ['GITHUB_TOKEN'] = tok

from github_release import *

try:
    gh_release_delete('thphd/2047','0.0.1')
except Exception as e:
    print(e)

gh_release_create('thphd/2047', '0.0.1',
    publish=True,
    # name="database backup",
    asset_pattern=basename_p,
    prerelease=True,
    )

os.remove(basename_p)
