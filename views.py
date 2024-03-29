from commons import *
from medals import get_medals, get_user_medals
from api import *

import glob
# hash all resource files see if they change
def hash_these(path_arr, pattern='*.*'):
    resource_files_contents = b''
    for path in path_arr:
        files = glob.glob(path+pattern)

        for fn in files:
            print_info('checking file:', fn)
            resource_files_contents += readfile(fn)

    resource_files_hash = calculate_etag(resource_files_contents)
    return resource_files_hash

resource_files_hash = ''
images_resources_hash = ''
ad_images_hash = ''

def calculate_resource_files_hash():
    global resource_files_hash, images_resources_hash, ad_images_hash

    resource_files_hash = hash_these(['templates/css/', 'templates/js/'])
    print_up('resource_files_hash:', resource_files_hash)

    images_resources_hash = hash_these(['templates/images/'], '*.png')
    print_up('images_resources_hash:', images_resources_hash)

    ad_images_hash = hash_these(['ads/images/'], '*.jpg')
    print_up('ad_images_hash:', ad_images_hash)

dispatch_with_retries(calculate_resource_files_hash)



def mark_blacklisted(postlist):
    # from api import get_blacklist_set
    bl_set = get_blacklist_set(g.selfuid)

    if 0 == len(bl_set):
        return

    for idx, i in enumerate(postlist):
        if i['uid'] in bl_set:
            # print('blacklisted', i)
            copy = postlist[idx].copy()
            copy['blacklist'] = True
            postlist[idx] = copy

def add_users(postlist):
    for i in postlist:
        uid = key(i,'uid')
        if uid:
            i['user'] = get_user_by_id_cached(uid)
        to_uid = key(i,'to_uid')
        if to_uid:
            i['to_user'] = get_user_by_id_cached(to_uid)

def threads_fill_lastuser(threadlist):
    tl = threadlist
    for i in tl:
        if 'last_reply_uid' in i:
            lruid = i['last_reply_uid']
            if lruid and is_integer(lruid):
                i['lastuser'] = get_user_by_id_cached(lruid)

def sink_deleted(postlist):
    newlist = []
    badapple = []

    for i in postlist:
        if key(i, 'blacklist') or key(i, 'delete') or key(i, 'spam'):
            badapple.append(i)
        else:
            newlist.append(i)

    return newlist+badapple


def generate_simple_pagination(pagesize=None):
    sd = simple_defaults
    pagenumber = rai('page') or sd['pagenumber']
    pagesize = pagesize or sd['pagesize']
    sortby = sd['sortby']
    order = sd['order']

    start = (pagenumber-1) * pagesize

    def eat_count(count):
        pagination = pgnt.get_pagination_obj(
            path=request.path,
            order=order,sortby=sortby,
            count=count, pagenumber=pagenumber, pagesize=pagesize,
            mode='simple',
            default_pagesize=pagesize,
        )
        return pagination

    return start, pagesize, pagenumber, eat_count

