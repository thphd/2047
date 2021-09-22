
html = '''
<p>yolo</p>asdf<input type="text">
<iframe src="solid">asdf<j><!-- comment -->
</iframe>
<img src="wiki.com/.jpg"/>
<span color=red azimuth=asdf>blue</span>
<![CDATA[A CDATA block]]>
<p><a href='http://asdf.com' title='asdfjj'>dfafew</a>yes</p>
<a href = 'javAscript:alert(1)'>no</a>
'''

import bs4, re
from bs4 import BeautifulSoup as BS
import monkeypatch

def parse_html(html):
    soup = BS(html, 'html.parser')
    return soup

# https://github.com/leizongmin/js-xss/blob/master/lib/default.js

allowed_tags = '''
a target href title
abbr title
address
area shape coords href alt
article
aside
audio autoplay controls loop preload src
source src sizes type
b
bdi dir
bdo dir
big
blockquote
br
caption
center
cite
code
col align valign span width
colgroup align valign span width
dd
del datetime
details open
summary
div data-id
dl
dt
em
font color size face
footer
figure
figcaption
h1
h2
h3
h4
h5
h6
header
hr
i
img src alt title width height
ins datetime
li
mark
nav
ol
p
pre
s
section
small
span
sub
sup
strong
table width border align valign
tbody align valign
td width rowspan colspan align valign
tfoot align valign
th width rowspan colspan align valign
thead align valign
tr rowspan align valign
tt
u
ul
video autoplay controls loop preload src height width
'''.split('\n').map(lambda i: i.strip())\
    .filter(lambda i: len(i)).map(lambda i: i.split(' '))\
    .map(lambda i:(i[0], i[1:]+['style','background','class']))

allowed_tags = dict((k, v) for k, v in allowed_tags)

def sanitizeAttrValue(tag, name, value):
    if isinstance(value, list): # quirkness
        value = ' '.join(value)

    value = value.strip()
    vl = value.lower()
    vl = re.sub(r'\s*', '', vl)

    if name=='href' or name=='src':

        if value=='#':
            return '#'

        if not (
            vl.startswith('http://') or
            vl.startswith('https://') or
            vl.startswith('mailto:') or
            vl.startswith('tel:') or
            vl.startswith('data:') or
            vl.startswith('ftp://') or
            vl.startswith('./') or
            vl.startswith('../') or
            vl.startswith('#') or
            vl.startswith('/') or
            0
        ):
            return ''

        # replace domain names pointing at self
        value = re.sub(r'^(?:http|https)://(?:(?:mohu\.)?(?:2047.name|pincong.org)|terminusnemheqvy.onion|terminus2xc2nnfk6ro5rmc5fu7lr5zm7n4ucpygvl5b6w6fqap6x2qd.onion)/(.+)', '/\g<1>', value)

        # kill img src s with relative paths due to an error found on 20201109
        if tag=='img' and re.match(r'^\./.*?_files/.*?$', value):
            value = ''

    elif name=='background':
        if vl.startswith('javascript'): return ''
    elif name=='style':
        if vl.startswith('javascript'): return ''

        if 'expression(' in vl: return ''
        if 'url(' in vl: return ''
        if 'position' in vl: return ''

        # filter css inside style attr

    elif name=='class':
        if vl in ['youtube-player','youtube-player-unprocessed',
        'poll-instance-unprocessed','comment_section_unprocessed',
        'twitter-tweet',
        'yellow','parody']:
            return value
        if vl.startswith('lang'):
            return value
        return ''

    return value

# https://github.com/leizongmin/js-css-filter/blob/master/lib/default.js

whiteList = {}
true = True

