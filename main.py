import logger_config

import time,os,sched,random,threading,traceback,datetime
import re,base64
import zlib

import requests as r

import mimetypes as mt

from commons import *
print = qprint

from aql import *
wait_for_database_online()

dispatch_with_retries(fix_view_loss(None))

import flask
from flask import Flask, g, abort # session
from flask import render_template, request, send_from_directory, make_response

from api import *

# ads
import sys
sys.path.append('./ads')
from advert import ads

import chat

dispatch_with_retries(create_all_necessary_collections)
dispatch_with_retries(dispatch_database_updaters)

from pgp_stuff import pgp_check
dispatch_with_retries(pgp_check)

import i18n_api

from app import app
import leet
import trust_score

import sb1024_encryption

import views
from views import *

def route(r):
    def rr(f):
        app.add_url_rule(r, str(random.random()), f)
    return rr

def path_is_parent(parent_path, child_path):
    # Smooth out relative path names, note: if you are concerned about symbolic links, you should use os.path.realpath too
    parent_path = os.path.realpath(os.path.abspath(parent_path))
    child_path = os.path.realpath(os.path.abspath(child_path))

    # Compare the common path of the parent and child path with the common path of just the parent path. Using the commonpath method on just the parent path will regularise the path name in the same way as the comparison that deals with both paths, removing any trailing path separator
    return os.path.commonpath([parent_path]) == \
        os.path.commonpath([parent_path, child_path])

def route_static(frompath, topath, maxage=1800):
    @route('/'+frompath+'/<path:path>')
    def _(path):
        path = re.sub(r'v=.+?/', '/', path)

        cc = topath+'/'+path

        # check if cc is within topath for security
        if not path_is_parent(topath, cc):
            abort(403, 'Access Denied')

        if not os.path.exists(cc):
            abort(404, 'File not found')
            # return make_response('File not found', 404)

        # with open(cc,'rb') as f:
        #     b = f.read()
        b = readfile(cc)

        resp = make_response(b, 200)
        resp = etag304(resp)

        type, encoding = mt.guess_type(cc)
        if encoding:
            resp.headers['Content-Encoding'] = encoding
        if type:
            resp.headers['Content-Type'] = type

        if maxage!=0:
            resp.headers['Cache-Control']= \
                f'max-age={str(maxage)}, stale-while-revalidate={str(maxage*10)}'

        return resp

route_static('static', 'static')
route_static('images', 'templates/images', 3600*24*5)
route_static('pr_images', 'ads/images', 3600*24*5)
route_static('css', 'templates/css', 3600*24*5)
route_static('js', 'templates/js', 3600*24*5)
route_static('highlight', 'templates/highlight', 3600*24*5)
route_static('jgawb', 'jgawb', 3600*24)
route_static('jicpb', 'jicpb', 3600*24)

@app.route('/favicon.ico')
def favicon():
    b = readfile('templates/images/favicon_new_pressed.png')
    resp = make_response(b, 200)
    resp = etag304(resp)
    resp.headers['Content-Type']='image/png'
    resp.headers['Cache-Control'] = 'max-age=864000'
    return resp

