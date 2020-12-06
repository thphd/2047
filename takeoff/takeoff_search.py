from takeoff import Weibo, QQ, JD, SF, Pingan

class Search:
    def __init__(self):
        self.g = [i() for i in (Weibo,QQ, JD, SF, Pingan)]

    def get_sources(self):
        return [i.path for i in self.g]

    def search(self, s):
        s = s.strip().split(' ')[0]
        res = []

        for i in self.g:
            r = i.find(s)
            res += r

        res = sorted(res, key=lambda a:1 if 'hit' in a else 2)

        return res

if __name__ == '__main__':
    s = Search()
    print(s.search('13915466930'))
    print(s.search('3798002017'))