# whiteList['align-content'] = false;
# whiteList['align-items'] = false;
# whiteList['align-self'] = false;
# whiteList['alignment-adjust'] = false;
# whiteList['alignment-baseline'] = false;
# whiteList['all'] = false;
# whiteList['anchor-point'] = false;
# whiteList['animation'] = false;
# whiteList['animation-delay'] = false;
# whiteList['animation-direction'] = false;
# whiteList['animation-duration'] = false;
# whiteList['animation-fill-mode'] = false;
# whiteList['animation-iteration-count'] = false;
# whiteList['animation-name'] = false;
# whiteList['animation-play-state'] = false;
# whiteList['animation-timing-function'] = false;
# whiteList['azimuth'] = false;
# whiteList['backface-visibility'] = false;
whiteList['background'] = true;
whiteList['background-attachment'] = true;
whiteList['background-clip'] = true;
whiteList['background-color'] = true;
whiteList['background-image'] = true;
whiteList['background-origin'] = true;
whiteList['background-position'] = true;
whiteList['background-repeat'] = true;
whiteList['background-size'] = true;
# whiteList['baseline-shift'] = false;
# whiteList['binding'] = false;
# whiteList['bleed'] = false;
# whiteList['bookmark-label'] = false;
# whiteList['bookmark-level'] = false;
# whiteList['bookmark-state'] = false;
whiteList['border'] = true;
whiteList['border-bottom'] = true;
whiteList['border-bottom-color'] = true;
whiteList['border-bottom-left-radius'] = true;
whiteList['border-bottom-right-radius'] = true;
whiteList['border-bottom-style'] = true;
whiteList['border-bottom-width'] = true;
whiteList['border-collapse'] = true;
whiteList['border-color'] = true;
whiteList['border-image'] = true;
whiteList['border-image-outset'] = true;
whiteList['border-image-repeat'] = true;
whiteList['border-image-slice'] = true;
whiteList['border-image-source'] = true;
whiteList['border-image-width'] = true;
whiteList['border-left'] = true;
whiteList['border-left-color'] = true;
whiteList['border-left-style'] = true;
whiteList['border-left-width'] = true;
whiteList['border-radius'] = true;
whiteList['border-right'] = true;
whiteList['border-right-color'] = true;
whiteList['border-right-style'] = true;
whiteList['border-right-width'] = true;
whiteList['border-spacing'] = true;
whiteList['border-style'] = true;
whiteList['border-top'] = true;
whiteList['border-top-color'] = true;
whiteList['border-top-left-radius'] = true;
whiteList['border-top-right-radius'] = true;
whiteList['border-top-style'] = true;
whiteList['border-top-width'] = true;
whiteList['border-width'] = true;
# whiteList['bottom'] = false;
whiteList['box-decoration-break'] = true;
whiteList['box-shadow'] = true;
whiteList['box-sizing'] = true;
whiteList['box-snap'] = true;
whiteList['box-suppress'] = true;
whiteList['break-after'] = true;
whiteList['break-before'] = true;
whiteList['break-inside'] = true;
# whiteList['caption-side'] = false;
# whiteList['chains'] = false;
whiteList['clear'] = true;
# whiteList['clip'] = false;
# whiteList['clip-path'] = false;
# whiteList['clip-rule'] = false;
whiteList['color'] = true;
whiteList['color-interpolation-filters'] = true;
# whiteList['column-count'] = false;
# whiteList['column-fill'] = false;
# whiteList['column-gap'] = false;
# whiteList['column-rule'] = false;
# whiteList['column-rule-color'] = false;
# whiteList['column-rule-style'] = false;
# whiteList['column-rule-width'] = false;
# whiteList['column-span'] = false;
# whiteList['column-width'] = false;
# whiteList['columns'] = false;
# whiteList['contain'] = false;
# whiteList['content'] = false;
# whiteList['counter-increment'] = false;
# whiteList['counter-reset'] = false;
# whiteList['counter-set'] = false;
# whiteList['crop'] = false;
# whiteList['cue'] = false;
# whiteList['cue-after'] = false;
# whiteList['cue-before'] = false;
# whiteList['cursor'] = false;
# whiteList['direction'] = false;
whiteList['display'] = true;
whiteList['display-inside'] = true;
whiteList['display-list'] = true;
whiteList['display-outside'] = true;
# whiteList['dominant-baseline'] = false;
# whiteList['elevation'] = false;
# whiteList['empty-cells'] = false;
# whiteList['filter'] = false;
# whiteList['flex'] = false;
# whiteList['flex-basis'] = false;
# whiteList['flex-direction'] = false;
# whiteList['flex-flow'] = false;
# whiteList['flex-grow'] = false;
# whiteList['flex-shrink'] = false;
# whiteList['flex-wrap'] = false;
# whiteList['float'] = false;
# whiteList['float-offset'] = false;
# whiteList['flood-color'] = false;
# whiteList['flood-opacity'] = false;
# whiteList['flow-from'] = false;
# whiteList['flow-into'] = false;
whiteList['font'] = true;
whiteList['font-family'] = true;
whiteList['font-feature-settings'] = true;
whiteList['font-kerning'] = true;
whiteList['font-language-override'] = true;
whiteList['font-size'] = true;
whiteList['font-size-adjust'] = true;
whiteList['font-stretch'] = true;
whiteList['font-style'] = true;
whiteList['font-synthesis'] = true;
whiteList['font-variant'] = true;
whiteList['font-variant-alternates'] = true;
whiteList['font-variant-caps'] = true;
whiteList['font-variant-east-asian'] = true;
whiteList['font-variant-ligatures'] = true;
whiteList['font-variant-numeric'] = true;
whiteList['font-variant-position'] = true;
whiteList['font-weight'] = true;
# whiteList['grid'] = false;
# whiteList['grid-area'] = false;
# whiteList['grid-auto-columns'] = false;
# whiteList['grid-auto-flow'] = false;
# whiteList['grid-auto-rows'] = false;
# whiteList['grid-column'] = false;
# whiteList['grid-column-end'] = false;
# whiteList['grid-column-start'] = false;
# whiteList['grid-row'] = false;
# whiteList['grid-row-end'] = false;
# whiteList['grid-row-start'] = false;
# whiteList['grid-template'] = false;
# whiteList['grid-template-areas'] = false;
# whiteList['grid-template-columns'] = false;
# whiteList['grid-template-rows'] = false;
# whiteList['hanging-punctuation'] = false;
whiteList['height'] = true;
# whiteList['hyphens'] = false;
# whiteList['icon'] = false;
# whiteList['image-orientation'] = false;
# whiteList['image-resolution'] = false;
# whiteList['ime-mode'] = false;
# whiteList['initial-letters'] = false;
# whiteList['inline-box-align'] = false;
# whiteList['justify-content'] = false;
# whiteList['justify-items'] = false;
# whiteList['justify-self'] = false;
# whiteList['left'] = false;
whiteList['letter-spacing'] = true;
whiteList['lighting-color'] = true;
# whiteList['line-box-contain'] = false;
# whiteList['line-break'] = false;
# whiteList['line-grid'] = false;
# whiteList['line-height'] = false;
# whiteList['line-snap'] = false;
# whiteList['line-stacking'] = false;
# whiteList['line-stacking-ruby'] = false;
# whiteList['line-stacking-shift'] = false;
# whiteList['line-stacking-strategy'] = false;
whiteList['list-style'] = true;
whiteList['list-style-image'] = true;
whiteList['list-style-position'] = true;
whiteList['list-style-type'] = true;
whiteList['margin'] = true;
whiteList['margin-bottom'] = true;
whiteList['margin-left'] = true;
whiteList['margin-right'] = true;
whiteList['margin-top'] = true;
# whiteList['marker-offset'] = false;
# whiteList['marker-side'] = false;
# whiteList['marks'] = false;
# whiteList['mask'] = false;
# whiteList['mask-box'] = false;
# whiteList['mask-box-outset'] = false;
# whiteList['mask-box-repeat'] = false;
# whiteList['mask-box-slice'] = false;
# whiteList['mask-box-source'] = false;
# whiteList['mask-box-width'] = false;
# whiteList['mask-clip'] = false;
# whiteList['mask-image'] = false;
# whiteList['mask-origin'] = false;
# whiteList['mask-position'] = false;
# whiteList['mask-repeat'] = false;
# whiteList['mask-size'] = false;
# whiteList['mask-source-type'] = false;
# whiteList['mask-type'] = false;
whiteList['max-height'] = true;
# whiteList['max-lines'] = false;
whiteList['max-width'] = true;
whiteList['min-height'] = true;
whiteList['min-width'] = true;
# whiteList['move-to'] = false;
# whiteList['nav-down'] = false;
# whiteList['nav-index'] = false;
# whiteList['nav-left'] = false;
# whiteList['nav-right'] = false;
# whiteList['nav-up'] = false;
# whiteList['object-fit'] = false;
# whiteList['object-position'] = false;
# whiteList['opacity'] = false;
# whiteList['order'] = false;
# whiteList['orphans'] = false;
# whiteList['outline'] = false;
# whiteList['outline-color'] = false;
# whiteList['outline-offset'] = false;
# whiteList['outline-style'] = false;
# whiteList['outline-width'] = false;
# whiteList['overflow'] = false;
# whiteList['overflow-wrap'] = false;
# whiteList['overflow-x'] = false;
# whiteList['overflow-y'] = false;
whiteList['padding'] = true;
whiteList['padding-bottom'] = true;
whiteList['padding-left'] = true;
whiteList['padding-right'] = true;
whiteList['padding-top'] = true;
# whiteList['page'] = false;
# whiteList['page-break-after'] = false;
# whiteList['page-break-before'] = false;
# whiteList['page-break-inside'] = false;
# whiteList['page-policy'] = false;
# whiteList['pause'] = false;
# whiteList['pause-after'] = false;
# whiteList['pause-before'] = false;
# whiteList['perspective'] = false;
# whiteList['perspective-origin'] = false;
# whiteList['pitch'] = false;
# whiteList['pitch-range'] = false;
# whiteList['play-during'] = false;
# whiteList['position'] = false;
# whiteList['presentation-level'] = false;
# whiteList['quotes'] = false;
# whiteList['region-fragment'] = false;
# whiteList['resize'] = false;
# whiteList['rest'] = false;
# whiteList['rest-after'] = false;
# whiteList['rest-before'] = false;
# whiteList['richness'] = false;
# whiteList['right'] = false;
# whiteList['rotation'] = false;
# whiteList['rotation-point'] = false;
# whiteList['ruby-align'] = false;
# whiteList['ruby-merge'] = false;
# whiteList['ruby-position'] = false;
# whiteList['shape-image-threshold'] = false;
# whiteList['shape-outside'] = false;
# whiteList['shape-margin'] = false;
# whiteList['size'] = false;
# whiteList['speak'] = false;
# whiteList['speak-as'] = false;
# whiteList['speak-header'] = false;
# whiteList['speak-numeral'] = false;
# whiteList['speak-punctuation'] = false;
# whiteList['speech-rate'] = false;
# whiteList['stress'] = false;
# whiteList['string-set'] = false;
# whiteList['tab-size'] = false;
# whiteList['table-layout'] = false;
whiteList['text-align'] = true;
whiteList['text-align-last'] = true;
whiteList['text-combine-upright'] = true;
whiteList['text-decoration'] = true;
whiteList['text-decoration-color'] = true;
whiteList['text-decoration-line'] = true;
whiteList['text-decoration-skip'] = true;
whiteList['text-decoration-style'] = true;
whiteList['text-emphasis'] = true;
whiteList['text-emphasis-color'] = true;
whiteList['text-emphasis-position'] = true;
whiteList['text-emphasis-style'] = true;
whiteList['text-height'] = true;
whiteList['text-indent'] = true;
whiteList['text-justify'] = true;
whiteList['text-orientation'] = true;
whiteList['text-overflow'] = true;
whiteList['text-shadow'] = true;
whiteList['text-space-collapse'] = true;
whiteList['text-transform'] = true;
whiteList['text-underline-position'] = true;
whiteList['text-wrap'] = true;
# whiteList['top'] = false;
# whiteList['transform'] = false;
# whiteList['transform-origin'] = false;
# whiteList['transform-style'] = false;
# whiteList['transition'] = false;
# whiteList['transition-delay'] = false;
# whiteList['transition-duration'] = false;
# whiteList['transition-property'] = false;
# whiteList['transition-timing-function'] = false;
# whiteList['unicode-bidi'] = false;
# whiteList['vertical-align'] = false;
# whiteList['visibility'] = false;
# whiteList['voice-balance'] = false;
# whiteList['voice-duration'] = false;
# whiteList['voice-family'] = false;
# whiteList['voice-pitch'] = false;
# whiteList['voice-range'] = false;
# whiteList['voice-rate'] = false;
# whiteList['voice-stress'] = false;
# whiteList['voice-volume'] = false;
# whiteList['volume'] = false;
# whiteList['white-space'] = false;
# whiteList['widows'] = false;
whiteList['width'] = true;
# whiteList['will-change'] = false;
whiteList['word-break'] = true;
whiteList['word-spacing'] = true;
whiteList['word-wrap'] = true;
# whiteList['wrap-flow'] = false;
# whiteList['wrap-through'] = false;
# whiteList['writing-mode'] = false;
# whiteList['z-index'] = false;

