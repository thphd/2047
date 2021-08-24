import shutil, os, tarfile, argparse as ap
from commons import *

parser = ap.ArgumentParser()
parser.add_argument('-u','--upload', action='store_true')
args = parser.parse_args()


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

if not args.upload:
    exit()

nope = 'conversations histories messages logs passwords invitations exams answersheets operations notifications questions challenge_submissions'\
.split(' ')
def accept(fn):
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

while 1:
    while 1:
        try:
            gh_release_delete('thphd/2047','0.0.1')
        except Exception as e:
            print(e)
        else:
            break


    try:
        gh_release_create('thphd/2047', '0.0.1',
            publish=True,
            # name="database backup",
            asset_pattern=basename_p,
            prerelease=True,
            )

        os.remove(basename_p)

    except Exception as e:
        print(e)
        import time
        time.sleep(1)
    else:
        break
