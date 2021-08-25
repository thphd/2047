import monkeypatch
import re,math
import shelve


if __name__ == '__main__':
    from aql import AQLController
    aqlc = AQLController('http://127.0.0.1:8529', 'db2047')
    aql = aqlc.aql

def allcn(text):
    text = text.lower()
    return re.findall(r'[\u4e00-\u9fbba-z\?\!？！。，]{1}',text).join('')

def preproc(text):
    allcnt = f'^{allcn(text)}$'

    grams = {}

    for gl in [2,3]: # bigram is enough
        for i in range(len(allcnt)-gl+1):
            gram2 = allcnt[i:i+gl]
            if gram2 not in grams:
                grams[gram2] = 0
            grams[gram2]+=1

    return grams,len(allcnt)

class SpamTrainer:
    def __init__(self):
        self.known_goods = {}
        self.known_spams = {}

        self.tc = {}

    def get_one_thread(self, tid):
        if tid not in self.tc:
            print('getting', tid ,'from db')
            self.tc[tid] = aql('''
            return (for i in threads filter i.tid==@tid return i)[0]
        ''', silent=True, tid=tid)[0]

        return self.tc[tid]

    def get_threads(self, tids):
        print('loading...', len(tids))
        tss=[]
        for tid in tids:
            ts = self.get_one_thread(tid)
            tss.append(ts)

        print('loaded...', len(tids))
        return tss

    def make_dict(self):
        self.spam_ts = spam_ts = self.get_threads(list(self.known_spams.keys()))
        self.good_ts = good_ts = self.get_threads(list(self.known_goods.keys()))

        spam_grams = {}
        spam_length = 0
        for idx, t in enumerate(spam_ts):
            for j in (t['title'] , t['content']):
                grams,length = preproc(j)

                for k in grams:
                    if k not in spam_grams:
                        spam_grams[k] = 0
                    spam_grams[k]+=grams[k]
                spam_length+=length

            if idx%20==0:
                print('parsing spam', idx, len(t['content']))

        good_grams = {}
        good_length = 0
        for idx, t in enumerate(good_ts):
            for j in (t['title'] , t['content']):
                grams,length = preproc(j)

                for k in grams:
                    if k not in good_grams:
                        good_grams[k]= 0
                    good_grams[k]+=grams[k]
                good_length+=length

            if idx%20==0:
                print('parsing good', idx, len(t['content']))

        final_grams = {}

        for k in spam_grams:
            if k not in final_grams:
                final_grams[k] = [1e-6, 1e-6, 0]

            freq_in_spam = spam_grams[k]/spam_length
            final_grams[k][0] += freq_in_spam
            final_grams[k][2] += spam_grams[k]

        for k in good_grams:
            if k not in final_grams:
                final_grams[k] = [1e-6, 1e-6, 0]

            freq_in_good = good_grams[k]/good_length
            final_grams[k][1] += freq_in_good
            final_grams[k][2] += good_grams[k]

        print('spamlen,goodlen',spam_length, good_length)

        print(len(final_grams), 'in final_grams')

        spamgoods = {}

        for k,v in final_grams.items():
            j = math.log(v[0]) - math.log(v[1])
            if (j>5 or j<-2) and v[2]>8:
                spamgoods[k] = j

        self.spamgoods = spamgoods

        print(len(spamgoods), 'in spamgoods')


    def score_text(self, *texts):
        sg = self.spamgoods


        spamlog = 0
        goodlog = 0

        for text in texts:
            grams,length = preproc(text)

            for gram in grams:
                if gram in sg:
                    spamlog += sg[gram] * grams[gram]
                    # spamscore *= sg[gram]**grams[gram]

                    minlog = max(spamlog, goodlog)
                    spamlog -= minlog
                    goodlog -= minlog

        # spamlog,goodlog = spamlog*.5, goodlog*.5

        spamscore = math.exp(spamlog)
        goodscore = math.exp(goodlog)

        sumscore = spamscore+goodscore
        return spamscore/sumscore, goodscore/sumscore
        # return spamscore,goodscore

    def save(self):
        with shelve.open('spamdb',flag='c') as d:
            d['good'] = self.known_goods
            d['spam'] = self.known_spams
            d['tc'] = self.tc

        with shelve.open('spamdata/spamgoods',flag='c') as d:
            d['spamgoods'] = self.spamgoods

    def load(self):
        with shelve.open('spamdb',flag='c') as d:
            if 'good' in d and 'spam' in d:
                self.known_goods = d['good']
                self.known_spams = d['spam']
            if 'tc' in d:
                self.tc = d['tc']

        with shelve.open('spamdata/spamgoods',flag='c') as d:
            if 'spamgoods' in d :
                self.spamgoods = d['spamgoods']

    def load_dict_only(self):
        with shelve.open('spamdata/spamgoods',flag='c') as d:
            if 'spamgoods' in d :
                self.spamgoods = d['spamgoods']

    def addgoods(self, goods):
        for j in goods:
            self.known_goods[j] = True

            if j in self.known_spams:
                del self.known_spams[j]

    def addspams(self, goods):
        for j in goods:
            self.known_spams[j] = True
            if j in self.known_goods:
                del self.known_goods[j]

