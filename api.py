import re
import time
from app import app
from commons import *
from api_commons import *
from flask import g, make_response

from recently import *

def create_all_necessary_collections():
    aqlc.create_collection('admins')
    aqlc.create_collection('operations')
    aqlc.create_collection('aliases')
    aqlc.create_collection('histories')
    aqlc.create_collection('votes')
    aqlc.create_collection('messages')
    aqlc.create_collection('conversations')
    aqlc.create_collection('notifications')

    aqlc.create_collection('tags')
    aqlc.create_collection('comments')
    aqlc.create_collection('followings')
    aqlc.create_collection('favorites')
    aqlc.create_collection('blacklist')

    aqlc.create_collection('polls')
    aqlc.create_collection('poll_votes')

    aqlc.create_collection('punchcards')

# def make_notification(to_uid, from_uid, why, url, **kw):
#     d = dict(
#         to_uid=to_uid,
#         from_uid=from_uid,
#         why=why,
#         url=url,
#         t_c=time_iso_now(),
#         **kw,
#     )
#
#     aql('insert @k into notifications', k=d, silent=True)

class IndexCreator:
    # create index
    @classmethod
    def create_indices(cls,coll,aa):
        for a in aa:
            qprint('creating index on',coll,a)
            aqlc.create_index(coll, type='persistent', fields=a,
                unique=False,sparse=False)

    # create index with unique=True
    @classmethod
    def create_index_unique_true(cls, coll, a, unique=True):
        for ai in a:
            qprint('creating index on',coll,[ai])
            aqlc.create_index(coll, type='persistent', fields=[ai], unique=unique, sparse=False)

def get_uidlist_by_namelist(names):
    uids = aql('''
    let uidlist = (
        for n in @names
        let user = (for i in users filter i.name==n return i)[0]
        return user.uid
    )
    let uids = remove_value(uidlist, null)
    return uids
    ''', names=names, silent=True)[0]
    return uids

def make_notification_names(names, from_uid, why, url, **kw):
    # names is a list of usernames
    uids = get_uidlist_by_namelist(names)
    return make_notification_uids(uids, from_uid, why, url, **kw)

def make_notification_uids(uids, from_uid, why, url, **kw):
    if not len(uids): return
    if "no_notifications" in g:
        print_err('likely spam, no notifications sent')
        return

    haters = get_reversed_blacklist(from_uid) + get_blacklist(from_uid)
    haters = [i['uid'] for i in haters]

    uids = [i for i in uids if i not in haters]

    # same as above but with uids
    d = dict(
        # to_uid=to_uid,
        from_uid=from_uid,
        why=why,
        url=url,
        t_c=time_iso_now(),
        **kw,
    )
    aql('''
    let uidlist = @uids
    let uids = remove_value(uidlist, null)

    for i in uids
    let d = merge({to_uid:i}, @k)
    upsert {to_uid:d.to_uid, from_uid:d.from_uid, why:d.why, url:d.url}
    insert d update {} into notifications
    ''', uids=uids, k=d, silent=True)

    aql('''
    let uidlist = @uids
    let uids = remove_value(uidlist, null)

    for uid in uids
    let user = (for u in users filter u.uid==uid return u)[0]

    update user with {
        nnotif: length(for n in notifications filter n.to_uid==user.uid and n.t_c>user.t_notif return n),
    } in users
    ''', uids=uids, silent=True)

def get_url_to_post(pid):
    # 1. get tid
    pobj = aql('for p in posts filter p._key==@k return p',k=pid,silent=True)

    if len(pobj)==0:
        raise Exception('no such post')

    pobj = pobj[0]
    tid = pobj['tid']

    # 2. check rank of post in thread

    # see how much posts before this one in thread
    rank = aql('''
        return length(
            for p in posts
            filter p.tid==@tid and p.t_c <= @tc
            return 1
        )
    ''', tid=tid, tc=pobj['t_c'], silent=True)[0]

    return get_url_to_post_given_details(tid, pid, rank)

