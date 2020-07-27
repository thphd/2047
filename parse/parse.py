import sys,os
sys.path.append(os.path.abspath('..'))

# AQL
from aql import AQLController

aqlc = AQLController('http://127.0.0.1:8529', 'db2047',[
    'posts','postlets','userlets'
])
aql = aqlc.aql
aqlcl = aqlc.clear_collection

def listdir(dir):
    l = os.listdir(dir)
    return [dir+'/'+i for i in l]



def read(fn):
    with open(fn, 'r', encoding='utf8') as f:
        return f.read()

# yaml
from yaml import load as nload, load_all as nloadall, dump as ndump, dump_all as ndumpall
try:
    from yaml import CLoader as Loader, CDumper as Dumper
    print('has LibYAML support')
except ImportError:
    print('no LibYAML support')
    from yaml import Loader, Dumper

# from yaml import Loader, Dumper

def load(x): return nload(x, Loader=Loader)
def loadall(x): return nloadall(x, Loader=Loader)
def dump(x): return ndump(x, Dumper=Dumper)
def dumpall(x): return ndumpall(x, Dumper=Dumper)




def datetime2str(datetime):
    return datetime.isoformat(timespec='seconds')[:19]

def nodate(obj):
    def fd(k):
        if k in obj:
            obj[k] = datetime2str(obj[k])

    fd('addTime')
    fd('date')
    fd('regTime')

    if 'comments' in obj:
        for i in obj['comments']:
            nodate(i)
    return obj

# l0 = list(loadall(ml))[0]
# nodate(l0)
# print(l0)

if __name__ == '__main__':

    # 1. load all _posts into postlets

    if 1:

        # list all files under _posts
        l = listdir('./2049bbs.github.io/_posts')
        # print(l)

        # test first file
        ml = read(l[0])
        print(ml)


        # aql('for i in postlets remove i in postlets')
        aqlcl('postlets')

        # t = read('./2049bbs.github.io/_posts/2018-01-11-10.md')
        # open('debug.yaml','w', encoding='utf8').write(t)
        # open('shit.yaml','w',encoding='utf8').write(dumpall(['jaime\n@fasdfasfasfafadf','@$$dfasdf\nadsfasfasf']))

        for fn in l:
            yamlt = read(fn)
            print(fn)
            # print(yamlt) # commented for faster loading

            ly = yamlt.split('\n---\n\n')
            # length = len(ly)
            assert(len(ly)==2)

            # print(ly)

            # ly = list(loadall(yamlt))
            # ly = list(loadall(yamlt))

            parsed = load(ly[0])
            parsed['content'] = ly[1].strip()

            nodate(parsed)
            aql('insert @i into postlets', i=parsed, silent=True)

        # print()
        # print()

    # 2. load all _users into userlets

    if 1:
        l = listdir('./2049bbs.github.io/_users')

        ml = read(l[2])
        print(ml)
        aql('for i in userlets remove i in userlets')

        for fn in l:
            yamlt = read(fn)
            print(fn)
            # print(yamlt) # commented for faster loading

            ly = yamlt.split('\n---\n\n')
            # length = len(ly)
            assert(len(ly)==2)

            # print(ly)

            # ly = list(loadall(yamlt))
            # ly = list(loadall(yamlt))

            parsed = load(ly[0])
            parsed['brief'] = ly[1].strip()

            nodate(parsed)
            aql('insert @i into userlets', i=parsed, silent=True)

    # 3. categories

    if 1:
        l = listdir('./2049bbs.github.io/_category_info')

        ml = read(l[2])
        print(ml)

        aqlc.create_collection('catlets')
        aql('for i in catlets remove i in catlets')

        for fn in l:
            yamlt = read(fn)
            print(fn)
            # print(yamlt) # commented for faster loading

            ly = yamlt.split('\n---\n\n')
            # length = len(ly)
            assert(len(ly)==2)

            # print(ly)

            # ly = list(loadall(yamlt))
            # ly = list(loadall(yamlt))

            parsed = load(ly[0])
            parsed['brief'] = ly[1].strip()

            nodate(parsed)
            aql('insert @i into catlets', i=parsed, silent=True)