# allowed_tags = [i for i in allowed_tags if len(i)]

# print(allowed_tags)

def escaped(s):
    return s.replace('<', '&lt;').replace('>','&gt;')

def sanitize_html(soup, k=0):
    # you have to traverse in reverse to avoid
    # list-index-change-when-manipulated

    for child in reversed(soup.contents):
        tag_name = child.name or ''
        # print('    '*k + tag_name)

        # non-tag
        if not tag_name:

            # text stays
            if type(child)==bs4.element.NavigableString:
                pass

            # others can go
            else:
                child.extract()

        # unwanted tag
        elif tag_name not in allowed_tags:
            child.extract()
            # print('    '*k + tag_name, 'kill')

        # tag
        else:
            # remove unwanted attributes
            attrs = child.attrs.copy()
            for attr_name in attrs:
                if attr_name not in allowed_tags[tag_name] and not attr_name.startswith('data'):
                    del child.attrs[attr_name]
                else:
                    child.attrs[attr_name] = sanitizeAttrValue(
                        tag_name,
                        attr_name,
                        child.attrs[attr_name],
                    )

            # add attributes
            if tag_name in ['area','img','video','audio']: # anything that's not a link
                child.attrs['referrerpolicy']='same-origin'

            if tag_name in ['a']:
                child.attrs['rel']='noopener'

            # recursive descent
            sanitize_html(child,k+1)

