import sys, time, os, re
sys.path.append('../')

def ensure_filelist(p):
    try:
        files = os.listdir(p)
        files = [p +'/'+ f for f in files]
    except NotADirectoryError as e:
        files = [p]
    return files

def filesize(f):
    if not os.path.exists(f): return 0
    fl = ensure_filelist(f)
    tot = 0
    for i in fl:
        tot += os.path.getsize(i)
    return tot

# import monkeypatch
# from commons import *

import sqlite3

class Weibo:
    def get_root(self):
        from root_path import root_path, dest_path, dest_path_universal
        return root_path, dest_path_universal
        # return root_path, dest_path

    def init_sqlite(self):
        print('fullpath is', self.fullpath)
        print('trying to connect to', self.dbpath)
        self.conn = sqlite3.connect(self.dbpath, check_same_thread=False)
        self.q('PRAGMA synchronous = OFF')
        self.q('PRAGMA journal_mode = MEMORY')
        self.q('PRAGMA cache_size = 1000000')

    def set_paths(self):
        self.path = '微博五亿2019.txt'
        self.name = 'weibo_500m'
        self.abbr = 'weibo'

        self.attrs = 'mobile,uid'.split(',')
        self.idxes = 'mobile,uid'.split(',')

    def __init__(self):
        root, dest = self.get_root()
        self.set_paths()
        self.fullpath = root + self.path
        self.dbpath = dest + self.name + '.db'

        self.origsize = filesize(self.fullpath)
        self.dbsize = filesize(self.dbpath)

        if self.dbsize<50000 and self.dbsize!=0:
            print('delete', self.dbpath)
            os.remove(self.dbpath)

        self.init_sqlite()

    def q(self, *a, **k):
        c = self.conn.cursor()
        c.execute(*a, **k)
        return c.fetchall()

    def qmany(self, *a, **k):
        c = self.conn.cursor()
        c.executemany(*a, **k)
        return c.fetchall()

    def commit(self):
        return self.conn.commit()

    def test(self):
        all = self.q(f'select * from {self.name} limit 10')
        print(all)
        return all

    def init_table(self):
        self.q(f'create table {self.name} (mobile integer, uid integer)')

    def create_index(self):
        def ci(name):
            self.q(f'''create index if not exists {name}_index on {self.name} ({name})''')

        [ci(k) for k in self.idxes]

    def parse(self):
        flushevery = 100000

        dl = []
        def flush():
            nonlocal dl
            print('got', len(dl))
            self.qmany(f'insert into {self.name} values (?,?)', dl)
            self.commit()

            dl = []

        with open(self.fullpath, 'r', encoding='utf-8') as f:

            count = 0
            while 1:
                k = f.readline()
                if k=='':
                    break

                k = k.split('\t')

                if len(k)!=2:
                    print(k)
                    continue

                mobile = k[0].strip()
                uid = k[1].strip()

                if len(mobile)<11:
                    print(mobile, uid)
                    continue

                # print(mobile, uid)

                try:
                    tpl = (int(mobile), int(uid))
                except Exception as e:
                    print(e)
                    print(k)
                else:
                    dl.append(tpl)

                # count+=1

                if len(dl)>=flushevery:
                    count+=len(dl)
                    flush()
                    print('count:', count)

            flush()

    def get_variants(self,s):
        if not isinstance(s, str):
            vs = [s]
            # int
            if s > 100_0000_0000 and s < 200_0000_0000:
                vs.append(s+86_000_0000_0000)
        else:
            if len(s)<7: return [s]
            vs = [s]
            if s[0]=='0': vs.append(s[1:])
            if s[0:2]=='00': vs.append(s[2:])
            vs.append('0'+s)
            vs.append('86'+s)

        return vs

    def auto_bracketed_search(self, num, propnames):
        res = []

        variants = self.get_variants(num)

        for v in variants:
            for n in propnames:
                res += self.q(f'''select * from {self.name}
                where {n}=?1 limit 30''', (v,))

        if not len(res): # if no hit in previous searches
            for n in propnames:
                res += self.q(
                    f'select * from {self.name} where {n}>=?1 order by {n} asc limit 1', (num,))
                res += self.q(
                    f'select * from {self.name} where {n}<=?1 order by {n} desc limit 1', (num,))
        return res

    def resultgen(self, q, l, name_map):
        name_map = [self.abbr+"_"+k for k in name_map]

        d = {}
        d['maxscore'] = 0
        for n, v in zip(name_map, l):
            d[n] = v
            variants = self.get_variants(q)
            if v in variants:
                d['hit'] = n
                d['maxscore'] = 1
            else:
                score = mssim(v, q)
                d['maxscore'] = max(d['maxscore'], score)

        d['source'] = self.path
        return d

    def find(self, num):
        try:
            num = int(num)
        except:
            return []

        res = self.auto_bracketed_search(num, self.idxes)
        return [self.resultgen(num, item, self.attrs) for item in res]

