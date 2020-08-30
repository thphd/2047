from colors import colored_print_generator as cpg, prettify as pfy
from colors import *
import requests as r
import time

# interface with arangodb.
class AQLController:
    def request(self, method, endp, raise_error=True, **kw):
        resp = r.request(
            method,
            self.dburl + endp,
            auth = r.auth.HTTPBasicAuth('root',''),
            json = kw,
            timeout = 10,
            proxies = {},
        ).json()

        if resp['error'] == False: # server returned success
            return resp
        else:
            if not raise_error:
                print(str(resp))
            else:
                if 'write-write' in resp['errorMessage']:
                    print_err('write-write conflict detected', kw)
                raise Exception(str(resp))

    def __init__(self, dburl, dbname, collections):
        self.dburl = dburl
        self.dbname = dbname
        self.collections = collections
        self.prepared = False

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

    def aql(self, query, silent=False, raise_error=True, **kw):
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
        res = resp['result']

        t = time.time()-t0
        if t>0.15:
            print_info('== AQL took {:d}ms =='.format(int(t*1000)))

        if not silent: print_down('AQL <<', str(res))
        return res

    def from_filter(self, _from, _filter, **kw):
        self.prepare()
        return self.aql('for i in {} filter {} return i'.format(_from, _filter), **kw)

if __name__ == '__main__':

    aqlc = AQLController('http://127.0.0.1:8529', 'test',[
    'queue'
    ])
    aql = aqlc.aql

    aql('insert {a:1} into queue')
    a = aql('for u in queue return u')

    aql('for u in queue filter u.a==1 remove u in queue')
    a = aql('for u in queue return u')

    print(a)
