from colors import colored_print_generator as cpg, prettify as pfy
from colors import *
import requests as r

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
                raise Exception(str(resp))

    def __init__(self, dburl, dbname, collections):
        self.dburl = dburl
        self.dbname = dbname

        # create database if nonexistent
        self.request('post','/_api/database', name=dbname, raise_error=False)

        # create collections if nonexistent
        for c in collections:
            self.create_collection(c)

    def create_collection(self, name):
        return self.request('POST', '/_db/'+self.dbname+'/_api/collection',
        name=name, waitForSync=True, raise_error=False)

    def clear_collection(self, name, filter=''):
        return self.aql('for i in {} {} remove i in {}'.format(
            name, filter, name))

    def create_index(self, collection, **kw):
        return self.request('post', '/_db/'+self.dbname+'/_api/index?collection='+collection, raise_error=False, **kw)

    def aql(self, query, silent=False, **kw):
        if not silent: print_up('AQL >>',query,kw)
        resp = self.request(
            'POST', '/_db/'+self.dbname+'/_api/cursor',
            query = query,
            batchSize = 1000,
            bindVars = kw,
        )
        res = resp['result']
        if not silent: print_down('AQL <<', str(res))
        return res

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