is_integer = lambda i:isinstance(i, int)
is_string = lambda i:isinstance(i, str)
class Paginator:
    def __init__(self,):
        pass

    def get_user_list(self,
        sortby='uid',
        order='desc',
        pagesize=50,
        pagenumber=1,
        path=''):

        assert sortby in ['t_c','uid','nthreads','nposts','nlikes','nliked','name',
            'pagerank','trust_score'] # future can have more.
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
        let salt = invite.salt

        return merge(u, {{invited_by, ip_addr, salt}}) //merge(u, stat)
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
        pl = self.get_post_list(by='ids', ids=['posts/'+str(pid)])
        if pl:
            return pl[0]
        else:
            return False

    def get_post_list(self,
        by='thread',
        tid=0,
        uid=0,

        sortby='t_c',
        order='desc',
        pagesize=50,
        pagenumber=1,

        path='',
        mode='',
        apply_origin=False,
        ids=[]):

        assert by in ['thread', 'user','all', 'ids']
        assert is_integer(tid)
        assert is_integer(uid)

        assert sortby in ['t_c','votes','nfavs','t_hn','t_hn2']
        # sortby = 't_c'
        assert order in ['desc', 'asc']

        assert isinstance(ids, list)

        pagenumber = max(1, pagenumber)

        start = (pagenumber-1)*pagesize
        count = pagesize

        qsc = querystring_complex = QueryString('for i in posts')

        filter = QueryString()

        if by=='thread':
            filter.append('filter i.tid == @tid', tid=tid)

            if mode=='question':
                mode='post_q'
            else:
                mode='post'

        elif by=='user': # filter by user
            filter.append('filter i.uid == @uid', uid=uid)
            mode='user_post'

        elif by=='all':
            filter.append('')
            mode='all_post'

        elif by=='ids':
            qsc = QueryString('for id in @ids let i = document(id)', ids=ids)

        selfuid = g.selfuid

        qsc+=filter

        qsc+=QueryString('''
            //let user = (for u in users filter u.uid==i.uid return u)[0]
            let self_voted = length(for v in votes filter v.uid==@selfuid and v.id==to_number(i._key) and v.type=='post' and v.vote==1 return v)

            let favorited = length(for f in favorites
            filter f.uid==@selfuid and f.pointer==i._id return f)

            let ncomments = length(for c in comments filter c.parent==i._id
            return c)

            let comments = (for c in comments filter c.parent==i._id
            sort c.t_c desc
            let uc = (for j in users filter j.uid==c.uid return j)[0]
            limit 6 return merge(c, {user:uc}))

        ''', selfuid=selfuid)

        if apply_origin:
            qsc+=QueryString('''
                let t = unset((for t in threads filter t.tid==i.tid return t)[0],'content')
                '''
            )
        else:
            qsc+=QueryString('let t = null')

        if by!='ids':
            qsc+=QueryString('''
                sort i.{sortby} {order}
                limit {start},{count}
                return merge(i, {{
                    //user,
                    self_voted, t,
                    favorited, ncomments, comments}})
                '''.format(
                    sortby = sortby,order=order,start=start,count=count,
                )
            )

            qss = querystring_simple = QueryString('return length(for i in posts')\
                + filter + QueryString('return i)')

            count = aql(qss.s, silent=True, **qss.kw)[0]
            postlist = aql(qsc.s, silent=True, **qsc.kw)

            # uncomment if you want floor number in final output.
            # for idx, p in enumerate(postlist):
            #     p['floor_num'] = idx + start + 1

            pagination_obj = self.get_pagination_obj(count, pagenumber, pagesize, order, path, sortby, mode=mode)

            add_users(postlist)
            mark_blacklisted(postlist)
            postlist = sink_deleted(postlist)

            remove_duplicate_brief(postlist)

            return postlist, pagination_obj

        else:
            qsc+=QueryString('''
            return merge(i, {
                //user,
                self_voted, t, favorited})
            ''')

            postlist = aql(qsc.s, silent=True, **qsc.kw)
            add_users(postlist)
            remove_duplicate_brief(postlist)
            return postlist

    def get_thread_list(self, *a, **k):
        tl, po= self.get_thread_list_cached(*a, **k, locale=g.locale)
        return tl.copy(), po.copy()

    @stale_cache(maxsize=256, ttr=3, ttl=30)
    def get_thread_list_cached(self, *a, locale=None, **k):
        return self.get_thread_list_uncached(*a,**k)

    def get_thread_list_uncached(self,
        mode='',
        by='category',
        category='all',
        tagname='yadda',
        uid=0,
        sortby='t_u',
        order='desc',
        pagesize=50,
        pagenumber=1,
        path='',
        ids=[],
        ):

        ts = time.time()

        assert by in ['category', 'user', 'tag', 'ids']
        assert is_string(category) or is_integer(category)
        assert is_integer(uid)
        assert sortby in ['t_u', 't_c', 'nreplies', 'vc', 'votes','t_hn','t_hn2','amv','nfavs']
        assert order in ['desc', 'asc']

        assert re.fullmatch(tagname_regex_long, tagname)

        pagenumber = max(1, pagenumber)
        assert pagesize<=50

        start = (pagenumber-1)*pagesize
        count = pagesize

        qsc = querystring_complex = QueryString('''
            for i in threads
        ''')

        filter = QueryString()

        if by=='category':
            if category=='all':
                filter.append('filter i.delete==null')
            elif category=='deleted':
                filter.append('filter i.delete==true')
            elif is_integer(category):
                filter.append('filter i.cid == @category and i.delete==null', category=category)
            else:
                # string bigcats
                filter.append(
                    'filter i.delete==null and @category in i.bigcats',
                    category=category
                )

            mode = mode or ('thread' if category!=4 else 'thread_water')

        elif by=='tag':
            filter.append('filter @tagname in i.tags and i.delete==null', tagname=tagname)
            mode='tag_thread'
        elif by=='user': # filter by user
            filter.append('filter i.uid==@iuid', iuid=uid)
            mode='user_thread'

        elif by=='ids':
            qsc = QueryString('''
                for id in @ids let i = document(id)
            ''', ids = ids)

        qsc += filter

        if by!='ids':
            qsc.append('''
                sort i.{sortby} {order}
                limit {start},{count}
                 '''.format(
                        sortby = sortby,
                        order = order,
                        start = start,
                        count = count,
                )
            )

        qsc.append('''
            //let user = (for u in users filter u.uid == i.uid return u)[0]
            let count = i.nreplies

            //let fin = (for p in posts filter p.tid == i.tid sort p.t_c desc limit 1 return p)[0]

            //let ufin = (for j in users filter j.uid == fin.uid return j)[0]
            let c = (for c in categories filter c.cid==i.cid return c)[0]

            //let mvu = ((i.mvu and i.mv>2) ?(for u in users filter u.uid == i.mvu return u)[0]: null)

        ''')

        if by=='ids':
            qsc.append('''
                let favorited = length(for f in favorites
                filter f.uid==@selfuid and f.pointer==i._id return f)

                let self_voted = length(for v in votes filter v.uid==@selfuid and v.id==to_number(i.tid) and v.type=='thread' and v.vote==1 return v)
            ''', selfuid=g.selfuid)

            qsc.append('''
                return merge(i, {
                //user:user, lastuser:ufin, last:unset(fin,'content'),
                cname:c.name, cat:c,
                count:count,
                favorited, self_voted})
            ''')

            threadlist = aql(qsc.s, silent=True, **qsc.kw)

            add_users(threadlist)
            threads_fill_lastuser(threadlist)
            remove_duplicate_brief(threadlist)
            return threadlist

        else:
            qsc.append('''
                return merge(i, {
                //user:user, lastuser:ufin, last:unset(fin,'content'),
                cname:c.name, cat:c,
                count:count})
            ''')

            qss = querystring_simple = \
                QueryString('return length(for i in threads')\
                + filter\
                + QueryString('return i)')

            count = aql(qss.s, silent=True, **qss.kw)[0]
            # print('done',time.time()-ts);ts=time.time()

            threadlist = aql(qsc.s, silent=True, **qsc.kw)
            # print('done',time.time()-ts);ts=time.time()

            pagination_obj = self.get_pagination_obj(count, pagenumber, pagesize, order, path, sortby, mode)

            for t in threadlist:
                if 'content' in t:
                    tc = t['content']
                    ytb_videos = extract_ytb(tc)
                    t['youtube'] = ytb_videos[0] if len(ytb_videos) else None
                    t['content'] = None

            add_users(threadlist)
            threads_fill_lastuser(threadlist)
            remove_duplicate_brief(threadlist)
            return threadlist, pagination_obj

    def get_pagination_obj(self, *a, **kw):
        return self.get_pagination_obj_raw(*a, **kw, locale=g.locale)

    @ttl_cache(maxsize=2048, ttl=120)
    def get_pagination_obj_raw(self,
        count, pagenumber, pagesize, order, path, sortby,
        mode='thread', postfix='', default_pagesize=None, locale=None):

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
        elif mode=='thread_water':
            defaults = thread_list_defaults_water

        elif mode=='post':
            defaults = post_list_defaults
        elif mode=='post_q':
            defaults = post_list_defaults_q

        elif mode=='user_thread':
            defaults = user_thread_list_defaults
        elif mode=='tag_thread':
            defaults = thread_list_defaults

        elif mode=='all_post':
            defaults = all_post_list_defaults
        elif mode=='user_post':
            defaults = user_post_list_defaults
        elif mode=='user':
            defaults = user_list_defaults
        elif mode=='invitation':
            defaults = inv_list_defaults
        elif mode=='fav':
            defaults = fav_list_defaults
        elif mode=='simple':
            defaults = simple_defaults.copy()
            defaults['pagesize'] = default_pagesize or defaults['pagesize']
            pass
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
            (zhen('降序','Desc'), querystring(pagenumber, pagesize, 'desc', sortby), order=='desc',zhen('大的排前面','Greatest First')),
            (zhen('升序','Asc'), querystring(pagenumber, pagesize, 'asc', sortby), order=='asc',zhen('小的排前面','Least First'))
        ]

        sortbys = [

        (zhen('即时','Latest'), querystring(pagenumber, pagesize, order, 't_u'), 't_u'==sortby,'按最后回复时间排序'),
        (zhen('新帖','New'), querystring(pagenumber, pagesize, order, 't_c'), 't_c'==sortby,'按发表时间排序'),

        (zhen('综合','Syn'), querystring(pagenumber, pagesize, order, 't_hn'), 't_hn'==sortby,'HackerNews 排序'),
        (zhen('精华','HQ'), querystring(pagenumber, pagesize, order, 't_hn2'), 't_hn2'==sortby,'更注重质量的 HackerNews 排序', 'golden'),

        # (zhen('回复','Replies'), querystring(pagenumber, pagesize, order, 'nreplies'), 'nreplies'==sortby,'按照回复数量排序'),

        (zhen('高赞','Likes'), querystring(pagenumber, pagesize, order, 'amv'), 'amv'==sortby,'按照得票（赞）数排序'),
        (zhen('观看','Views'), querystring(pagenumber, pagesize, order, 'vc'), 'vc'==sortby,'按照被浏览次数排序'),
        ]

        sortbys2 = [
        ('UID',querystring(pagenumber, pagesize, order, 'uid'),
            'uid'==sortby),
        (zhen('户名','Name'), querystring(pagenumber, pagesize, order, 'name'),
            'name'==sortby),

        (zhen('主题数','Threads'), querystring(pagenumber, pagesize, order, 'nthreads'),
            'nthreads'==sortby),
        (zhen('评论数','Replies'), querystring(pagenumber, pagesize, order, 'nposts'),
            'nposts'==sortby),

        (zhen('点赞','Likes(Sent)'), querystring(pagenumber, pagesize, order, 'nliked'),
            'nliked'==sortby),
        (zhen('被赞','Likes'), querystring(pagenumber, pagesize, order, 'nlikes'),
            'nlikes'==sortby),
        (zhen('声望','Reputation'), querystring(pagenumber, pagesize, order, 'pagerank'),
            'pagerank'==sortby),
        (zhen('信用分','TrustScore'), querystring(pagenumber, pagesize, order, 'trust_score'),
            'trust_score'==sortby),
        ]

        if mode=='post' or mode=='post_q':
            sortbys3 = [
                (zh('综合'),querystring(pagenumber, pagesize, 'desc', 't_hn'), 't_hn'==sortby),
                (zhen('时间','Time'),querystring(pagenumber, pagesize, 'asc', 't_c'), 't_c'==sortby),
                (zhen('票数','Likes'),querystring(pagenumber, pagesize, 'desc', 'votes'), 'votes'==sortby),
            ]
        elif mode=='user_post' or mode=='all_post':
            sortbys3 = [
                (zh('综合'),querystring(pagenumber, pagesize, 'desc', 't_hn'), 't_hn'==sortby),
                (zh('时间'),querystring(pagenumber, pagesize, 'desc', 't_c'), 't_c'==sortby),
                (zh('票数'),querystring(pagenumber, pagesize, 'desc', 'votes'), 'votes'==sortby),

                (zhen('精华','HQ'), querystring(pagenumber, pagesize, 'desc', 't_hn2'), 't_hn2'==sortby,'更注重质量的 HackerNews 排序', 'golden'),
            ]

        button_groups = []

        if len(slots):
            turnpage = []

            if pagenumber!=1:
                turnpage.insert(0,(zhen('上一页','Prev Page'),querystring(pagenumber-1, pagesize, order,sortby)))

            if pagenumber!=total_pages:
                turnpage.insert(0, (zhen('下一页','Next Page'),querystring(pagenumber+1, pagesize, order, sortby)))

            button_groups.append(turnpage)
            button_groups.append(slots)

        # no need to sort if number of items < 2
        if count>4:

            if mode=='thread' or mode=='user_thread' or mode=='tag_thread' or 'thread' in mode:
                button_groups.append(sortbys)

            if mode=='user':
                button_groups.append(sortbys2)

            if mode=='post' or mode=='user_post' or mode=='post_q' or mode=='all_post':
                button_groups.append(sortbys3)

            if mode=='simple':
                pass
            else:
                if 1: # bypass to see effect
                    button_groups.append(orders)

            button_groups.append([(spf(zhen('共 $0', '$0 Total'))(count), '')])

        return {
            'button_groups':button_groups,
            'count':count,
        }

