from commons import *

@stale_cache(maxsize=256, ttr=10, ttl=3600)
def search_term(s, start=0, length=25):
    # 1. break str into pieces
    s = s.split(' ')
    s = [i.strip() for i in s if len(i.strip())]

    s = s[:4] # take first 4 terms only

    query = 'for i in sv search '

    terms = {}

    for idx, i in enumerate(s):
        query += f'(ngram_match(i.content, @term{idx}, 0.6,"text_zh")'
        query += f' or ngram_match(i.title, @term{idx}, 0.6,"text_zh") )'

        terms['term'+str(idx)] = i

        if idx!=len(s)-1:
            query += ' and '

    query += f'''
    let score = bm25(i) + sqrt(i.votes)*3
    sort score desc
    limit {start},{length}
    let t = i.title?null:(for k in threads filter k.tid==i.tid return k)[0]
    let user = (for u in users filter u.uid==i.uid return u)[0]

    return merge(i, {{score, t, user}})
    '''

    search_result = aql(query, silent=True, **terms)
    search_terms = s

    # print(search_result)
    # print(search_terms)

    uq = '''
    for i in sv
    search ngram_match(i.name,
    @term
    ,0.5,"text_zh")

    or ngram_match(i.brief,
    @term
    ,0.5,"text_zh")

    let score = bm25(i) + (sqrt(i.nlikes)*1.0 + sqrt(i.nposts)*0.1+sqrt(i.nthreads)*1.0)*0.6
    sort score desc
    limit 3
    return merge(i,{score})
    '''

    if len(s)==1 and start==0:
        user_search_result = aql(uq, silent=True, term=s[0])
    else:
        user_search_result = None

    return dict(
        users = user_search_result,
        results = search_result,
        terms = search_terms,
    )


def _main():
    search('自由 亚洲')

if __name__ == '__main__':
    _main()
