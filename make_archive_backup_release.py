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
print('complete backup written to', basename)

if not args.upload:
    exit()

yay = '''
admins aliases avatars blacklist categories chat_channels chat_memberships
counters entities favorites followings poll_votes polls posts
tags threads translations users view_counters votes
'''

yay = re.findall(r'[a-z\_]+', yay)
print(yay)
yay = set(yay)

# exit()

nope = ('conversations histories messages logs passwords invitations exams answersheets operations notifications questions challenge_submissions punchcards'
.split(' '))
def accept(fn):
    if fn=='dump':
        return True

    # for obvious reasons
    sfn = '_'.join(fn.split('_')[:-1])[5:]
    # print(fn,sfn)
    # print(sfn)

    if sfn not in yay:
        print('x', fn)
        return False
    else:
        print('√', fn)
        return True
    # for k in nope:
    #     if k in fn:
    #         print('skip', fn)
    #         return False
    # print('accept', fn)
    # return True

tar = tarfile.open(basename_p,"w")
tar.add('dump', filter=lambda x: x if accept(x.name) else None)
tar.close()
print('partial backup written to', basename_p)


tok = open('release_token.txt','r').read().strip()
os.environ['GITHUB_TOKEN'] = tok

print('github token is', tok)

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