pgnt = Paginator()


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

# @app.route('/')
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

    threadlist = remove_hidden_from_visitor(threadlist)
    mark_blacklisted(threadlist)
    threadlist = sink_deleted(threadlist)

    return render_template_g('threadlist.html.jinja',
        page_title='所有分类',
        threadlist=threadlist,
        pagination=pagination,
        categories=categories,
        # threadcount=count,

    )

@app.route('/c/deleted')
def delall():
    must_be_logged_in()
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

@app.route('/medals')
def usermedals():
    medals = get_medals()
    t = get_thread_full(9403)

    return render_template_g('usermedals.html.jinja',
        page_title = '勋章墙',
        medals = medals,
        t = t,
    )

@app.route('/p/<int:pid>')
def getpost(pid):
    p = get_post(pid)
    url = get_url_to_post(str(pid))
    resp = make_response('', 307)
    resp.headers['Location'] = url
    resp.headers['Cache-Control']= 'max-age=86400, stale-while-revalidate=864000'

    # user_is_self = p['uid'] == g.selfuid
    # if not user_is_self: increment_view_counter('post', pid)

    return resp

@app.route('/p/<int:pid>/code')
def getpostcode(pid):
    if not can_do_to(g.current_user,'view_code', -1):
        abort(404, 'forbidden')

    p = aql('for p in posts filter p._key==@k return p',k=str(pid), silent=True)[0]
    return make_text_response(p['content'])

