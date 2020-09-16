# useful definitions in one place

import os, hashlib, binascii as ba
import base64, re
from colors import *
from functools import lru_cache

def dispatch(f):
    import threading
    t = threading.Thread(target=f, daemon=True)
    t.start()

def init_directory(d):
    try:
        os.mkdir(d)
    except FileExistsError as e:
        print_err('directory {} already exists.'.format(d), e)
    else:
        print_info('directory {} created.'.format(d))

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

def format_time_relative_fallback(s):
    dt = dfs(s).astimezone(working_timezone)
    now = dtn(working_timezone)

    past = now-dt # larger=>longer in the past

    if past < dttd(seconds=3600):
        return str(past.seconds // 60) + '分钟前'
    if past < dttd(seconds=3600*24):
        return str(past.seconds // 3600) + '小时前'
    else:
        return format_time_dateonly(s)

def format_time_absolute_fallback(s):
    dt = dfs(s).astimezone(working_timezone)
    now = dtn(working_timezone)

    past = now-dt # larger=>longer in the past

    if past < dttd(seconds=3600*15):
        return format_time_timeonly(s)
    else:
        return format_time_dateonly(s)

working_timezone = dttz(dttd(hours=+8)) # Hong Kong

def time_iso_now():
    return format_time_iso(dtn(working_timezone))

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

# extract non-markdown urls
url_regex = r'((((http|https|ftp):(?:\/\/)?)(?:[\-;:&=\+\$,\w]+@)?[A-Za-z0-9\.\-]+(:\[0-9]+)?|(?:www\.|[\-;:&=\+\$,\w]+@)[A-Za-z0-9\.\-]+)((?:\/[\+~%\/\.\w\-_]*)?\??(?:[\-\+=&;%@\.\w_]*)#?(?:[\.\!\/\\\w]*))?)(?![^<]*?(?:<\/\w+>|\/?>))(?![^\(]*?\))'
# dont use for now

# username rule
username_regex=r'^[0-9a-zA-Z\u4e00-\u9fff\-\_\.]{2,16}$'
username_regex_string = str(username_regex).replace('\\\\','\\')

at_extractor_regex = r'@([0-9a-zA-Z\u4e00-\u9fff\-\_\.]{2,16}?)(?=[^0-9a-zA-Z\u4e00-\u9fff\-\_\.]|$)'

@lru_cache(maxsize=4096)
def extract_ats(s): # extract @usernames out of text
    groups = re.findall(at_extractor_regex, s, flags=re.MULTILINE)
    return groups

# @lru_cache(maxsize=4096)
def replace_ats(s): # replace occurence
    def f(match):
        uname = match.group(1)
        return '[@{uname}](/member/{uname})'.format(uname=uname)

    return re.sub(at_extractor_regex, f, s, flags=re.MULTILINE)

post_autolink_regex = r'<[#p]/?([0-9]{1,16})>'
thread_autolink_regex = r'<t/?([0-9]{1,16})>'

# @lru_cache(maxsize=4096)
def replace_pal(s):
    def f(match):
        pid = match.group(1)
        return '[#{}](/p/{})'.format(pid,pid)

    return re.sub(post_autolink_regex, f, s, flags=re.MULTILINE)

# @lru_cache(maxsize=4096)
def replace_tal(s):
    def f(match):
        pid = match.group(1)
        return '[t{}](/t/{})'.format(pid,pid)

    return re.sub(thread_autolink_regex, f, s, flags=re.MULTILINE)

# match only youtube links that occupy a single line
youtube_extractor_regex = r'(?=\n|\r|^)(?:http|https|)(?::\/\/|)(?:www.|)(?:youtu\.be\/|youtube\.com(?:\/embed\/|\/v\/|\/watch\?v=|\/ytscreeningroom\?v=|\/feeds\/api\/videos\/|\/user\S*[^\w\-\s]|\S*[^\w\-\s]))([\w\-]{11})[A-Za-z0-9;:@#?&%=+\/\$_.-]*(?=\n|$)'

# match those from 2049bbs
old_youtube_extractor_regex = r'<div class="videowrapper"><iframe src="https://www\.youtube\.com/embed/([\w\-]{11})" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen=""></iframe></div>'

# combined together
combined_youtube_extractor_regex = \
'(?:'+youtube_extractor_regex+'|'+old_youtube_extractor_regex+')'

# @lru_cache(maxsize=4096)
def replace_ytb_f(match):
    vid = match.group(1) or match.group(2)
    return '<div class="youtube-player-unprocessed" data-id="{}"></div>'.format(vid)

# @lru_cache(maxsize=4096)
def replace_ytb(s):
    s = re.sub(combined_youtube_extractor_regex,
        replace_ytb_f, s, flags=re.MULTILINE)
    return s

@lru_cache(maxsize=4096)
def extract_ytb(s):
    groups = re.findall(combined_youtube_extractor_regex, s, flags=re.MULTILINE)
    return [g[0] or g[1] for g in groups]
youtube_extraction_test_string="""
youtu.be/DFjD8iOUx0I
https://youtu.be/DFjD8iOUx0I

自动
youtu.be/DFjD8iOUx0I

http://youtu.be/dQw4w9WgXcQ

// https://www.youtube.com/embed/dQw4w9WgXcQ
// http://www.youtube.com/watch?v=dQw4w9WgXcQ
// http://www.youtube.com/?v=dQw4w9WgXcQ
// http://www.youtube.com/v/dQw4w9WgXcQ
// http://www.youtube.com/e/dQw4w9WgXcQ
// http://www.youtube.com/user/username#p/u/11/dQw4w9WgXcQ
// http://www.youtube.com/sandalsResorts#p/c/54B8C800269D7C1B/0/dQw4w9WgXcQ
// http://www.youtube.com/watch?feature=player_embedded&v=dQw4w9WgXcQ
//

http://www.youtube.com/?feature=player_embedded&v=dQw4w9WgXcQ

" https://youtu.be/yVpbFMhOAwE ",
"https://www.youtube.com/embed/yVpbFMhOAwE",
"youtu.be/yVpbFMhOAwE",
"youtube.com/watch?v=yVpbFMhOAwE",
"http://youtu.be/yVpbFMhOAwE",
"http://www.youtube.com/embed/yVpbFMhOAwE",
"http://www.youtube.com/watch?v=yVpbFMhOAwE",
"http://www.youtube.com/watch?v=yVpbFMhOAwE&feature=g-vrec",
"http://www.youtube.com/watch?v=yVpbFMhOAwE&feature=player_embedded",
好的" http://www.youtube.com/v/yVpbFMhOAwE?fs=1&hl=en_US  ",
" http://www.youtube.com/ytscreeningroom?v=yVpbFMhOAwE ",
"http://www.youtube.com/watch?NR=1&feature=endscreen&v=yVpbFMhOAwE",
"http://www.youtube.com/user/Scobleizer#p/u/1/1p3vcRhsYGo",
" http://www.youtube.com/watch?v=6zUVS4kJtrA&feature=c4-overview-vl&list=PLbzoR-pLrL6qucl8-lOnzvhFc2UM1tcZA ",
"
#真人献唱#

**《没有倒车档就没有庆丰国》**

<div class="videowrapper"><iframe src="https://www.youtube.com/embed/kfUx7Lv-az8" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen=""></iframe></div>

https://www.youtube.com/watch?v=FZu097wb8wU&list=RDFZu097wb8wU
 "
youtu.be/DFjD8iOUx0I
"""

# markdown renderer

if 0:
    import markdown
    def convert_markdown(s):
        return markdown.markdown(s)

elif 1:
    import mistletoe

    @lru_cache(maxsize=4096)
    def convert_markdown(s):
        s = replace_pal(s)
        s = replace_tal(s)
        s = replace_ats(s)
        s = replace_ytb(s)
        return mistletoe.markdown(s)

else:

    import re
    pattern = (
        r'((((http|https|ftp):(?:\/\/)?)'  # scheme
        r'(?:[\-;:&=\+\$,\w]+@)?[A-Za-z0-9\.\-]+(:\[0-9]+)?'  # user@hostname:port
        r'|(?:www\.|[\-;:&=\+\$,\w]+@)[A-Za-z0-9\.\-]+)'  # www.|user@hostname
        r'((?:\/[\+~%\/\.\w\-_]*)?'  # path
        r'\??(?:[\-\+=&;%@\.\w_]*)'  # query parameters
        r'#?(?:[\.\!\/\\\w]*))?)'  # fragment
        r'(?![^<]*?(?:<\/\w+>|\/?>))'  # ignore anchor HTML tags
        r'(?![^\(]*?\))'  # ignore links in brackets (Markdown links and images)
    )
    link_patterns = [(re.compile(pattern),r'\1')]
    import markdown2 as markdown
    from markdown2 import Markdown
    md = Markdown(
        extras=[
            'link-patterns',
            'fenced-code-blocks',
            'nofollow',
            'tag-friendly',
            'strike',
        ],
        link_patterns = link_patterns,
    )

    def convert_markdown(s):
        return md.convert(s)

# database connection
from aql import AQLController
aqlc = AQLController('http://127.0.0.1:8529', 'db2047',[])
aql = aqlc.aql

# site pagination defaults

thread_list_defaults = dict(
    pagenumber=1,
    pagesize=30,
    order='desc',
    sortby='t_hn',
    # sortby='t_u',
)

user_thread_list_defaults = dict(
    pagenumber=1,
    pagesize=30,
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
    sortby='votes',

    get_default_order=lambda sortby:('asc' if sortby=='t_c' else 'desc'),
)

user_post_list_defaults = dict(
    pagenumber=1,
    pagesize=50,
    order='desc',
    sortby='t_c',

    get_default_order=lambda sortby:('desc' if sortby=='t_c' else 'desc'),
)

inv_list_defaults = dict(
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
    pagesize=30,
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
用户名录 /u/all 本站用户名册
评论集合 /p/all 全站评论集合
老用户 /t/7108 原2049用户取回账号方式
邀请码 /t/7109 获取邀请码
删帖 /c/deleted 本站被删帖子
数据备份 /t/7135 论坛数据库备份
服务条款 /t/7110 违者封号
''')

friendly_links = linkify('''
火光 https://2049post.wordpress.com/ 薪火相传光明不息
英雄 https://nodebe4.github.io/hero/ 人民英雄永垂不朽
BE4 https://nodebe4.github.io/ BE4的网络服务
XsDen https://xsden.info/ 講粵語嘅討論區
連登 https://lihkg.com/ 光復香港冷氣革命
Tor上的2047 http://terminusnemheqvy.onion/ 特殊情况下使用
膜乎 https://mohu.rocks/ 中南海皇家娱乐城
新品葱 https://pincong.rocks/ 带关键词审查的墙外论坛
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
        raise Exception('target string failed to split')
    if not (len(s[0]) and len(s[1])):
        raise Exception('splitted parts have zero length(s)')

    targ = s[0]
    _id = int(s[1]) if force_int else s[1]

    return targ, _id

# parse string that contains t123 or p456
def parse_showcases(s):
    rsc = r'(t|p)([0-9]{1,16})'
    occurences = re.findall(rsc, s)
    return occurences

if __name__ == '__main__':
    print(parse_showcases('''
如“t7113”或者“p247105”）,t112,p1
    '''),parse_showcases(''))

entity_info = convert_markdown('''
在这个界面，你可以添加、修改或删除 entity（JSON对象），尺寸限制5k

可以使用[RJSON](https://oleg.fi/relaxed-json/)语法

entity可以从下列URL访问：

- `/e/<entity_id>` (document as JSON)
- `/e/<entity_id>/<field_name>` (document.field_name as JSON)

其他特殊的使用方式会单独开帖介绍

''')

password_warning = convert_markdown('''
# 密码安全警告

2047不接收明文密码，因此无法帮助用户判断其密码是否符合安全要求。

密码太简单（少于13位纯数字、少于8位数字+字母、[最常见的一百万个密码](https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10-million-password-list-top-1000000.txt)）将导致你的密码被人用计算机在短时间内猜解。

我们建议您使用浏览器提供的随机密码。

''')

cant_login_info = convert_markdown('''
# 2049bbs老用户请注意

如果你是2049bbs的老用户，请注意2047的数据库中没有你的密码记录（因为2049bbs早前并未公开这些记录），所以你是无法登录的。请按照[这里](/t/7108)的指示取回你的老账号。
''')

invitation_info = convert_markdown('''
# 没有邀请码怎么办

参见[这里](/t/7109)。
''')

public_key_info = convert_markdown('''
# Public Key Cryptography

2047将在未来某个时间允许用户将上传的公钥用于验证身份并登录。届时，将个人公钥上传至2047的用户，可用他的私钥加密/签名凭据登录2047，免除密码泄露之虞。

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
# 请注意

使用2047的所有用户都必须遵守[《服务条款》](/t/7110)。违反《服务条款》的用户，其账号将会被封禁。

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