def create_all_necessary_indices():
    ci = IndexCreator.create_indices
    ciut = IndexCreator.create_index_unique_true

    ciut('view_counters', ['targ'])

    ciut('threads', ['tid'])
    ciut('threads', ['bigcats','pinned'], unique=False)
    ciut('threads', ['cid','pinned'], unique=False)
    ci('threads', indexgen(
            [['delete'],['uid'],['delete','cid'],['delete','bigcats[*]'],['delete','tags[*]'],['tags[*]']],
            ['t_u','t_c','nreplies','vc','votes','t_hn','t_hn2','amv','nfavs','t_manual'],
    ))
    ci('threads', indexgen([[]], ['t_hn_u','t_next_hn_update','title','pinned']))

    ci('posts', indexgen(
            [['tid'],['uid'],['tid','delete']],
            ['t_c','vc','votes','nfavs','t_hn','t_hn2'],
    ))

    ciut('categories', ['cid'])

    ciut('users',['uid'])
    ci('users',[['invitation'],['t_next_pr_update']])
    ci('users',indexgen(
        [[],['delete']],
        ['t_c','nposts','nthreads','nlikes','nliked','name','pagerank','trust_score']
    ))

    ci('invitations',indexgen(
        [['uid','active'],['uid']],
        ['t_c'],
    ))

    ci('votes',indexgen(
        [
            ['type','id','vote','uid'],
            ['type','id','uid'],
            ['type','id','vote'],
            ['uid','vote'],
            ['to_uid','vote'],
        ],
        ['t_c'],
    ))

    ci('conversations',[['convid']])
    ci('conversations',indexgen(
        [['uid'],['to_uid'],['uid','to_uid']],
        ['t_u'],
    ))

    ci('messages',indexgen([['convid'],['to_uid']],['t_c']))

    ci('notifications',indexgen([['to_uid'],['to_uid','from_uid','why','url']],['t_c']))
    ci('avatars',[['uid']])
    ci('admins',[['name']])
    ci('aliases',[['is','name'],['name','is']])
    ci('operations',indexgen([['target'],[]], ['t_c']))
    ci('followings', indexgen([['uid','follow'],['to_uid','follow']],['t_c']))
    ci('favorites', indexgen([['uid'],[]], ['t_c','pointer']))
    ci('polls', [['t_c']])
    ci('poll_votes', [['pollid', 'uid'],['pollid', 'choice']])

    ci('blacklist',[['uid','to_uid'],['uid','enabled'],['to_uid','enabled']])

    ci('comments',indexgen([[],['parent'],['parent','deleted'],['uid']],['t_c']))
    ci('questions',indexgen([[],['question']],['t_c']))

    ci('punchcards', [['salt','uid','hostname'],['t_u']])


# filter bots/DOSes that use a fixed UA
'''
不是我说你们，你们要是真会写代码，也不至于过来干这个，我都替你们着急啊
'''
class UAFilter:
    def __init__(self):
        self.d = {}
        self.dt = {}
        self.blacklist = {}

    def timedelta(self, ua):
        this_time = time.time()

        if ua in self.dt:
            last_time = self.dt[ua]
        else:
            last_time = this_time

        duration = max(0.001, this_time - last_time)
        self.dt[ua] = this_time

        return duration

    def cooldown(self, ua):
        duration = self.timedelta(ua)
        factor = 0.6 ** duration

        if ua in self.d:
            self.d[ua] *= factor

    def judge(self, uastring, weight=1., infostring=''):
        ua = uastring

        if ua in self.d:
            self.d[ua]+=1*weight
            if ua in self.blacklist:
                self.d[ua]+=3*weight
        else:
            self.d[ua]=1

        duration = self.timedelta(ua)
        factor = 0.98 ** duration

        self.d[ua] *= factor
        # print(self.d[ua])

        # print_err(self.d[ua])
        if self.d[ua]>50:
            # self.d[ua]+=3*weight

            if self.d[ua]>100 and (ua not in self.blacklist):
                with open('blacklisted.txt', 'a+') as f:
                    f.write(time_iso_now()+' '+ua+' '+infostring+'\n')
                self.blacklist[ua] = infostring
                pass

            return False
        else:
            return True

    def get_max(self):
        m = -998
        kk = 'None'
        for k in self.d:
            if self.d[k]>m:
                m = self.d[k]
                kk = k
        return kk, m

uaf = UAFilter()

okaybots = ['AdsBot-Google-Mobile','googlebot','blexbot','semrushbot','webmeup','ahrefsbot'].map(lambda k:k.lower())

def is_okay_bot(uas):
    uas = uas.lower()
    for botname in okaybots:
        if botname in uas:
            return True
    return False