class Hotel2013(Weibo):
    def set_paths(self):
        self.path = '2000W开房-2013'
        self.name = 'hotel2013'
        self.abbr = 'hotel13'

        self.attrs = 'name,sfz,mobile,email,addr'.split(',')
        self.idxes = 'name,mobile,email'.split(',')

    def init_table(self):
        self.q(f'create table {self.name} ('+
        ','.join([i+' text' for i in self.attrs])
        +')')

    def create_index(self):
        def ci(name):
            self.q(f'''create index if not exists {name}_index on {self.name} ({name})''')

        [ci(k) for k in self.idxes]

    def find(self, num):
        res = self.auto_bracketed_search(num, self.idxes)
        name_map = self.attrs
        return [self.resultgen(num, item, name_map) for item in res]


    def parse(self):

        flushevery = 100000
        count = 0

        dl = []
        def flush():
            nonlocal dl
            print('got', len(dl))
            self.qmany(f'insert into {self.name} values (?,?,?,?,?)', dl)
            self.commit()
            dl = []

        def eat(tpl):
            nonlocal count

            dl.append(tpl)

            if len(dl)>=flushevery:
                count+=len(dl)
                flush()
                print(tpl)
                print('count:', count)


        files = ensure_filelist(self.fullpath)
        print(files)
        # exit()

        for path in files:
            import csv
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                # reader = csv.reader(f, )

                print('opened', path)

                colnames = []
                colidx = {}

                import re
                fcount = 0
                while 1:
                    k = f.readline()
                    if k=='':
                        break

                    cols = k.split(',')

                    if len(cols)<33:
                        if len(cols)<3:
                            print('shortcol', cols)
                            continue
                        else:
                            nc = f.readline().split(',')

                            if len(nc)<3:
                                print('shortcol(nc)', nc)
                                continue
                            else:

                                cols[-1] = cols[-1].strip()+ nc[0].strip()
                                cols += nc[1:]

                                if len(cols)!=33:
                                    print('failed',count, fcount, cols)
                                    continue
                                else:
                                    print('joined', cols)

                    cols = [c.strip().lower().replace(' ','') for c in cols]

                    if fcount==0:
                        colnames = cols
                        for idx, i in enumerate(colnames):
                            colidx[i] = idx
                        colidx['name']=0

                        print(colidx)
                        fcount+=1
                        continue

                    # print(len(cols))
                    assert len(cols) >= len(colnames)


                    def ob(s): return cols[colidx[s]]

                    name = ob('name')
                    sfz = ob('ctfid')
                    addr = ob('address')
                    mobile = ob('mobile')
                    tel = ob('tel')
                    email = ob('email')

                    mobile = mobile if len(mobile) > len(tel) else tel

                    # print(name, sfz, mobile, email, addr)
                    eat((name,sfz,mobile,email,addr))
                    fcount+=1

        flush()

def ssim(s1, s2):
    tot = max(len(s1), len(s2))
    score = 0
    for i in range(min(len(s1), len(s2))):
        if s1[i] == s2[i]:
            score+=1
    if tot==0: return 0
    return score/tot

def mssim(s1, s2):
    s1, s2 = str(s1), str(s2)
    if min(len(s1), len(s2))<1:
        return 0

    return max(
        ssim(s1, s2),
        ssim(s1[1:], s2),
        ssim(s1[2:], s2),
        ssim(s1, s2[1:]),
        ssim(s1, s2[2:]),
    )

