from commons import *
from app import app

aqlc_pmf = AQLController(None, 'dbpmf')
aql_pmf = aqlc_pmf.aql

def break_terms(s):
    s = s.split(' ')
    s = [i.strip() for i in s if len(i.strip())]
    s = s[:4] # take first 4 terms only
    return s

def break_terms_arangosearch(s):
    return aql("return tokens(@s,'text_zh')", s=s)[0]

@stale_cache(maxsize=256, ttr=10, ttl=3600)
def search_term(s, start=0, length=25):
    # 1. break str into pieces
    original_terms = s
    bt = broken_terms = break_terms_arangosearch(original_terms)
    bt = [i for i in bt if i not in '的 不 是 了 嗯 一 个'.split(' ')]
    bt2 = broken_terms2 = break_terms(original_terms)

    bta = broken_terms+broken_terms2

    search_result2 = aql(f'''
    for i in sv
    search analyzer(
        i.title in @bt
        or i.content in @bt
        or boost(ngram_match(i.title, @bt2, 0.1, 'text_zh'), 20)
        or boost(ngram_match(i.content, @bt2, 0.1, 'text_zh'), 20)
    , 'text_zh')

    let score = tfidf(i) + sqrt(i.votes) * 5
    sort score desc
    limit {start},{length}

    let t = i.title?null:(for k in threads filter k.tid==i.tid return k)[0]
    let user = (for u in users filter u.uid==i.uid return u)[0]

    return merge(i, {{score, t, user}})

    ''', silent=True, bt2 = bt2[0], bt = bt)

    # print(search_result)
    # print(search_terms)

    uq = '''
    for i in sv
    search analyzer(
        i.name in tokens(@st, 'text_zh')
        or i.brief in tokens(@st, 'text_zh')
    , 'text_zh')

    let score = tfidf(i) + (sqrt(i.nlikes)*1.0 + sqrt(i.nposts)*0.1+sqrt(i.nthreads)*1.0)*0.6
    sort score desc
    limit 6
    filter i.delete==null
    return merge(i,{score})
    '''

    if start==0:
        user_search_result = aql(uq, silent=True, st=original_terms)[:3]
    else:
        user_search_result = None

    return dict(
        users = user_search_result,
        results = search_result2,
        terms = bt,
        original_terms = original_terms,
    )

@lru_cache(maxsize=256)
def search_yyets(s):
    return aql_pmf('''
for i in yyv
search analyzer(
    i.title in tokens(@st, 'text_zh')
    or boost(ngram_match(i.title, @st, 0.05, 'text_zh'), 3)
, 'text_zh')

let score = tfidf(i) //+ sqrt(i.votes) * 3
sort score desc

limit 36

let category = i.data.data.info.channel_cn or i.data.data.info.channel
let area = i.data.data.info.area
let no = i.no
let title = i.title

return merge({title, no, score, category, area})
    ''', silent=True, st=s)

@app.route('/search')
def search():
    q = ras('q').strip()
    if not q:
        return render_template_g(
            'search.html.jinja',
            hide_title=True,
            page_title='搜索',
            has_result=False,
        )
    else:
        result = search_term(q, start=0, length=20)
        return render_template_g(
            'search.html.jinja',
            query=q,
            hide_title=True,
            page_title='搜索 - '+q,
            has_result=True,
            **result
        )

@app.route('/search_yyets')
def search_yyets_page():
    q = ras('q').strip()
    if not q:
        return render_template_g(
            'search.html.jinja',
            hide_title=True,
            page_title='影视搜索',
            has_result=False,

            mode='yyets',
        )
    else:
        yyets_results = search_yyets(q)
        return render_template_g(
            'search.html.jinja',
            query=q,
            hide_title=True,
            page_title='影视搜索 - '+q,
            has_result=True,

            mode='yyets',
            yyets_results = yyets_results,
            original_terms = q,
        )

aqlc_pmf.create_index('yyets', type='persistent', fields=['no'],
    unique=False,sparse=False)

@lru_cache(maxsize=128)
def yyets_formatter(_id):
    j = aql_pmf('''for i in yyets filter i.no==@no return i''', silent=True, no=_id)

    if not j:
        raise Exception('id not found in yyets')

    j = j[0]

    lines = []

    l = j['data']['data']['list']
    for seas in l:
        season_str = seas['season_cn']
        resos = seas['items']

        for reso in resos:
            details = resos[reso]
            for ep in details:
                epn = ep['episode']
                files = ep['files']

                name = ep['name']
                size = ep['size']
                if isinstance(files, list):
                    for file in files:
                        addr = file['address']
                        meth = file['way_cn']
                        pw = file['passwd']

                        line = ' '.join(
                            [season_str, reso, name, size, meth, addr, pw])
                        lines.append(line)

    lines = sorted(lines)
    lines.insert(0, '数据来自 https://t.me/mikuri520/676')
    lines = '\n'.join(lines)
    return j,lines

@app.route('/yyets/<int:_id>')
def yyets_page(_id):
    j,lines = yyets_formatter(_id)

    # r = make_response(obj2json(j), 200)
    # r.headers['Content-Type'] = 'application/json'

    r = make_text_response(lines)

    return r

def _main():
    search('自由 亚洲')

if __name__ == '__main__':
    _main()
