import inspect
from cachetools.func import *
from functools import *
from cachy import stale_cache
import re

def pp(*a):
    assert len(a)>=2
    f = a[0]
    params = a[1:]
    print(f.__name__, params)
    print(f(*params))

# currently supported languages, their display names,
# their fallback candidates in order
allowed_languages_attribs = ala = [
    i.strip().split(' ') for i in '''

    zh *中文 zh-cn zh-sg zh-hk zh-tw en
    en *English en-us

    zh-cn 大陆中文 zh
    zh-hk 香港中文 zh-tw zh
    zh-tw 台灣中文 zh-hk zh
    zh-sg 新加坡中文 zh

    en-us English(US) en-gb en
    en-gb English(UK) en-us en

    zh-mohu 膜乎 zh-cn

    default *默认 zh en

    expl *注解 default

'''.strip().split('\n') if len(i)
]

allowed_languages = {
        t[0]:{
            'name':t[1],
            'fallbacks':t[2:],
        }
    for t in ala}

# print('allowed_languages', allowed_languages)

# given a language, return list of fallback in order
def find_fallback_order(target_lang) -> list:
    fbs = allowed_languages[target_lang]['fallbacks'].copy()
    fbs.append('default')

    cand_s = set([target_lang])
    cand_l = []

    q = [target_lang]+fbs
    visited = set(q)
    res = []

    # BFS
    while q:
        lang = q.pop(0)
        if lang != 'default':
            res.append(lang)

        for j in allowed_languages[lang]['fallbacks']:
            if j not in visited:
                visited.add(j)
                q.append(j)
    return res

# pp(find_fallback_order,'zh')

for lang in allowed_languages:
    fbo = find_fallback_order(lang)
    allowed_languages[lang]['fallback_order'] = fbo
    print(f'fallback_order for {lang} is {fbo}')


class Translations:
    '''
    manage translations of string for display.
    '''
    def __init__(self, allowed_languages, gcl):
        '''
        allowed_languages is a dict in the form of
        {
            en:{
                name:English,
                fallbacks:[zh, zh-cn],
                fallback_order:[zh, zh-cn, zh-tw...],
            },
            zh:{
                name:简体中文,
                fallbacks:...,
                fallback_order:...,
            }
        }
        '''
        self.d = {} # from code
        self.d2 = {} # from database
        self.get_d2 = lambda:self.d2
        # external function that returns a d2 object

        self.s, self.s2 = {},{}
        # check whether a call to mark_for_translate occured before

        self.allowed_languages = allowed_languages
        self.get_current_locale = gcl

    @lru_cache(maxsize=1024)
    def fallback(self, target_lang:str, avail_langs:tuple) -> str:
        '''
        given target lang, find the best candidate in a dict of langs
        '''

        if len(avail_langs)==0:
            raise Exception('avail_langs is empty', target_lang)

        if len(avail_langs)==1:
            # if isinstance(avail_langs, dict):
            #     return avail_langs.keys().__iter__().__next__()
            # elif isinstance(avail_langs, set):
            #     return avail_langs.__iter__().__next__()
            # else: # list
                return avail_langs[0]

        if target_lang in avail_langs:
            return target_lang

        if target_lang not in allowed_languages:
            raise Exception(f'lang "{target_lang}" not defined in allowed_languages')

        for i in allowed_languages[target_lang]['fallback_order']:
            if i in avail_langs:
                return i

        raise Exception(f'non of the fallbacks of {target_lang} found in avail_langs {avail_langs}')

    def mark_for_translate_gen(self, lang, ci=1):
        '''
        returns a function that labels the enclosing text
        to be of a certain language and returns translations
        of that text.
        '''
        import os.path

        get_current_locale = self.get_current_locale
        d = self.d
        st = self.s
        st2 = self.s2

        caller_index = ci

        assert lang in self.allowed_languages
        # if 'mft' in self.allowed_languages[lang]:
        #     return self.allowed_languages[lang]['mft']

        @ttl_cache(ttl=30, maxsize=4096)
        def return_translate(s, cl):
            ds = d[s]
            dskeys = tuple(ds.keys())

            d2 = self.get_d2()
            sind2 = s in d2
            if sind2:
                d2s = d2[s]
                dskeys = dskeys + tuple(d2s.keys())

            # find best fallback candidate
            appropriate_lang = self.fallback(cl, dskeys)

            if appropriate_lang:
                if sind2 and (appropriate_lang in d2s):
                    return d2s[appropriate_lang]
                else:
                    return ds[appropriate_lang]
            else:
                return f'No available fallback found for "{s}" in {lang}'

        def mark_for_translate(*tups) -> str:
            # (s, tup0, tup1,...)
            s = tups[0]

            # print('curr locale', cs)

            # if never ran with these params before
            if tups not in st:
                st[tups] = 1

                # commented out because jinja is inspect-unfriendly

                # try:
                #     # info on caller
                #     sl = inspect.stack()
                #     lsl = len(sl)
                #     k = 0
                #     while 1:
                #         f = sl[caller_index+k]
                #         fn_only = os.path.basename(f.filename)
                #         # print(ci, f.lineno, fn_only, f.code_context[0].strip())
                #         if fn_only!='runtime.py': # skip runtime.py in call stack
                #             break
                #         elif caller_index+k >= lsl-1:
                #             break
                #         else:
                #             k+=1
                #
                #     # keep filename and lineno for later use
                #     st2[s] = dict(filename=fn_only, lineno=f.lineno)
                # except:
                #     st2[s] = dict(filename='unknown file', lineno='_')

                if s not in d:
                    d[s] = {}

                ds = d[s]
                ds[lang] = s

                # tupN -> <lang>,<translation> pairs
                for ilang, translation in tups[1:]:
                    # ilang = ilang.replace('_','-')
                    if ilang not in ds:
                        ds[ilang] = translation

            # load current locale
            cl = get_current_locale()

            return return_translate(s, cl)

        # self.allowed_languages[lang]['mft'] = mark_for_translate
        return mark_for_translate

    def update(self, d2):
        '''
        update translations from external dictionary.
        '''
        self.d2.update(d2)

    def list_allowed_languages(self):
        sal = self.allowed_languages
        return [(k,v['name']) for k,v in sal.items()]

    def is_allowed_language(self, s):
        sal = self.allowed_languages
        return s in sal