class QQ(Weibo):
    def set_paths(self):
        self.path = '6.9更新总库(qq).txt'
        self.name = 'qqleak'
        self.abbr = 'qq'

        self.attrs = 'mobile,uid'.split(',')
        self.idxes = 'mobile,uid'.split(',')

    def parse(self):
        flushevery = 100000

        dl = []
        def flush():
            nonlocal dl
            print('got', len(dl))
            self.qmany(f'insert into {self.name} values (?,?)', dl)
            self.commit()

            dl = []

        with open(self.fullpath, 'r', encoding='utf-8') as f:
            count = 0

            def eat(k):
                nonlocal count
                if len(k[0])>20 or len(k[1])> 20:
                    print('toolong')
                    return

                try:
                    tpl = (int(k[1].strip()), int(k[0].strip()))
                except Exception as e:
                    print(e)
                    print(k)
                    return

                # tpl = (tpl[1], tpl[0])
                dl.append(tpl)

                if len(dl)>=flushevery:
                    count+=len(dl)
                    flush()
                    print(tpl)
                    print('count:', count)

            while 1:
                k = f.readline()
                if k=='':
                    break

                # k = k.decode('ascii')
                k = k.split('----')

                if len(k)!=2:
                    if len(k)==3:
                        if k[0]==k[1]:
                            j = (k[1], k[2])
                            eat(j)
                        else:
                            j = (k[1], k[2])
                            eat(j)
                            j = (k[0], k[2])
                            eat(j)
                    else:
                        s = repr(k)
                        if len(s)<100:
                            print(s)
                        else:
                            print(len(s))
                        # print(k)
                        continue
                else:
                    eat(k)

            flush()

    def find(self, num):
        try:
            num = int(num)
        except:
            return []
        res = self.auto_bracketed_search(num, self.idxes)
        return [self.resultgen(num, item, self.attrs) for item in res]

class Momo2015(Weibo):
    def set_paths(self):
        self.path = '3100W--陌陌-高.txt'
        self.name = 'momo2015'
        self.abbr = 'momo15'

        self.attrs = 'f1,f2_pw'.split(',')
        self.idxes = 'f1,f2_pw'.split(',')

    def init_table(self):
        self.q(f'create table {self.name} ('+
        ','.join([i+' text' for i in self.attrs])
        +')')

        self.q(f'create table {self.name}_t ('+
        ','.join([i+' text' for i in self.attrs])
        +')')

    def find(self, num):
        res = self.auto_bracketed_search(num, self.idxes)
        return [self.resultgen(num, item, self.attrs) for item in res]

    def parse(self):
        flushevery = 100000

        dl = []
        def flush():
            nonlocal dl
            print('got', len(dl))
            self.qmany(f'insert into {self.name}_t values (?,?)', dl)
            self.commit()

            dl = []

        with open(self.fullpath, 'r', encoding='utf-8', errors='ignore') as f:
            count = 0

            def eat(k):
                nonlocal count
                if len(k[0])>40 or len(k[1])> 40:
                    print('toolong', k )
                    return

                # tpl = (tpl[1], tpl[0])
                tpl = tuple((i.strip() for i in k))
                dl.append(tpl)

                if len(dl)>=flushevery:
                    count+=len(dl)
                    flush()
                    print(tpl)
                    print('count:', count)

            while 1:
                k = f.readline()
                if k=='':
                    break

                # k = k.decode('ascii')
                # print('rawline', k)
                k = k.split('----')

                if len(k)<2:
                    print('knot2', k)
                    continue

                if len(k)>2:
                    k = (k[0],'----'.join(k[1:]))

                eat(k)

            flush()

        self.q(f'insert into {self.name} select distinct * from {self.name}_t')
        self.q(f'drop table {self.name}_t')
        self.commit()

class SF(Weibo):
    def set_paths(self):
        self.path = '1/shunfeng_script.sql'
        self.name = 'sfleak'
        self.abbr = 'sf'

    def init_table(self):
        self.q(f'create table {self.name} (mobile text, name text, addr text)')

    def create_index(self):
        self.q(f'''create index if not exists mobile_index on {self.name} (mobile)''')
        self.q(f'''create index if not exists name_index on {self.name} (name)''')

    def parse(self):
        flushevery = 100000

        dl = []
        def flush():
            nonlocal dl
            print('got', len(dl))
            self.qmany(f'insert into {self.name} values (?,?,?)', dl)
            self.commit()

            dl = []

        with open(self.fullpath, 'r', encoding='utf-16') as f:
            count = 0
            countlines = 0
            while 1:
                k = f.readline()
                if len(k)<1:
                    break

                k = k.strip()

                countlines+=1

                # print(k)

                g = re.search(r'\(N\'(.*?)\', N\'(.*?)\', N\'(.*?)\', N\'(.*?)\', N\'(.*?)\', N\'(.*?)\'\)', k)
                # print(g)
                if not g: continue
                # print(g[1], g[2], g[6])
                if not len(g[2]): continue

                try:
                    phone = g[2].strip()
                except Exception as e:
                    print(e)
                    # continue
                    # phone = -1
                    phone = ''

                addr = g[6].strip().replace(r"\'","'")
                # if '，暂不显示' in addr:

                # addr = addr.encode('utf-16')

                name = g[1].strip()

                if not(
                    (name and addr) or (name and phone) or (phone and addr)
                ): continue


                tpl = (name, phone, addr)
                # print(tpl)

                dl.append(tpl)

                # if count==3560: break

                if len(dl)>=flushevery:
                    count+=len(dl)
                    flush()
                    print(tpl)
                    print('count:', count, 'lines:', countlines)

            flush()

    def find(self, num):
        res = self.auto_bracketed_search(num, ['mobile', 'name'])
        name_map = 'name,mobile,addr'.split(',')
        return [self.resultgen(num, item, name_map) for item in res]

