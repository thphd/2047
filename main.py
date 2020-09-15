from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '%(levelname)s/%(module)s %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

import time,os,sched,random,threading,traceback,datetime
import re,base64
import zlib

import requests as r

import Identicon
Identicon._crop_coner_round = lambda a,b:a # don't cut corners, please
import mimetypes as mt

from commons import *

from flask_cors import CORS

from flask import Flask, session, g, abort
from flask import render_template, request, send_from_directory, make_response
# from flask_gzip import Gzip

from werkzeug.middleware.proxy_fix import ProxyFix

from api import api_registry, get_categories_info, get_url_to_post, get_url_to_post_given_details
from api import *

from quotes import get_quote

# init_directory('./static/')
# init_directory('./static/upload/')

def get_secret():
    fn = 'secret.bin'
    if os.path.exists(fn):
        f = open(fn, 'rb');r = f.read();f.close()
    else:
        r = os.urandom(32)
        f = open(fn, 'wb');f.write(r);f.close()
    return r

app = Flask(__name__, static_url_path='')

app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

app.secret_key = get_secret()
CORS(app)
from flask_response_gzip import gzipify
gzipify(app)

def route(r):
    def rr(f):
        app.add_url_rule(r, str(random.random()), f)
    return rr

def calculate_etag(bin):
    checksum = zlib.adler32(bin)
    chksum_encoded = base64.b64encode(checksum.to_bytes(4,'big')).decode('ascii')
    return chksum_encoded

# hash all resource files see if they change
def hash_these(path_arr, pattern='*.*'):
    resource_files_contents = b''
    for path in path_arr:
        import glob
        files = glob.glob(path+pattern)

        for fn in files:
            print_info('checking file:', fn)
            with open(fn, 'rb') as f:
                resource_files_contents += f.read()

    resource_files_hash = calculate_etag(resource_files_contents)
    return resource_files_hash

resource_files_hash = hash_these(['templates/css/', 'templates/js/'])
print_info('resource_files_hash:', resource_files_hash)

images_resources_hash = hash_these(['templates/images/'], '*.png')
print_info('images_resources_hash:', images_resources_hash)

def route_static(frompath, topath, maxage=1800):
    @route('/'+frompath+'/<path:path>')
    def _(path):
        cc = topath+'/'+path
        if not os.path.exists(cc):
            abort(404, 'File not found')
            # return make_response('File not found', 404)

        with open(cc,'rb') as f:
            b = f.read()

        resp = make_response(b, 200)
        resp = etag304(resp)

        type, encoding = mt.guess_type(cc)
        if encoding:
            resp.headers['Content-Encoding'] = encoding
        if type:
            resp.headers['Content-Type'] = type

        if maxage!=0:
            resp.headers['Cache-Control']= 'max-age='+str(maxage)

        return resp

route_static('static', 'static')
route_static('images', 'templates/images', 3600*24*5)
route_static('css', 'templates/css', 3600*24*5)
route_static('js', 'templates/js', 3600*24*5)
route_static('jgawb', 'jgawb', 1800)
route_static('jicpb', 'jicpb', 1800)