@app.before_request
def before_request():
    hostname = request.host
    g.hostname = hostname

    # redirection
    if hostname[0:4]=='www.':
        resp = make_response('For Aesthetics', 307)
        goto = request.scheme+'://'+hostname[4:]+ request.full_path
        goto = goto[:-1] if goto[-1]=='?' else goto
        resp.headers['Location'] = goto
        log_err('307 from',hostname,'to', goto)
        return resp

    g.request_start_time = time.monotonic()
    g.get_elapsed = lambda: int((time.monotonic() - g.request_start_time)*1000)

    rh = request.headers

    # request figerprinting
    acceptstr = rh['Accept'] if 'Accept' in rh else 'NoAccept'

    uas = rh['User-Agent'] if 'User-Agent' in rh else 'NoUA'

    g.user_agent_string = uas
    ipstr = request.remote_addr

    is_local = ipstr[0:8]=='192.168.'

    g.display_ip_address = '[hidden]' if is_local else ipstr

    if 'action' in request.args and request.args['action']=='ping':
        is_ping = True
    else:
        is_ping = False

    rp = request.path
    def rpsw(s): return rp.startswith(s)

    is_avatar = rpsw('/avatar/')

    is_static = is_avatar or rpsw('/js/') or rpsw('/css/') or rpsw('/images/') or rpsw('/qr/') or rpsw('/pr_images/')

    # rate limiting does not need to be applied to those paths
    non_critical_paths = (
        is_static
        or is_ping
        or (rpsw('/login'))
        or (rpsw('/logout'))
        or (rpsw('/register'))
    )

    session = load_session() # a dict
    g.session = session

    if 'browser' not in session:
        ub = g.using_browser = False
    else:
        ub = g.using_browser = True

    browserstr = 'browser' if ub else '==naked=='

    if 'locale' in session:
        g.locale = session['locale']
        if g.locale=='zh':
            g.locale = 'zh-cn'
    else:
        if is_mohu_2047_name():
            g.locale = 'zh-mohu'
        else:
            g.locale = 'zh-cn'

    salt = get_current_salt()

    # ----

    # log the user in
    g.selfuid = 0
    g.logged_in = False
    g.current_user = False
    g.is_admin = False

    g.is_static = is_static

    g.after_request_cb = None

    if (not is_static):
        if 'uid' in session and session['uid']:
            uid = int(session['uid'])
            g.logged_in = get_user_by_id_admin(uid)

            if g.logged_in: # okay uid
                cu = g.current_user = g.logged_in
                g.selfuid = cu['uid']

                g.is_admin = bool(cu['admin'])

                # when is the last time you check your inbox?
                if 't_inbox' not in cu: cu['t_inbox'] = '1989-06-04T00:00:00'

                # when is the last time you check your notifications?
                if 't_notif' not in cu: cu['t_notif'] = '1989-06-04T00:00:00'

                if 'nnotif' not in cu: cu['nnotif'] = 0
                if 'ninbox' not in cu: cu['ninbox'] = 0

                cu['num_unread']=cu['ninbox']
                cu['num_notif']=cu['nnotif']

                g.after_request_cb = lambda:(
                    qprint(
                        colored_err(ipstr),
                        colored_info(f'({uid}) {cu["name"]}'),
                        browserstr,
                        colored_info(salt),
                        colored_down(hostname),
                        colored_err(str(g.get_elapsed())+'ms'),
                        )
                    )
                return # done

            else: # bad uid
                pass
        else: # no uid not static
            g.after_request_cb = lambda:(
                qprint(
                    colored_err(ipstr),
                    # f'({uid}) {cu["name"]}',
                    browserstr,
                    colored_info(salt),
                    colored_down(hostname),
                    colored_err(str(g.get_elapsed())+'ms'),
                    )
                )

    else: # is static
        if salt!='==nosalt==' and ub: # browser user
            return


    weight = 1.
    if is_local:
        weight *= 1.5 # be more strict on tor side
    if acceptstr=='NoAccept':
        weight *= 1.

    '''
    你们这样不行的啊！！
    '''

    uasl = uas.lower()

    # filter bot/dos requests
    allowed = (
        # uaf.judge(uas, weight) and
        # uaf.judge(acceptstr, weight) and
        # is_okay_bot(uas) or
        (uaf.judge(ipstr, weight, infostring=uas) if not is_local else True)

        and (ipstr!='45.155.205.206')
    )

    def uafd(k):
        if k in uaf.d:
            return uaf.d[k]
        else:
            return 0

    if not allowed:
        log_err(f'block [{ipstr}]({uafd(ipstr):.2f}) {hostname} {uas}\n'
        +f'bl:{list(uaf.blacklist.keys()).join(",")}')


        if 0 and (not is_okay_bot(uas) or 1) and (ipstr in uaf.blacklist) or (ipstr=='45.155.205.206'):

            resp = make_response('rate limit exceeded', 307)
            resp.headers['Location'] = 'https://community.geph.io/'
            return resp
        else:
            return make_response('rate limit exceeded', 429)

    else:
        # log_up(f'allow [{ipstr}]({uafd(ipstr):.1f}) {hostname} {uas}')
        pass