class JD(Weibo):
    def find(self, num):
        res = self.auto_bracketed_search(num, ['mobile', 'name','username','email','mobile2'])
        name_map = 'name,username,email,sfz,mobile,mobile2'.split(',')
        return [self.resultgen(num, item, name_map) for item in res]

    def set_paths(self):
        self.path = '1/www_jd_com_12g.txt'
        self.name = 'jdleak'
        self.abbr = 'jd'

    def init_table(self):
        self.q(f'create table {self.name} (name text, username text, email text, sfz text, mobile text, mobile2 text)')

    def create_index(self):
        def ci(name):
            self.q(f'''create index if not exists {name}_index on {self.name} ({name})''')

        [ci(k) for k in 'name,username,email,mobile,mobile2'.split(',')]

    def parse(self):
        flushevery = 100000

        dl = []
        def flush():
            nonlocal dl
            print('got', len(dl))
            self.qmany(f'insert into {self.name} values (?,?,?,?,?,?)', dl)
            self.commit()

            dl = []

        with open(self.fullpath, 'r', encoding='utf-8') as f:
            count = 0
            countlines = 0
            while 1:
                k = f.readline()
                if len(k)<1:
                    break

                k = k.strip()

                countlines+=1

                # print(k)

                g = re.search(r'(.*?)---(.*?)---(.*?)---(.*?)---(.*?)---(.*?)---(.*?)$', k)
                # print(g)
                if not g: continue
                # print(g[1], g[2], g[6])

                name, username, email, sfz, mobile, mobile2 =\
                    g[1], g[2], g[4], g[5], g[6], g[7]


                tpl = (name, username, email, sfz, mobile, mobile2)
                tpl = tuple(( k.strip().lower().replace('\\n', '') for k in tpl))
                # print(tpl)

                dl.append(tpl)

                # if count==3560: break

                if len(dl)>=flushevery:
                    count+=len(dl)
                    flush()
                    print(tpl)
                    print('count:', count, 'lines:', countlines)

            flush()

class Pingan(Weibo):

    def find(self, num):
        res = self.auto_bracketed_search(num, ['mobile', 'name', 'email'])
        name_map = 'name,sfz,mobile,email'.split(',')
        return [self.resultgen(num, item, name_map) for item in res]

    def set_paths(self):
        self.path = '1/平安保险2020年-10w.csv'
        self.name = 'pinganleak'
        self.abbr = 'pingan'

    def init_table(self):
        self.q(f'create table {self.name} \
        (name text, sfz text, mobile text, email text)')

    def create_index(self):
        def ci(name):
            self.q(f'''create index if not exists {name}_index on {self.name} ({name})''')

        [ci(k) for k in 'name,email,mobile'.split(',')]

    def parse(self):
        flushevery = 100000

        dl = []
        def flush():
            nonlocal dl
            print('got', len(dl))
            self.qmany(f'insert into {self.name} values (?,?,?,?)', dl)
            self.commit()

            dl = []

        # with open(self.fullpath, 'r', encoding='utf-8') as f:
        with open(self.fullpath, 'rb') as f:
            count = 0
            countlines = 0
            while 1:
                k = f.readline()

                if len(k)<1:
                    break

                k = k.decode('gb2312', errors='ignore')
                k = k.strip()

                countlines+=1

                cols = k.split(',')
                assert len(cols)==16

                c = cols

                name, sfz, mobile, email = c[3], c[4], c[6], c[7]
                # print(cols[3])

                tpl = (name.strip(), sfz.strip(), mobile.strip(), email.lower().strip())
                # print(tpl)

                dl.append(tpl)

                # if count==3560: break

                if len(dl)>=flushevery:
                    count+=len(dl)
                    flush()
                    print(tpl)
                    print('count:', count, 'lines:', countlines)

            flush()

