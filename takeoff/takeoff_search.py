from takeoff import *
import time

class Search:
    def __init__(self):
        self.g = [i() for i in (
            Weibo,QQ, JD, SF, Pingan, CarOwner20
        )]

    def get_sources(self):
        return [dict(
            path = i.path,
            origsize = i.origsize,
            dbsize = i.dbsize,
        ) for i in self.g]

    def search(self, s):
        t0 = time.time()

        s = s.strip().split(' ')[0]
        res = []

        for i in self.g:
            r = i.find(s)
            res += r

        res = reversed(
            sorted(res, key=lambda a:
            1 if 'hit' in a else (a['maxscore'] if 'maxscore' in a else 0))
        )

        t1 = time.time()-t0

        return res, t1

if __name__ == '__main__':
    s = Search()
    print(s.search('13915466930'))
    print(s.search('3798002017'))
