from api import *
from commons import *
from app import app

aqlc.create_collection('translations')

@register('set_locale')
def _():
    j = g.j
    locale = es('locale')
    if locale not in dict_of_languages or locale=='expl':
        raise Exception('this locale is not yet supported here.')
    return {'error':False,'set_locale':locale}

@register('get_allowed_languages')
def _():
    return {'allowed_languages':dict_of_languages}

@register('update_translation')
def _():
    j = g.j
    must_be_logged_in()
    banned_check()
    if current_user_doesnt_have_enough_likes():
        raise Exception('you don\'t have enough likes to submit translation')

    original = es('original')
    o2=j['original']
    lang = es('lang')
    string = es('string')

    uid = g.current_user['uid']

    if lang not in trans.allowed_languages:
        raise Exception('this language is not supported yet.')

    # if original not in trans.d:
    #     print(original)
    #     print(o2)
    #     raise Exception('original text not in trans.d')

    t_c = time_iso_now()

    new_trans = dict(
        original=original,
        lang=lang,
        string=string,
        uid=uid,
        t_c=t_c,
        t_u=t_c,
        approved=False,
    )

    aql('''
    let d = @nt
    upsert {uid:d.uid, lang:d.lang, original:d.original}
    insert d update {string:d.string, t_u:d.t_c} into translations
    ''', nt=new_trans)

    return {}

@register('approve_translation')
def _():
    must_be_logged_in()
    must_be_admin()

    trans_id = es('id')
    delete = eb('delete')

    aql('''
    for t in translations
    filter t._key==@key
    update t with {approved:@approved} in translations
    ''', key=trans_id, approved=not delete)

    return {}

def textualize(s):
    resp = make_response(s, 200)
    resp.headers['Content-type'] = 'text/plain; charset=utf-8'
    return resp

def get_all_translations():
    all_translations = aql('''
for t in translations
let user = (for i in users filter i.uid==t.uid return i)[0]
collect original = t.original into groups = merge(t, {user})
return {original, groups}
    ''', silent=True)

    return all_translations

    # for d in all_translations:
    #     original = d['original']

@stale_cache(ttr=10, ttl=1200) # database to code form
def at2d2():
    at = get_all_translations()
    d2 = {}
    for d in at:
        orig = d['original']
        lots = d['groups']
        d2[orig] = d2o = {}

        for t in lots: # t -> translation object {original, string, lang}
            t_lang = t['lang']
            if t['approved']:
                if t_lang not in d2o:
                    d2o[t_lang] = t
                else:
                    if d2o[t_lang]['user']['pagerank'] < t['user']['pagerank']:
                        d2o[t_lang] = t

        for t_lang in d2o:
            d2o[t_lang] = d2o[t_lang]['string']

    return d2

@stale_cache(ttr=3, ttl=120) # code to database form
def d2at():
    d = trans.d
    l = []
    for original,langs in d.items():
        od = dict(original=original, groups=[])
        groups = od['groups']
        l.append(od)

        # commented out because jinja2 is inspect-unfriendly

        # ts2o = trans.s2[original]
        # fn,ln  = ts2o['filename'], ts2o['lineno']

        for lang, string in langs.items():
            groups.append(
                dict(lang=lang, string=string))
                # dict(lang=lang, string=string, filename=fn, lineno=ln))
    return l

trans.get_d2 = at2d2

@app.route('/translations')
def translations_page():
    at = get_all_translations() # from database
    at2 = d2at() # from code

    ld = {}
    for d in at2+at:
        original = d['original']
        if original not in ld:
            ld[original] = []
        ld[original]+=d['groups']

    l = [(k,v) for k,v in ld.items()]
    l.sort(key=lambda t:t[0])

    return render_template_g('trans.html.jinja', translations=l, page_title='翻译')

@app.route('/translations/list_allowed_languages')
def list_allowed_languages():
    tal = trans.allowed_languages
    s = '\n'.join((str(k) +' '+ repr(v) for k,v in tal.items()))
    return textualize(s)

@app.route('/translations/list_translations')
def list_translations():
    d = at2d2()
    s = '\n'.join((str(k) +' '+ repr(v) for k,v in d.items()))
    return textualize(s)
