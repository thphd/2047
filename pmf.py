from commons import *
from search import break_terms

aqlc2 = AQLController(None, 'dbpmf')
aqlc2.create_collection('pms')
aql = aqlc2.aql

def loadall():
    datapath = r'[redacted]\ill\result.txt'

    keys = 'id name gender race area committee sfz addr mobile mobile2 education'.split(' ')
    lk = len(keys)

    aql('for i in pms remove i in pms')

    dl = []
    def flush():
        nonlocal dl
        print('got', len(dl))
        aql('for i in @k insert i into pms', silent=True, k=dl)
        dl = []

    with open(datapath, 'r', encoding='utf-8') as f:
        for l in f:
            if not l:
                break
            else:
                l = l.strip()
                if not len(l):
                    continue
                else:
                    l = l.split(',')
                    assert len(l) == lk

                    d = {}

                    for k,v in zip(keys, l):
                        d[k] = v

                    dl.append(d)
                    # aql('''insert @k into pms''', k=d, silent=True)
                    if len(dl) > 500:
                        flush()

    flush()

@ttl_cache(ttl=3600, maxsize=256)
def search_term(term):
    s = break_terms(term)

    terms = {}

    query = 'for i in pmv search '

    for idx, i in enumerate(s):
        query += '('
        query += f' boost(phrase(i.name, @term{idx}, "text_zh"), 2.5)'
        query += f' or boost(ngram_match(i.name, @term{idx}, 1, "text_zh"), 1)'
        query += f' or ngram_match(i.addr, @term{idx}, 0.6,"text_zh")'
        query += f' or ngram_match(i.committee, @term{idx}, 0.6,"text_zh")'
        query += f' or ngram_match(i.area, @term{idx}, 0.6,"text_zh")'
        query += f' or phrase(i.mobile, @term{idx}, "text_zh")'
        query += f' or phrase(i.mobile2, @term{idx},"text_zh")'
        query += f' or phrase(i.sfz, @term{idx},"text_zh")'
        query += ')'

        terms['term'+str(idx)] = i

        if idx!=len(s)-1:
            query += ' and '

    query += f'''
    let score = tfidf(i)
    sort score desc
    limit 100

    return merge(i,{{score}})
    '''

    search_result = aql(query, silent=True, **terms)

    return dict(pms=search_result, terms=s)

if __name__ == '__main__':
    # loadall()
    pass
