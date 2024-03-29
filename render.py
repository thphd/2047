from cachetools.func import *
from cachy import stale_cache
import threading
import re

from commons_static import *
from colors import *

# extract non-markdown urls
url_regex = r'((((http|https|ftp):(?:\/\/)?)(?:[\-;:&=\+\$,\w]+@)?[A-Za-z0-9\.\-]+(:\[0-9]+)?|(?:www\.|[\-;:&=\+\$,\w]+@)[A-Za-z0-9\.\-]+)((?:\/[\+~%\/\.\w\-_]*)?\??(?:[\-\+=&;%@\.\w_]*)#?(?:[\.\!\/\\\w]*))?)(?![^<]*?(?:<\/\w+>|\/?>))(?![^\(]*?\))'
# dont use for now

# username rule
legal_chars = r'0-9a-zA-Z\u4e00-\u9fbb\-\_\.'
username_regex_proto = f'[{legal_chars}]' + r'{2,16}'
username_regex=r'^' + username_regex_proto + r'$'
username_regex_pgp = r'2047login#(' + username_regex_proto + r')#(.{19})'
username_regex_pgp_new = r'2047login##(.*?)##(.{19})'
username_regex_string = str(username_regex).replace('\\\\','\\')

tagname_regex_long = username_regex_proto.replace('2,16','1,40')
tagname_regex = username_regex_proto.replace('2,16','1,14')

at_extractor_regex = (r'(?:(?<=^)|(?<=[(),。，（） *]))@([a-z]{2,16}?)(?=[^a-z]|$)').replace('a-z', legal_chars)

# @lru_cache(maxsize=4096)
def _extract_ats(s): # extract @usernames out of text
    groups = re.findall(at_extractor_regex, s, flags=re.MULTILINE)
    print(groups)
    return [g[1] for g in groups]

def extract_ats(s):
    html, collected = frend(s)
    return collected['at_user_list']

# @lru_cache(maxsize=4096)
def replace_ats(s): # replace occurence
    if s.startswith('<p>'):
        return s

    def f(match):
        uname = match.group(2)
        return match.group(1) + f'[@{uname}](/member/{uname})'

    return re.sub(at_extractor_regex, f, s, flags=re.MULTILINE)

post_autolink_regex = r'</?[#p]/?([0-9]{1,16})>'
thread_autolink_regex = r'</?t/?([0-9]{1,16})>'

replace_autolink_regex = r'</?([pt])([0-9]{1,16})>'
def replace_tal_form(s):
    def f(match):
        type = match.group(1)
        id = match.group(2)
        return f'</{type}/{id}>'
    return re.sub(replace_autolink_regex, f, s, flags=re.M)

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

def replace_polls(s):
    def f(match):
        pollid = match.group(1)
        return f'<div class="poll-instance-unprocessed" data-id="{pollid}"></div>'

    return re.sub(r'(?=^)#poll(\d{1,16})(?=\s|\t|$)', f, s, flags=re.MULTILINE)

# match only youtube links that occupy a single line
youtube_extractor_regex = r'(?=\n|\r|^)(?:http|https|)(?::\/\/|)(?:www.|)(?:youtu\.be\/|youtube\.com(?:\/embed\/|\/v\/|\/watch\?v=|\/ytscreeningroom\?v=|\/feeds\/api\/videos\/|\/user\S*[^\w\-\s]|\S*[^\w\-\s]))([\w\-]{11})[A-Za-z0-9;:@#?&%=+\/\$_.-]*(?=\n|$)'

# match those from 2049bbs
old_youtube_extractor_regex = r'<div class="videowrapper"><iframe src="https://www\.youtube\.com/embed/([\w\-]{11})" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen=""></iframe></div>'

youtube_extractor_regex_bugfix = r'<div class="youtube-player".*?data-id="(.*?)">.*?播放</a>'

# combined together
combined_youtube_extractor_regex = \
'(?:'+youtube_extractor_regex+'|'+old_youtube_extractor_regex+'|'\
    +youtube_extractor_regex_bugfix + ')'

# @lru_cache(maxsize=4096)
def replace_ytb_f(match):
    vid = match.group(1) or match.group(2) or match.group(3)

    ts = None
    if vid==match.group(1):
        url = match.group(0)
        # print('urlmatch', url)
        timestamp_found = re.search(r'\?t=([0-9]{1,})', url)
        if timestamp_found:
            ts = timestamp_found.group(1)
            ts = int(ts)
    # print('timestamp', ts)

    ts = ('?t='+str(ts)) if ts else ''

    return f'''<a target="_blank" href="https://youtu.be/{vid}{ts}">https://youtu.be/{vid}{ts}</a><div class="youtube-player-unprocessed" data-id="{vid}" data-ts="{ts}"></div>'''.format(vid)

twitter_extractor_regex = r"^(https://twitter.com/[a-zA-Z0-9_]*?/status/\d+).*?$"
def replace_twitter_f(match):
    turl = match.group(1)

    k = f'''<a href="{turl}">{turl}</a><blockquote class="twitter-tweet" data-conversation="true" data-dnt="true"><a href="{turl}">{turl}</a></blockquote>'''
    return k