class DefaultTranslations(Translations):
    def __init__(self, *a, **kw):
        super().__init__(allowed_languages, *a, **kw)

# sprintf-ish string replacer
spf_regex_split=r'\$(?:(?:[a-zA-Z]{0,3})(?:[0-9]{1,2})|\$);?'
spf_regex = spf_regex_split.replace('?:','')
english_months = 'Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec'.split(',')
formatters = {
    'em':lambda i: english_months[i-1],
    'yy':lambda y: f'{y%100:02d}',
    '':str,
    'es':lambda i:'' if i==1 else 's',
}

@lru_cache(maxsize=1024)
def spf(s):
    try:
        splits = re.split(spf_regex_split, s)
        found = re.findall(spf_regex, s)
        assert len(splits) == len(found)+1

        # print(found)
        s2 = [splits[0]]
        f2 = []
        fmt2 = []
        for fi, si1 in zip(found, splits[1:]):
            if fi[0]=='$':
                s2[-1] += fi[0] + si1
            else:
                f2.append(int(fi[2]))
                s2.append(si1)
                fmt2.append(formatters[fi[1]])

        ans_t = [s2[0]]
        # print(s2, f2)
        if len(fmt2) == 0:
            s20 = s2[0]
            def f(*a):
                return s20
            return f

        if len(fmt2) == 1:
            s20 = s2[0]; s21 = s2[1]
            fmt20 = fmt2[0]
            f20 = f2[0]
            @lru_cache(maxsize=512)
            def f(*a):
                return s20 + fmt20(a[f20]) + s21
            return f

    except Exception as e:
        se = str(e)
        def f(*a):
            return se+'_'+','.join((str(i) for i in a))

    else:
        @lru_cache(maxsize=1024)
        def f(*a):
            try:
                lena = len(a)
                ans = ans_t.copy()
                for f2i, fmt2i, s2i1 in zip(f2, fmt2, s2[1:]):
                    ans.append(fmt2i(a[f2i]))
                    ans.append(s2i1)

                return ''.join(ans)
            except Exception as e:
                return str(e)+'_'+','.join((str(i) for i in a))

    return f

assert spf('h$$ello$0$1;3')('world', 2) == 'h$elloworld23'
assert spf('$em0 $1, $yy2')(1,1,2020) == 'Jan 1, 20'

if __name__ == '__main__':

    print(spf('$em0 $1, $yz2')(1,1,2020))
    print(spf('$em0 $1, $yy4')(1,1,2020))

    current_locale = 'en'
    def get_current_locale():
        return current_locale

    trans = DefaultTranslations(get_current_locale)

    print(trans.list_allowed_languages())

    zh = trans.mark_for_translate_gen('zh')
    zh2 = trans.mark_for_translate_gen('zh',ci=2)
    en = trans.mark_for_translate_gen('en')
    en2 = trans.mark_for_translate_gen('en',ci=2)

    zhen = lambda a,b:zh2(a,('en', b))
    enzh = lambda a,b:en2(a,('zh', b))

    pp(trans.fallback, 'zh', ('en',))
    pp(trans.fallback, 'zh', ('en', 'zh-tw'))
    pp(trans.fallback, 'zh', ('en', 'zh'))

    def hello():
        print(en('this needs to be translated'))
        print(zh('你好世界', ('en','Hello World')))
        print(zhen('自由','freedom'))

    hello()

    trans.update({
        'this needs to be translated':{
            'zh-cn':'这需要被翻译'
        }
    })

    current_locale = 'zh'

    hello()