st = SpamTrainer()

def is_spam(*texts):
    threshold = told = 0.99999
    spam, good = st.score_text(*texts)
    if spam > told:
        return True
    else:
        return False

if __name__!='__main__':
    st.load_dict_only()

if __name__ == '__main__':
    st.load()
    known_spams = [14223,14127,14075,14074,13290,13289,
    3573,3572,3575,4180,4288,4378,4437,4436,4488,4489,4538,4535,4526,4537
    ]

    st.addspams(known_spams)

    print('make_dict...')
    st.make_dict()
    print('save...')
    st.save()

    print(f'got {len(st.known_goods)}good  {len(st.known_spams)}spam')

    lenallt = aql('return count(for i in threads return 1)')[0]

    # lenallt = 100

    overkill = 0
    underkill = 0
    g,s = [],[]

    # scan thru all threads
    for i in range(lenallt):
        t = aql(f'for i in threads sort i.t_c desc limit {i},1 return i', silent=True)[0]
        tid = t['tid']

        # add thread to [goods] if good enough via some metric
        if 1:
            if 'votes' in t and t['votes']>=8:
                if len(t['content'])>200 and (('delete' not in t)
                    or (not t['delete'])):

                    print(tid,'added b/c very good')
                    st.addgoods([tid])
                    continue
                else:
                    if tid in st.known_goods:
                        print(tid,'deleted b/c problematic')

                        del st.known_goods[tid]

        spam,good = st.score_text(t['title'], t['content'])
        tid = t['tid']

        if i % 20==0:
            print(f"{i} {t['tid']} {spam:.7f}/{good:.7f}")


        if spam >0.99:
            print(f"spam{spam:.7f} #{t['tid']}# ###CONSIDERED SPAM### {t['title']}")
            # print(t['content'])

        threshold = told = 0.99999
        # elif 0.05<good<0.95:
        if spam < told and tid in st.known_spams:
            print('UNDERKILL!!!',f'{spam:.7f}', tid,  t['title'])
            underkill+=1

        # if CONSIDERED as spam but not included in [spams]
        if spam>told and tid not in st.known_spams:

            # if overkill
            if tid in st.known_goods:
                print('OVERKILL!!!',f'{spam:.7f}', tid, t['title'])
                overkill+=1

            print(f"{good:.7f} {t['tid']}, {t['title']}")
            print(t['content'])

            print('tid in spam, good:', tid in st.known_spams, tid in st.known_goods)

            # ask whether this thread should be considered as good instead
            end = 0
            while 1:
                print(tid, 'is this good?')
                ss = input().lower()
                if 'y' in ss:
                    # g.append(t['tid'])

                    st.addgoods([tid])
                    break
                elif 'n' in ss:
                    # s.append(t['tid'])
                    st.addspams([tid])
                    break
                elif 'i' in ss:
                    print('ignore', tid)

                    if tid in st.known_goods:
                        del st.known_goods[tid]
                    if tid in st.known_spams:
                        del st.known_spams[tid]
                    break

                elif 'l' in ss:
                    # learn
                    st.make_dict()
                    st.save()
                    continue

                elif 'q' in ss:
                    end = 1
                    break
                else:
                    continue
            if end:
                break

    print(f'got {len(st.known_goods)}good  {len(st.known_spams)}spam')
    print(f'overkills {overkill} underkills {underkill}')
    st.save()