def replace_soundcloud_f(match):

    return f'''<iframe width="100%" height="166" scrolling="no" frameborder="no" allow="autoplay" src="https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/993308041&color=%23ff5500&auto_play=false&hide_related=false&show_comments=true&show_user=true&show_reposts=false&show_teaser=true"></iframe><div style="font-size: 10px; color: #cccccc;line-break: anywhere;word-break: normal;overflow: hidden;white-space: nowrap;text-overflow: ellipsis; font-family: Interstate,Lucida Grande,Lucida Sans Unicode,Lucida Sans,Garuda,Verdana,Tahoma,sans-serif;font-weight: 100;"><a href="https://soundcloud.com/trinhcongdan" title="Trịnh Công Đan" target="_blank" style="color: #cccccc; text-decoration: none;">Trịnh Công Đan</a> · <a href="https://soundcloud.com/trinhcongdan/cafe-khong-duong-jombie-x-tkan-bean-official-music-audio" title="CAFE KHÔNG ĐƯỜNG || JOMBIE x TKAN &amp; BEAN || OFFICIAL MUSIC AUDIO" target="_blank" style="color: #cccccc; text-decoration: none;">CAFE KHÔNG ĐƯỜNG || JOMBIE x TKAN &amp; BEAN || OFFICIAL MUSIC AUDIO</a></div>'''

def replace_pincong(s):
    def f(match):
        return f'<mark class="parody">{match.group(1)}</mark>'
    s = re.sub(r'(?<![>@/])((?:姨|桂|支|偽|伪|张献|張獻|韭|鹿)(?:葱|蔥)|(?:品|葱|蔥)韭)', f, s)
    return s

# @lru_cache(maxsize=4096)
def replace_ytb(s):
    s = re.sub(combined_youtube_extractor_regex,
        replace_ytb_f, s, flags=re.MULTILINE)
    return s

def replace_twitter(s):
    s = re.sub(twitter_extractor_regex, replace_twitter_f, s, flags=re.M)
    return s

# @lru_cache(maxsize=4096)
# def extract_ytb(s):
#     groups = re.findall(combined_youtube_extractor_regex, s, flags=re.MULTILINE)
#     return [g[0] or g[1] for g in groups]

@lru_cache(maxsize=4096)
def extract_ytb(s):
    res, collected = frend(s)
    return collected['youtube_players']

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

    from html_stuff import parse_html, sanitize_html

    # @lru_cache(maxsize=2048)
    def just_markdown(s):
        # s = replace_pal(s)
        # s = replace_tal(s)
        s = replace_tal_form(s)
        # s = replace_ats(s)
        # s = replace_pincong(s)
        # s = replace_ytb(s)
        # s = replace_twitter(s)
        # s = replace_polls(s)
        # html = mistletoe.markdown(s)
        html, _collected = frend(s)

        return html

    @lru_cache(maxsize=4096)
    def convert_markdown(s):
        out = just_markdown(s)

        try:
            soup = parse_html(out)
            sanitize_html(soup)
            out = soup.decode()
        except Exception as e:
            print_err('failed to parse with bs4')
            out = '(parse failure: check your HTML)'

        return out

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

###

import mistletoe
from html_stuff import parse_html, sanitize_html
from mistletoe import Document
from mistletoe.span_token import SpanToken,RawText,AutoLink
from mistletoe.block_token import BlockToken
from mistletoe.html_renderer import HTMLRenderer
from mistletoe.ast_renderer import ASTRenderer

OldAutoLink = AutoLink
class AutoLink(OldAutoLink):
    def __init__(self, match):
        content = match.group(self.parse_group)
        self.children = (RawText(content),)
        self.target = content
        self.mailto = (0 and '@' in self.target) and 'mailto' not in self.target.casefold()

mistletoe.span_token.AutoLink = AutoLink

class AtUser(SpanToken):
    pattern = re.compile(at_extractor_regex)
    parse_inner = False
    parse_group = 1 # useful only when parse_inner = 1
    precedence = 1 # default 5
    def __init__(self, match):
        self.username = match.group(1)
        # self.children = (RawText(self.username),)

class PostMention(SpanToken):
    pattern = re.compile(post_autolink_regex)
    parse_inner = False
    parse_group = 1 # useful only when parse_inner = 1
    precedence = 6 # default 5
    def __init__(self, match):
        self.id = match.group(1)

class LjhReference(SpanToken):
    pattern = re.compile(':liangjiahe\-?(\d{1,4}):')
    parse_inner = False
    parse_group = 1 # useful only when parse_inner = 1
    precedence = 1 # default 5
    def __init__(self, match):
        self.id = match.group(1)

class ModMessage(SpanToken):
    pattern = re.compile('\[mod\](.*?)\[/mod\]')
    parse_inner = True
    parse_group = 1 # useful only when parse_inner = 1
    precedence = 1 # default 5
    def __init__(self, match):
        self.inner = match.group(1)

