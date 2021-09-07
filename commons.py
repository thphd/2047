from commons_static import *

import flask
from flask import Flask, g, abort # session
from flask import render_template, request, send_from_directory, make_response

def make_text_response(text):
    r = make_response(text, 200)
    r = etag304(r)
    r.headers['Content-Type']='text/plain; charset=utf-8'
    r.headers['Content-Language']= 'en-US'
    return r

def etag304(resp):
    etag = calculate_etag(resp.data)
    # print(etag, request.if_none_match, request.if_none_match.contains_weak(etag))
    if request.if_none_match.contains_weak(etag):
        resp = make_response('', 304)

    resp.set_etag(etag)
    return resp

def html_escape(s): return flask.escape(s)

# return requests.args[k] as int or 0
def rai(k):
    v = key(request.args,k)
    return int(v) if v else 0

# return requests.args[k] as string or ''
def ras(k):
    v = key(request.args,k)
    return str(v) if v else ''


# translations

from i18n import DefaultTranslations, spf

def get_current_locale():
    try:
        locale = g.locale if hasattr(g, 'locale') else 'zh'
    except:
        locale = 'zh'

    if locale not in trans.allowed_languages:
        locale = 'zh'

    return locale
def get_current_locale(): return g.locale

trans = DefaultTranslations(get_current_locale)
dict_of_languages = {
    k:v['name']
    for k,v in trans.allowed_languages.items()
    if not v['name'].startswith('*') or k=='expl'
}
if __name__ == '__main__':
    print(trans.list_allowed_languages())

zh = zh_ = trans.mark_for_translate_gen('zh')
en = en_ = trans.mark_for_translate_gen('en')
zhen = lambda a,b:zh_(a,('en', b))
enzh = lambda a,b:en_(a,('zh', b))

# everything time related

import datetime

dtdt = datetime.datetime
dtt = datetime.time
dtd = datetime.date
dtn = dtdt.now
dttz = datetime.timezone
dttd = datetime.timedelta

# default time parsing
def dtdt_from_stamp(stamp):
    return dtdt.fromisoformat(stamp)

dfs = dtdt_from_stamp

def dfshk(stamp):
    return dfs(stamp).replace(tzinfo=working_timezone)

# proper time formatting
# input: string iso timestamp
# output: string formatted time

def format_time(dtdt,s):
    return dtdt.strftime(s)

# default time formatting
def format_time_iso(dtdt):
    return dtdt.isoformat(timespec='seconds')[:19]
fti = format_time_iso

format_time_datetime = lambda s: format_time(dfs(s), '%Y-%m-%d %H:%M')
format_time_dateonly = lambda s: format_time(dfs(s), '%Y-%m-%d')
format_time_timeonly = lambda s: format_time(dfs(s), '%H:%M')

def format_time_dateifnottoday(s):
    # dt = dfs(s)
    # now = dtn(working_timezone)
    #
    # if now.date() > dt.date():
    #     return format_time_dateonly(s)
    # else:
    #     return format_time_timeonly(s)

    return format_time_absolute_fallback(s)

def days_since(ts):
    then = dfshk(ts)
    now = dtn(working_timezone)
    dt = now - then
    return dt.days

def days_between(ts0, ts1):
    return abs(days_since(ts0) - days_since(ts1))

def seconds_since(ts):
    then = dfshk(ts)
    now = dtn(working_timezone)
    dt = now - then
    return dt.total_seconds()

def cap(x, mi, ma):
    return min(max(x, mi),ma)

def page_grayness():
    now_year = time_iso_now()[0:5]
    lod = list_of_dates = [
        '06-04 00:00:00',
    ]
    lod = [now_year+i for i in lod]
    k = b = 86400*0.4
    for d in lod:
        ssd = seconds_since(d)
        assd = abs(ssd)
        if assd < k:
            k = assd

    return cap(1 - (1 - (b-k) / b)**1.2, 0, 1) * 0.95