@app.route('/p/<int:pid>/votes')
def getpostvotes(pid):
    must_be_logged_in()

    votes = aql('''
        for v in votes filter v.type=="post" and v.id==@id
        sort v.t_c desc
        let user = (for i in users filter i.uid==v.uid return i)[0]
        return merge(v, {user})
        ''', id=pid, silent=True)
    votes = [' '.join([str(v['vote']), v['t_c'], v['user']['name']]) for v in votes]
    votes = '\n'.join(votes)
    return make_text_response(votes)

@app.route('/t/<int:pid>/votes')
def getthreadvotes(pid):
    must_be_logged_in()

    votes = aql('''
        for v in votes filter v.type=="thread" and v.id==@id
        sort v.t_c desc
        let user = (for i in users filter i.uid==v.uid return i)[0]
        return merge(v, {user})
        ''', id=pid, silent=True)
    votes = [' '.join([str(v['vote']), v['t_c'], v['user']['name']]) for v in votes]
    votes = '\n'.join(votes)
    return make_text_response(votes)

@app.route('/t/<int:tid>/code')
def getthreadcode(tid):
    if not can_do_to(g.current_user,'view_code', -1):
        abort(404, 'forbidden')

    p = aql('for p in threads filter p.tid==@k return p',k=tid, silent=True)[0]
    return make_text_response(p['content'])

@app.route('/c/<int:cid>')
@app.route('/c/<string:cid>')
def _get_category_threads(cid):
    return get_category_threads(cid)

@app.route('/')
def _get_main_threads():
    if is_mohu_2047_name():
        return get_category_threads('tainment')
    else:
        return get_category_threads('main')

@stale_cache(10,1800)
def get_pinned_threads(cid):
    if is_integer(cid):
        pinned_ids = aql('''
            for i in threads
            filter i.delete==null and i.cid==@cid and i.t_manual>=@now
            sort i.t_manual desc
            return i._id''',
        cid=cid, silent=True, now=time_iso_now())
    else:
        pinned_ids = aql('''
            for i in threads
            filter i.delete==null and @cid in i.bigcats and i.t_manual>=@now
            sort i.t_manual desc
            return i._id
        ''', cid=cid, silent=True, now=time_iso_now())

    if pinned_ids:
        pinned_threads = pgnt.get_thread_list_uncached(
            by='ids',
            ids=pinned_ids)

        pinned=pinned_threads
    else:
        pinned=[]

    tids = set(pinned_ids)
    # qprint(pinned_ids)
    # for p in pinned: qprint (p['tid'], p['t_manual'])
    return pinned, tids


def get_category_threads(cid):
    bigcats = get_bigcats_w_cid()

    category_mode = ''
    parent_bigcats = []

    if is_integer(cid):
        rcil = get_raw_categories_info()

        catobj = ()
        for rci in rcil:
            if rci['cid']==cid:
                catobj = (rci,)
                break
        # catobj = aql('for c in categories filter c.cid==@cid return c',cid=cid, silent=True)

        if len(catobj)<1:
            abort(404, 'category not exist')

        visitor_error_if_hidden(cid)

        catobj = catobj[0]

        category_mode = 'cat'

        for k,v in bigcats['briefs'].items():
            if cid in bigcats['cats'][k]:
                parent_bigcats.append(v)

        if len(parent_bigcats)==0:
            parent_bigcats.append(bigcats['briefs']['main'])

    elif is_string(cid):

        bigcats_briefs = bigcats['briefs']
        bigcats_cats = bigcats['cats']

        if cid not in bigcats_briefs:
            abort(404, 'bigcat not exist')

        catobj = bigcats_briefs[cid]

        if len(bigcats_cats[cid])==1:
            category_mode = 'bigcat_single'
        else:
            category_mode = 'bigcat'

    tlds, mode = iif(
        # cid!=4 and cid!='water' and cid!='inner',
        cid=='main' and random.random()>0.5,
        (thread_list_defaults, 'thread'),
        (thread_list_defaults_water, 'thread_water'),
    )


    pagenumber = rai('page') or tlds['pagenumber']
    pagesize = rai('pagesize') or tlds['pagesize']
    order = ras('order') or tlds['order']
    sortby = ras('sortby') or tlds['sortby']

    rpath = request.path
    # print(request.args)

    threadlist, pagination = pgnt.get_thread_list(
        mode=mode,
        by='category', category=cid,
        sortby=sortby,
        order=order,
        pagenumber=pagenumber, pagesize=pagesize,
        path = rpath)

    if pagenumber==1:
        pinned_threads, pinned_tids = get_pinned_threads(cid)
        threadlist = pinned_threads + [t for t in threadlist if t['_id']not in pinned_tids]

    # if cid=='main':
    #     threadlist = remove_hidden_from_visitor(threadlist)

    mark_blacklisted(threadlist)
    threadlist = sink_deleted(threadlist)

    return render_template_g('threadlist.html.jinja',
        page_title=catobj['name'],
        page_subheader=(catobj['brief'] or '').replace('\\',''),
        threadlist=threadlist,
        pagination=pagination,
        categories=get_categories_info(),
        category=catobj,
        bigcatism = bigcats,
        cid=cid,
        category_mode = category_mode,
        cats_two_parts = get_categories_info_twoparts(
            cid=cid, mode=category_mode),
        # threadcount=count,
        parent_bigcats = parent_bigcats,
    )