xss_cheatsheet = '''
<img src=# onerror\x3D"javascript:alert(1)" >
<input onfocus=javascript:alert(1) autofocus>
<input onblur=javascript:alert(1) autofocus><input autofocus>
<video poster=javascript:javascript:alert(1)//
<body onscroll=javascript:alert(1)><br><br><br><br><br><br>...<br><br><br><br><br><br><br><br><br><br>...<br><br><br><br><br><br><br><br><br><br>...<br><br><br><br><br><br><br><br><br><br>...<br><br><br><br><br><br><br><br><br><br>...<br><br><br><br><input autofocus>
<form id=test onforminput=javascript:alert(1)><input></form><button form=test onformchange=javascript:alert(1)>X
<video><source onerror="javascript:javascript:alert(1)">
<video onerror="javascript:javascript:alert(1)"><source>
<form><button formaction="javascript:javascript:alert(1)">X
<body oninput=javascript:alert(1)><input autofocus>
<math href="javascript:javascript:alert(1)">CLICKME</math>  <math> <maction actiontype="statusline#http://google.com" xlink:href="javascript:javascript:alert(1)">CLICKME</maction> </math>
<frameset onload=javascript:alert(1)>
<table background="javascript:javascript:alert(1)">
<!--<img src="--><img src=x onerror=javascript:alert(1)//">
<comment><img src="</comment><img src=x onerror=javascript:alert(1))//">

<style><img src="</style><img src=x onerror=javascript:alert(1)//">
<li style=list-style:url() onerror=javascript:alert(1)> <div style=content:url(data:image/svg+xml,%%3Csvg/%%3E);visibility:hidden onload=javascript:alert(1)></div>
<head><base href="javascript://"></head><body><a href="/. /,javascript:alert(1)//#">XXX</a></body>
<SCRIPT FOR=document EVENT=onreadystatechange>javascript:alert(1)</SCRIPT>
<OBJECT CLASSID="clsid:333C7BC4-460F-11D0-BC04-0080C7055A83"><PARAM NAME="DataURL" VALUE="javascript:alert(1)"></OBJECT>
<object data="data:text/html;base64,%(base64)s">
<embed src="data:text/html;base64,%(base64)s">
<b <script>alert(1)</script>0
<div id="div1"><input value="``onmouseover=javascript:alert(1)"></div> <div id="div2"></div><script>document.getElementById("div2").innerHTML = document.getElementById("div1").innerHTML;</script>
<x '="foo"><x foo='><img src=x onerror=javascript:alert(1)//'>
<embed src="javascript:alert(1)">
<img src="javascript:alert(1)">
<image src="javascript:alert(1)">
<script src="javascript:alert(1)">
<div style=width:1px;filter:glow onfilterchange=javascript:alert(1)>x
<? foo="><script>javascript:alert(1)</script>">
<! foo="><script>javascript:alert(1)</script>">
</ foo="><script>javascript:alert(1)</script>">
<? foo="><x foo='?><script>javascript:alert(1)</script>'>">
<! foo="[[[Inception]]"><x foo="]foo><script>javascript:alert(1)</script>">
<% foo><x foo="%><script>javascript:alert(1)</script>">
<div id=d><x xmlns="><iframe onload=javascript:alert(1)"></div> <script>d.innerHTML=d.innerHTML</script>
<img \x00src=x onerror="alert(1)">
<img \x47src=x onerror="javascript:alert(1)">
<img \x11src=x onerror="javascript:alert(1)">
<img \x12src=x onerror="javascript:alert(1)">
<img\x47src=x onerror="javascript:alert(1)">
<img\x10src=x onerror="javascript:alert(1)">
<img\x13src=x onerror="javascript:alert(1)">
<img\x32src=x onerror="javascript:alert(1)">
<img\x47src=x onerror="javascript:alert(1)">
<img\x11src=x onerror="javascript:alert(1)">
<img \x47src=x onerror="javascript:alert(1)">
<img \x34src=x onerror="javascript:alert(1)">
<img \x39src=x onerror="javascript:alert(1)">
<img \x00src=x onerror="javascript:alert(1)">
<img src\x09=x onerror="javascript:alert(1)">
<img src\x10=x onerror="javascript:alert(1)">
<img src\x13=x onerror="javascript:alert(1)">
<img src\x32=x onerror="javascript:alert(1)">
<img src\x12=x onerror="javascript:alert(1)">
<img src\x11=x onerror="javascript:alert(1)">
<img src\x00=x onerror="javascript:alert(1)">
<img src\x47=x onerror="javascript:alert(1)">
<img src=x\x09onerror="javascript:alert(1)">
<img src=x\x10onerror="javascript:alert(1)">
<img src=x\x11onerror="javascript:alert(1)">
<img src=x\x12onerror="javascript:alert(1)">
<img src=x\x13onerror="javascript:alert(1)">
<img[a][b][c]src[d]=x[e]onerror=[f]"alert(1)">
<img src=x onerror=\x09"javascript:alert(1)">
<img src=x onerror=\x10"javascript:alert(1)">
<img src=x onerror=\x11"javascript:alert(1)">
<img src=x onerror=\x12"javascript:alert(1)">
<img src=x onerror=\x32"javascript:alert(1)">
<img src=x onerror=\x00"javascript:alert(1)">
<a href=java&#1&#2&#3&#4&#5&#6&#7&#8&#11&#12script:javascript:alert(1)>XXX</a>
<img src="x` `<script>javascript:alert(1)</script>"` `>
<img src onerror /" '"= alt=javascript:alert(1)//">
<title onpropertychange=javascript:alert(1)></title><title title=>
<a href=http://foo.bar/#x=`y></a><img alt="`><img src=x:x onerror=javascript:alert(1)></a>">
<!--[if]><script>javascript:alert(1)</script -->
<!--[if<img src=x onerror=javascript:alert(1)//]> -->
<script src="/\%(jscript)s"></script>
<script src="\\%(jscript)s"></script>
<object id="x" classid="clsid:CB927D12-4FF7-4a9e-A169-56E4B8A75598"></object> <object classid="clsid:02BF25D5-8C17-4B23-BC80-D3488ABDDC6B" onqt_error="javascript:alert(1)" style="behavior:url(#x);"><param name=postdomevents /></object>
<a style="-o-link:'javascript:javascript:alert(1)';-o-link-source:current">X
<style>p[foo=bar{}*{-o-link:'javascript:javascript:alert(1)'}{}*{-o-link-source:current}]{color:red};</style>
<link rel=stylesheet href=data:,*%7bx:expression(javascript:alert(1))%7d
<style>@import "data:,*%7bx:expression(javascript:alert(1))%7D";</style>
<a style="pointer-events:none;position:absolute;"><a style="position:absolute;" onclick="javascript:alert(1);">XXX</a></a><a href="javascript:javascript:alert(1)">XXX</a>
<style>*[{}@import'%(css)s?]</style>X
<div style="font-family:'foo&#10;;color:red;';">XXX
<div style="font-family:foo}color=red;">XXX
<// style=x:expression\28javascript:alert(1)\29>
<style>*{x:ｅｘｐｒｅｓｓｉｏｎ(javascript:alert(1))}</style>
<div style=content:url(%(svg)s)></div>
<div style="list-style:url(http://foo.f)\20url(javascript:javascript:alert(1));">X
<div id=d><div style="font-family:'sans\27\3B color\3Ared\3B'">X</div></div> <script>with(document.getElementById("d"))innerHTML=innerHTML</script>
<div style="background:url(/f#&#127;oo/;color:red/*/foo.jpg);">X
<div style="font-family:foo{bar;background:url(http://foo.f/oo};color:red/*/foo.jpg);">X
<div id="x">XXX</div> <style>  #x{font-family:foo[bar;color:green;}  #y];color:red;{}  </style>
<x style="background:url('x&#1;;color:red;/*')">XXX</x>
<script>({set/**/$($){_/**/setter=$,_=javascript:alert(1)}}).$=eval</script>
<script>({0:#0=eval/#0#/#0#(javascript:alert(1))})</script>
<script>ReferenceError.prototype.__defineGetter__('name', function(){javascript:alert(1)}),x</script>
<script>Object.__noSuchMethod__ = Function,[{}][0].constructor._('javascript:alert(1)')()</script>
<meta charset="x-imap4-modified-utf7">&ADz&AGn&AG0&AEf&ACA&AHM&AHI&AGO&AD0&AGn&ACA&AG8Abg&AGUAcgByAG8AcgA9AGEAbABlAHIAdAAoADEAKQ&ACAAPABi
<meta charset="x-imap4-modified-utf7">&<script&S1&TS&1>alert&A7&(1)&R&UA;&&<&A9&11/script&X&>
<meta charset="mac-farsi">¼script¾javascript:alert(1)¼/script¾
X<x style=`behavior:url(#default#time2)` onbegin=`javascript:alert(1)` >
1<set/xmlns=`urn:schemas-microsoft-com:time` style=`beh&#x41vior:url(#default#time2)` attributename=`innerhtml` to=`&lt;img/src=&quot;x&quot;onerror=javascript:alert(1)&gt;`>
1<animate/xmlns=urn:schemas-microsoft-com:time style=behavior:url(#default#time2) attributename=innerhtml values=&lt;img/src=&quot;.&quot;onerror=javascript:alert(1)&gt;>
<vmlframe xmlns=urn:schemas-microsoft-com:vml style=behavior:url(#default#vml);position:absolute;width:100%;height:100% src=%(vml)s#xss></vmlframe>
1<a href=#><line xmlns=urn:schemas-microsoft-com:vml style=behavior:url(#default#vml);position:absolute href=javascript:javascript:alert(1) strokecolor=white strokeweight=1000px from=0 to=1000 /></a>
<a style="behavior:url(#default#AnchorClick);" folder="javascript:javascript:alert(1)">XXX</a>
<x style="behavior:url(%(sct)s)">
<xml id="xss" src="%(htc)s"></xml> <label dataformatas="html" datasrc="#xss" datafld="payload"></label>
<event-source src="%(event)s" onload="javascript:alert(1)">
<a href="javascript:javascript:alert(1)"><event-source src="data:application/x-dom-event-stream,Event:click%0Adata:XXX%0A%0A">
<div id="x">x</div> <xml:namespace prefix="t"> <import namespace="t" implementation="#default#time2"> <t:set attributeName="innerHTML" targetElement="x" to="&lt;img&#11;src=x:x&#11;onerror&#11;=javascript:alert(1)&gt;">
<script>%(payload)s</script>
<script src=%(jscript)s></script>
<script language='javascript' src='%(jscript)s'></script>
<script>javascript:alert(1)</script>
<IMG SRC="javascript:javascript:alert(1);">
<IMG SRC=javascript:javascript:alert(1)>
<IMG SRC=`javascript:javascript:alert(1)`>
'''

import mistletoe as mt
def just_markdown(s):
    return mt.markdown(s)

# h = just_markdown(xss_cheatsheet)

h = xss_cheatsheet

def walk(node, k=0):
    if hasattr(node, 'children'):
        for child in node.children:
            ns = child.string or ''
            print('    '*k + str(child.name), type(child),'#', ns)
            walk(child, k+1)

def walk_p_texts(soup, f, k=0):
    for child in reversed(soup.contents):
        tagname = child.name or ''

        if not tagname:
            # text stays
            if type(child)==bs4.element.NavigableString:
                f(child, k=k)
            else:
                child.extract()
        else:
            treewalk(child, f, k+1)

if __name__ == '__main__':

    soup = parse_html(h)
    # soup = parse_html(html)
    # print(soup.prettify())
    # walk(soup)

    sanitize_html(soup)

    print('-------')
    # print(soup.prettify())
    walk(soup)

    # soup = parse_html(soup.prettify())
    # sanitize_html(soup)
    #
    # print('-------')
    # print(soup.prettify())

    print('----')

    soup = parse_html('''
    <p>@yes</p>
    <ul><li>@yes</li></ul>
    ''')