class ThreadMention(SpanToken):
    pattern = re.compile(thread_autolink_regex)
    parse_inner = False
    parse_group = 1 # useful only when parse_inner = 1
    precedence = 6 # default 5
    def __init__(self, match):
        self.id = match.group(1)

class Cnmb(BlockToken):
    pattern = re.compile(r'cnm(.+?)b$')

    # pattern = re.compile(r' {0,3}(?:([-_*])\s*?)(?:\1\s*?){2,}$')
    def __init__(self, matches):
        self.content = matches[0]

    @classmethod
    def start(cls, line):
        return cls.pattern.match(line)

    @staticmethod
    def read(lines):
        return [next(lines)]

class YoutubePlayer(Cnmb):
    pattern = re.compile(combined_youtube_extractor_regex)

    def __init__(self, matches):
        line = matches[0].strip()
        g = self.pattern.match(line).group
        url = g(0)
        vid = g(1) or g(2) or g(3)

        ts = None
        if vid==g(1):
            timestamp_found = re.search(r'\?t=([0-9]{1,})', url)
            if timestamp_found:
                ts = timestamp_found.group(1)
                ts = int(ts)

        ts = ('?t='+str(ts)) if ts else ''

        self.url = url
        self.replacement = f'''<a target="_blank" href="https://youtu.be/{vid}{ts}">youtu.be/{vid}{ts}</a><div class="youtube-player-unprocessed" data-id="{vid}" data-ts="{ts}"></div>'''

class TwitterFrame(Cnmb):
    pattern = re.compile(twitter_extractor_regex)

    def __init__(self, matches):
        line = matches[0].strip()
        g = self.pattern.match(line).group
        url = g(0)
        twid = g(1)

        self.url = url
        turl = url

        self.replacement = f'''<a href="{turl}">{turl}</a><blockquote class="twitter-tweet" data-conversation="true" data-dnt="true"><a href="{turl}">{turl}</a></blockquote>'''

class PollInstance(Cnmb):
    pattern = re.compile(r'#{0,1}poll(\d{1,16})(?=\s|\t|$)')

    def __init__(self, matches):
        line = matches[0].strip()
        g = self.pattern.match(line).group

        self.pollid = g(1)
        self.replacement = f'<div class="poll-instance-unprocessed" data-id="{self.pollid}"></div>'


class FlavoredRenderer(HTMLRenderer):
    def __init__(self):
        # bad interface design ?
        super().__init__(PollInstance, YoutubePlayer, TwitterFrame, Cnmb,
            AtUser, PostMention, ThreadMention, LjhReference, ModMessage)

        self.init_collection()

    def init_collection(self):
        self.collected = {
            'at_user_list':[],
            'youtube_players':[],
            'twitter_frames':[],
        }

    def render_at_user(self, token):
        # implicit PascalCase to snake_case conversion
        # no documentation at all
        un = token.username
        self.collected['at_user_list'].append(un)
        # un = self.escape_html(un)
        # un = flask.escape(un)
        return f'<a href="/member/{un}">@{un}</a>'

    def render_post_mention(self, token):
        tid = token.id
        return f'<a href="/p/{tid}">#{tid}</a>'

    def render_thread_mention(self, token):
        tid = token.id
        return f'<a href="/t/{tid}">/t/{tid}</a>'

    def render_cnmb(self, token):
        return f'<a href="#">{token.content}</a>'

    def render_youtube_player(self, token):
        self.collected['youtube_players'].append(token.url)
        return token.replacement

    def render_twitter_frame(self, token):
        self.collected['twitter_frames'].append(token.url)
        return token.replacement

    def render_poll_instance(self, token):
        return token.replacement

    def render_ljh_reference(self, token):
        from api import render_ljh_one
        return render_ljh_one(token.id)

    def render_auto_link(self, token): # overridden
        template = '<a href="{target}">{inner}</a>'
        if token.mailto:
            target = 'mailto:{}'.format(token.target)
        else:
            target = self.escape_url(token.target)
        inner = self.render_inner(token)

        # unescape inner
        inner = decodeURI(inner)

        return template.format(target=target, inner=inner)

    def render_mod_message(self, token):
        inner = self.render_inner(token)
        return f'<span data-class="mod_message">{inner}</span>'


import urllib.parse
unquote_ = decodeURI = urllib.parse.unquote

# flavored_renderer = FlavoredRenderer()
renderlock = threading.Lock()

@lru_cache(maxsize=16384)
def frend(md):
    with renderlock:
        # ren = FlavoredRenderer()
        with FlavoredRenderer() as ren:
            # again very bad interface design
            rend = ren.render(Document(md))
            coll = ren.collected

        return rend, coll


if __name__ == '__main__':

    xamplemd = '''
# heading1

@yesno

- @yesno
- totally @yesno yes!

```python
@yesno

 @yesno

```

    '''*10
    print(frend(xamplemd))

    print(just_markdown('<https://baidu.com/>'))
    print(convert_markdown('<https://baidu.com/>'))