@app.route('/tag/<string:tag>')
def get_tag_threads(tag):

    tlds = thread_list_defaults

    pagenumber = rai('page') or tlds['pagenumber']
    pagesize = rai('pagesize') or tlds['pagesize']
    order = ras('order') or tlds['order']
    sortby = ras('sortby') or tlds['sortby']

    rpath = request.path
    # print(request.args)

    threadlist, pagination = pgnt.get_thread_list(
        by='tag', tagname=tag,
        sortby=sortby,
        order=order,
        pagenumber=pagenumber, pagesize=pagesize,
        path = rpath)

    return render_template_g('threadlist.html.jinja',
        page_title='标签 - '+tag,
        # page_subheader=(catobj['brief'] or '').replace('\\',''),
        threadlist=threadlist,
        pagination=pagination,
        categories=get_categories_info(),
        # category=catobj,
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
    docid = aql('for i in threads filter i.tid==@tid return i._id', tid=tid, silent=True)
    if len(docid)<1:
        return False

    docid = docid[0]
    thobj = pgnt.get_thread_list_uncached(by='ids', ids=[docid])[0]
    return thobj

def remove_duplicate_brief(postlist):
    # remove duplicate brief string within a page
    bd = set()
    for p in postlist:
        if isinstance(p, dict) and 'user' in p:
            pu = p['user'] or {}

            if 'brief' in pu:
                k = ('brief', pu['name'], pu['brief'])
                if k in bd:
                    p['hide_brief']=True
                else:
                    bd.add(k)

            if 'personal_title' in pu:
                k = ('pt', pu['name'], pu['personal_title'])
                if k in bd:
                    p['hide_personal_title']=True
                else:
                    bd.add(k)

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
        pagenumber=pagenumber,
        t=thobj,
        # threadcount=count,
        viewed_target='thread/'+str(tid) if not user_is_self else '',

        viewed_target_v2 = thobj['_id'],

    )


# list of user posts.
@app.route('/u/<int:uid>/p')
def uposts(uid):
    uobj = get_user_by_id(uid)

    if not uobj:
        abort(404, 'user not exist')
        return make_response('user not exist', 404)

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
        path = rpath,
        apply_origin=True,
        )

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

# list of followed/follower
@app.route('/u/<int:uid>/fo')
def ufollowing(uid):
    uobj = get_user_by_id(uid)

    if not uobj:
        abort(404, 'user not exist')
        return make_response('user not exist', 404)

    ul = aql('''for i in followings filter i.uid==@uid
    sort i.t_c desc
    let user = (for u in users filter u.uid==i.to_uid return u)[0]
    return merge(user, {t_c: i.t_c})
    ''', uid=uid, silent=True)

    return render_template_g('userlist.html.jinja',
        page_title = uobj['name'] + ' 关注的人',
        userlist = ul,
    )
@app.route('/u/<int:uid>/fr')
def ufollower(uid):
    uobj = get_user_by_id(uid)

    if not uobj:
        abort(404, 'user not exist')
        return make_response('user not exist', 404)

    ul = aql('''for i in followings filter i.to_uid==@uid
    sort i.t_c desc
    let user = (for u in users filter u.uid==i.uid return u)[0]
    return merge(user, {t_c: i.t_c})
    ''', uid=uid, silent=True)

    return render_template_g('userlist.html.jinja',
        page_title = uobj['name'] + ' 的关注者',
        userlist = ul,
    )