def get_url_to_post_given_details(tid, pid, rank): # assume you know rank
    # 3. calculate page number
    pnum = ((rank - 1) // post_list_defaults['pagesize']) + 1

    # 4. assemble url
    if pnum>1:
        url = '/t/{}?page={}#{}'.format(tid, pnum, pid)
    else:
        url = '/t/{}#{}'.format(tid, pid)

    return url

@stale_cache(ttr=3, ttl=1200)
def get_bigcats():
    return aql("return document('counters/bigcats')",silent=True)[0]

def get_categories_info():
    return get_categories_info_withuid(show_empty=0 or is_self_admin())

def cats_into_lines(cats):
    bc = get_bigcats()

    res = cats
    catd = {c['cid']:c for c in res}
    catl = []

    singles = []

    def lasttrue(l):
        # if len(l):
        #     l[-1]['last']=True
        # return l
        l.append(None)
        return l

    # sort by bigcats
    briefs, cats = bc['briefs'], bc['cats']
    for bck in briefs:
        cntr = []

        if bck=='main' or bck.startswith('-'):
            continue

        bccats = key(cats, bck) or [] #cats[bck]

        for ck in catd.copy():
            if ck in bccats:
                cntr.append(catd[ck])
                del catd[ck]

        if cntr:
            if len(cntr)>1:
                lasttrue(cntr)
                catl+=cntr
            else:
                singles+=cntr

    leftovers = sorted(catd.values(), key=lambda n:-n['count'])
    singles = sorted(singles, key=lambda n:-n['count'])

    catl += lasttrue(singles+leftovers) # + lasttrue(leftovers)

    return catl

# def get_raw_categories_info():
#     return get_raw_categories_info_raw()

@stale_cache(ttr=5, ttl=1800)
def get_raw_categories_info():
    return aql('''
    for c in categories
        let cnt = length(for i in threads filter i.cid==c.cid return i)
        sort cnt desc
        return merge(c, {count:cnt})
    ''', silent=True)

@stale_cache(ttr=5, ttl=1200)
def get_categories_info_withuid(show_empty=False):
    res = get_raw_categories_info()
    res = [i for i in cats_into_lines(res) if i is not None]

    if show_empty:
        return res
    else:
        return [i for i in res if i['count']>0]

def get_categories_info_twoparts(cid, mode='cat'):
    res = get_raw_categories_info()
    bc = get_bigcats()

    all_upper = False

    if mode == 'cat':
        bcid = None
        for k,v in bc['cats'].items():
            if cid in v:
                bcid = k
                break
        # upper = [i for i in res if i['cid']==cid]
        # lower = [i for i in res if i['cid']!=cid]

        if bcid is not None:
            cid = bcid
        else:
            all_upper = True

    if not all_upper:
        bc = get_bigcats()
        lcats = set(bc['cats'][cid])
        upper = [i for i in res if i['cid'] in lcats]
        lower = [i for i in res if i['cid'] not in lcats]

        upper = cats_into_lines(upper)
        lower = cats_into_lines(lower)

        return upper, lower

    else:
        upper = cats_into_lines(res)
        return upper,

def get_current_salt():
    salt = g.session['salt'] if 'salt' in g.session else '==nosalt=='
    return salt

# json apis sharing a common endpoint

api_registry = {}
def register(name):
    def k(f):
        api_registry[name] = f
    return k

def es(k):
    j = g.j
    return (str(j[k]) if ((k in j) and (k is not None)) else None)

def eb(k):
    j = g.j
    return ((True if j[k] else False) if k in j else False)

def ei(k):
    j = g.j
    return (int(j[k]) if ((k in j) and (k is not None)) else None)

def get_user_by_name(name):
    res = aql('for u in users filter u.name==@n return u', n=name, silent=True)
    if len(res)>0:
        return res[0]
    else:
        return None

def get_user_by_id(id):
    try:
        id = int(id)
    except:
        print_err('personal_party_wrongly_set', id)
        return None

    res = aql('for u in users filter u.uid==@n return u', n=id, silent=True)
    if len(res)>0:
        return res[0]
    else:
        return None

def get_user_by_id_admin(uid):
    uo = aql('for i in users filter i.uid==@k \
        let admin = length(for a in admins filter a.name==i.name return a)\
        return merge(i, {admin})',
        k=uid, silent=True)
    return uo[0] if uo else False

@stale_cache(ttr=10, ttl=1800, maxsize=8192)
def get_user_by_id_cached(uid):
    return get_user_by_id(uid)

@register('test')
def _():
    # raise Exception('ouch')
    return {'double':int(g.j['a'])*2}

def get_public_key_by_uid(uid):
    pk = aql('''
    for i in entities filter i.uid==@uid and i.type=='public_key' sort i.t_c desc limit 1 return i
    ''', uid=uid, silent=True)

    if pk and 'doc' in pk[0]:
        s = pk[0]['doc']
        if isinstance(s, str):
            return s

    return None

from pgp_stuff import verify_publickey_message

@register('login_pgp')
def _():
    msg = es('message')

    # find username in message
    groups = re.findall(username_regex_pgp, msg)
    if len(groups)<1:
        groups = re.findall(username_regex_pgp_new, msg)
        if len(groups)<1:
            raise Exception('No username found in message')
        else:
            uname = base64.b64decode(groups[0][0]).decode('utf-8')
    else:
        uname = groups[0][0]

    timestamp = groups[0][1] # GMT +0
    print_down('attempt pgp login:', uname, timestamp)
    user = get_user_by_name(uname)
    if not user:
        raise Exception('no user named '+uname)

    if not login_time_validation(timestamp):
        raise Exception('timestamp too old, try with a more current one')

    # find public_key
    pk = get_public_key_by_uid(user['uid'])
    if not pk:
        raise Exception('user does not have a public key')

    n = 3
    while n:
        try:
            result = verify_publickey_message(pk, msg)
            if not result:
                raise Exception('verification failed')
        except Exception as e:
            n-=1
            if n:
                print_err('Error:',n,e)
                time.sleep(0.3)
                continue
            else:
                raise e
        else:
            break

    # user sucessfully logged in with pgp
    aql('update @u with {pgp_login:true} in users', u=user)
    return {'error':False, 'message':'login success', 'setuid':user['uid']}

@register('login')
def _():
    uname = es('username')
    pwh = es('password_hash')

    # find user
    u = get_user_by_name(uname)

    if not u:
        raise Exception('username not found')

    if key(u, 'delete'):
        raise Exception('your account has been banned')


    # find password object
    p = aql('for p in passwords filter p.uid==@uid return p', uid=u['uid'])
    if len(p)==0:
        raise Exception('password record not found.')

    p = p[0]
    hashstr = p['hashstr']
    saltstr = p['saltstr']

    # hash incoming with salt and check
    verified = check_hash_salt_pw(hashstr, saltstr, pwh)

    if not verified:
        raise Exception('wrong password')

    # there's one more possibility: user has alias
    alias = aql('for i in aliases filter i.is==@n return i', n=u['name'])

    if len(alias)>=1:
        alias = alias[0]['name']
        au = aql('for u in users filter u.name==@n return u',n=alias)

        if len(au)!=0:
            # don't log into the aliasing account
            # if the aliasing account got its own password
            have_password = aql('for p in passwords filter p.uid==@uid return p', uid=au[0]['uid'])
            if not have_password:
                u = au[0]

    return {'error':False, 'message':'login success', 'setuid':u['uid']}

def insert_new_password_object(uid, pwh):
    # generate salt, hash the pw
    hashstr, saltstr = hash_w_salt(pwh)

    pwobj = dict(
        uid=uid,
        hashstr=hashstr,
        saltstr=saltstr,
    )

    aql('''insert @i into passwords''', i=pwobj)

@stale_cache(ttr=30, ttl=1860)
def get_banned_salts():
    return aql('''for u in users sort u.t_c desc
        limit 100

        filter u.delete==true

        let inv = (for i in invitations filter i._key==u.invitation return i)[0]
        let invsalt = inv.salt

        return invsalt
    ''', silent=True)

def get_salt_registration():
    inv = key(g.current_user, 'invitation')
    if inv:
        isalts = aql('for i in invitations filter i._key==@inv return i.salt', inv=inv,
            silent=True)
        if len(isalts):
            return isalts[0]
    return 'salt not found'

def has_banned_friends():
    # check if salty friends are banned
    banned_friends = get_banned_salts()
    salt = get_current_salt()
    salt2 = get_salt_registration()
    has = salt in banned_friends
    if has: print_err(salt, 'has banned friends')
    has2 = salt2 in banned_friends
    if has2: print_err(salt2, '(during invitation) has_banned_friends')
    return has or has2

@register('register')
def _():
    uname = es('username')
    pwh = es('password_hash')
    ik = es('invitation_code')

    if 'salt' not in g.session:
        raise Exception('to register you must enable cookies / use a browser.')

    salt = g.session['salt']

    # check if user name is legal
    m = re.fullmatch(username_regex, uname)
    if m is None:
        raise Exception('username doesnt match requirement')

    # check if username occupied
    if len(aql('for u in users filter u.name==@n return 1',n=uname))>0:
        raise Exception('username occupied')

    # assert len(pwh) == 32 # sanity

    # check if invitation code exist and valid
    invitation = aql('''
        for i in invitations
        filter i._key == @ik and i.active != false return i
    ''',ik=ik)

    if len(invitation) == 0:
        raise Exception('invitation code not exist or already used by someone else')

    # check if inviting user is banned
    invu = aql('''for u in users filter u.uid==@invuid return u''', invuid=invitation[0]['uid'])
    if len(invu)!=0:
        invu = invu[0]
        if 'delete' in invu and invu['delete']:
            raise Exception('registration is closed, please try again tomorrow')

    # obtain a new uid
    uid = obtain_new_id('uid')

    newuser = dict(
        uid=uid,
        name=uname,
        t_c=time_iso_now(),
        brief='',
        invitation=ik,
    )

    # generate salt, hash the pw
    insert_new_password_object(uid, pwh)

    # hashstr, saltstr = hash_w_salt(pwh)
    #
    # pwobj = dict(
    #     uid=uid,
    #     hashstr=hashstr,
    #     saltstr=saltstr,
    # )
    #
    # aql('''insert @i into passwords''', i=pwobj)

    aql('''insert @i into users''', i=newuser)

    aql('''for i in invitations filter i._key==@ik
        update i with {active:false, ip_addr:@ip, salt:@salt} in invitations''', ik=ik, ip=g.display_ip_address, salt=salt)

    return newuser

def obtain_new_id(name):
    # obtain a new uid
    uid = aql('''
        let c = document('counters/counters')
        update c with {{ {d}:c.{d}+1}} in counters return NEW.{d}
    '''.format(d=name))[0]
    return uid

def increment_view_counter(target_type, _id):
    if target_type=='thread' or target_type=='user':
        _id = int(_id)
        keyname=target_type[0]+'id'
    elif target_type=='post':
        _id = str(_id)
        keyname='_key'
    else:
        raise Exception('unsupported tt for vc increment')
    aql('''
        for i in {collname} filter i.{keyname}=={_id}
        update i with {{ vc:i.vc+1 }} in {collname}
    '''.format(
        collname = target_type+'s',
        keyname = keyname,
        _id = _id,
    ),
    silent=True)

@register('logout')
def _():
    return {'logout':True}

def get_thread(tid):
    thread = aql('for t in threads filter t.tid==@k return t',
    k=int(tid),silent=True)
    if len(thread)==0:
        raise Exception('tid not exist')
    return thread[0]

def get_post(pid):
    post = aqlc.from_filter('posts','i._key==@k', k=str(pid), silent=True)
    if len(post) == 0:
        raise Exception('pid not found')
    return post[0]

def banned_check():
    if 'delete' in g.current_user and g.current_user['delete']:
        raise Exception('your account has been banned')

def get_comment(k):
    c = aqlc.from_filter('comments', 'i._key==@k', k=str(k), silent=True)
    if len(c) == 0: raise Exception('comment id not found')
    return c[0]

@register('comment')
def _():
    must_be_logged_in()
    uid = g.selfuid
    op = es('op')
    t_c = time_iso_now()

    if op=='add':
        content = es('content').strip()
        parent = es('parent').strip()

        parent_object = aql('return document(@parent)', parent=parent, silent=True)
        if not parent_object:
            raise Exception('parent object not found')

        # check if user repeatedly submitted the same content
        lp = aql('for p in comments filter p.uid==@k sort p.t_c desc limit 1 return p',k=uid, silent=True)
        if len(lp) >= 1:
            if lp[0]['content'] == content:
                raise Exception('repeatedly posting same content')


        coid = str(obtain_new_id('pid'))

        content_length_check(content, allow_short=True)

        newcomment = dict(
            _key = coid,
            content = content,
            parent = parent,
            t_c = t_c,
            uid = uid,
        )

        aql('insert @k in comments', k=newcomment)

    elif op=='edit':
        content = es('content').strip()
        key = es('key').strip()
        comm = get_comment(key)

        if not can_do_to(g.current_user, 'edit', comm['uid']):
            raise Exception('insufficient priviledge')

        content_length_check(content)

        newcomment = dict(
            _key = key,
            content = content,
            t_e = t_c,
            editor = uid,
        )

        aql('update @k with @k in comments', k=newcomment)
    else:
        raise Exception('unsupported op on comments')

    return {'error':False}

def get_comments(parent):
    comments = aql('''for i in comments filter i.parent==@p
        sort i.t_c asc
        let user = (for u in users filter u.uid==i.uid return u)[0]
        return merge(i, {user})''', p=parent, silent=True)
    html = render_template_g(
        'comment_section.html.jinja',
        comments = comments,
        parent = parent,
    )
    return html

@register('render_comments')
def _():
    j = g.j
    parent = es('parent').strip()
    html = get_comments(parent)
    return {'error':False, 'html':html}

@app.route('/comments/<string:k1>/<string:k2>')
def getcomments(k1,k2):
    parent = k1+'/'+k2
    html = get_comments(parent)
    return html

def current_user_doesnt_have_enough_likes():
    return g.current_user['nlikes'] < 3 if 'nlikes' in g.current_user else True

def dlp_ts(ts): return min(60, max(5 +0, int(ts*0.025*2)))
def dlt_ts(ts): return min(10, max(2 +0, int(ts*0.006*2)))

def daily_limit_posts(uid):
    user = get_user_by_id_cached(uid)
    trust_score = trust_score_format(user)
    return dlp_ts(trust_score)

def daily_limit_threads(uid):
    user = get_user_by_id_cached(uid)
    trust_score = trust_score_format(user)
    return dlt_ts(trust_score)

def daily_number_posts(uid):
    return aql('return length(for t in posts filter t.uid==@k and t.t_c>@t return t)', silent=True, k=uid, t=time_iso_now(-86400*2))[0]

def daily_number_threads(uid):
    return aql('return length(for t in threads filter t.uid==@k and t.t_c>@t return t)', silent=True, k=uid, t=time_iso_now(-86400*2))[0]

@ttl_cache(ttl=10, maxsize=1024)
def daily_limit_posts_cached(uid):return daily_limit_posts(uid)
@ttl_cache(ttl=10, maxsize=1024)
def daily_limit_threads_cached(uid):return daily_limit_threads(uid)

@ttl_cache(ttl=10, maxsize=1024)
def daily_number_posts_cached(uid):return daily_number_posts(uid)
@ttl_cache(ttl=10, maxsize=1024)
def daily_number_threads_cached(uid):return daily_number_threads(uid)


def spam_kill(content):
    from antispam import is_spam
    spam_detected = False
    if is_spam(content):
        spam_detected = True

        if current_user_doesnt_have_enough_likes():
            aql('update @u with @u in users', u={
                '_key':g.current_user['_key'],
                'delete':True,
            })
            g.no_notifications = True
    return spam_detected

@register('post')
def _():
    must_be_logged_in()
    banned_check()

    # check if salty friends are banned
    if has_banned_friends() \
        and not is_self_admin() \
        and current_user_doesnt_have_enough_likes():

        aql('update @u with @u in users', u={
            '_key':g.current_user['_key'],
            'delete':True,
        })
        g.no_notifications = True

    uid = g.current_user['uid']

    target_type, _id = parse_target(es('target'), force_int=False)

    # title = es('title').strip()

    content = es('content').strip()
    content_length_check(content)

    pagerank = pagerank_format(g.current_user)
    trust_score = trust_score_format(g.current_user)

    spam_detected = spam_kill(content)

    if target_type=='thread':
        _id = int(_id)
        # check if tid exists
        tid = _id
        thread = get_thread(tid)

        # check if user repeatedly submitted the same content
        lp = aql('for p in posts filter p.uid==@k sort p.t_c desc limit 1 return p',k=uid, silent=True)
        if len(lp) >= 1:
            if lp[0]['content'] == content:
                raise Exception(en('repeatedly posting same content'))


        # daily limit for low pagerank users
        # daily_limit = int(pagerank*2+6)
        daily_limit = daily_limit_posts(uid)
        recent24hs = daily_number_posts(uid)

        if recent24hs>=daily_limit:
            raise Exception(spf(zh('你在过去$3小时发表了$0个评论，达到或超过了你目前的社会信用分($1) 所允许的值($2)。如果要提高这个限制，请尽量发表受其他用户欢迎的内容，以提高社会信用分。'))(recent24hs, trust_score, daily_limit,48))


        # check if user posted too much content in too little time
        recents = aql('return length(for t in posts filter t.uid==@k and t.t_c>@t return t)', silent=True, k=uid, t=time_iso_now(-1200))[0]
        if recents>=5:
            raise Exception(spf(en('too many posts ($0) in the last $1 minute(s)'))(recents, 1200//60))


        if lp and lp[0]['t_c'] > time_iso_now(-60):
            raise Exception(en('please wait one minute between posts'))

        # # new users cannot post outside water in the first hours
        # if g.current_user['t_c'] > time_iso_now(-600) and \
        #     thread['cid']!=4 and current_user_doesnt_have_enough_likes():
        #     raise Exception('新注册用户前十分钟只能在水区发帖')

        # can only post once in questions
        if 'mode'in thread and thread['mode']=='question':
            nposts_already = len(aql(
                'for p in posts filter p.uid==@k and p.tid==@tid return 1',
                k=uid, tid=tid, silent=True))

            if nposts_already:
                raise Exception(zh('（从2021年7月8日开始）每个问题只允许发表一次回答。'))

        timenow = time_iso_now()

        tu = thread['uid']
        if im_in_blacklist_of(tu):
            raise Exception(en('you are in the blacklist of the thread owner'))

        while 1:
            new_pid = str(obtain_new_id('pid'))
            exists = aql('for p in posts filter p._key==@pid return p', silent=False, pid=new_pid)
            if len(exists):
                continue
            else:
                break

        newpost = dict(
            uid=uid,
            t_c=timenow,
            content=content,
            tid=tid,
            _key=str(new_pid),
        )

        if spam_detected:
            newpost['spam']=True

        inserted = aql('insert @p in posts return NEW', p=newpost)[0]
        inserted['content']=None

        # update thread update time
        aql('''
        for t in threads filter t.tid==@tid
        update t with {t_u:@now} in threads
        ''',silent=True,tid=tid,now=timenow)

        # assemble url to the new post
        url = get_url_to_post(str(inserted['_key']))
        # url = '/p/{}'.format(inserted['_key'])
        inserted['url'] = url

        # notifications
        # extract_ats
        ats = extract_ats(content)
        ats = [name for name in ats if name!=g.current_user['name']]
        if len(ats):
            make_notification_names(
                names=ats,
                why='at_post',
                url=url,
                from_uid=uid,
            )

        # replies
        publisher = get_user_by_id(thread['uid'])
        if thread['uid']!=uid and (publisher['name'] not in ats):
            make_notification_uids(
                uids=[thread['uid']],
                why='reply_thread',
                url=url,
                from_uid=uid,
            )

        update_thread_votecount(thread['tid'])
        update_user_votecount(g.current_user['uid'])

        return inserted

    elif target_type=='username' or target_type=='user': # send another user a new message
        if target_type=='username':
            _id =  _id

            target_user = get_user_by_name(_id)
            if not target_user:
                raise Exception('username not exist')
            target_uid = target_user['uid']

        else:
            _id = int(_id)

            target_uid = _id

            target_user = get_user_by_id(target_uid)
            if not target_user:
                raise Exception('uid not exist')

        # new users are not allowed to send pms to other ppl unless they
        # got enough likes
        if current_user_doesnt_have_enough_likes()\
            and target_user['name']!='thphd':
            raise Exception(zh("你暂时还是新用户，不可以发信给除了站长(thphd)之外的其他人"))

        # content_length_check(content)
        url = send_message(uid, target_uid, content)
        return {'url':url}

    elif target_type=='category':
        _id = int(_id)

        title = es('title').strip()
        title_length_check(title)

        mode = es('mode')
        mode = None if mode!='question' else mode
        assert mode in [None, 'question']

        # check if cat exists
        cid = _id
        cat = aql('for c in categories filter c.cid==@k return c',k=cid,silent=True)

        if len(cat)==0:
            raise Exception('cid not exist')

        cat = cat[0]

        # check if user repeatedly submitted the same content
        lp = aql('for t in threads filter t.uid==@k sort t.t_c desc limit 1 return t',k=uid, silent=True)
        if len(lp) >= 1:
            if lp[0]['content'] == content:
                raise Exception(en('repeatedly posting same content'))

        # check if the same title has been used before
        jk = aql('for t in threads filter t.title==@title limit 1 return 1', title=title, silent=True)
        if len(jk):
            raise Exception(zh('这个标题被别人使用过'))


        # # new users cannot post outside water in the first hours
        # if g.current_user['t_c'] > time_iso_now(-43200) and \
        #     cid!=4 and current_user_doesnt_have_enough_likes():
        #     raise Exception('新注册用户最开始只能在水区发帖')


        daily_limit = daily_limit_threads(uid)
        recent24hs = daily_number_threads(uid)

        if recent24hs>=daily_limit:
            raise Exception(spf(zh('你在过去$3小时发表了$0个主题帖或问题，达到或超过了你目前的社会信用分($1) 所允许的值($2)。如果要提高这个限制，请尽量发表受其他用户欢迎的内容，以提高社会信用分。'))(recent24hs, trust_score, daily_limit, 48))


        # check if user posted too much content in too little time
        recents = aql('return length(for t in threads filter t.uid==@k and t.t_c>@t return t)', silent=True, k=uid, t=time_iso_now(-1200))[0]
        if recents>=2 and not g.is_admin:
            raise Exception(spf(en('too many threads ($0) in the last $1 minute(s)'))(recents, 1200//60))


        # ask for a new tid
        tid = obtain_new_id('tid')

        timenow = time_iso_now()

        newthread = dict(
            _key = str(tid),

            uid = uid,
            t_c = timenow,
            t_u = timenow,
            content = content,
            mode = mode,
            tid = tid,
            cid = cid,
            title = title,
        )
        if spam_detected: newthread['spam']=True

        inserted = aql('insert @p in threads return NEW', p=newthread)[0]
        inserted['content']=None

        # assemble url to the new thread
        url = '/t/{}'.format(inserted['tid'])
        inserted['url'] = url

        # notifications
        # extract_ats
        ats = extract_ats(content)
        ats = [name for name in ats if name!=g.current_user['name']]
        if len(ats):
            make_notification_names(
                names=ats,
                why='at_thread',
                url=url,
                from_uid=uid,
            )

        update_user_votecount(g.current_user['uid'])
        update_thread_votecount(inserted['tid'])

        return inserted

    elif target_type == 'edit_thread':
        _id = int(_id)

        title = es('title').strip()
        title_length_check(title)

        mode = es('mode')
        mode = None if mode!='question' else mode
        assert mode in [None, 'question']

        thread = get_thread(_id)
        if not can_do_to(g.current_user,'edit',thread['uid']):
            raise Exception('insufficient priviledge')

        if 'title' in thread and title==thread['title'] and\
            mode==(thread['mode']if 'mode' in thread else None):

            if 'content' in thread and content==thread['content']:
                return {'url':'/t/{}'.format(_id)}

        timenow = time_iso_now()

        # update the current thread object
        newthread = dict(
            title = title,
            content = content,
            editor = g.current_user['uid'],
            mode = mode,
            t_e = timenow,
        )

        aql('for t in threads filter t.tid==@_id update t with @k in threads',
            _id=_id, k=newthread)

        # push the old thread object into histories
        del thread['_key']
        thread['type']='thread'
        thread['t_h']=timenow

        inserted = aql('insert @i into histories return NEW',i=thread)[0]
        inserted['content']=None
        inserted['url'] = '/t/{}'.format(_id)
        url = inserted['url']

        # notifications
        # extract_ats
        ats = extract_ats(content)
        ats = [name for name in ats if name!=g.current_user['name']]
        if len(ats):
            make_notification_names(
                names=ats,
                why='at_thread',
                url=url,
                # from_uid=uid,
                from_uid=thread['uid'],
            )

        update_thread_votecount(_id)
        return inserted

    elif target_type == 'edit_post':
        _id = int(_id)

        post = get_post(_id)
        if not can_do_to(g.current_user, 'edit', post['uid']):
            raise Exception('insufficient priviledge')

        if 'content' in post and content==post['content']:
            return {'url':'/p/{}'.format(_id)}

        timenow = time_iso_now()

        newpost = dict(
            content = content,
            editor = g.current_user['uid'],
            t_e = timenow,
        )

        aql('for p in posts filter p._key==@_id update p with @k in posts',
            _id=str(_id), k=newpost)

        post['pid']=post['_key']
        del post['_key']
        post['type']='post'
        post['t_h']=timenow

        inserted = aql('insert @i into histories return NEW',i=post)[0]
        inserted['content']=None
        url = get_url_to_post(str(_id))
        inserted['url'] = url

        # notifications
        # extract_ats
        ats = extract_ats(content)
        ats = [name for name in ats if name!=g.current_user['name']]
        if len(ats):
            make_notification_names(
                names=ats,
                why='at_post',
                url=url,
                from_uid=post['uid'],
                # from_uid=uid,
            )

        return inserted
    else:
        raise Exception('unsupported target type')

'''
hackernews ranking algorithm

instead of calculating a score, this version calculates a new timestamp relative to the old timestamp.

i can't read arc so i copied this:
https://medium.com/hacking-and-gonzo/how-hacker-news-ranking-algorithm-works-1d9b0cf2c08d

in essence,
score = 1 / (time_passed ** 2) * points[or votes, assume min(points)=1]

now if a post go from 1 points to 5 points, it's score should raise five times.
which will push the post forward in time, in front of other posts with score 1.

but exactly how much time forward (time_advance) to push?
or, what exact time should we push the post to (time_passed_advanced)?

    old_score = 1/(time_passed**2) * 1 # default score if you got 1 point
    now_score = 1/(time_passed**2) * points

    # now assume we push the post forward by time_advance,
    # reaching time_passed_advanced.

    time_passed_advanced = time_passed - time_advance
    advanced_score = 1/(time_passed_advanced**2) = now_score

    time_passed_advanced = sqrt(1/now_score)
    = sqrt(1/( points/(time_passed**2) ))
    = sqrt((time_passed**2)/points)
    = time_passed / sqrt(points) # voila!

    hence,
    time_hackernews = time_now - time_passed_advanced
    = time_now - time_passed / sqrt(points)
    = time_now - (time_now - time_submitted) / sqrt(points)

    a very high points of score will make a post's time_hackernews very close to time_now.

'''

hn_formula = QueryString('''
let bigcats = (
    let ccats = document('counters/bigcats').cats
    let jj = t.cid
    for ii in attributes(ccats)
    filter position(ccats[ii], jj)
    return ii
)

let t_submitted = date_timestamp(t.t_c)
let t_updated = date_timestamp(t.t_u)

let t_man = date_timestamp(t.t_manual) or 0

let pinned = t_man > t_now or null

let votes = t.amv or 0

let points = max([(votes - 0.9), 0]) * 3 + 1 + t.nreplies * .2
let points2 = max([(votes - 0.9), 0]) * 3 + 1 + t.nreplies * .2

let t_ref = t_submitted * 0.8 + t_updated * 0.2
let t_offset = 3600*1000*2.5
let t_offset2 = 3600*1000*24*10
let t_backoff = (t_now - t_ref + t_offset) / sqrt(points)
let t_backoff2 = (t_now - t_ref + t_offset2) / sqrt(points2)

let t_hn = max([t_now + t_offset - t_backoff, t_man and 0])
let t_hn2 = max([t_now + t_offset2 - t_backoff2, t_man and 0])

//let min_interval = 5*60*1000
//let interval_multiplier = (20*60*1000)

let t_next_hn_update = t_now + max([max([0, t_now - t_hn]) / 86400000 * @interval_multiplier, @min_interval])

let t_hn_iso = left(date_format(t_hn,'%z'), 19)
let t_hn2_iso = left(date_format(t_hn2,'%z'), 19)

let viewcount_v2 = (for j in view_counters filter j.targ==t._id return j.c)[0]
let total_viewcount = (viewcount_v2 or 0) + (t.old_vc or 0)

limit 20
update t with {
    t_hn:t_hn_iso, t_hn2: t_hn2_iso,
    t_next_hn_update, pinned, bigcats,
    vc:total_viewcount,
    new_vc:viewcount_v2 or 0,
} in threads return 1
''')

hn_formula_post = QueryString('''
let t_submitted = date_timestamp(t.t_c)
let t_updated = date_timestamp(t.t_u)

let t_man = date_timestamp(t.t_manual) or 0

let votes = (t.votes or 0) + (t.nfavs or 0) //differ
let points = max([(votes - 0.9), 0]) * 3 + 1 //differ
let t_offset = 3600*1000*1 //differ
let t_offset2 = 3600*1000*24*10 //differ
let t_hn = max([t_now + t_offset - (t_now - t_submitted + t_offset) / sqrt(points), t_man and 0])

let t_hn2 = max([t_now + t_offset2 - (t_now - t_submitted + t_offset2) / sqrt(points), t_man and 0])

//let min_interval = 5*60*1000
//let interval_multiplier = (20*60*1000)

let t_next_hn_update = t_now + max([max([0, t_now - t_hn]) / 86400000 * @interval_multiplier, @min_interval])

let t_hn_iso = left(date_format(t_hn,'%z'), 19)
let t_hn2_iso = left(date_format(t_hn2,'%z'), 19)
limit 20
update t with {t_hn:t_hn_iso, t_hn2:t_hn2_iso,
 t_next_hn_update} in posts return 1 //differ
''')

def update_thread_hackernews_batch():
    qr = QueryString('''
        let t_now = date_timestamp(@now)

        for t in threads

        filter t.t_next_hn_update < t_now
        sort t.t_next_hn_update asc
    ''', now=time_iso_now())

    qr += hn_formula
    qr.append(min_interval=300*1000, interval_multiplier=3600*1000)

    res = aql(qr, silent=True, raise_error=False)
    return len(res)

def update_thread_hackernews(tid):
    qr = QueryString('''
        let t_now = date_timestamp(@now)

        for t in threads
        filter t.tid==@tid
    ''', now=time_iso_now(), tid=tid)

    qr += hn_formula
    qr.append(min_interval=300*1000, interval_multiplier=3600*1000)

    aql(qr, silent=True, raise_error=False)

def update_post_hackernews_batch():
    qr = QueryString('''
        let t_now = date_timestamp(@now)

        //for t in threads
        for t in posts

        filter t.t_next_hn_update < t_now
        sort t.t_next_hn_update asc
    ''', now=time_iso_now())

    qr += hn_formula_post
    qr.append(min_interval=600*1000, interval_multiplier=14400*1000)

    res = aql(qr, silent=True, raise_error=False)
    return len(res)

update_user_pagerank_qr = QueryString('''

//let now = date_iso8601(date_now())
//let t_now = date_timestamp(now)
let t_now = date_now()

//let now_iso = @now_iso

let uid = t.uid
let time_factor = 0.99999985

let update_interval = @update_interval // 30min
let newuser_update_interval = 60*1000 // 60s
let uidelta = update_interval - newuser_update_interval

//nlikes: received
//nliked: gave

let target_user = t

// all-time pagerank
let newscore = sum(
    for v in votes filter v.to_uid==target_user.uid and v.vote==1

    let voter = (for u in users filter u.uid==v.uid return u)[0]
    let voterrank = voter.pagerank or 0
    let voterbonus = (voter.uid==5108?1:0) + voterrank
    let score = (voter.nliked?voterbonus / voter.nliked:0) * .95

    return score
)

//let last_recent_update_time = t.last_recent_update_time or '1971-01-01'

//let mrl = max([@recent_timestamp, last_recent_update_time])
//let mrl = last_recent_update_time
//let dtni = date_timestamp(@now_iso)
//let dtlru = date_timestamp(last_recent_update_time)
//let dt_since_last = (dtni - dtlru)/1000

let efs = @efs

// exp-falloff pagerank
let newscore_recent = sum(
    for ef in efs let earlier=ef[0],later=ef[1],multiplier=ef[2]
        return sum(
            for v in votes filter v.to_uid==target_user.uid and v.vote==1
            and v.t_cc >= earlier and v.t_cc < later

            let voter = (for u in users filter u.uid==v.uid return u)[0]
            let voterrank = voter.pagerank_recent or 0
            let voterbonus = (voter.uid==5108?1:0) + voterrank
            let score = (voter.recent_votes_gave?voterbonus/voter.recent_votes_gave:0)*.95
            return score
        )*multiplier )

let total_activities = (t.recent_threads or 0) + (t.recent_posts or 0)
let total_activities_w_votes = total_activities + (t.recent_votes or 0)
let total_activities_plain = (t.nthreads or 0)+(t.nposts or 0)+(t.nlikes or 0)
let tawvp = total_activities_plain*.5 + total_activities_w_votes * 2

let trust_factor = 1 - pow(0.85, tawvp)
let unit_pr = total_activities?newscore_recent / total_activities:0

let trust_score = unit_pr*trust_factor + (1-trust_factor)*(0/1000000)
// in the beginning everyone have 0 points

//----

let recent_threads = sum(
    for ef in efs let earlier=ef[0],later=ef[1],multiplier=ef[2]
        return count(
            for i in threads filter i.uid==uid
                and i.t_c >= earlier and i.t_c < later return i
        )*multiplier )

let recent_posts = sum(
    for ef in efs let earlier=ef[0],later=ef[1],multiplier=ef[2]
        return count(
            for i in posts filter i.uid==uid
                and i.t_c >= earlier and i.t_c < later return i
        )*multiplier )

let recent_votes = sum(
    for ef in efs let earlier=ef[0],later=ef[1],multiplier=ef[2]
        return count(
            for i in votes filter i.to_uid==uid and i.vote==1
                and i.t_cc >= earlier and i.t_cc < later return i
        )*multiplier )

let recent_votes_gave = sum(
    for ef in efs let earlier=ef[0],later=ef[1],multiplier=ef[2]
        return count(
            for i in votes filter i.uid==uid and i.vote==1
                and i.t_cc >= earlier and i.t_cc < later return i
        )*multiplier )

//----

let new_vc = (for j in view_counters filter j.targ==t._id return j.c)[0] or 0
let vc = (t.old_vc or 0) + new_vc

update t with {
    t_next_pr_update: t_now,
    pagerank:newscore,

    //last_recent_update_time:@now_iso,

    recent_threads,
    recent_posts,
    recent_votes,
    recent_votes_gave,

    total_activities,
    total_activities_w_votes,
    total_activities_plain,
    tawvp,
    pagerank_recent:newscore_recent,
    trust_factor:trust_factor,

    trust_score:trust_score,

    new_vc,
    vc,

} in users

return {name:NEW.name, pr:NEW.pagerank}
    ''', update_interval = 1800*1000)

def update_user_pagerank_batch():
    quantifier = QueryString('''
    let t_now2 = date_now()
    for t in users
    filter t.t_next_pr_update < t_now2 - @update_interval
    sort t.t_next_pr_update asc
    limit 30
    ''')

    res = aql(quantifier+update_user_pagerank_qr,
        silent=True, raise_error=False,
        # recent_timestamp=time_iso_now(-86400*365),
        # now_iso_24h=time_iso_now(-3600*24),
        # now_iso=time_iso_now(),
        efs = get_exponential_falloff_spans_for_now(),
    )
    return len(res)

def update_user_pagerank_one(uid):
    quantifier = QueryString('''
    for t in users
    filter t.uid==@uid
    ''', uid = uid,)

    res = aql(quantifier+update_user_pagerank_qr,
        silent=True, raise_error=False,
        # now_iso_24h=time_iso_now(-3600*24),
        efs = get_exponential_falloff_spans_for_now(),
    )
    return len(res)

uf_registry = {}
def update_forever_generator(update_function, name_string, balance_count=25):
    def update_forever():
        global uf_registry
        if name_string in uf_registry: return
        uf_registry[name_string] = 1

        # itvl = 1
        logitvl = 0

        while 1:
            itvl = math.exp(logitvl)

            time.sleep(itvl)
            l = 0
            try:
                l = update_function()
            except Exception as e:
                print_err('e_update_forever', e)
                print_info(f'update {name_string} failed, retry...')
                continue

            print_info(f'updated {name_string}: {l:3d} itvl: {itvl:3.2f}')

            err = l - balance_count

            logitvl = logitvl - err*0.01
            logitvl = clip(-5, 8)(logitvl)

    return update_forever

# dispatch(update_forever)
def dispatch_database_updaters():
    time.sleep(3)
    dispatch(update_forever_generator(
        update_thread_hackernews_batch, 'hackernews(t)', 10))
    dispatch(update_forever_generator(
        update_post_hackernews_batch, 'hackernews(p)', 10))
    dispatch(update_forever_generator(
        update_user_pagerank_batch, 'user pagerank', 15))


def update_thread_votecount(tid):

    res = aql('''
let t = (for i in threads filter i.tid==@_id return i)[0]

let bigcats = (
    let ccats = document('counters/bigcats').cats
    let jj = t.cid
    for ii in attributes(ccats)
    filter position(ccats[ii], jj)
    return ii
)

let nfavs = length(for f in favorites filter f.pointer==t._id return f)

let rv = t.recovered_votes or 0
let upv= length(for v in votes filter v.type=='thread' and v.id==t.tid and v.vote==1 return v) + rv
let nreplies = length(for p in posts filter p.tid==t.tid return p)
let nreplies_visible = length(for p in posts filter p.tid==t.tid and p.delete==null return p)

let last_reply = (for p in posts filter p.tid==t.tid and p.delete==null sort p.t_c desc limit 1 return p)[0]

let last_reply_uid = last_reply.uid
let t_u = (last_reply.t_c or t.t_c)

let mvp = (for p in posts filter p.tid==t.tid sort p.votes desc limit 1 return p)[0]

// mvp = max vote post, mv = max vote (of that post)
// mvu = uid of mvp, amv = absolute max vote (of both the mvp and the thread)
update t with {
    votes:upv,
    nreplies, nreplies_visible,
    t_u,
    last_reply_uid, last_reply_pid:last_reply._key,
    mvp:mvp._key, mv:mvp.votes or 0, mvu:mvp.uid,
    amv: max([mvp.votes or 0, upv or 0]), nfavs, bigcats}
in threads
return NEW
    ''', _id=int(tid), silent=True)

    update_thread_hackernews(int(tid))
    return res[0]

def update_post_votecount(pid):
    res = aql('''
let t = (for i in posts filter i._key==@_id return i)[0]

let nfavs = length(for f in favorites filter f.pointer==t._id return f)

let rv = t.recovered_votes or 0
let upv = length(for v in votes filter v.type=='post' and v.id==to_number(t._key) and v.vote==1 return 1) + rv

update t with {votes:upv, nfavs} in posts
return NEW
    ''', _id=str(pid), silent=True)

    return res[0]

def update_user_votecount(uid):
    res = aql('''
    for u in users filter u.uid==@uid
    update u with
    {
        ninbox: length(for m in messages filter m.to_uid==u.uid and m.t_c>u.t_inbox return m),

        nnotif: length(for n in notifications filter n.to_uid==u.uid and n.t_c>u.t_notif return n),

        nthreads:length(for t in threads filter t.uid==u.uid return t),
        nposts:length(for p in posts filter p.uid==u.uid return p),
        nlikes:length(for v in votes filter v.to_uid==u.uid and v.vote==1 return v),
        nliked:length(for v in votes filter v.uid==u.uid and v.vote==1 return v),

        nfavs:length(for f in favorites filter f.uid==u.uid return f),
        nfaveds:length(for f in favorites filter f.to_uid==u.uid return f),

        nfollowings:length(for f in followings filter f.uid==u.uid and f.follow==true return f),
        nfollowers:length(for f in followings filter f.to_uid==u.uid and f.follow==true return f),

    } in users
    ''', uid=int(uid), silent=True)

@register('update_votecount')
def _():
    must_be_logged_in()
    target_type,_id = parse_target(es('target'))

    if target_type=='thread':
        update_thread_votecount(_id)
    elif target_type=='post':
        update_post_votecount(_id)
    else:
        raise Exception('target_type not supported')
    return {'ok':'done'}

updateable_personal_info = [
    ('brief', '个人简介（80字符，帖子中显示在用户名旁边）'),
    ('url', '个人URL（80字符，显示在用户个人主页）'),
    ('receipt_addr','收款地址（数字货币等）'),
    ('contact_method','联系方式'),
    ('personal_title', '个性抬头（6字符，显示在用户头像左上角）'),
    ('personal_party', '个性党徽（数字UID，所对应用户头像的缩小版会显示在用户头像左上角）（会屏蔽个性抬头）'),
    ('showcase', '个人主页展示帖子或评论（例如“t7113”或者“p247105”，中间逗号或空格隔开），限4项'),
    ('ignored_categories', '主页不显示的分类（数字ID，中间用逗号隔开，例如不想看水区和江湖，就写“4,21”）'),
    ('background_color', '背景色（R,G,B 用半角逗号隔开，0-255）（你浏览本站的时候，以及别人浏览你的个人主页或帖子的时候，背景颜色都会变成这个）'),

    ('header_background_color', '导航栏背景色（同上）（你浏览本站的时候，以及别人浏览你的个人主页或帖子的时候，导航栏颜色都会变成这个）'),
    ('header_text_color', '导航栏文字颜色（同上）'),

    ('background_image_uid', '背景水印图片（使用头像图片，请填写头像UID，所对应用户头像会变成背景水印'),
    ('background_image_opacity', '背景水印不透明度(0.0-1.0)'),
    ('background_image_scale', '背景水印放大比例(0.5-4.0)'),

    ('delay_send', '启用延时发送功能（yes即启用，留空即停用）（发帖的时候可以选择延时发送）'),
    ('hide_avatar', '隐藏页面中的头像（yes即隐藏，留空即显示）'),
    ('hide_title', '隐藏头像上方的绿帽（yes即隐藏，留空即显示）'),
]

@register('update_personal_info')
def _():
    must_be_logged_in()
    banned_check()

    upd=dict()
    for item,explain in updateable_personal_info:
        if item not in g.j:
            continue

        value = es(item).strip()

        # if item=='brief' or item=='showcase':
        if (
            len(value)>180 or
            (not item.startswith('receipt') and len(value)>80)
            or (item=='personal_title' and len(value)>6) or (item=='ignored_categories' and len(value)>40)
        ):
            raise Exception('其中一项超出长度限制')

        if item=='personal_party' and value.strip()!='' and not intify(value):
            raise Exception('党派只能填数字UID或留空')

        if item=='background_image_uid' and value.strip()!='' and not intify(value):
            raise Exception('背景水印图片只能填数字UID或留空')

        if item=='background_image_opacity' and value:
            fv = float(value)
            if 0<=fv and fv<=1:
                pass
            else:
                raise Exception('透明度不在允许范围内')

        if item=='background_image_scale' and value:
            fv = float(value)
            if .5<=fv and fv<=4.0:
                pass
            else:
                raise Exception('缩放比例不在允许范围内')

        upd[item] = value

    aql('for u in users filter u.uid==@uid update u with @upd in users return NEW',
        uid=g.current_user['uid'], upd=upd, silent=True)

    return {'error':False}

aqlc.create_collection('tags')
@register('edit_tag')
def _():
    must_be_logged_in()
    banned_check()

    target_type,_id = parse_target(es('target'))
    tagname = es('name')
    to_remove = eb('delete')

    assert target_type == 'thread'

    # check if thread actually exists
    thread = get_thread(_id)

    if 'tags' in thread:
        tags = thread['tags']
    else:
        tags = []

    if not can_do_to(g.current_user, 'edit', thread['uid']):
        raise Exception('insufficient priviledge')

    if not to_remove:
        # check legality of tagname
        m = re.fullmatch(tagname_regex, tagname)
        if m is None:
            raise Exception('tagname illegal')

        # add new tag
        if tagname in tags:
            raise Exception('tag already exists')
        tags.append(tagname)

        if len(tags)>6:
            raise Exception('最多只能加6个标签')

        # check tag record existence
        tag = aqlc.from_filter('tags', 'i.name==@n', n=tagname)

        # if tag doesn't exist:
        if not tag:
            aql('insert @k into tags', k=dict(
                name=tagname,
                t_c=time_iso_now(),
                uid=g.selfuid,
            ))

        thread['tags'] = tags
        aql('update @t with @t in threads', t=thread, silent=True)

    else:
        # remove existing tag
        if tagname not in tags:
            raise Exception('tag not in thread')

        tags = [i for i in tags if i!=tagname]
        thread['tags'] = tags

        aql('update @t with @t in threads', t=thread, silent=True)

    return {'error':False}



@register('cast_vote')
def _():
    must_be_logged_in()
    banned_check()

    target_type,_id = parse_target(es('target'))
    vote_number = int(es('vote'))

    # assert vote_number in [0, 1, -1]
    assert vote_number in [0, 1]

    if target_type=='thread':
        thread = get_thread(_id)
        pointer = thread['_id']

        if not can_do_to(g.current_user, 'vote', thread['uid']):
            raise Exception('insufficient priviledge')

        # see if you already voted
        votes = aqlc.from_filter('votes','i.uid==@k and i.type=="thread" and i.id==@_id',k=g.current_user['uid'],_id=_id)

        timenow = time_iso_now()

        # if you havent voted
        if not votes:
            if vote_number==0:
                return {'ok':'no-op'}

            # make vote
            vobj = dict(
                uid=g.current_user['uid'],
                to_uid=thread['uid'],
                type='thread',
                id=_id,
                vote=vote_number,
                t_c=timenow,
                t_u=timenow,

                t_cc = thread['t_c'],

                pointer=pointer,
            )
            # put in db
            n = aql('insert @i into votes return NEW',i=vobj,silent=False)[0]

        #if you voted before
        else:
            vote = votes[0]
            if vote['vote'] == vote_number:
                return {'ok':'no-op'}

            # make vote
            vobj = dict(
                vote=vote_number,
                t_u=timenow,
            )

            # put in db
            n = aql('update @k with @o in votes return NEW',k=vote,o=vobj,silent=False)[0]

        update_thread_votecount(_id)

        update_user_votecount(thread['uid'])
        update_user_votecount(g.current_user['uid'])

        target_user = get_user_by_id_cached(thread['uid'])
        if (key(target_user, 'trust_score') or 0) < 200/1000000:
            update_user_pagerank_one(thread['uid'])
        # update_user_pagerank_one(g.current_user['uid'])

        return {'ok':vote_number}

    elif target_type=='post':
        post = get_post(_id)
        pointer = post['_id']

        if not can_do_to(g.current_user, 'vote', post['uid']):
            raise Exception('insufficient priviledge')

        # see if you already voted
        votes = aqlc.from_filter('votes','i.uid==@k and i.type=="post" and i.id==@_id',k=g.current_user['uid'],_id=_id)

        timenow = time_iso_now()

        # if you havent voted
        if not votes:
            if vote_number==0:
                return {'ok':'no-op'}

            # make vote
            vobj = dict(
                uid=g.current_user['uid'],
                to_uid=post['uid'],
                type='post',
                id=_id,
                vote=vote_number,
                t_c=timenow,

                t_cc = post['t_c'],

                pointer=pointer,
            )
            # put in db
            n = aql('insert @i into votes return NEW',i=vobj,silent=False)[0]

        #if you voted before
        else:
            vote = votes[0]
            if vote['vote'] == vote_number:
                return {'ok':'no-op'}

            # make vote
            vobj = dict(
                vote=vote_number,
                t_u=timenow,
            )

            # put in db
            n = aql('update @k with @o in votes return NEW',k=vote,o=vobj,silent=False)[0]

        update_post_votecount(_id)
        update_thread_votecount(post['tid'])

        update_user_votecount(post['uid'])
        update_user_votecount(g.current_user['uid'])

        target_user = get_user_by_id_cached(post['uid'])
        if (key(target_user, 'trust_score') or 0) < 200/1000000:
            update_user_pagerank_one(post['uid'])
        # update_user_pagerank_one(g.current_user['uid'])

        return {'ok':vote_number}

    else:
        raise Exception('target type unsupported')

@register('mark_delete')
def _():
    must_be_logged_in()
    banned_check()

    uobj = g.current_user
    uid = uobj['uid']

    target = es('target')
    target_type,_id = parse_target(target,force_int=False)

    # get target obj
    if 'post' in target_type:
        # _id = str(_id)
        pobj = get_post(_id)
        tobj = get_thread(pobj['tid'])

    elif 'thread' in target_type:
        _id = int(_id)
        pobj = get_thread(_id)

    elif 'conversation' in target_type:
        cobj = aqlc.from_filter('conversations','i.convid==@cid and i.uid==@uid',cid=_id, uid=uid)[0]

    elif 'message' in target_type:
        mobj = aqlc.from_filter('messages', 'i._key==@k', k=_id)[0]

    else:
        raise Exception('target type not supported')

    noperm = 'you don\'t have the required permissions for this operation'

    if 'post' in target_type:
        if not can_do_to(uobj,'delete',pobj['uid']) and not can_do_to(uobj, 'delete', tobj['uid']):
            raise Exception(noperm)

    elif 'thread' in target_type:
        if not can_do_to(uobj,'delete',pobj['uid']):
            raise Exception(noperm)

    elif 'conversation' in target_type:
        if not can_do_to(uobj, 'delete', cobj['uid']):
            raise Exception(noperm)

    elif 'message' in target_type:
        if not(mobj['uid']==uid or mobj['to_uid']==uid):
            raise Exception(noperm)

    upd = False

    if target_type=='thread':
        upd = aql('for i in threads filter i.tid==@_id\
            update i with {delete:true} in threads return NEW',_id=_id)

        if len(upd)<1:
            raise Exception('tid not found')

    elif target_type=='post':
        upd = aql('for i in posts filter i._key==@_id\
            update i with {delete:true} in posts return NEW',_id=_id)

        update_thread_votecount(pobj['tid'])

        if len(upd)<1:
            raise Exception('pid not found')

    elif target_type == 'conversation':
        upd = aql('for i in conversations filter i.convid==@_id and i.uid==@uid\
            update i with {delete:true} in conversations return NEW',
            _id=_id, uid=uid)

        if len(upd)<1:
            raise Exception('convid not found')

    elif target_type == 'uconversation':
        upd = aql('for i in conversations filter i.convid==@_id and i.uid==@uid\
            update i with {delete:null} in conversations return NEW',
            _id=_id, uid=uid)

        if len(upd)<1:
            raise Exception('convid not found')

    # prefix 'u' means to un-mark an entity of deleted status

    elif target_type=='uthread':
        upd = aql('for i in threads filter i.tid==@_id\
            update i with {delete:null} in threads return NEW',_id=_id)

        if len(upd)<1:
            raise Exception('tid not found')

    elif target_type=='upost':
        upd = aql('for i in posts filter i._key==@_id\
            update i with {delete:null} in posts return NEW',_id=_id)

        update_thread_votecount(pobj['tid'])

        if len(upd)<1:
            raise Exception('pid not found')

    elif target_type=='message':
        upd = aql('update @k with {delete:true} in messages return NEW', k=mobj)
    elif target_type=='umessage':
        upd = aql('update @k with {delete:null} in messages return NEW', k=mobj)

    else:
        raise Exception('target type not supported')

    if 'message' not in target_type:
        aql('insert @k in operations',k={
            'uid':uid,
            'op':'mark_delete',
            'target':target,
            't_c':time_iso_now(),
        })

    return upd[0]

@register('render')
def _():
    must_be_logged_in()

    content = es('content').strip()
    content_length_check(content, allow_short=True)

    return {'html':convert_markdown(content)}

import os, base64
def r8():return os.urandom(8)

def generate_invitation_code(uid):
    if uid:
        num_invs = aql('''return length(for i in invitations
            filter i.uid==@k and i.active == true
            return i)''',
            k=uid, silent=True)[0]

        if num_invs>=num_max_used_invitation_codes:
            raise Exception('you can only generate so much unused invitation code({})'.format(num_max_used_invitation_codes))
    else:
        uid=False

    while 1:
        code = '2047'+base64.b16encode(r8()).decode('ascii')
        inv = dict(
            active=True,
            uid=uid,
            _key=code,
            t_c=time_iso_now(),
        )
        if aql('return length(for i in invitations filter i._key==@k return i)',k=code)[0]:
            continue
        else:
            aql('insert @k in invitations', k=inv)
            break

    return code

@register('generate_invitation_code')
def _():
    must_be_logged_in()
    banned_check()

    uid = g.current_user['uid']

    code = generate_invitation_code(uid)
    return {'error':False}

@register('change_password')
def _():
    j = g.j

    must_be_logged_in()
    uid = g.current_user['uid']

    pwo = j['old_password_hash']
    pwn = j['new_password_hash']

    # find password object
    p = aql('for p in passwords filter p.uid==@uid return p', uid=uid)
    if len(p)==0:
        # generate salt, hash the pw
        insert_new_password_object(uid, pwo)
        time.sleep(0.5)

        p = aql('for p in passwords filter p.uid==@uid return p', uid=uid)

        if len(p)==0:
            raise Exception('password record for the user not found')

    p = p[0]

    res = check_hash_salt_pw(p['hashstr'],p['saltstr'],pwo)
    if not res:
        raise Exception('password incorrect')

    hash,salt = hash_w_salt(pwn)

    aql('for p in passwords filter p.uid==@uid update p with \
        {hashstr:@h, saltstr:@s} in passwords',uid=uid,h=hash,s=salt)

    return {'error':False}

def send_message(fromuid, touid, content):
    timenow = time_iso_now()

    # 1. determine whether to start a new conversation or not
    # find conversation object
    found = aql('''
    let c1 = (for c in conversations filter c.uid==@a and c.to_uid==@b
    sort c.t_c desc limit 1 return c)
    let c2 = (for c in conversations filter c.uid==@b and c.to_uid==@a
    sort c.t_c desc limit 1 return c)

    return append(c1, c2)
    ''',
        a=fromuid, b=touid, silent=True)[0]

    if len(found)!=0 and len(found)!=2:
        raise Exception('conversation data corrupted, contact admin')

    if len(found)==0:
        # generate a unique convid
        while 1:
            convid = get_random_hex_string(8)
            # check collision
            collisions = aql('return length(for c in conversations filter c.convid==@k return c)', k=convid)[0]

            if not collisions:
                break

        conv1,conv2 = aql('''
        for i in @k insert i into conversations return NEW
        ''',k=[
            dict(
                uid=fromuid,
                to_uid=touid,
                convid=convid,
                t_u=timenow,
                t_c=timenow,
            ),
            dict(
                uid=touid,
                to_uid=fromuid,
                convid=convid,
                t_u=timenow,
                t_c=timenow,
            ),
        ])

    else:
        # use existing conversation
        conv1, conv2 = found[0],found[1]

    assert conv1['convid']==conv2['convid']
    convid = conv1['convid']

    aql('insert @k in messages', k=dict(
        uid=fromuid,
        to_uid=touid,
        t_c=timenow,
        content=content.strip(),
        convid=convid,
    ))

    if found:
        # update conversation object
        aql('for i in @c update i with {t_u:@t} in conversations', c=[conv1,conv2], t=timenow)

    url = '/m/'+convid

    # update target user's ninbox
    update_user_votecount(touid)

    return url

@register('ban_user')
def _():
    j = g.j
    must_be_logged_in()
    must_be_admin()

    reason = es('reason')
    uid = ei('uid')
    t_c = time_iso_now()

    reverse = es('reverse')

    if not reverse:
        # mark user as banned
        aql('for u in users filter u.uid==@uid update u with {delete:true, t_d:@t_d} in users',
        uid=uid,t_d=t_c)

        # log
        aql('insert @k in operations',k={
            'uid':g.current_user['uid'],
            'op':'ban_user',
            'target':uid,
            'reason':reason,
            't_c':t_c,
        })

        return {'error':False}

    else:
        # mark user as unbanned
        aql('for u in users filter u.uid==@uid update u with {delete:false, t_d:@t_d} in users',
        uid=uid,t_d=t_c)

        # log
        aql('insert @k in operations',k={
            'uid':g.current_user['uid'],
            'op':'ban_user',
            'target':uid,
            'reason':reason,
            't_c':t_c,
            'reverse':True,
        })

        return {'error':False}

def is_self_admin():
    return True if g.current_user and g.current_user['admin'] else False

def must_be_admin():
    must_be_logged_in()
    if not is_self_admin():
        raise Exception("you are not admin")

@register('add_alias')
def _():
    j = g.j
    # @掀翻小池塘
    must_be_logged_in()
    must_be_admin()

    name = es('name')
    _is = es('is')

    un = get_user_by_name(name)
    uis = get_user_by_name(_is)

    if un and uis:
        l = aql('for i in aliases filter i.is == @n return i',n=_is)
        if len(l):
            raise Exception('this user already linked to '+str(l[0]['name']))

        aql('insert @k into aliases', k={
            'name':name,
            'is':_is
        })
        return {'error':False}
    else:
        raise Exception('user not exist')

@register('browser_check')
def _():
    j = g.j
    return {'error':False,'setbrowser':1}

# @register('viewed_target')
# def _():
#     raise Exception('api abandoned')
#     j = g.j
#     ty, _id = parse_target(j['target'])
#
#     uasl = g.user_agent_string.lower()
#
#     if ('bot' in uasl
#         or 'archiver' in uasl
#         or 'noua' == uasl
#         or 'webmeup' == uasl):
#         print_err('viewed_target request for', j['target'],
#             'seems to be from a bot.', uasl)
#         return {'error':False, 'info':'nicework'}
#
#     if not g.using_browser:
#         print_err('someone without a browser tried viewed_target()')
#         return {'error':False, 'info':'nicework'}
#
#     print_info('trying to increment_view_counter for', j['target'], g.user_agent_string)
#
#     if ty=='thread':
#         increment_view_counter('thread', _id)
#     elif ty=='user':
#         increment_view_counter('user', _id)
#     else:
#         raise Exception('unsupported target')
#     return {'error':False, 'info':'nicework'}

aqlc.create_collection('view_counters')
@register('viewed_target_v2')
def _():
    targ = es('target')
    if not targ:
        raise Exception ('no target specified')

    uas = g.user_agent_string
    uasl = uas.lower()

    if ('bot' in uasl
        or 'archiver' in uasl
        or 'noua' == uasl
        or 'webmeup' in uasl):
        print_err('viewed_target_v2 request for', j['target'],
            'seems to be from a bot.', uas)
        return {'error':False, 'info':'botlike'}

    # if not g.using_browser:
    #     print_err('someone without a browser tried viewed_target_v2()')
    #     return {'error':False, 'info':'browserless'}

    print_up('trying to increment_view_counter_v2 for', targ, uas)

    c = aql("upsert {targ:@targ} insert {targ:@targ , c:1} update {c:OLD.c+1} in view_counters return NEW.c", silent=True, targ=targ)[0]

    return {'error':False, 'info':'nicework', 'c':c}

def must_be_logged_in():
    if not g.logged_in: raise Exception('you are not logged in')

@register('get_categories_info')
def _():
    must_be_logged_in()
    return {'categories':get_categories_info_withuid(show_empty=g.is_admin)}

@register('move_thread')
def _():
    must_be_logged_in()

    j = g.j
    ty, _id = parse_target(j['target'])
    cid = int(j['cid'])

    t = get_thread(_id)
    if not can_do_to(g.current_user, 'move', t['uid']):
        raise Exception('not enought priviledge')

    c = aql('for c in categories filter c.cid==@cid return c', cid=cid, silent=True)
    if not c:
        raise Exception('no such category')

    aql('for i in threads filter i.tid==@_id \
        update i with {cid:@cid} in threads', _id=_id, cid=cid)

    aql('insert @k in operations',k={
        'uid':g.current_user['uid'],
        'op':'move',
        'target':j['target'],
        't_c':time_iso_now(),
        'cid':cid,
    })

    update_thread_votecount(_id)
    return {'error':False}

@register('become')
def _():
    must_be_logged_in()
    must_be_admin()

    uid = g.j['uid']
    assert 5108==g.selfuid
    return {'setuid':uid}

from polls import *
@register('add_poll')
def _():
    must_be_logged_in()
    j = g.j
    qs = j['question']
    add_poll(qs)
    return {'error':False}

@register('modify_poll')
def _():
    must_be_logged_in()
    qv = g.j['question']
    qid = g.j['qid']
    modify_poll(qid, qv)
    return {'error':False}

@register('add_poll_vote')
def _():
    must_be_logged_in()
    j = g.j
    id = j['pollid']
    choice = j['choice']
    delete = j['delete'] if 'delete' in j else False
    add_poll_vote(id, choice, delete=delete)
    return {'error':False}

from flask import render_template
@register('render_poll')
def _():
    j = g.j
    pollid=j['pollid']
    poll = get_poll(pollid, g.selfuid)

    html = render_template(
        'poll_one.html.jinja',
        poll = poll,
    )
    return {'error':False, 'html':html}

@register('change_time')
def _():
    must_be_admin()
    tid = g.j['tid']
    ts = g.j['t_manual']
    ts = str(ts)
    ttttt = dfs(ts) # sanity check

    if ttttt < dfs('1989-06-04'):
        ts = '1989-06-04'

    aql('for i in threads filter i.tid==@tid update i with {t_manual:@t} in threads', tid=tid, t=ts)

    update_thread_votecount(tid)

    return {'error':False}

@register('list_admins')
def _():
    must_be_admin()
    l = aql('for i in admins return i.name')
    return {'list_admins':l}

import json,re

@register('add_entity')
def _():
    must_be_logged_in()
    j = g.j
    _type = j['type'].strip()
    assert isinstance(_type, str)
    exp = r"^[a-zA-Z0-9_\-.]{1,20}$"
    if not re.match(exp, _type):
        raise Exception(f'"type" does not conform to the regex "{exp}"')

    doc = j['doc']
    s = json.dumps(doc, ensure_ascii=False)

    if len(s)>1024*10:
        raise Exception('json too large')

    numcreated = aql('return length(for i in entities filter i.uid==@uid return 1)', silent=True, uid=g.current_user['uid'])[0]
    if numcreated>=128:
        raise Exception('you can only create so much entities')

    now = time_iso_now()
    aql('insert @k into entities', k=dict(
        t_c = now,
        uid = g.current_user['uid'],
        type = _type,
        doc = doc,
    ))
    return {'error':False}

@register('modify_entity')
def _():
    must_be_logged_in()

    j = g.j
    _key = j['_key']

    ent = aql('for i in entities filter i._key==@k return i',k=_key)[0]

    if ent['uid']!=g.current_user['uid']:
        must_be_admin()

    doc = j['doc']
    s = obj2json(doc)

    if len(s)>1024*10:
        raise Exception('json too large')

    now = time_iso_now()
    aql('update @k with @k in entities', k=dict(
        _key=_key,
        t_e = now,
        editor = g.current_user['uid'],
        doc = doc,
    ))
    return {'error':False}

@register('delete_entity')
def _():
    must_be_logged_in()
    j = g.j
    _key = j['_key']
    ent = aql('for i in entities filter i._key==@k return i',k=_key)[0]
    if ent['uid']!=g.current_user['uid']:
        must_be_admin()

    aql('for i in entities filter i._key==@k remove i in entities', k=_key)

    return {'error':False}


aqlc.create_collection('followings')

def did_follow(uid, to_uid):
    followed_before = aql('''for i in followings filter i.uid==@uid and i.to_uid==@to_uid return i''', uid=uid, to_uid=to_uid, silent=True)
    if not followed_before:
        return False
    else:
        return followed_before[0]['follow']

def get_followers(uid, followings=False, limit=5):
    if followings:
        return aql(f'''
        for i in followings filter i.uid==@uid and i.follow==true sort i.t_c desc
        let user = (for u in users filter u.uid==i.to_uid return u)[0]
        limit {limit}
        return merge(i, {{user}})
        ''', uid=uid, silent=True)
    else:
        return aql(f'''
        for i in followings filter i.to_uid==@uid and i.follow==true sort i.t_c desc
        let user = (for u in users filter u.uid==i.uid return u)[0]
        limit {limit}
        return merge(i, {{user}})
        ''', uid=uid, silent=True)

@register('follow')
def _():
    must_be_logged_in()
    j=g.j
    uid = j['uid']
    follow = j['follow'] # Boolean
    assert follow in [True, False]

    if g.selfuid == uid:
        raise Exception('you cannot follow yourself')

    user = get_user_by_id(uid)
    if not user:
        raise Exception('user does not exist')

    if follow == True:
        followed_before = aql('''for i in followings filter i.uid==@uid and i.to_uid==@to_uid return i''', uid=g.selfuid, to_uid=uid, silent=True)

        if not followed_before:
            make_notification_uids([uid], g.selfuid, 'follow', url='')

    aql('''
    upsert {uid:@uid, to_uid:@to_uid} insert {follow:@follow, uid:@uid, to_uid:@to_uid, t_c:@ts} update {follow:@follow, t_u:@ts}
    in followings
    ''', uid=g.selfuid, to_uid=uid,
        ts=time_iso_now(), follow=follow, silent=True,
    )

    update_user_votecount(uid)
    update_user_votecount(g.selfuid)
    return {'error':False}

aqlc.create_collection('favorites')
@register('favorite')
def _():
    must_be_logged_in()
    target_type,_id = parse_target(es('target'))
    delete = eb('delete')

    if target_type=='thread' or target_type=='post':
        if target_type=='thread':
            # check existence of thread
            ob = get_thread(_id)
        else:
            ob = get_post(_id)
        assert ob

        pointer = ob['_id']

        if not delete:
            k = dict(
                type = target_type,
                id = _id,
                uid = g.selfuid,
                to_uid = ob['uid'],
                t_c = time_iso_now(),
                pointer = pointer,
            )

            lk = dict(
                uid = k['uid'],
                pointer = k['pointer']
            )

            # upsert
            aql('upsert @lk insert @k update @k into favorites', lk=lk, k=k)

        else:
            aql('for i in favorites filter i.uid==@uid and i.pointer==@ptr remove i in favorites',
                ptr = pointer,
                uid = g.selfuid,
            )

        if target_type=='thread':
            update_thread_votecount(_id)
        else:
            update_post_votecount(_id)

        update_user_votecount(ob['uid'])
        update_user_votecount(g.selfuid)

    else:
        raise Exception('target not supported')

    return {'error':False}

error_false = {'error':False}

aqlc.create_collection('blacklist')
@register('blacklist')
def _():
    must_be_logged_in()
    uid = ei('uid')
    uname = es('username')
    delete = eb('delete')

    if not uid:
        uid = get_user_by_name(uname)['uid']

    enabled = False if delete else True

    curr = get_blacklist(uid)

    mbs = max_blacklist_size = 25
    if len(curr)>=mbs and enabled == True:
        raise Exception(f'you cannot blacklist more than {mbs} user(s)')

    # check existence of uid
    u = get_user_by_id(uid)

    if not u:
        raise Exception('no such user')

    now = time_iso_now()

    aql('upsert @lk insert @ik update @uk into blacklist',
        lk = dict(uid=g.selfuid, to_uid=uid),
        ik = dict(uid=g.selfuid, to_uid=uid,
            t_c = now,
            t_u = now,
            enabled = enabled,
        ),
        uk = dict(uid=g.selfuid, to_uid=uid,
            t_u = now,
            enabled = enabled,
        ),
    )

    return error_false

@stale_cache(ttr=5, ttl=1800)
def get_blacklist(uid):
    list = aql('''for i in blacklist filter i.uid==@uid and i.enabled == true
    let user = (for u in users filter u.uid==i.to_uid return u)[0]
    return merge(i, {user})''', uid=uid, silent=True)
    return list

def get_blacklist_set(uid):
    return set(i['to_uid'] for i in get_blacklist(uid))

@stale_cache(ttr=5, ttl=1800)
def get_reversed_blacklist(uid): # who hates me
    list = aql('''for i in blacklist filter i.to_uid==@uid and i.enabled == true
    let user = (for u in users filter u.uid==i.uid return u)[0]
    return merge(i, {user})''', uid=uid, silent=True)
    return list

@register('get_blacklist')
def _():
    must_be_logged_in()
    list = get_blacklist(g.selfuid)
    return {'blacklist':[(l['user']['name'],l['to_uid']) for l in list]}

def im_in_blacklist_of(uid, reversed=False):
    su = g.selfuid
    tu = uid

    if reversed:
        su,tu = tu,su

    res = aql('''for i in blacklist
    filter i.uid==@tu and i.to_uid==@su and i.enabled==true
    return i
    ''', tu=tu, su=su)

    if res:
        return True
    return False

@stale_cache(ttr=5, ttl=1800)
def get_blacklist_all():
    return aql('''for i in blacklist filter i.enabled==true
    let user = (for u in users filter u.uid==i.uid return u)[0]
    let to_user = (for u in users filter u.uid==i.to_uid return u)[0]
    sort i.t_u
    return merge(i,{user, to_user})
    ''', silent=True)

@register('get_blacklist_all')
def _():
    # must_be_admin()
    res = get_blacklist_all()
    return {'blacklist': [(
        l['user']['name'],
        l['user']['uid'],
        l['to_user']['name'],
        l['to_user']['uid'],
        l['t_u'],
    ) for l in res]}

@app.route('/blacklist')
def listbl():
    all = get_blacklist_all()
    r = all.map(lambda a:' '.join([
        a['t_c'],
        a['user']['name'],
        '-->',
        a['to_user']['name'],
    ]))
    r = '\n'.join(r)
    resp = make_response(r, 200)
    resp.headers['Content-type'] = 'text/plain; charset=utf-8'
    return resp

# @register('chat')
# def _():
#     must_be_logged_in()
#     op = es('op')
#     if op == ''

@register('get_online_stats')
def _():
    tot, reg = get_online_stats()
    return {'total':tot,'registered':reg}

@stale_cache(ttr=3, ttl=1800)
def get_online_stats():
    n = aql('''
    for i in punchcards
    filter i.t_u > @recent
    collect aggregate n=count(i),nu=count_unique(i.uid)
    let lu=nu-1
    return {n, lu}
    ''',silent=True, recent=time_iso_now(-1800))[0]
    return n['n'],n['lu']

@stale_cache(ttr=6, ttl=1800)
def get_online_admins():
    n = aqls('''
for i in punchcards
filter i.t_u > @recent
sort i.t_u desc
    for u in users
    filter u.uid==i.uid
        for a in admins
        filter a.name==u.name
        collect uid=i.uid into g=i.t_u
        let gm = max(g)
        sort gm desc
        return {uid, t_u:gm}
    ''', recent=time_iso_now(-86400/4))

    return n

@register('get_user_data_by_uid')
def _():
    j = g.j
    uid = key(j,'uid')
    uid = intify(uid)

    if not (uid and uid>0):
        raise Exception('uid illegal')

    u = get_user_by_id_cached(uid)
    if not u:
        raise Exception('user not exist')
    return {'user':u}

def put_punchcard():
    t_c = time_iso_now()
    t_u = t_c

    uid = g.selfuid
    salt = get_current_salt()

    hostname=request.host

    if salt=='==nosalt==':
        qprint('ping no salt')
        return

    if not g.using_browser:
        qprint('ping no browser')
        return

    # get punchcard. if within 3 minutes, don't stamp again
    n=aql('''return count(
    for i in punchcards
    filter i.t_u > @recent3 and i.salt==@salt
     and i.uid==@uid and i.hostname==@hostname
     return i)
    ''', silent=True, recent3=time_iso_now(-180),
        salt=salt, uid=uid, hostname=hostname)[0]

    if n:
        # print_down('within 3 minutes, not stamping again')
        return

    ups = dict(salt=salt, uid=uid, hostname=hostname)
    kins = dict(t_c=t_c, t_u=t_u, uid=uid, salt=salt, hostname=hostname)
    kups = dict(t_u=t_u, hostname=hostname)

    aql('upsert @ups insert @kins update @kups in punchcards',
        ups=ups, kins=kins, kups=kups, silent=True)
    print_down(f'stamped {uid} {salt} {hostname}')

# feedback regulated ping service
# average 1 ping every 3 sec
lastping = time.time()
# pingtime = 1.
logpt = 0
durbuf = 0
@register('ping')
def _():
    global lastping,durbuf,logpt
    now = time.time()
    dur = now - lastping
    lastping = now

    durbuf = dur*0.2+durbuf*0.8
    target = 5
    err = target - dur

    logpt = min(max(0, logpt+err*.05), 10)
    pingtime = math.exp(logpt)
    print_up(f'PING duration {durbuf:4.2f} pingtime {pingtime:4.2f}')
    ping_itvl = int(pingtime*1000)

    put_punchcard()

    return {'ping':'pong','interval':ping_itvl}
