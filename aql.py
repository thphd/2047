from colors import colored_print_generator as cpg, prettify as pfy
from colors import *
import requests as r
import time

import os

def get_environ(k):
    k = k.upper()
    if k in os.environ:
        return os.environ[k]
    else:
        return None

# rs = r.Session()
basic_auth = r.auth.HTTPBasicAuth('root','')

def extract(key, d, default):
    if key in d:
        a = d[key]
        del d[key]
        return a
    return default

# interface with arangodb.
class AQLController:
    def request(self, method, endp, raise_error=True, **kw):
        while 1:
            resp = self.session.request(
                method,
                self.dburl + endp,
                auth = basic_auth,
                json = kw,
                timeout = self.timeout,
                proxies = {},
            ).json()

            if ('error' not in resp) or resp['error'] == False:
                # server returned success
                return resp
            else:
                if not raise_error:
                    print_err(str(resp))
                    return False
                else:
                    em = resp['errorMessage']
                    if 'write-write' in em and 'conflict' in em:
                        print_err('WWC: write-write conflict detected, retry...', kw)
                        time.sleep(0.5)
                        continue
                    else:
                        raise Exception(str(resp))

    def __init__(self, dburl, dbname, collections=[], timeout=12):
        self.dburl = dburl or (get_environ('dbaddr') or 'http://127.0.0.1:8529')
        self.dbname = dbname
        self.collections = collections
        self.prepared = False

        self.session = r.Session()
        a = r.adapters.HTTPAdapter(pool_connections=30, pool_maxsize=15,)
        self.session.mount('http://', a)

        self.timeout = timeout

    def prepare(self):
        if not self.prepared:
            # create database if nonexistent
            self.request('post','/_api/database', name=self.dbname, raise_error=False)

            self.prepared = True
            # create collections if nonexistent
            for c in self.collections:
                self.create_collection(c)


    def create_collection(self, name):
        self.prepare()
        return self.request('POST', '/_db/'+self.dbname+'/_api/collection',
        name=name, waitForSync=True, raise_error=False)

    def clear_collection(self, name, filter=''):
        self.prepare()
        return self.aql('for i in {} {} remove i in {}'.format(
            name, filter, name))

    def create_index(self, collection, **kw):
        self.prepare()
        return self.request('post', '/_db/'+self.dbname+'/_api/index?collection='+collection, raise_error=False, **kw)

    def aql(self, query, **kw):

        if isinstance(query, QueryString):
            kw.update(query.kw)
            return self.aql(query.s, **kw)

        silent = extract('silent', kw, False)
        raise_error = extract('raise_error', kw, True)

        self.prepare()

        if not silent: print_up('AQL >>',query,kw)

        t0 = time.time()

        resp = self.request(
            'POST', '/_db/'+self.dbname+'/_api/cursor',
            query = query,
            batchSize = 1000,
            raise_error = raise_error,
            bindVars = kw,
        )
        if raise_error==False and resp==False:
            return []

        res = resp['result']

        t = time.time()-t0
        if t>0.15:
            print_info('== AQL took {:d}ms =='.format(int(t*1000)))

        if not silent: print_down('AQL <<', str(res))
        return res

    def change_view_properties(self, viewname, **kw):
        print_info(f'attempting to change view properties on {self.dbname}/{viewname}')
        resp = self.request('PATCH',
            '/_db/'+self.dbname+'/_api/view/'+viewname
            +'/properties#ArangoSearch',
            **kw,
        )

    def from_filter(self, _from, _filter, **kw):
        self.prepare()
        return self.aql('for i in {} filter {} return i'.format(_from, _filter), **kw)

    def wait_for_online(self):
        i = 1
        while 1:
            try:
                one = self.aql('return 1')[0]
            except Exception as e:
                print_err(e)
                print_up('fail #' + str(i) + '\n')
                i+=1
                time.sleep(1)
            else:
                if one==1:
                    return

class QueryString:
    def __init__(self, s='', **kw):
        self.s = s
        self.kw = kw.copy()

    def append(self, s='', **kw):
        self.s += '\n' + s
        self.kw.update(kw)

    def prepend(self, s='', **kw):
        self.s = s+'\n'+self.s
        self.kw.update(kw)

    def __add__(self, b):
        k = self.kw.copy()
        k.update(b.kw)
        result = QueryString(self.s+'\n'+b.s, **k)
        return result

def fix_view_loss(addr):
    aqlc = AQLController(addr, 'db2047', timeout=60)
    aqlc.change_view_properties(
        'sv',
        links = {
                    'threads':{
                        'analyzers':['text_zh'],
                        'fields':{
                        'title':{},
                        'content':{},
                        },
                    },
                    'posts':{
                        'analyzers':['text_zh'],
                        'fields':{
                            'content':{},
                        },
                    },
                    'users':{
                        'analyzers':['text_zh'],
                        'fields':{
                        'name':{},
                        'brief':{},
                        },
                    },
                }
        )

if __name__ == '__main__':

    # aqlc = AQLController('http://127.0.0.1:8529', 'test',[
    # 'queue'
    # ])
    # aql = aqlc.aql
    #
    # aql('insert {a:1} into queue')
    # a = aql('for u in queue return u')
    #
    # aql('for u in queue filter u.a==1 remove u in queue')
    # a = aql('for u in queue return u')
    #
    # print(a)

    pass