def create_all_necessary_indices():
    # create index
    def ci(coll,aa):
        for a in aa:
            print('creating index on',coll,a)
            aqlc.create_index(coll, type='persistent', fields=a,
                unique=False,sparse=False)

    # create index with unique=True
    def ciut(coll, a):
        for ai in a:
            print('creating index on',coll,[ai])
            aqlc.create_index(coll, type='persistent', fields=[ai], unique=True, sparse=False)

    ciut('threads', ['tid'])
    ci('threads', indexgen(
            [['delete'],['uid'],['delete','cid']],
            ['t_u','t_c','nreplies','vc','votes','t_hn'],
    ))
    ci('threads', indexgen([[]], ['t_hn_u']))

    ci('posts', indexgen(
            [['tid'],['uid'],['tid','delete']],
            ['t_c','vc','votes'],
    ))

    ciut('categories', ['cid'])

    ciut('users',['uid'])
    ci('users',[['invitation']])
    ci('users',indexgen(
        [[],['delete']],
        ['t_c','nposts','nthreads','nlikes','nliked','name']
    ))

    ci('invitations',indexgen(
        [['uid','active'],['uid']],
        ['t_c'],
    ))

    ci('votes',indexgen(
        [
            ['type','id','vote','uid'],
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

is_integer = lambda i:isinstance(i, int)
class Paginator:
    def __init__(self,):
        pass

    def get_user_list(self,
        sortby='uid',
        order='desc',
        pagesize=50,
        pagenumber=1,
        path=''):

        assert sortby in ['t_c','uid','nthreads','nposts','nlikes','nliked','name'] # future can have more.
        # sortby = 't_c'
        assert order in ['desc', 'asc']

        pagenumber = max(1, pagenumber)

        start = (pagenumber-1)*pagesize
        count = pagesize

        mode = 'user'

        querystring_complex = '''
        for u in users
        sort u.{sortby} {order}
        limit {start},{count}

        //let stat = {{
        //    nthreads:length(for t in threads filter t.uid==u.uid return t),
        //    nposts:length(for p in posts filter p.uid==u.uid return p),
        //}}

        let invite = (for i in invitations filter i._key==u.invitation return i)[0]
        let invited_by = invite.uid
        let ip_addr = invite.ip_addr

        return merge(u, {{invited_by, ip_addr}}) //merge(u, stat)
        '''.format(sortby=sortby, order=order,
        start=start, count=count,)

        querystring_simple = 'return length(for u in users return 1)'

        num_users = aql(querystring_simple, silent=True)[0]
        userlist = aql(querystring_complex, silent=True)

        pagination_obj = self.get_pagination_obj(num_users, pagenumber, pagesize, order, path, sortby, mode=mode)

        for u in userlist:
            userfill(u)
            # u['profile_string'] = u['name']

        return userlist, pagination_obj

    def get_post_one(self, pid):
        selfuid = g.selfuid

        qs = '''for i in posts filter i._key==@pid

        let u = (for u in users filter u.uid==i.uid return u)[0]
        let self_voted = length(for v in votes filter v.uid==@selfuid and v.id==to_number(i._key) and v.type=='post' and v.vote==1 return v)

        return merge(i, {user:u},{self_voted})
        '''

        ps = aql(qs, pid=str(pid),selfuid=selfuid, silent=True)
        if len(ps)<1: return False
        ps = ps[0]
        return ps

    def get_post_list(self,
        by='thread',
        tid=0,
        uid=0,

        sortby='t_c',
        order='desc',
        pagesize=50,
        pagenumber=1,

        path='',
        mode=''):

        assert by in ['thread', 'user','all']
        assert is_integer(tid)
        assert is_integer(uid)

        assert sortby in ['t_c','votes']
        # sortby = 't_c'
        assert order in ['desc', 'asc']

        pagenumber = max(1, pagenumber)

        start = (pagenumber-1)*pagesize
        count = pagesize

        if by=='thread':
            filter = 'filter i.tid == {}'.format(tid)

            if mode=='question':
                mode='post_q'
            else:
                mode='post'

        elif by=='user': # filter by user
            filter = 'filter i.uid == {}'.format(uid)
            mode='user_post'
        elif by=='all':
            filter = ''
            mode='user_post'

        selfuid = g.selfuid

        querystring_complex = '''
        for i in posts
        {filter}

        let u = (for u in users filter u.uid==i.uid return u)[0]
        let self_voted = length(for v in votes filter v.uid=={selfuid} and v.id==to_number(i._key) and v.type=='post' and v.vote==1 return v)

        sort i.{sortby} {order}
        limit {start},{count}
        return merge(i, {{user:u}},{{self_voted}})
        '''.format(
            selfuid = selfuid,
            sortby = sortby,order=order,start=start,count=count,filter=filter,
        )

        querystring_simple = '''
        return length(for i in posts {filter} return i)
        '''.format(filter=filter)

        count = aql(querystring_simple, silent=True)[0]
        # print('done',time.time()-ts);ts=time.time()

        postlist = aql(querystring_complex, silent=True)
        # print('done',time.time()-ts);ts=time.time()

        # uncomment if you want floor number in final output.
        # for idx, p in enumerate(postlist):
        #     p['floor_num'] = idx + start + 1

        pagination_obj = self.get_pagination_obj(count, pagenumber, pagesize, order, path, sortby, mode=mode)

        remove_duplicate_brief(postlist)

        return postlist, pagination_obj

    def get_thread_list(self,
        by='category',
        category='all',
        uid=0,
        sortby='t_u',
        order='desc',
        pagesize=50,
        pagenumber=1,
        path=''):

        ts = time.time()

        assert by in ['category', 'user']
        assert category=='all' or category=='deleted' or is_integer(category)
        assert is_integer(uid)
        assert sortby in ['t_u', 't_c', 'nreplies', 'vc', 'votes','t_hn']
        assert order in ['desc', 'asc']

        pagenumber = max(1, pagenumber)
        assert pagesize<=50

        start = (pagenumber-1)*pagesize
        count = pagesize

        if by=='category':
            if category=='all':
                filter = 'filter i.delete==null'
            elif category=='deleted':
                filter = 'filter i.delete==true'
            else:
                filter = 'filter i.cid == {} and i.delete!=true'.format(category)
            mode='thread'
        else: # filter by user
            filter = 'filter i.uid == {}'.format(uid)
            mode='user_thread'

        querystring_complex = '''
        for i in threads

        let u = (for u in users filter u.uid == i.uid return u)[0]
        let fin = (for p in posts filter p.tid == i.tid sort p.t_c desc limit 1 return p)[0]
        //let count = length(for p in posts filter p.tid==i.tid return p)
        let count = i.nreplies
        let ufin = (for j in users filter j.uid == fin.uid return j)[0]
        let c = (for c in categories filter c.cid==i.cid return c)[0]

        {filter}

        sort i.{sortby} {order}
        limit {start},{count}
        let kk = unset(i,'content')
        return merge(i, {{user:u, last:unset(fin,'content'), lastuser:ufin, cname:c.name, count:count}})
         '''.format(
                sortby = sortby,
                order = order,
                start = start,
                count = count,
                filter = filter,
        )

        querystring_simple = '''
        return length(for i in threads {filter} return i)
        '''.format(filter=filter)

        count = aql(querystring_simple, silent=True)[0]
        # print('done',time.time()-ts);ts=time.time()

        threadlist = aql(querystring_complex, silent=True)
        # print('done',time.time()-ts);ts=time.time()

        pagination_obj = self.get_pagination_obj(count, pagenumber, pagesize, order, path, sortby, mode)

        for t in threadlist:
            if 'content' in t:
                tc = t['content']
                ytb_videos = extract_ytb(tc)
                t['youtube'] = ytb_videos[0] if len(ytb_videos) else None
                t['content'] = None

        remove_duplicate_brief(threadlist)

        return threadlist, pagination_obj

    def get_pagination_obj(self, count, pagenumber, pagesize, order, path, sortby, mode='thread', postfix=''):
        # total number of pages
        total_pages = max(1, (count-1) // pagesize +1)

        if total_pages > 1:
            # list of surrounding numbers
            slots = [pagenumber]
            for i in range(1,9):
                if len(slots)>=9:
                    break
                if pagenumber+i <= total_pages:
                    slots.append(pagenumber+i)
                if len(slots)>=9:
                    break
                if pagenumber-i >= 1:
                    slots.insert(0, pagenumber-i)

            # first and last numbers
            slots[0] = 1
            slots[-1]=total_pages

            # second first and second last numbers
            if len(slots)>5:
                if slots[0]!=slots[2]-2:
                    slots[1] = (slots[0]+slots[2]) // 2
                if slots[-1]!=slots[-3]+2:
                    slots[-2] = (slots[-1]+slots[-3]) // 2

        else:
            slots = []

        defaults = None
        # if a parameter is at its default value,
        # don't put it into url query params
        if mode=='thread':
            defaults = thread_list_defaults
        elif mode=='post':
            defaults = post_list_defaults
        elif mode=='post_q':
            defaults = post_list_defaults_q

        elif mode=='user_thread':
            defaults = user_thread_list_defaults
        elif mode=='user_post':
            defaults = user_post_list_defaults
        elif mode=='user':
            defaults = user_list_defaults
        elif mode=='invitation':
            defaults = inv_list_defaults
        else:
            raise Exception('unsupported mode')

        # querystring calculation for each of the paginator links.
        def querystring(pagenumber, pagesize, order, sortby):
            ql = [] # query list

            if pagenumber!=defaults['pagenumber']:
                ql.append(('page', pagenumber))

            if pagesize!=defaults['pagesize']:
                ql.append(('pagesize', pagesize))

            if sortby!=defaults['sortby']:
                ql.append(('sortby', sortby))

            if 'get_default_order' not in defaults:
                default_order = defaults['order']
            else:
                default_order = defaults['get_default_order'](sortby)

            if order!=default_order:
                ql.append(('order', order))

            # join the kv pairs together
            qs = '&'.join(['='.join([str(j) for j in k]) for k in ql])

            # question mark
            if len(qs)>0:
                qs = path+'?'+qs
            else:
                qs = path

            return qs+postfix

        slots = [(i, querystring(i, pagesize, order, sortby), i==pagenumber) for i in slots]

        orders = [
            ('降序', querystring(pagenumber, pagesize, 'desc', sortby), order=='desc','大的排前面'),
            ('升序', querystring(pagenumber, pagesize, 'asc', sortby), order=='asc','小的排前面')
        ]

        sortbys = [
        ('综合', querystring(pagenumber, pagesize, order, 't_hn'), 't_hn'==sortby,'HackerNews 排序'),
        ('更新', querystring(pagenumber, pagesize, order, 't_u'), 't_u'==sortby,'按最后回复时间排序'),
        ('发表', querystring(pagenumber, pagesize, order, 't_c'), 't_c'==sortby,'按发表时间排序'),

        ('回复', querystring(pagenumber, pagesize, order, 'nreplies'), 'nreplies'==sortby,'按照回复数量排序'),
        ('点赞', querystring(pagenumber, pagesize, order, 'votes'), 'votes'==sortby,'按照得票（赞）数排序'),
        ('浏览', querystring(pagenumber, pagesize, order, 'vc'), 'vc'==sortby,'按照被浏览次数排序'),
        ]

        sortbys2 = [
        ('UID',querystring(pagenumber, pagesize, order, 'uid'),
            'uid'==sortby),
        ('户名', querystring(pagenumber, pagesize, order, 'name'),
            'name'==sortby),

        ('主题数', querystring(pagenumber, pagesize, order, 'nthreads'),
            'nthreads'==sortby),
        ('评论数', querystring(pagenumber, pagesize, order, 'nposts'),
            'nposts'==sortby),

        ('点赞', querystring(pagenumber, pagesize, order, 'nliked'),
            'nliked'==sortby),
        ('被赞', querystring(pagenumber, pagesize, order, 'nlikes'),
            'nlikes'==sortby),
        ]

        if mode=='post' or mode=='post_q':
            sortbys3 = [
                ('时间',querystring(pagenumber, pagesize, 'asc', 't_c'), 't_c'==sortby),
                ('票数',querystring(pagenumber, pagesize, 'desc', 'votes'), 'votes'==sortby),
            ]
        elif mode=='user_post':
            sortbys3 = [
                ('时间',querystring(pagenumber, pagesize, 'desc', 't_c'), 't_c'==sortby),
                ('票数',querystring(pagenumber, pagesize, 'desc', 'votes'), 'votes'==sortby),
            ]

        button_groups = []

        if len(slots):
            button_groups.append([])
            button_groups.append(slots)

            if pagenumber!=1:
                button_groups[0].insert(0,('上一页',querystring(pagenumber-1, pagesize, order,sortby)))

            if pagenumber!=total_pages:
                button_groups[0].insert(0, ('下一页',querystring(pagenumber+1, pagesize, order, sortby)))

        # no need to sort if number of items < 2
        if count>3:
            button_groups.append(orders)

            if mode=='thread' or mode=='user_thread':
                button_groups.append(sortbys)

            if mode=='user':
                button_groups.append(sortbys2)

            if mode=='post' or mode=='user_post' or mode=='post_q':
                button_groups.append(sortbys3)

            button_groups.append([('共 {:d}'.format(count), '')])

        return {
            'button_groups':button_groups,
            'count':count,
        }

pgnt = Paginator()

def key(d, k):
    if k in d:
        return d[k]
    else:
        return None

# return requests.args[k] as int or 0
def rai(k):
    v = key(request.args,k)
    return int(v) if v else 0

# return requests.args[k] as string or ''
def ras(k):
    v = key(request.args,k)
    return str(v) if v else ''

# filter bots/DOSes that use a fixed UA
'''
不是我说你们，你们要是真会写代码，也不至于过来干这个，我都替你们着急啊
'''
class UAFilter:
    def __init__(self):
        self.d = {}
        self.dt = {}
        self.blacklist = ''

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

    def judge(self, uastring, weight=1.):
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
        if self.d[ua]>45:
            self.d[ua]+=3*weight

            if self.d[ua]>75 and (ua not in self.blacklist):
                self.blacklist+=ua

            return False
        else:
            return True

    def get_max(self):
        k = max(self.d)
        return k, self.d[k]

uaf = UAFilter()
sessiondict = dict()

def log_info(*a):
    text = ' '.join(map(lambda i:str(i), a))
    app.logger.warning(colored_info(text))
def log_up(*a):
    text = ' '.join(map(lambda i:str(i), a))
    app.logger.warning(colored_up(text))
def log_down(*a):
    text = ' '.join(map(lambda i:str(i), a))
    app.logger.warning(colored_down(text))
def log_err(*a):
    text = ' '.join(map(lambda i:str(i), a))
    app.logger.warning(colored_err(text))

@app.before_request
def before_request():
    # redirection
    if request.host[0:4]=='www.':
        resp = make_response('For Aesthetics', 307)
        goto = request.scheme+'://'+request.host[4:]+ request.full_path
        goto = goto[:-1] if goto[-1]=='?' else goto
        resp.headers['Location'] = goto
        log_err('307 from',request.host,'to', goto)
        return resp

    # request figerprinting
    acceptstr = request.headers['Accept'] if 'Accept' in request.headers else 'NoAccept'
    uas = str(request.user_agent) if request.user_agent else 'NoUA'
    ipstr = request.remote_addr

    is_local = ipstr[0:8]=='192.168.'

    g.display_ip_address = '[hidden]' if is_local else ipstr
    g.request_start_time = time.time()
    g.get_elapsed = lambda: int((time.time() - g.request_start_time)*1000)

    if 'browser' not in session:
        g.using_browser = False
    else:
        g.using_browser = True

    session.permanent = True

    # ----

    if 'action' in request.args and request.args['action']=='ping':
        is_ping = True
    else:
        is_ping = False

    # avatar requests can go.
    is_avatar = request.path.startswith('/avatar/')
    path_critical = (
        (not is_ping)
        and (not is_avatar)
        and (not request.path.startswith('/login'))
        and (not request.path=='/')
        and (not request.path.startswith('/js/'))
        and (not request.path.startswith('/css/'))
        and (not request.path.startswith('/images/'))
        and (not request.path.startswith('/api'))
    )

    # log the user in
    g.selfuid = 0
    g.logged_in = False
    g.current_user = False
    g.is_admin = False

    if 'uid' in session:
        g.logged_in = get_user_by_id_admin(int(session['uid']))
        g.current_user = g.logged_in
        g.selfuid = g.logged_in['uid']
        # print(g.selfuid,'selfuid')
        g.is_admin = True if g.current_user['admin'] else False

        if not is_avatar:
            # print_info(g.logged_in['name'], 'browser' if g.using_browser else '')
            log_info(g.logged_in['name'], 'browser' if g.using_browser else '')

        # print_err(request.headers)
        if path_critical or 1:

            # when is the last time you check your inbox?
            if 't_inbox' not in g.current_user:
                g.current_user['t_inbox'] = '1989-06-04T00:00:00'

            # when is the last time you check your notifications?
            if 't_notif' not in g.current_user:
                g.current_user['t_notif'] = '1989-06-04T00:00:00'

            if 'nnotif' not in g.current_user:
                g.current_user['nnotif'] = 0
            if 'ninbox' not in g.current_user:
                g.current_user['ninbox'] = 0

            g.current_user['num_unread']=g.current_user['ninbox']
            g.current_user['num_notif']=g.current_user['nnotif']

        uaf.cooldown(uas)
        uaf.cooldown(acceptstr)

        # if you're logged in then end of story
        return

    if g.using_browser and path_critical:
        log_info(ipstr, 'using browser')

    # now seems you're not logged in. we have to be more strict to you

    if not path_critical or g.using_browser:
        # uaf.cooldown(uas)
        uaf.cooldown(acceptstr)
        return

    weight = 1.
    if is_local:
        weight = 5.

    # if is_local:
    #     # no tor crawler allowed
    #     return ('rate limit exceeded. if you think this is a mistake, please notify our engineers.', 429)

    # filter bot/dos requests
    allowed = \
        uaf.judge(uas, weight) and\
        uaf.judge(acceptstr, weight) and\
        (uaf.judge(ipstr, weight) if not is_local else True)

    if not allowed:
        log_err('[{}][{}][{}][{:.2f}][{:.2f}][{:.2f}]'.format(uas, acceptstr[-50:], ipstr, uaf.d[uas], uaf.d[acceptstr], uaf.d[ipstr] if ipstr in uaf.d else -1))

        if random.random()>0:
            return ('rate limit exceeded', 429)
        elif random.random()>0.02:
            return (b'please wait a moment before accesing this page'+base64.b64encode(os.urandom(int(random.random()*256))), 200)
        else:
            pass
    else:
        m = uaf.get_max()
        log_up('max: [{}][{:.2f}][{}]'.format(m[0][-50:],m[1], uaf.blacklist))

def tryint(str):
    try:
        a = int(str)
    except:
        a = False
    return a

def remove_hidden_from_visitor(threadlist):
    if g.current_user and 'ignored_categories' in g.current_user:
        cats = g.current_user['ignored_categories']
        cats = cats.split(',')
        cats = [tryint(c.strip()) for c in cats]
        cats = [c for c in cats if c]

        if len(cats)>0:
            hidden_list = cats
        else:
            hidden_list = hidden_from_visitor
    else:
        hidden_list = hidden_from_visitor

    ntl = []
    for i in threadlist:
        if 'cid' in i:
            if i['cid'] not in hidden_list:
                ntl.append(i)
    threadlist=ntl
    return threadlist

def visitor_error_if_hidden(cid):
    if cid in hidden_harder_from_visitor:
        if not g.logged_in:
            raise Exception('you must log in to see whatever\'s inside')

@app.route('/')
@app.route('/c/all')
def get_all_threads():
    pagenumber = rai('page') or thread_list_defaults['pagenumber']
    pagesize = rai('pagesize') or thread_list_defaults['pagesize']
    order = ras('order') or thread_list_defaults['order']
    sortby = ras('sortby') or thread_list_defaults['sortby']

    rpath = request.path
    # print(request.args)

    threadlist, pagination = pgnt.get_thread_list(
        by='category', category='all', sortby=sortby, order=order,
        pagenumber=pagenumber, pagesize=pagesize,
        path = rpath)

    categories=get_categories_info()

    if not g.logged_in:
        threadlist = remove_hidden_from_visitor(threadlist)
        categories = remove_hidden_from_visitor(categories)
    else:
        threadlist = remove_hidden_from_visitor(threadlist)

    return render_template_g('threadlist.html.jinja',
        page_title='所有分类',
        threadlist=threadlist,
        pagination=pagination,
        categories=categories,
        # threadcount=count,

    )

@app.route('/c/deleted')
def delall():
    pagenumber = rai('page') or thread_list_defaults['pagenumber']
    pagesize = rai('pagesize') or thread_list_defaults['pagesize']
    order = ras('order') or thread_list_defaults['order']
    sortby = ras('sortby') or thread_list_defaults['sortby']

    rpath = request.path

    threadlist, pagination = pgnt.get_thread_list(
        by='category', category='deleted', sortby=sortby, order=order,
        pagenumber=pagenumber, pagesize=pagesize,
        path = rpath)

    return render_template_g('threadlist.html.jinja',
        page_title='所有分类',
        threadlist=threadlist,
        pagination=pagination,
        categories=get_categories_info(),
        # threadcount=count,

    )

@app.route('/u/all')
def alluser():
    uld = user_list_defaults
    pagenumber = rai('page') or uld['pagenumber']
    pagesize = rai('pagesize') or uld['pagesize']
    sortby = ras('sortby') or uld['sortby']
    order = ras('order') or uld['get_default_order'](sortby)

    rpath = request.path

    userlist, pagination = pgnt.get_user_list(
        sortby=sortby, order=order,
        pagenumber=pagenumber, pagesize=pagesize,
        path = rpath)

    return render_template_g('userlist.html.jinja',
        page_title='所有用户',
        # threadlist=threadlist,
        userlist = userlist,
        pagination=pagination,
        # threadcount=count,

    )

@app.route('/p/<int:pid>')
def getpost(pid):
    p = get_post(pid)
    url = get_url_to_post(str(pid))
    resp = make_response('', 307)
    resp.headers['Location'] = url
    resp.headers['Cache-Control']= 'max-age=86400'

    # user_is_self = p['uid'] == g.selfuid
    # if not user_is_self: increment_view_counter('post', pid)

    return resp

@app.route('/p/<int:pid>/code')
def getpostcode(pid):
    if not can_do_to(g.current_user,'view_code', -1):
        abort(404, 'forbidden')

    p = aql('for p in posts filter p._key==@k return p',k=str(pid), silent=True)[0]
    resp = make_response(p['content'], 200)
    resp.headers['Cache-Control']='max-age=1800'
    resp.headers['Content-Type']='text/plain; charset=UTF-8'
    return resp

@app.route('/t/<int:tid>/code')
def getthreadcode(tid):
    if not can_do_to(g.current_user,'view_code', -1):
        abort(404, 'forbidden')

    p = aql('for p in threads filter p.tid==@k return p',k=tid, silent=True)[0]
    resp = make_response(p['content'], 200)
    resp.headers['Cache-Control']='max-age=1800'
    resp.headers['Content-Type']='text/plain; charset=UTF-8'
    return resp

@app.route('/c/<int:cid>')
def get_category_threads(cid):
    catobj = aql('for c in categories filter c.cid==@cid return c',cid=cid, silent=True)

    if len(catobj)!=1:
        abort(404, 'category not exist')

    visitor_error_if_hidden(cid)

    catobj = catobj[0]

    pagenumber = rai('page') or thread_list_defaults['pagenumber']
    pagesize = rai('pagesize') or thread_list_defaults['pagesize']
    order = ras('order') or thread_list_defaults['order']
    sortby = ras('sortby') or thread_list_defaults['sortby']

    rpath = request.path
    # print(request.args)

    threadlist, pagination = pgnt.get_thread_list(
        by='category', category=cid,
        sortby=sortby,
        order=order,
        pagenumber=pagenumber, pagesize=pagesize,
        path = rpath)

    return render_template_g('threadlist.html.jinja',
        page_title=catobj['name'],
        page_subheader=(catobj['brief'] or '').replace('\\',''),
        threadlist=threadlist,
        pagination=pagination,
        categories=get_categories_info(),
        category=catobj,
        # threadcount=count,

    )

@app.route('/u/<int:uid>/t')
def userthreads(uid):
    uobj = aql('''
    for u in users filter u.uid==@uid
    return u
    ''', uid=uid, silent=True)

    if len(uobj)!=1:
        abort(404, 'user not exist')
        # return make_response('user not exist', 404)

    uobj = uobj[0]
    utld = user_thread_list_defaults
    pagenumber = rai('page') or utld['pagenumber']
    pagesize = rai('pagesize') or utld['pagesize']
    order = ras('order') or utld['order']
    sortby = ras('sortby') or utld['sortby']

    rpath = request.path
    # print(request.args)

    threadlist, pagination = pgnt.get_thread_list(
        by='user', uid=uid,
        sortby=sortby,
        order=order,
        pagenumber=pagenumber, pagesize=pagesize,
        path = rpath)

    return render_template_g('threadlist.html.jinja',
        # page_title=catobj['name'],
        page_title='帖子 - '+uobj['name'],
        threadlist=threadlist,
        pagination=pagination,
        # threadcount=count,

    )

def get_thread_full(tid, selfuid=-1):
    thobj = aql('''
    for t in threads filter t.tid==@tid
    let u = (for u in users filter u.uid==t.uid return u)[0]

    let self_voted = length(for v in votes filter v.uid==@selfuid and v.id==to_number(t.tid) and v.type=='thread' and v.vote==1 return v)

    return merge(t, {user:u},{self_voted:self_voted})
    ''', tid=tid, selfuid=selfuid, silent=True)

    if len(thobj)<1:
        return False

    thobj = thobj[0]
    return thobj

def remove_duplicate_brief(postlist):
    # remove duplicate brief string within a page
    bd = dict()
    for p in postlist:
        if 'user' in p:
            pu = p['user'] or {}
            if 'brief' in pu:
                b = pu['brief']+pu['name']
                if b in bd:
                    pu['brief']=''
                else:
                    bd[b] = 1

    bd = dict()
    for p in postlist:
        if 'user' in p:
            pu = p['user'] or {}
            if 'personal_title' in pu:
                b = pu['personal_title']+pu['name']
                if b in bd:
                    pu['personal_title']=''
                else:
                    bd[b] = 1

# thread, list of posts
@app.route('/t/<int:tid>')
def get_thread(tid):

    selfuid = g.selfuid

    thobj = get_thread_full(tid, selfuid)
    if not thobj:
        abort(404, 'thread not exist')
        # return 'thread not exist', 404

    catobj = aql('''
    for c in categories filter c.cid==@cid return c
    ''', cid=thobj['cid'], silent=True)[0]
    thobj['category'] = catobj

    visitor_error_if_hidden(thobj['cid'])

    if 'mode' in thobj and thobj['mode']=='question':
        mode = 'question'
        pld = post_list_defaults_q
    else:
        mode = ''
        pld = post_list_defaults

    pagenumber = rai('page') or pld['pagenumber']
    pagesize = rai('pagesize') or pld['pagesize']
    sortby = ras('sortby') or pld['sortby']
    order = ras('order') or pld['get_default_order'](sortby)

    rpath = request.path

    postlist, pagination = pgnt.get_post_list(
        by='thread',
        tid=tid,
        sortby=sortby,
        order=order,
        pagenumber=pagenumber, pagesize=pagesize,
        path = rpath, mode=mode)

    # remove duplicate brief string within a page
    # remove_duplicate_brief(postlist)

    user_is_self = selfuid==thobj['uid']

    return render_template_g('postlist.html.jinja',
        page_title=thobj['title'],
        # threadlist=threadlist,
        postlist=postlist,
        pagination=pagination,
        t=thobj,
        # threadcount=count,
        viewed_target='thread/'+str(tid) if not user_is_self else '',

    )

# list of user posts.
@app.route('/u/<int:uid>/p')
def uposts(uid):
    uobj = aql('''
    for u in users filter u.uid==@uid
    return u
    ''', uid=uid, silent=True)

    if len(uobj)!=1:
        abort(404, 'user not exist')
        return make_response('user not exist', 404)

    uobj = uobj[0]

    upld = user_post_list_defaults
    pagenumber = rai('page') or upld['pagenumber']
    pagesize = rai('pagesize') or upld['pagesize']
    sortby = ras('sortby') or upld['sortby']
    order = ras('order') or upld['get_default_order'](sortby)

    rpath = request.path

    postlist, pagination = pgnt.get_post_list(
        # by='thread',
        by='user',
        # tid=tid,
        uid=uid,
        sortby=sortby,
        order=order,
        pagenumber=pagenumber, pagesize=pagesize,
        path = rpath)

    # remove_duplicate_brief(postlist)

    return render_template_g('postlist_userposts.html.jinja',
        page_title='回复 - '+uobj['name'],
        # threadlist=threadlist,
        postlist=postlist,
        pagination=pagination,
        # t=thobj,
        u=uobj,
        # threadcount=count,

    )

@app.route('/p/all')
def get_all_posts():
    upld = user_post_list_defaults
    pagenumber = rai('page') or upld['pagenumber']
    pagesize = rai('pagesize') or upld['pagesize']
    sortby = ras('sortby') or upld['sortby']
    order = ras('order') or upld['get_default_order'](sortby)

    rpath = request.path

    postlist, pagination = pgnt.get_post_list(
        # by='thread',
        by='all',
        # tid=tid,
        # uid=uid,
        sortby=sortby,
        order=order,
        pagenumber=pagenumber, pagesize=pagesize,
        path = rpath)

    # remove_duplicate_brief(postlist)

    return render_template_g('postlist_userposts.html.jinja',
        page_title='所有评论',
        # threadlist=threadlist,
        postlist=postlist,
        pagination=pagination,
        # t=thobj,
        # u=uobj,
        # threadcount=count,

    )

@app.route('/editor')
def editor_handler():
    details = dict()
    details['has_title'] = True

    target = ras('target')
    target_type, _id = parse_target(target, force_int=False)

    if target_type not in [
        'user','username','edit_post','edit_thread','category','thread'
        ]:
        raise Exception('unsupported target_type')

    if target_type=='edit_post':
        details['has_title'] = False
        post_original = aqlc.from_filter('posts', 'i._key==@_id', _id=str(_id))[0]

        details['content'] = post_original['content']

    if target_type == 'edit_thread':
        _id = int(_id)
        thread_original = aqlc.from_filter('threads', 'i.tid==@id',id=_id)[0]

        details['content'] = thread_original['content']
        details['title'] = thread_original['title']
        details['mode'] = thread_original['mode'] if 'mode' in thread_original else None

    if target_type=='user':
        _id = int(_id)

    if 'user' in target_type:
        details['has_title'] = False

    page_title = '{} - {}'.format(
        '发表' if 'edit' not in target_type else '编辑',
        target)

    return render_template_g('editor.html.jinja',
        page_title = page_title,
        target=target,
        details=details,

    )

def userfill(u):
    if 't_c' not in u: # some user data are incomplete
        u['t_c'] = '1989-06-04T00:00:00'
        u['brief'] = '此用户的数据由于各种可能的原因，在github上2049bbs.xyz的备份中找不到，所以就只能像现在这样处理了'

@app.route('/u/<int:uid>')
def userpage(uid):
    return _userpage(uid)

def get_alias_user_by_name(uname):
    return aql('''let oname = (
        for i in aliases filter i.is==@uname return i
        )[0].name
        return (for i in users filter i.name==oname return i)[0]
        ''', uname=uname, silent=True,
    )[0]

@app.route('/member/<string:name>')
def userpage_byname(name):
    # check if user exists
    res = aql('for u in users filter u.name==@n return u', n=name)
    if len(res)==0:
        return make_response(f'''
        <p>
        找不到用户: {name}
        <br>
        你可以试试: <a href='https://pincong.rocks/people/{name}'>
        {name}(品葱)
        </a>
        <br>
        或者试试: <a href='https://mohu.rocks/people/{name}'>
        {name}(膜乎)
        </a>
        </p>
        ''', 404)

    u = res[0]
    return _userpage(u['uid'])

def _userpage(uid):
    uobj = get_user_by_id_admin(int(uid))

    if not uobj:
        abort(404, 'user not exist')
        # return make_response('user not exist', 404)

    u = uobj

    userfill(u)

    selfuid = g.selfuid
    user_is_self = (uid == selfuid)

    # display showcase thread/post
    sc_ts = []
    if 'showcase' in u:
        showcases = parse_showcases(u['showcase'])
        if len(showcases):
            for idx, case in enumerate(showcases):
                if case[0]=='t':
                    tid = int(case[1])
                    thobj = get_thread_full(tid, selfuid)
                    if thobj:
                        thobj['type']='thread'
                        sc_ts.append(thobj)

                elif case[0]=='p':
                    pid = case[1]
                    pobj = pgnt.get_post_one(pid)
                    if pobj:
                        pobj['type']='post'
                        sc_ts.append(pobj)

                if len(sc_ts)>=4: # at most 4 for now
                    break

                # print(thobj)


    stats = aql('''return {
            nthreads:length(for t in threads filter t.uid==@uid return t),
            nposts:length(for p in posts filter p.uid==@uid return p),
            nlikes:length(for v in votes filter v.to_uid==@uid and v.vote==1 return v),
            nliked:length(for v in votes filter v.uid==@uid and v.vote==1 return v),
        }
        ''',uid=uid, silent=True)[0]

    uobj['stats']=stats

    uobj['alias'] = get_alias_user_by_name(uobj['name'])

    invitations = None
    pagination = None
    if g.logged_in:
        if user_is_self:
            pagenumber=rai('page') or inv_list_defaults['pagenumber']
            pagesize=inv_list_defaults['pagesize']
            order = ras('order') or inv_list_defaults['order']
            sortby = 't_c'

            ninvs = aql('return length(for i in invitations filter i.uid==@k\
            return i)',k=selfuid)[0]

            k = aql(f'for i in invitations filter i.uid==@k\
            let users = (for u in users filter u.invitation==i._key return u)\
            sort i.t_c {order} limit {pagesize*(pagenumber-1)},{pagesize} return merge(i,{{users}})', k=selfuid,silent=True)
            invitations = k

            pagination = pgnt.get_pagination_obj(
                pagenumber=pagenumber,
                pagesize=pagesize,
                order = order,
                sortby = sortby,
                count = ninvs,
                path = request.path,
                postfix = '#invitation_list',
                mode='invitation',
            )
            # print(pagination)

    if not user_is_self:
        viewed_target='user/'+str(uobj['uid'])
    else:
        viewed_target=''

    return render_template_g('userpage.html.jinja',
        page_title=uobj['name'],
        u=uobj,
        invitations=invitations,
        user_is_self=user_is_self,

        sc_ts = sc_ts, # showcase_threads
        viewed_target=viewed_target,
        pagination = pagination,
    )
@app.route('/register')
def regpage():
    invitation = ras('code') or ''

    return render_template_g('register.html.jinja',
        invitation=invitation,
        page_title='注册',

    )

@app.route('/login')
def loginpage():
    username = ras('username') or ''

    return render_template_g('login.html.jinja',
        username=username,
        page_title='登录',

    )
# print(ptf('2020-07-19T16:00:00'))

@app.route('/avatar/<int:uid>')
def route_get_avatar(uid):

    # first check db
    res = aql('for a in avatars filter a.uid==@uid return a', uid=uid, silent=True)
    # print(res)
    if len(res)>0:
        res = res[0]

        if 'data_new' in res:
            # new 2047 png pipeline
            d = res['data_new']
            rawdata = base64.b64decode(d)

            resp = make_response(rawdata, 200)
            resp = etag304(resp)
            resp.headers['Content-Type'] = 'image/png'
        elif 'data' in res:
            # old 2049bbs jpeg pipeline

            d = res['data']
            match = re.match(r'^data:(.*?);base64,(.*)$',d)
            mime,b64data = match[1],match[2]

            rawdata = base64.b64decode(b64data)

            resp = make_response(rawdata, 200)
            resp = etag304(resp)
            resp.headers['Content-Type'] = 'image/jpeg'

        else:
            raise Exception('no data in avatar object found')

    else: # db no match
        # render an identicon
        identicon = Identicon.render(str(uid*uid))
        resp = make_response(identicon, 200)
        resp = etag304(resp)
        resp.headers['Content-Type'] = 'image/png'

    # resp = etag304(resp)

    if 'no-cache' in request.args:
        resp.headers['Cache-Control']= 'no-cache'
    else:
        resp.headers['Cache-Control']= 'max-age=14400'
    return resp

    # # default: 307 to logo.png
    # resp = make_response(
    #     'no avatar obj found for uid {}'.format(uid), 307)
    # resp.headers['Location'] = '/images/logo.png'
    # resp.headers['Cache-Control']= 'max-age=1800'
    # return resp

@app.route('/m')
def conversation_page():
    if not g.logged_in: raise Exception('not logged in')

    conversations = aql('''
    for i in conversations
    filter i.uid==@uid

    sort i.t_u desc

    let last = (for m in messages filter m.convid==i.convid
    sort m.t_c desc limit 1 return m)[0]

    let count = length(for m in messages filter m.convid==i.convid
    return m)

    let user = (for u in users filter u.uid==last.uid return u)[0]
    let to_user = (for u in users filter u.uid==last.to_uid return u)[0]

    return merge(i, {count, last: merge(last, {user:user, to_user:to_user})})
    ''', uid=g.logged_in['uid'],silent=True)


    # mark unread
    for i in conversations:
        if i['t_u']>g.current_user['t_inbox']:
            if i['last']['user']['uid'] != g.current_user['uid']:
                i['unread'] = True

    # update t_inbox
    timenow = time_iso_now()
    aql('update @user with {t_inbox:@t} in users',
        user=g.current_user,t=timenow,silent=True)

    # update user
    update_user_votecount(g.current_user['uid'])

    g.current_user['num_unread']=0

    return render_template_g('conversations.html.jinja',
        page_title='私信（测试中）',
        conversations=conversations,
        can_send_message=True,

    )

@app.route('/m/<string:convid>')
def messages_by_convid(convid):
    if not g.logged_in: raise Exception('not logged in')
    uid = g.current_user['uid']

    # only allow user to see own conversation
    c = aql('for i in conversations filter i.convid==@k return i', k=convid, silent=True)
    if len(c)==0:
        raise Exception('convid not found')

    conv = c[0]
    if conv['uid']!=uid and conv['to_uid']!=uid:
        raise Exception('you dont own the conversation')

    res = aql('''
    for i in messages
    filter i.convid==@convid
    sort i.t_c desc

    let user = (for u in users filter u.uid==i.uid return u)[0]
    let to_user = (for u in users filter u.uid==i.to_uid return u)[0]

    return merge(i,{user, to_user})
    ''', convid=convid, silent=True)

    last = res[0]
    u1n = last['user']['name']
    u2n = last['to_user']['name']

    if uid==last['user']['uid']:
        myname = u1n
        hisname = u2n
    else:
        myname = u2n
        hisname = u1n

    return render_template_g('messages.html.jinja',
        page_title='和 {} 之间的私信对话'.format(hisname),
        conversation=c,
        hisname=hisname,
        editor_target = dict(
            target = 'username/{}'.format(hisname),
            uid=uid,
        ),
        messages=res,

    )

@app.route('/n')
def notification_page():
    if not g.logged_in: raise Exception('not logged in')
    uid = g.current_user['uid']

    notifications = aql('for i in notifications \
    filter i.to_uid==@uid sort i.t_c desc limit 50 \
    let from_user=(for u in users filter u.uid==i.from_uid return u)[0]\
    return merge(i,{from_user})',
        uid=uid,
        silent=True)

    # mark unread
    for i in notifications:
        if i['t_c']>g.current_user['t_notif']:
            i['unread'] = True

    # update t_notif
    timenow = time_iso_now()
    aql('update @user with {t_notif:@t} in users',
        user=g.current_user,t=timenow,silent=True)

    # update user
    update_user_votecount(g.current_user['uid'])

    g.current_user['num_notif']=0

    return render_template_g('notifications.html.jinja',
        page_title='系统提醒',
        notifications=notifications,

    )

def e(s): return make_response({'error':s}, 500)

@app.route('/api', methods=['GET', 'POST'])
def apir():

    if request.method not in ['GET','POST']:
        return e('support GET and POST only')

    if request.content_length:
        if request.content_length > 1024*1024*3: # 3MB limit
            return e('request too large')

    j = request.get_json(silent=False)

    if j is None:
        if request.method=='POST':
            return e('empty body for post')
        else: # GET
            if 'action' not in request.args:
                return e('action not specified in url params')
            else:
                j = {}
                for k in request.args:
                    j[k] = request.args[k]
    else:
        if 'action' not in j:
            return e('action not specified in json')

    # print(j)
    action = j['action']
    j['logged_in'] = g.logged_in
    if action in api_registry:
        g.j = j

        if action not in ('ping','viewed_target','browser_check'):
            print_up('API >>', j)

        try:
            answer = api_registry[action]()

        except Exception as ex:
            traceback.print_exc()
            errstr = ex.__class__.__name__+'/{}'.format(str(ex))
            print_err('Exception in api "{}":'.format(action), errstr)
            return e(errstr)

        else:
            if answer is None:
                raise Exception('return value is None, what the fuck?')
            if action not in ('ping','viewed_target','browser_check'):
                print_down('API <<', answer)
            if 'setuid' in answer:
                session['uid'] = answer['setuid']
                session.permanent = True
            if 'setbrowser' in answer:
                session['browser'] = 1
            if 'logout' in answer:
                if 'uid' in session:
                    del session['uid']

            return answer
    else:
        return e('action function not registered')

@app.route('/upload', methods=['POST'])
def upload_file():
    if request.method != 'POST':
        return e('please use POST')
    if not g.logged_in: raise Exception('log in please')

    data = request.data # binary
    # print(len(data))

    from imgproc import avatar_pipeline

    png = avatar_pipeline(data)
    png = base64.b64encode(png).decode('ascii')

    avatar_object = dict(
        uid=g.logged_in['uid'],
        data_new=png,
    )
    aql('upsert {uid:@uid} insert @k update @k into avatars',
        uid=avatar_object['uid'], k=avatar_object)
    return {'error':False}

def etag304(resp):
    etag = calculate_etag(resp.data)
    # print(etag, request.if_none_match, request.if_none_match.contains_weak(etag))
    if request.if_none_match.contains_weak(etag):
        resp = make_response('', 304)

    resp.set_etag(etag)
    return resp

@app.route('/qr/<path:to_encode>')
def qr(to_encode):

    to_encode = request.full_path[4:]
    if to_encode[-1]=='?':
        to_encode = to_encode[:-1]

    import qrcode
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=2,
    )
    qr.add_data(to_encode)
    qr.make(fit=True)
    img = qr.make_image()
    import io
    out = io.BytesIO()
    img.save(out, format='PNG')

    bin = out.getvalue()

    resp = make_response(bin, 200)
    resp = etag304(resp)

    resp.headers['Content-Type']='image/png'

    if 'no-cache' in request.args:
        resp.headers['Cache-Control']= 'no-cache'
    else:
        resp.headers['Cache-Control']= 'max-age=8640000'
    return resp

aqlc.create_collection('exams')
aqlc.create_collection('answersheets')
aqlc.create_collection('questions')

@app.route('/exam')
def get_exam():
    ipstr = request.remote_addr
    timenow = time_iso_now()[:15] # every 10 min
    from questions import make_exam
    exam_questions = make_exam(ipstr+timenow, 5)
    exam = {}
    exam['questions'] = exam_questions
    exam['t_c'] = time_iso_now()
    inserted = aql('insert @k into exams return NEW',k=exam,silent=True)[0]

    return render_template_g(
        'exam.html.jinja',
        page_title='考试',
        exam=inserted,

    )

@app.route('/questions')
def list_questions():
    must_be_admin()

    qs = aql('''
    for i in questions sort i.t_c desc
    let user = (for u in users filter u.uid==i.uid return u)[0]
    return merge(i,{user})
    ''', silent=True)

    return render_template_g(
        'qs.html.jinja',
        page_title='题库',
        questions = qs,

    )
@app.route('/questions/preview')
def list_q_preview():
    must_be_admin()

    qs = aql('''
    for i in questions sort i.t_c desc
    let user = (for u in users filter u.uid==i.uid return u)[0]
    return merge(i,{user})
    ''', silent=True)

    exam = {}
    exam['questions'] = qs

    return render_template_g(
        'exam.html.jinja',
        page_title='题目预览',
        exam=exam,
    )

def render_template_g(*a, **k):
    k.update(globals())
    return render_template(*a, **k)

@app.route('/hero')
def heropage():
    return render_template_g(
    'iframe.html.jinja',
    page_title='人民英雄纪念碑',
    # url = 'https://nodebe4.github.io/hero/',
    url = 'https://hero-form.vercel.app',
    height=2500,
    )

aqlc.create_collection('entities')
@app.route('/entities')
def entpage():
    ents = aql('for i in entities sort i.type, i.t_c desc return i')
    return render_template('entities.html.jinja',
        page_title='entities',
        entities = ents,
    )

@app.route('/invitation/<string:iid>')
def get_invitation(iid):
    i = aql('for i in invitations filter i._key==@k return i', k=iid, silent=True)[0]

    if i['uid']:
        resp = make_response('',307)
        resp.headers['Location'] = '/u/'+str(i['uid'])
    else:
        resp=make_response(str(i),200)
        resp.headers['content-type']='text/plain'
    return resp

@app.route('/404/<string:to_show>')
def f404(to_show):
    if 'reason' in request.args:
        reason = request.args['reason']
    else:
        reason = ''

    return render_template('404.html.jinja',
        page_title='404',
        to_show=to_show,
        reason = reason,
    )

@app.route('/robots.txt')
def robots():
    with open('templates/robots.txt', 'r') as f:
        s = f.read()
    resp = make_response(s, 200)
    resp.headers['content-type'] = 'text/plain'
    return resp

@app.errorhandler(404)
def e404(e):
    return render_template_g('404.html.jinja',
        page_title='404',
        err=e,
    ), 404

@app.errorhandler(500)
def e5001(e):
    return render_template_g('404.html.jinja',
        page_title='500',
        e500=True,
        err=e,
    ), 500

if __name__ == '__main__':
    dispatch(create_all_necessary_indices)

    import os
    if 'PORT' in os.environ:
        port = os.environ['PORT']
    else:
        port = '5000'

    if 'PROFILE' not in os.environ:
        if 'DEBUG' in os.environ:
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