# @app.route('/u/<int:uid>/favorited')
# def user_favorited(uid):
#     lpointers = aql('''
#     for i in favorites
#     filter i.to_uid==@uid
#     sort i.t_c desc
#
#     // let item = document(i.pointer)
#     return i.pointer
#
#     // return merge(i, {item})
#     ''', uid=uid, silent=True)
#
#     u = get_user_by_id(uid)
#     litem = resolve_mixed_content_pointers(lpointers)
#
#     return render_template_g(
#         'favorites.html.jinja',
#         page_title = u['name']+' 被其他人收藏的内容',
#         list_items = litems,
#     )
#     # return str(litems)

@app.route('/404/<string:to_show>')
def f404(to_show):
    if 'reason' in request.args:
        reason = request.args['reason']
    else:
        reason = ''

    return render_template_g('404.html.jinja',
        page_title='404',
        to_show=to_show,
        reason = reason,
    )

@app.route('/robots.txt')
def robots():
    s = readfile('templates/robots.txt', 'r')
    resp = make_text_response(s)
    return resp

@app.route('/templates/<path:path>')
def templates(path):
    return render_template_g(f'{path}.html.jinja',
        page_title = path,
    )

@app.route('/502')
def e502():
    return make_response('502', 502)

@app.errorhandler(404)
def e404(e):
    err = str(e) or str(e.original_exception) or str(e.original_exception.__class__.__name__)
    return render_template_g('404.html.jinja',
        page_title='404',
        err=err,
    ), 404

@app.errorhandler(500)
def e5001(e):
    err = str(e.original_exception) or str(e.original_exception.__class__.__name__)
    print(f"{err}",len(err))
    return render_template_g('404.html.jinja',
        page_title='500',
        e500=True,
        err=err,
    ), 500

@app.after_request
def after_request(response):
    # save_session(response)

    # punch!
    # tpe.submit(put_punchcard)
    put_punchcard()
    k = g.after_request_cb
    if k is not None:
        k()

    return response

from template_globals import tgr; tgr.update(globals())

if __name__ == '__main__':
    dispatch_with_retries(create_all_necessary_indices)

    port = get_environ('PORT') or 5000

    if not get_environ('PROFILE'):
        if get_environ('DEBUG'):
            app.run(host='0.0.0.0', port=port, debug=True)
        else:
            app.run(host='0.0.0.0', port=port)

    else:
        import yappi # Dobrosław Żybort
        yappi.start()
        app.run(host='0.0.0.0', port=port)
        # profile_this("app.run(host='0.0.0.0', port=port)")

        yappi.stop()
        stats = yappi.get_func_stats()
        stats.sort('tavg','desc')
        stats.print_all(out=open('prof/out.txt','w'))