@app.route('/p/all')
def get_all_posts():
    upld = all_post_list_defaults
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
        path = rpath,
        apply_origin=True,
    )

    # remove duplicate thread titles for posts
    lt = ''
    for i in postlist:
        if i and i['t'] and i['t']['title']:
            title = i['t']['title']
            if title==lt:
                i['t']['title']=''
            else:
                lt = title

    # remove_duplicate_brief(postlist)

    # kill water
    pl = []
    for i in postlist:
        if i and i['t'] and i['t']['cid']==4 and i['t']['tid']!=14636:
            pass
        else:
            pl.append(i)
    postlist = pl

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
    res = get_user_by_name(name)

    if not res:
        # assert is_legal_username(name)
        # name=flask.escape(name)

        response = render_template_g('user404.html.jinja',
            page_title='查无此人',
            name=name,
        )
        return make_response(response, 404)

    u = res
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
    if g.logged_in:
        stats['ifollowedhim'] = did_follow(g.selfuid, uid)
        stats['hefollowedme'] = did_follow(uid, g.selfuid)

    stats['followers'] = get_followers(uid, limit=6)
    stats['followings'] = get_followers(uid, limit=6, followings=True)
    stats['medals'] = get_user_medals(uid)

    uobj['public_key']=get_public_key_by_uid(uid)
    uobj['alias'] = get_alias_user_by_name(uobj['name'])

    # calculate rank for pagerank and credit score
    uobj['pagerank_rank'] = pagerank_rank = aql('''
    return length(for u in users filter u.pagerank>@pr return u)''',
    silent=True,pr=key(uobj, 'pagerank')or 0)[0]

    uobj['trust_score_rank'] = trust_score_rank = aql('''
    return length(for u in users filter u.trust_score>@pr return u)''',
    silent=True,pr=key(uobj, 'trust_score')or 0)[0]

    if 1 or key(uobj, 'delete'):
        ban_information = aql('''
        for i in operations filter i.op=='ban_user' and i.target==@uid
        sort i.t_c desc
        return i
        ''', silent=True, uid=uid)
    else:
        ban_information = []

    uobj['ban_information'] = ban_information

    invitations = None
    pagination = None
    if g.logged_in:
        if user_is_self:
            pagenumber=rai('page') or inv_list_defaults['pagenumber']
            pagesize=inv_list_defaults['pagesize']
            order = ras('order') or inv_list_defaults['order']
            assert order in ['asc', 'desc']
            sortby = 't_c'

            ninvs = aql('return length(for i in invitations filter i.uid==@k\
            return i)',k=selfuid,silent=True)[0]

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
        viewed_target_v2 = uobj['_id']
    else:
        viewed_target=''
        viewed_target_v2=''

    return render_template_g('userpage.html.jinja',
        page_title=uobj['name'],
        u=uobj,
        invitations=invitations,
        user_is_self=user_is_self,

        sc_ts = sc_ts, # showcase_threads
        viewed_target=viewed_target,
        viewed_target_v2=viewed_target_v2,
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

from avatar_generation import render_identicon

@app.route('/avatar/<int:uid>')
@app.route('/avatar/<int:uid>.png')
@app.route('/avatar/<int:uid>.jpg')
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

        elif 'data' in res:
            # old 2049bbs jpeg pipeline

            d = res['data']
            match = re.match(r'^data:(.*?);base64,(.*)$',d)
            mime,b64data = match[1],match[2]

            rawdata = base64.b64decode(b64data)

            resp = make_response(rawdata, 200)
            resp = etag304(resp)

        else:
            raise Exception('no data in avatar object found')

    else: # db no match
        if 1:
            # render an identicon

            img = render_identicon(str(uid*uid+uid))
            resp = make_response(img, 200)
            resp = etag304(resp)

        else:
            # identicon is overrated

            # avdf = readfile('templates/images/avatar-max-img.png','rb')
            # resp = make_response(avdf, 200)
            # resp = etag304(resp)

            resp = make_response('', 307)
            resp.headers['Location'] = '/images/avatar-max-img.png'
            resp.headers['Cache-Control']= 'max-age=86400, stale-while-revalidate=864000'
            return resp

    resp.headers['Content-Type'] = 'image/png'

    # resp = etag304(resp)

    if 'no-cache' in request.args:
        resp.headers['Cache-Control']= 'no-cache'
    else:
        resp.headers['Cache-Control']= 'max-age=186400, stale-while-revalidate=1864000'
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

    let last = (for m in messages filter m.convid==i.convid and m.delete==null
    sort m.t_c desc limit 1 return m)[0]

    filter last

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
    filter i.convid==@convid and i.delete==null
    sort i.t_c desc

    limit 100

    //let user = (for u in users filter u.uid==i.uid return u)[0]
    //let to_user = (for u in users filter u.uid==i.to_uid return u)[0]

    //return merge(i,{user, to_user})
    return i
    ''', convid=convid, silent=True)

    add_users(res)

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

    notifications = aql('''
    for i in notifications
    filter i.to_uid==@uid sort i.t_c desc limit 50

    let from_user=(for u in users filter u.uid==i.from_uid return u)[0]
    return merge(i,{from_user})
    ''',
        uid=uid,
        silent=True)

    def prehash(url):
        return url.split('#')[0]
    ph = prehash

    # obtain titles for every mention
    titles = []
    for i in notifications:
        u = i['url']
        u = prehash(u)
        grps = re.findall(r'/t/([0-9]{1,10})', u)
        titles.append(int(grps[0]) if grps else None)
    # print(titles)
    titles = aql('for tid in @tids return (for t in threads filter t.tid==tid return [t.title, t.mode])[0]', tids=titles, silent=True)

    # print(titles)
    assert len(titles)==len(notifications)

    for idx, i in enumerate(titles):
        if notifications[idx] and i:
            notifications[idx]['title']=i[0]
            notifications[idx]['mode']=i[1]

    # concat mentions of same problem
    ns = []
    flag = 0
    for i in notifications:
        if len(ns):
            # if two mentions are about a same problem
            if ns[-1]['why']==i['why'] and ph(ns[-1]['url'])==ph(i['url']):
                if flag==0 or flag==1:
                    if 'from_users' not in ns[-1]:
                        ns[-1]['from_users'] = [ns[-1]['from_user']]

                    ns[-1]['from_users'].insert(0,i['from_user'])
                    # ns[-1]['url'] = i['url'] # use older url
                    flag = 1
                    continue

            # if two mentions are from the same guy
            if ns[-1]['from_uid']==i['from_uid'] and ns[-1]['why']==i['why']:
                if flag==0 or flag==2:
                    if 'urls' not in ns[-1]:
                        ns[-1]['urls'] = [ns[-1]['url']]
                        ns[-1]['titles'] = [ns[-1]['title']]

                    ns[-1]['urls'].insert(0,i['url'])
                    ns[-1]['titles'].insert(0,i['title'])

                    flag = 2
                    continue

        flag=0
        ns.append(i)

    notifications = ns


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


rld = {}
rldlock = threading.Lock()
def ratelimit(uid, k=1):
    global rld
    tn = time.time()

    with rldlock:
        if uid not in rld:
            rld[uid] = [tn, 0]

        lt, ls = rld[uid]

        dt = tn-lt

        ls *= 0.95**dt
        ls += k

        rld[uid] = [tn, ls]

        return ls


@app.route('/api', methods=['GET', 'POST'])
def apir():
    # method check
    if request.method not in ['GET','POST']:
        return e('support GET and POST only')

    if request.content_length:
        if request.content_length > 1024*1024*3: # 3MB limit
            return e('request too large')

    # json body
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

    # find out what action to take
    action = j['action']

    # method limitation
    if (action not in ['ping','sb1024_encrypt','sb1024_decrypt']
        and ('get' not in action)):
        if request.method != 'POST':
            return e('you must use POST for this action')

    # CSRF prevention
    # if action!='ping':
        # check if referrer == self
        if request.referrer and request.referrer.startswith(request.host_url):
            pass
        else:
            log_err('referrer:'+str(request.referrer))
            log_err('hosturl:'+request.host_url)
            return e('use a referrer field or the request will be considered an CSRF attack')

    # is the function registered?
    # j['logged_in'] = g.logged_in
    if action not in api_registry:
        return e('action function not registered')

    rate = ratelimit(g.selfuid, 1)
    if g.selfuid>0 and rate>10 and ('delete' in action or 'edit' in action):
        log_err(f'api rate limit: {g.selfuid} {g.current_user and g.current_user["name"]}\naction: {action}\n{j}')

        aql('insert @i into logs', i={
            'event':'ratelimit',
            't_c':time_iso_now(),
            'uid':g.selfuid,
            'name':g.current_user and g.current_user['name'],
            'action':action,
            'body':j,
        })
        return e("ratelimit exceeded")

    # thread-local access to json body
    g.j = j

    printback = action not in 'ping viewed_target viewed_target_v2 browser_check render_poll'.split(' ') and 'render' not in action.lower() and 'silent' not in j

    if printback:
        print_up('API >>', j)

    # perform action
    try:
        answer = api_registry[action]()
        if answer is None:
            raise Exception('return value is None, what the fuck?')
    except Exception as ex:
        traceback.print_exc()
        errstr = ex.__class__.__name__+'/{}'.format(str(ex))
        print_err('Exception in api "{}":'.format(action), errstr)
        return e(errstr)

    # send the response back
    answerj = obj2json(answer)
    response = make_response(answerj)
    response.headers['Content-Type']='application/json'

    if printback:
        print_down('API <<', answer)

    # set cookies accordingly

    ss = False
    if 'setuid' in answer:
        g.session['uid'] = answer['setuid']
        ss = True

    if 'setbrowser' in answer or 'ping'==action:
        g.session['browser'] = 1
        ss = True

    if 'set_locale' in answer:
        g.session['locale'] = answer['set_locale']
        ss = True

    if 'salt' not in g.session:
        g.session['salt'] = get_random_hex_string(3)
        ss = True

    if 'logout' in answer:
        if 'uid' in g.session:
            del g.session['uid']
            ss = True

    if ss: save_session(response)
    return response


from imgproc import avatar_pipeline
@app.route('/upload', methods=['POST'])
def upload_file():

    if request.method != 'POST':
        return e('please use POST')
    must_be_logged_in()

    data = request.data # binary
    # print(len(data))

    png = avatar_pipeline(data)
    etag = calculate_etag(png)
    png = base64.b64encode(png).decode('ascii')

    etag += time_iso_now() # ensure renewal

    avatar_object = dict(
        uid=g.selfuid,
        data_new=png,
    )
    aql('upsert {uid:@uid} insert @k update @k into avatars',
        uid=g.selfuid, k=avatar_object)
    aql('for i in users filter i.uid==@uid update i with {has_avatar:true, avatar_etag:@etag} in users', uid=g.selfuid, etag=etag)

    time.sleep(0.5)

    return {'error':False}


import qrcode, io
@app.route('/qr/<path:to_encode>')
def qr(to_encode):

    to_encode = request.full_path[4:]
    if to_encode[-1]=='?':
        to_encode = to_encode[:-1]

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=2,
    )
    qr.add_data(to_encode)
    qr.make(fit=True)
    img = qr.make_image()
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

aqlc.create_collection('answersheets')
aqlc.create_collection('questions')

from questions import *
from polls import *

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
@app.route('/e')
def entpage():
    start, pagesize, pagenumber, eat_count = generate_simple_pagination()
    #
    # sd = simple_defaults
    # pagenumber = rai('page') or sd['pagenumber']
    # pagesize = sd['pagesize']
    # sortby = sd['sortby']
    # order = sd['order']
    #
    # start = (pagenumber-1) * pagesize

    count = aql('return length(for i in entities return i)',silent=True)[0]
    pagination = eat_count(count)

    eid = ras('eid') or None
    if eid:
        ent0 = aql('''for i in entities filter i._key==@k
        let user = (for u in users filter u.uid==i.uid return u)[0]
        return merge(i, {user})
        ''',
            silent=True, k=eid)
    else:
        ent0 = []

    ents = aql('''
        for i in entities sort i.t_c desc
        let user = (for u in users filter u.uid==i.uid return u)[0]
        '''
        + f'limit {start},{pagesize}' +
        '''
        return merge(i, {user})
    ''', silent=True)

    # pagination = pgnt.get_pagination_obj(
    #     path=request.path,
    #     order=order,sortby=sortby,
    #     count=count, pagenumber=pagenumber, pagesize=pagesize,
    #     mode='simple',
    # )

    return render_template_g('entities.html.jinja',
        page_title='entities',
        entities = ent0+ents,
        pagination = pagination,
        pagenumber = pagenumber,
    )

@app.route('/e/<string:key>')
def entjson(key):
    ent = aql('for i in entities filter i._key==@k return i', k=key, silent=True)
    if len(ent):
        ent = ent[0]['doc']
        return doc2resp(ent)

    resp = make_response({'error':'no such entity'}, 400)
    return resp

@app.route('/e/<string:key>/<string:field>')
def entjsonwfield(key,field):
    ent = aql('for i in entities filter i._key==@k return i', k=key, silent=True)
    if len(ent):
        ent = ent[0]['doc']
        if field in ent:
            ent = ent[field]
            return doc2resp(doc)

    resp = make_response({'error':'no such entity'}, 400)
    return resp

@app.route('/member/<string:uname>/e/<string:ty>')
def pkey_uname(uname, ty):
    u = get_user_by_name(uname)
    if not u:
        raise Exception('user not exist')
    return pkey(u['uid'], ty)

@app.route('/u/<int:uid>/e/<string:ty>')
def pkey_uid(uid, ty):
    return pkey(uid, ty)

@app.route('/public_key/<string:uname>')
def pkey_un(uname):
    u = get_user_by_name(uname)
    if not u:
        raise Exception('user not exist')
    return pkey(u['uid'],'public_key')

def doc2resp(doc):
    pk = doc
    if isinstance(pk, str):
        return make_text_response(pk)
    else:
        r = make_response(obj2json(pk), 200)
        r.headers['Content-Type'] = 'application/json'
    return r

def pkey(uid, ty):
    doc = aql('for i in entities filter i.type==@ty and i.uid==@uid sort i.t_c desc limit 1 return i', silent=True, uid=uid, ty=ty)[0]['doc']
    return doc2resp(doc)

@app.route('/invitation/<string:iid>')
def get_invitation(iid):
    i = aql('for i in invitations filter i._key==@k return i', k=iid, silent=True)[0]

    if g.current_user['uid']!=5108:
        if 'ip_addr' in i:
            del i['ip_addr']

    if i['uid']:
        resp = make_response('',307)
        resp.headers['Location'] = '/u/'+str(i['uid'])
    else:
        resp = make_text_response(str(i))
    return resp

@app.route('/links')
def show_links():
    linksd, linksl = get_links()
    return render_template_g('links.html.jinja',
        page_title='链接',
        links = linksd,
    )

@stale_cache(maxsize=256, ttr=3, ttl=1800)
def get_oplog(target=None, raw=False):
    query = f'''
    for i in operations
    {'filter i.target==@target' if target else ''}
    sort i.t_c desc limit 500
    let user = (for u in users filter u.uid==i.uid return u)[0]
    return merge(i,{{username:user.name, user}})
    '''

    if target:
        l = aql(query, silent=True, target=target)
    else:
        l = aql(query, silent=True)

    if raw:
        return l

    s = ''
    for i in l:
        del i['_key']
        del i['_rev']
        del i['_id']
        del i['user']
        s+= obj2json(i) + '\n'
    return s.strip()

def t_pain(s):
    return make_response(s, 200)
    resp.headers['Content-type'] = 'text/plain; charset=utf-8'
    return resp

@app.route('/oplog')
def oplog_():
    # l = get_oplog()
    must_be_logged_in()
    l = get_oplog(raw=True)

    return render_template_g('oplog.html.jinja',
        oplog = l,
    )
    return t_pain(s)

@app.route('/oplog/<path:target>')
def oplog_t(target):
    must_be_logged_in()
    l = get_oplog(target=target, raw=True)

    return render_template_g('oplog.html.jinja',
        oplog = l,
    )

    resp = make_response(s, 200)
    resp.headers['Content-type'] = 'text/plain; charset=utf-8'
    return resp

from search import search_term

from pmf import search_term as pm_search_term
@app.route('/ccpfinder')
def searchpm():
    q = ras('q').strip()
    if not q:
        return render_template_g(
            'searchpm.html.jinja',
            hide_title=True,
            page_title='维尼查',
        )
    else:
        result = pm_search_term(q)
        return render_template_g(
            'searchpm.html.jinja',
            query=q,
            hide_title=True,
            page_title='维尼查 - '+flask.escape(q),
            **result,
        )

import sys

sys.path.append('./takeoff/')
from takeoff_search import Search

@app.route('/guizhou')
def tksearch():
    tks = Search()

    q = ras('q').strip()
    if not q:
        return render_template_g(
            'search_guizhou.html.jinja',
            hide_title=True,
            page_title='云上贵州',
            sources = tks.get_sources()
        )
    else:
        # result = pm_search_term(q)
        result,t1 = tks.search(q)
        return render_template_g(
            'search_guizhou.html.jinja',
            query=q,
            hide_title=True,
            page_title='云上贵州 - '+flask.escape(q),
            # **result,
            result=result,
            t1=t1,
        )

@app.route('/u/<int:uid>/favorites')
def user_favorites(uid):
    upld = fav_list_defaults
    pagenumber = rai('page') or upld['pagenumber']
    pagesize = rai('pagesize') or upld['pagesize']
    sortby = ras('sortby') or upld['sortby']
    order = ras('order') or upld['order']

    lq = QueryString('''
        return length(for i in favorites
        filter i.uid==@uid return i)
    ''', uid=uid)

    count = lenfav = aql(lq)[0]

    pagination = pgnt.get_pagination_obj(
        count, pagenumber, pagesize, order,
        request.path, sortby, mode='fav')

    start = (pagenumber-1) * pagesize

    lpointers = aql(f'''
        for i in favorites
        filter i.uid==@uid
        sort i.t_c desc
        limit {start},{start+pagesize}
        return i.pointer
    ''', uid=uid, silent=True)

    u = get_user_by_id(uid)
    litems = resolve_mixed_content_pointers(lpointers)

    return render_template_g(
        'favorites.html.jinja',
        page_title = u['name']+' 的收藏',
        list_items = litems,
        pagination = pagination,
    )

@app.route('/u/<int:uid>/upvoted')
def user_upvoted_contents(uid):
    upld = fav_list_defaults
    pagenumber = rai('page') or upld['pagenumber']
    pagesize = rai('pagesize') or upld['pagesize']
    sortby = ras('sortby') or upld['sortby']
    order = ras('order') or upld['order']

    lq = QueryString('''
        return length(for i in votes
        filter i.uid==@uid and i.vote==1 return i)
    ''', uid=uid)

    count = lenfav = aql(lq)[0]

    pagination = pgnt.get_pagination_obj(
        count, pagenumber, pagesize, order,
        request.path, sortby, mode='fav')

    start = (pagenumber-1) * pagesize

    lpointers = aql(f'''
        for i in votes
        filter i.uid==@uid and i.vote==1

        sort i.t_c desc
        limit {start},{start+pagesize}

        let id = (i.type=='post')?
            concat('posts/',to_string(i.id)):
            (for t in threads filter t.tid==i.id return t)[0]._id

        return id
    ''', uid=uid, silent=True)

    u = get_user_by_id(uid)
    litems = resolve_mixed_content_pointers(lpointers)

    return render_template_g(
        'favorites.html.jinja',
        page_title = u['name']+' 点赞过的内容',
        list_items = litems,
        pagination = pagination,
    )

    # return str(litems)

def resolve_mixed_content_pointers(list_pointers):
    lpointers = list_pointers

    lp_posts = lpointers.filter(lambda p:p.startswith('posts'))
    lp_threads = lpointers.filter(lambda p:p.startswith('threads'))

    lp_posts = pgnt.get_post_list(by='ids', ids=lp_posts, apply_origin=True)
    lp_threads = pgnt.get_thread_list_uncached(by='ids', ids=lp_threads)

    dp = {item['_id']: item for item in lp_posts if item}
    dt = {item['_id']: item for item in lp_threads if item}
    dp.update(dt)

    litems = lpointers.map(lambda s:dp[s] if s in dp else None)
    litems = [i for i in litems if i]

    return litems


from template_globals import tgr; tgr.update(globals())
