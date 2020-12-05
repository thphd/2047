from takeoff import Weibo, QQ, JD, SF, Pingan

class Search:
    def __init__(self):
        self.g1 = [i() for i in (Weibo,QQ)]
        self.g2 = [i() for i in (JD, SF, Pingan)]

    def get_sources(self):
        return [i.path for i in self.g1] + [i.path for i in self.g2]

    def search(self, s):
        # g1 = [i() for i in (Weibo,QQ)]
        # g2 = [i() for i in (JD, SF, Pingan)]
        g1,g2 = self.g1, self.g2

        s = s.strip().split(' ')[0]

        res = []

        try:
            si = int(s)
        except:
            pass
        else:
            for i in g1:
                r = i.find(si)
                res += r

        for i in g2:
            r = i.find(s)
            res += r

        return res

if __name__ == '__main__':
    s = Search()
    print(s.search('13915466930'))
    print(s.search('3798002017'))