def format_time_relative_fallback(s):
    dt = dfshk(s)
    now = dtn(working_timezone)

    past = now-dt # larger=>longer in the past
    ps = int(past.total_seconds())

    if past < dttd(seconds=60):
        return zhen('几秒前','seconds ago')
    if past < dttd(seconds=3600):
        return spf(zhen('$0 分钟前','$0 min ago'))(str(ps // 60))
    if past < dttd(seconds=3600*24):
        return spf(zhen('$0 小时前','$0 h ago'))(str(ps // 3600))
    if past < dttd(seconds=86400*200):
        # days = str((ps // 86400))
        # return days + '天前'
        # return f'{dt.month}月{dt.day}日'
        return spf(zhen('$0月$1日','$em0 $1'))(dt.month, dt.day)
    # if past < dttd(seconds=86400*365):

    else:
        # return f'{dt.year}年{dt.month}月{dt.day}日'
        return spf(zhen('$0年$1月$2日',"$em1 $2 '$yy0"))(
            dt.year, dt.month, dt.day)
        return format_time_dateonly(s)

@lru_cache(maxsize=2048)
def format_time_absolute_fallback(s):
    dt = dfshk(s)
    now = dtn(working_timezone)

    past = now-dt # larger=>longer in the past

    if past < dttd(seconds=3600*15):
        return format_time_timeonly(s)
    else:
        return format_time_dateonly(s)

def login_time_validation(s):
    dt = dfs(s).replace(tzinfo=gmt_timezone)
    now = dtn(working_timezone)
    # print('ltv',dt, now)

    past = now - dt
    print_info('message signed:', past, 'ago')
    if past < dttd(seconds=60*30): # within 30 minutes
        return True
    else:
        return False

working_timezone = dttz(dttd(hours=+8)) # Hong Kong
gmt_timezone = dttz(dttd(hours=0)) # GMT

def time_iso_now(dt=0): # dt in seconds
    return format_time_iso(dtn(working_timezone) + dttd(seconds=dt))

# pw hashing

def bytes2hexstr(b):
    return ba.b2a_hex(b).decode('ascii')

def hexstr2bytes(h):
    return ba.a2b_hex(h.encode('ascii'))

# https://nitratine.net/blog/post/how-to-hash-passwords-in-python/
def get_salt():
    return os.urandom(32)

def get_random_hex_string(b=8):
    return base64.b16encode(os.urandom(b)).decode('ascii')

def hash_pw(salt, string):
    return hashlib.pbkdf2_hmac(
        'sha256',
        string.encode('ascii'),
        salt,
        100000,
    )

# input string, output hash and salt
def hash_w_salt(string):
    salt = get_salt()
    hash = hash_pw(salt, string)
    return bytes2hexstr(hash), bytes2hexstr(salt)

# input hash,salt,string, output comparison result
def check_hash_salt_pw(hashstr, saltstr, string):
    chash = hash_pw(hexstr2bytes(saltstr), string)
    return chash == hexstr2bytes(hashstr)

from render import *

# render with globals
from flask import render_template
from template_globals import tgr
def render_template_g(*a, **k):
    k.update(tgr)
    g.time_elapsed_before_render = g.get_elapsed()
    return render_template(*a, **k)

def eat_rgb(s, raw=False):
    s = s.split(',')
    if len(s)!=3:
        return False

    try:
        s = [int(i) for i in s]
    except Exception as e:
        return False

    s = [max(0,min(255, i)) for i in  s]
    if raw:
        return s
    return f'rgb({s[0]}, {s[1]}, {s[2]})'

# database connection
from aql import AQLController, QueryString
aqlc = AQLController(None, 'db2047')
aql = aqlc.aql

def wait_for_database_online():
    qprint('waiting for database online...')
    aqlc.wait_for_online()
    qprint('database online.')

# site pagination defaults

thread_list_defaults = dict(
    pagenumber=1,
    pagesize=50,
    order='desc',
    sortby='t_hn',
    # sortby='t_u',
)
thread_list_defaults_water = thread_list_defaults.copy()
thread_list_defaults_water['sortby'] = 't_u'

user_thread_list_defaults = dict(
    pagenumber=1,
    pagesize=50,
    order='desc',
    sortby='t_c',
)

post_list_defaults = dict(
    pagenumber=1,
    pagesize=50,
    order='asc',
    sortby='t_c',

    get_default_order=lambda sortby:('asc' if sortby=='t_c' else 'desc'),
)

post_list_defaults_q = dict(
    pagenumber=1,
    pagesize=50,
    order='desc',
    sortby='t_hn',

    get_default_order=lambda sortby:('asc' if sortby=='t_c' else 'desc'),
)

user_post_list_defaults = dict(
    pagenumber=1,
    pagesize=50,
    order='desc',
    sortby='t_c',

    get_default_order=lambda sortby:('desc' if sortby=='t_c' else 'desc'),
)

all_post_list_defaults = dict(
    pagenumber=1,
    pagesize=50,
    order='desc',
    sortby='t_hn',
    get_default_order=lambda sortby:('desc' if sortby=='t_hn' else 'desc'),
)

inv_list_defaults = dict(
    pagenumber=1,
    pagesize=25,
    order='desc',
    sortby='t_c',
)

fav_list_defaults = dict(
    pagenumber=1,
    pagesize=25,
    order='desc',
    sortby='t_c',
)

simple_defaults = dict(
    pagenumber=1,
    pagesize=25,
    order='desc',
    sortby='t_c',
)

if __name__ == '__main__':
    print(post_list_defaults['get_default_order']('t_c'))
    print(post_list_defaults['get_default_order']('votes'))

user_list_defaults = dict(
    pagenumber=1,
    pagesize=50,
    order='desc',
    sortby='uid',
    get_default_order=lambda sortby:('asc' if sortby=='name' else 'desc'),
)

# visitors can't see those on homepage
hidden_from_visitor = [int(i) for i in '4 19'.split(' ')]
# visitors can't see those anywhere
hidden_harder_from_visitor = [19]

def linkify(s):
    lines = s.split('\n')
    lines = [l.strip() for l in lines if len(l.strip())!=0]
    lines = [l.split(' ') for l in lines if len(l.split(' '))==3]
    lines = [{'text':l[0],'url':l[1],'notes':l[2]} for l in lines]
    return lines

common_links = linkify('''
新手指南 /t/7623 如题
用户名录 /u/all 本站用户名册
社会信用分 /u/all?sortby=trust_score 试点项目
创建投票 /t/9564 应用户强烈要求
老用户 /t/7108 原2049用户取回账号方式
勋章墙 /medals 荣光
黑名单 /t/9807 真/言论自由
删帖 /c/deleted 本站被删帖子
管理员 /t/7408 成为管理员
l337 /leet 做题家
数据备份 /t/7135 论坛数据库备份
服务条款 /t/7110 违者封号
题库 /questions 考试题目编撰
机读 /choice_stats 答题卡统计
实体编辑 /entities 公钥上传/其他杂项数据
链接 /links 2047网址导航
语录 /quotes 你不是一个人在战斗
oplog /oplog 管理日志
英雄 /hero BE4的实验性项目
维尼查 /ccpfinder 镰和锤子不可兼得
云上贵州 /guizhou 年轻人不讲武德
人人影视 /search_yyets?q=越狱 人人英雄永垂不朽
图书馆 https://zh.b-ok.org/ 人类进步的阶梯
''')

tor_address = 'http://terminus2xc2nnfk6ro5rmc5fu7lr5zm7n4ucpygvl5b6w6fqap6x2qd.onion'

friendly_links = linkify(f'''
Tor上的2047 {tor_address} 特殊情况下使用
旧品葱 https://pincongbackup.github.io/ pin-cong.com备份
火光 https://2049post.wordpress.com/ 薪火相传光明不息
BE4 https://nodebe4.github.io/ BE4的网络服务
XsDen https://xsden.info/ 講粵語嘅討論區
英雄 https://nodebe4.github.io/hero/ 人民英雄永垂不朽
迷雾通 https://community.geph.io/ 迷雾通官方交流社区
2049备份 https://2049bbs.github.io/ 本站前身
1亩3分地 https://www.1point3acres.com/ 马基雅维利
''')

site_name='2047论坛，自由人的精神角落'
site_name_header='2047'

num_max_used_invitation_codes = 20

# priviledge: who can do what to whom

def can_do_to(u1, operation, u2id):
    if not u1:
        return False

    is_self = True if u1['uid'] == u2id else False
    is_admin = True if (('admin' in u1) and u1['admin']) else False

    if operation == 'delete':
        if is_self or is_admin:
            return True

    elif operation == 'edit':
        if is_self or is_admin:
            return True

    elif operation == 'vote':
        if not is_self:
            return True

    elif operation == 'update_votecount':
        if is_admin:
            return True

    elif operation == 'ban_user':
        if is_admin:
            return True

    elif operation == 'move':
        if is_admin:
            return True

    elif operation == 'add_alias':
        if is_admin:
            return True

    elif operation == 'view_code':
        return True

    return False

# parse string of form "target_type/target_id"

def parse_target(s, force_int=True):
    s = s.split('/')
    if len(s)!=2:
        raise Exception(en('target string failed to split', zh='目标字符串分割失败'))
    if not (len(s[0]) and len(s[1])):
        raise Exception(en('splitted parts have zero length(s)', zh='分割后其中一部分长度为零'))

    targ = s[0]
    _id = int(s[1]) if force_int else s[1]

    return targ, _id

# parse string that contains t123 or p456
def parse_showcases(s):
    rsc = r'(t|p)([0-9]{1,16})'
    occurences = re.findall(rsc, s)
    return occurences

from flask import request
def is_pincong_org():
    return 'pincong.org' in request.host

def pagerank_format(u):
    pr = key(u, 'pagerank') or 0
    return int(pr*1000)

def trust_score_format(u):
    ts = key(u, 'trust_score') or 0
    return int(ts*1000000)

def redact(s):
    out = []
    for idx, l in enumerate(s):
        if idx==0:
            out.append(l)
        else:
            if idx%5>1:
                out.append(l)
            else:
                out.append('*')

    return ''.join(out)

if __name__ == '__main__':
    print(parse_showcases('''
如“t7113”或者“p247105”）,t112,p1
    '''),parse_showcases(''))

entity_info = convert_markdown('''
在这个界面，你可以添加、修改或删除 entity（[JSON](https://en.wikipedia.org/wiki/JSON)对象），尺寸限制5k

可以使用[RJSON](https://oleg.fi/relaxed-json/)语法。所有entities都会纳入论坛数据备份，请不要存放敏感信息。

entity可以从下列URL访问：

- `/e/<entity_id>` (document as JSON)
- `/e/<entity_id>/<field_name>` (document.field_name as JSON)
- `/member/<username>/e/<type>` (first document of type of user)，例如[/member/thphd/e/public_key](/member/thphd/e/public_key)

其他特殊的使用方式会单独开帖介绍。添加公钥请填写`type`为`public_key`，并点击“作为文字内容新增”按钮。

''')

password_warning = convert_markdown('''
# 密码安全警告

2047不接收明文密码，因此无法帮助用户判断其密码是否符合安全要求。

密码太简单（少于13位纯数字、少于8位数字+字母、[最常见的一百万个密码](https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10-million-password-list-top-1000000.txt)）将导致你的密码被人用计算机在短时间内猜解。

我们建议您使用浏览器提供的随机密码。

''')

cant_login_info = convert_markdown('''
# 2049bbs老用户请注意

如果你是2049bbs的老用户，请注意2047的数据库中没有你的密码记录（因为2049bbs早前并未公开这些记录），所以你是无法登录的，也无法注册同名账户。请按照[这里](/t/7108)的指示取回你的老账号。

''')

invitation_info = convert_markdown('''
# 没有邀请码怎么办

参见[这里](/t/7109)获取邀请码。
''')

public_key_info = convert_markdown('''
# Public Key Cryptography

2047允许用户将上传的公钥用于验证身份并登录。将个人公钥上传至2047的用户，可用他的私钥加密/签名凭据登录2047，免除密码泄露之虞。

''')

messaging_warning = convert_markdown('''
# 私信安全警告

2047在数据库中明文保存所有私信。

私信内容不会纳入论坛数据备份。除非FBI敲门，我们不会将私信内容提供给任何第三方。

站长可以阅读所有私信内容（在这一点上，品葱、膜乎等墙外网站是一样的），使用私信功能即视为默许。

如果您不希望站长阅读私信内容，可以将私信内容加密。

我们不会对私信内容作任何限制，不存在比如说新品葱搞的那种关键词审查/过滤。

但请注意，如果您发送的私信令其他用户感到困扰，在收到举报后我们有可能根据《服务条款》封禁您的账号。

未来2047会添加私信加密功能。
''')

register_warning = convert_markdown('''
# 不想被封号？

使用2047的所有用户都**必须**遵守[《服务条款》](/t/7110)，违反《服务条款》的用户，其违规内容会被删除，违规账号会被封禁。

概括来讲：

- 在他人楼下不得作出任何无礼行为，包括脏话、歧视、骚扰、控诉、调戏讽刺挖苦、重复灌水、强迫他人接受观点。如果确实有需要，可以另开一楼。
- 对管理、对内容有任何意见，请私信联系管理员。

不受欢迎行为清单详见[品葱行为倡议](/t/7623)。虽然它只是一份倡议，但是我们经过研究决定封禁所有违反倡议的用户。

''')

register_warning2 = convert_markdown(f'''

# 注册提示

- 用户名需符合 {username_regex_string}

- 密码不应过分简单

- 密码提交前将在浏览器端作hash，服务器不接收、不记录明文密码

- 服务器端收到用户提交hash后，会再用pbkdf2-hmac-sha256+salt作hash

''')

def indexgen(condss, sorts):
    r1 = []
    for conds in condss:
        for sort in sorts:
            r1.append(conds+[sort])
    return r1

def is_legal_username(n):
    return re.fullmatch(username_regex, n)

def is_alphanumeric(n):
    return re.fullmatch(r'^[0-9a-zA-Z]*$', n)

import random
from quotes import *

@stale_cache(ttr=10, ttl=900)
def get_links():
    links = aql('''
    for i in entities
    filter i.type=='links'
    sort i.t_c desc
    let user = (for u in users filter u.uid==i.uid return u)[0]
    return merge(i, {user})
    ''', silent=True)

    def issomething(typ):
        def k(s):
            return isinstance(s, typ)
        return k

    isstr = issomething(str)
    islist = issomething(list)
    isdict = issomething(dict)

    fin = []
    din = {}

    for link in links:
        if not islist(link['doc']): continue
        linklist = link['doc']

        default_category = '未分类'

        for obj in linklist:
            hasstr = lambda s: (s in obj) and isstr(obj[s])
            if not isdict(obj): continue
            if not hasstr('name') or not hasstr('url'): continue

            dl = {}
            dl['_key'] = link['_key']
            dl['name'] = obj['name']
            dl['url'] = obj['url']

            if not dl['url'].startswith('http://') and not dl['url'].startswith('https://'):
                dl['url'] = 'https://' + dl['url']

            dl['user'] = link['user']
            dl['t_c'] = link['t_c']

            if hasstr('brief'):
                dl['brief'] = obj['brief']

            if hasstr('category'):
                dl['category'] = obj['category']
                default_category = obj['category']
            else:
                if hasstr('cat'):
                    dl['category'] = obj['cat']
                    default_category = obj['cat']
                else:
                    dl['category'] = default_category

            fin.append(dl)
            dlc = dl['category']
            if dlc not in din:
                din[dlc] = []
            din[dlc].append(dl)

    for key in din:
        din[key] = sorted(din[key], key=lambda k:k['name'].lower())

    return din, fin

def get_link_one():
    linksd, linksl = get_links()
    return random.choice(linksl)

@stale_cache(ttr=60, ttl=1800)
def get_weekly_best(start=7, stop=14, n=10):
    lastweek = format_time_iso(dfs(time_iso_now()) - dttd(days=start))
    lastweek2 = format_time_iso(dfs(time_iso_now()) - dttd(days=stop))
    wb = aql(f'''
    for t in threads
    filter t.t_c > '{lastweek2}' and t.t_c <'{lastweek}'
    sort t.amv desc
    limit {n}
    return t
    ''', silent=True)
    return wb

@stale_cache(ttr=60, ttl=1800)
def get_weekly_best_user(start=7, stop=14, n=10):
    lastweek = format_time_iso(dfs(time_iso_now()) - dttd(days=start))
    lastweek2 = format_time_iso(dfs(time_iso_now()) - dttd(days=stop))

    wbu = aql(f'''
    for v in votes
    filter v.t_c > '{lastweek2}' and v.t_c <'{lastweek}'
    collect uid=v.to_uid with count into n
    sort n desc
    limit {n}

    let user = (for u in users filter u.uid==uid return u)[0]

    return {{uid, n, user}}
''', silent=True)

    return wbu

@stale_cache(ttr=60, ttl=1800)
def get_user_best_threads(uid):
    return aql('''
        for t in threads
        filter t.uid==@uid and t.delete==null
        sort t.amv desc
        limit 40
        return t
    ''', uid=int(uid), silent=True)

def get_user_picked_threads(uid):
    ts = get_user_best_threads(uid)
    ts = random.sample(ts,min(7, len(ts)))
    ts = sorted(ts, key=lambda t:t['amv'] if 'amv' in t else 0, reverse=True)
    return ts

@stale_cache(ttr=600, ttl=1800)
def get_best_threads():
    return aql('''
        for t in threads
        filter t.delete==null
        sort t.amv desc
        limit 400
        return t
    ''', silent=True)

def get_picked_threads():
    ts = get_best_threads()
    ts = random.sample(ts,min(7, len(ts)))
    ts = sorted(ts, key=lambda t:t['amv'] if 'amv' in t else 0, reverse=True)
    return ts

@stale_cache(ttr=3, ttl=1800)
def get_water_threads():
    wt = aql('for i in entities filter i.type=="water_thread" return i.doc',
        silent=True)
    return wt

def is_water_thread(tid):
    wt = get_water_threads()
    return tid in wt

@stale_cache(ttr=600, ttl=1800)
def get_high_trust_score_users():
    l1 = aql('''
        for u in users
        sort u.trust_score desc
        limit 500
        filter u.delete==null and u.trust_score>0
        return u
    ''', silent=True)
    l2 = l1.map(lambda u:u['trust_score'] or 0)
    return l1,l2

@stale_cache(ttr=5, ttl=180)
def get_high_trust_score_users_random_pre(k):
    htsu, scores = get_high_trust_score_users()
    scores = scores.map(lambda k:math.sqrt(k))
    idxes = random.choices(list(range(len(htsu))), weights=scores, k=2*k)

    d = {}
    l = []
    for i in idxes:
        if i not in d:
            l.append(i)
            d[i] = True
        if len(l)>=k:
            break

    htsu = [htsu[idx] for idx in l]
    return htsu

def get_high_trust_score_users_random(k):
    htsu = get_high_trust_score_users_random_pre(k)
    if g.current_user:
        shouldinsert = True
        for i in htsu:
            if i['uid']==g.selfuid:
                shouldinsert = False
                break
        if shouldinsert:
            htsu.append(g.current_user)

    htsu = sorted(htsu, key=lambda u:-u['trust_score'] or 0)
    htsu = htsu.map(
        lambda d:{'user':d, 'n': trust_score_format(d)})
    return htsu

if __name__ == '__main__':
    print('filtgen')
    print(indexgen([['cond1'],['cond2'],['cond1','cond2']], ['sort1','sort2']))

if __name__ == '__main__':
    h, s = hash_w_salt('1989')
    assert check_hash_salt_pw(h, s, '1989')
    assert check_hash_salt_pw(h, s, '0604') == False

    import re
    print(re.fullmatch(username_regex, 'asdf你好中国'))

    for i in range(10):
        print(get_random_hex_string(6))

    # test timezone
    print(format_time_iso(dtn()))
    print(format_time_iso(dtn(working_timezone)))

    print(format_time_relative_fallback(
        format_time_iso(dtn())
    ))