class Telegram40(Weibo):
    def set_paths(self):
        self.path = 'telegram_40M.txt'
        self.name = 'telegram40M'
        self.abbr = 'tg40m'

        self.idxes = self.attrs = 'mobile,uid'.split(',')

    def parse(self):
        flushevery = 100000

        dl = []
        def flush():
            nonlocal dl
            print('got', len(dl))
            self.qmany(f'insert into {self.name} values (?,?)', dl)
            self.commit()

            dl = []

        # with open(self.fullpath, 'r', encoding='utf-8') as f:
        with open(self.fullpath, 'rb') as f:
            count = 0
            countlines = 0
            while 1:
                k = f.readline()

                if len(k)<1:
                    break

                k = k.decode('utf-8', errors='ignore')
                k = k.strip()

                countlines+=1

                cols = k.split('|')
                # print(len(cols))
                assert len(cols)>=9

                c = cols

                def p(ix=4):
                    return cols[ix], cols[ix+1]
                mobile, uid =tpl= p(4)
                # print(cols[3])

                success = False
                for i in range(30):
                    try:
                        mobile, uid =tpl= p(4+i)
                        tpl = tuple((int(i.lower().strip()) for i in tpl))
                    # print(tpl)
                    except Exception as e:
                        # print(e)
                        continue
                    else:
                        success=True
                        break

                if success==False:
                    print('gave up on', k)
                    continue

                dl.append(tpl)

                # if count==3560: break

                if len(dl)>=flushevery:
                    count+=len(dl)
                    flush()
                    print(tpl)
                    print('count:', count, 'lines:', countlines)

            flush()


class CarOwner20(Pingan):
    def set_paths(self):
        self.path = '1/全国车主76万2020年.csv'
        self.name = 'co20leak'
        self.abbr = 'co20'

    def init_table(self):
        self.q(f'create table {self.name} \
        (name text, sfz text, mobile text, email text, addr text)')

    def parse(self):
        flushevery = 10000

        dl = []
        def flush():
            nonlocal dl
            print('got', len(dl))
            self.qmany(f'insert into {self.name} values (?,?,?,?,?)', dl)
            self.commit()

            dl = []

        # with open(self.fullpath, 'r', encoding='utf-8') as f:
        with open(self.fullpath, 'rb') as f:
            count = 0
            countlines = 0
            while 1:
                k = f.readline()

                if len(k)<1:
                    break

                k = k.decode('gb2312', errors='ignore')
                k = k.strip()

                countlines+=1

                cols = k.split(',')
                assert len(cols)==22

                c = cols

                name, sfz, mobile, email, addr = tpl = c[1], c[2], c[4], c[5], c[8]
                # print(cols[3])

                tpl = tuple((i.lower().strip() for i in tpl))
                # print(tpl)

                dl.append(tpl)

                # if count==3560: break

                if len(dl)>=flushevery:
                    count+=len(dl)
                    flush()
                    print(tpl)
                    print('count:', count, 'lines:', countlines)

            flush()

def emp(k):
    if filesize(k.dbpath)>10000:
        print(k.dbpath, 'exists, skip..')
        return

    k.init_table()
    k.parse()
    k.test()
    k.create_index()
    k.test()

if __name__ == '__main__':
    weibo = Weibo()
    emp(weibo)

    print(weibo.find('15890981333'))
    print(weibo.find('3798002017'))

    qq = QQ()
    emp(qq)

    print(qq.find('13550121037'))

    sf = SF()
    emp(sf)

    print(sf.find('黄小姐'))
    print(sf.find('13662168290'))

    jd = JD()
    emp(jd)

    print(jd.find('刘庆宁'))
    print(jd.find('OGVTK28'))
    print(jd.find('13165993135'))

    pingan = Pingan()
    emp(pingan)

    print(pingan.find('陈希'))
    print(pingan.find('13079804169'))

    co20 = CarOwner20()
    emp(co20)

    tg40 = Telegram40()
    emp(tg40)

    hotel2013 = Hotel2013()
    emp(hotel2013)

    mo15 = Momo2015()
    emp(mo15)
