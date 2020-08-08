import re
import time

from constants import *

aqlc.create_collection('admins')
aqlc.create_collection('operations')
aqlc.create_collection('aliases')

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

    # 3. calculate page number
    pnum = ((rank - 1) // post_list_defaults['pagesize']) + 1

    # 4. assemble url
    if pnum>1:
        url = '/t/{}?page={}#{}'.format(tid, pnum, pid)
    else:
        url = '/t/{}#{}'.format(tid, pid)

    return url

def get_categories_info():
    return aql('''
        for i in threads collect cid = i.cid with count into cnt
        sort cnt desc
        let co = (for c in categories filter c.cid==cid return c)[0]
        //return {cid, count:cnt, category:co}
        return merge(co, {count:cnt})
    ''', silent=True)

# json apis sharing a common endpoint

api_registry = {}
def register(name):
    def k(f):
        api_registry[name] = f
    return k

@register('test')
def _(j):
    # raise Exception('ouch')
    return {'double':int(j['a'])*2}

@register('login')
def _(j):
    def k(s): return j[s]
    uname = k('username')
    pwh = k('password_hash')

    # find user
    u = aql('for u in users filter u.name==@n return u', n=uname)

    if len(u)==0:
        raise Exception('username not found')

    u = u[0]

    # find password object
    p = aql('for p in passwords filter p.uid==@uid return p', uid=u['uid'])
    if len(p)==0:
        raise Exception('password record not found')

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

        if len(au)==0:
            # raise Exception('alias for user not found')
            pass
        else:
            u = au[0]

    return {'error':False, 'message':'login success', 'setuid':u['uid']}

@register('register')
def _(j):
    def k(s): return j[s]

    uname = k('username')
    pwh = k('password_hash')
    ik = k('invitation_code')

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
        raise Exception('invitation code not exist or expired')

    # generate salt, hash the pw
    hashstr, saltstr = hash_w_salt(pwh)

    # obtain a new uid
    uid = obtain_new_id('uid')

    newuser = dict(
        uid=uid,
        name=uname,
        t_c=time_iso_now(),
        brief='',
        invitation=ik,
    )

    pwobj = dict(
        uid=uid,
        hashstr=hashstr,
        saltstr=saltstr,
    )

    aql('''insert @i into users''', i=newuser)
    aql('''insert @i into passwords''', i=pwobj)

    aql('''for i in invitations filter i._key==@ik
        update i with {active:false} in invitations''', ik=ik)

    return newuser

def obtain_new_id(name):
    # obtain a new uid
    uid = aql('''
        let c = document('counters/counters')
        update c with {{ {d}:c.{d}+1}} in counters return NEW.{d}
    '''.format(d=name))[0]
    return uid

@register('logout')
def _(j):
    return {'logout':True}

def content_length_check(content, allow_short=False):
    if len(content)>100000:
        raise Exception('content too long')
    if len(content)<4 and allow_short==False:
        raise Exception('content too short')

def title_length_check(title):
    if len(title)>35:
        raise Exception('title too long')
    if len(title)<3:
        raise Exception('title too short')

@register('post')
def _(j):
    if 'logged_in' not in j:
        raise Exception('you are not logged in')

    uid = j['logged_in']['uid']

    def es(k): return (str(j[k]) if (k in j) else None)

    target = es('target')
    target = target.split('/')
    if len(target)!=2:
        raise Exception('target format not correct')

    target_type = target[0]
    # pid = int(es('pid'))
    _id = int(target[1])

    # title = es('title').strip()

    content = es('content').strip()
    content_length_check(content)

    if target_type=='thread':
        # check if tid exists
        tid = _id

        thread = aql('for t in threads filter t.tid==@k return t',k=tid,silent=True)
        if len(thread)==0:
            raise Exception('tid not exist')

        thread = thread[0]

        # check if user repeatedly submitted the same content
        lp = aql('for p in posts filter p.uid==@k sort p.t_c desc limit 1 return p',k=uid, silent=True)
        if len(lp) >= 1:
            if lp[0]['content'] == content:
                raise Exception('repeatedly posting same content')

        timenow = time_iso_now()

        newpost = dict(
            uid=uid,
            t_c=timenow,
            content=content.strip(),
            tid=tid,
        )
        inserted = aql('insert @p in posts return NEW', p=newpost)[0]

        # update thread update time
        aql('''
        for t in threads filter t.tid==@tid
        update t with {t_u:@now} in threads
        ''',silent=True,tid=tid,now=timenow)

        # assemble url to the new post
        url = '/p/{}'.format(inserted['_key'])
        inserted['url'] = url

        return inserted

    elif target_type=='category':
        title = es('title').strip()
        title_length_check(title)

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
                raise Exception('repeatedly posting same content')

        # ask for a new tid
        tid = obtain_new_id('tid')

        timenow = time_iso_now()

        newthread = dict(
            uid = uid,
            t_c = timenow,
            t_u = timenow,
            content = content,
            tid = tid,
            cid = cid,
            title = title,
        )

        inserted = aql('insert @p in threads return NEW', p=newthread)[0]

        # assemble url to the new thread
        url = '/t/{}'.format(inserted['tid'])
        inserted['url'] = url

        return inserted

    else:
        raise Exception('unsupported target type')

@register('mark_delete')
def _(j):
    if 'logged_in' not in j:
        raise Exception('you are not logged in')

    uid = j['logged_in']['uid']

    if 'admin' not in j['logged_in']:
        raise Exception('you are not admin')

    if not j['logged_in']['admin']:
        raise Exception('you are not admin')

    def es(k): return (str(j[k]) if (k in j) else None)

    target = es('target')
    target = target.split('/')
    if len(target)!=2:
        raise Exception('target format not correct')

    target_type = target[0]
    # pid = int(es('pid'))
    _id = int(target[1])

    if target_type=='thread':
        upd = aql('for i in threads filter i.tid==@_id\
            update i with {delete:true} in threads return NEW',_id=_id)

        if len(upd)<1:
            raise Exception('tid not found')

    elif target_type=='post':
        upd = aql('for i in posts filter i._key==@_id\
            update i with {delete:true} in posts return NEW',_id=_id)

        if len(upd)<1:
            raise Exception('pid not found')

    else:
        raise Exception('target type not supported')

    aql('insert @k in operations',k={
        'uid':uid,
        'op':'mark_delete',
        'target':target,
    })

    return upd[0]

@register('render')
def _(j):
    if 'logged_in' not in j: raise Exception('you are not logged in')

    def es(k): return (str(j[k]) if (k in j) else None)

    content = es('content').strip()
    content_length_check(content, allow_short=True)

    return {'html':convert_markdown(content)}

import os, base64
def r8():return os.urandom(8)

@register('generate_invitation_code')
def _(j):
    if 'logged_in' not in j: raise Exception('you are not logged in')
    uid = j['logged_in']['uid']

    invs = aql('''for i in invitations
        filter i.uid==@k and i.active == true
        return i''',
        k=uid, silent=True)

    if len(invs)>=5:
        raise Exception('you can only generate so much invitation code')

    code = '2047'+base64.b16encode(r8()).decode('ascii')

    inv = dict(
        active=True,
        uid=uid,
        _key=code,
        t_c=time_iso_now(),
    )

    aql('insert @k in invitations', k=inv)

    return {'error':False}

@register('change_password')
def _(j):
    if 'logged_in' not in j: raise Exception('you are not logged in')
    uid = j['logged_in']['uid']

    pwo = j['old_password_hash']
    pwn = j['new_password_hash']

    # find password object
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

# feedback regulated ping service
# average 1 ping every 3 sec
lastping = time.time()
pingtime = 1.
durbuf = 0
@register('ping')
def _(args):
    global lastping,durbuf,pingtime
    now = time.time()
    dur = now - lastping

    durbuf = dur*0.1+durbuf*0.9
    lastping = now
    target = 3
    err = target - dur

    pingtime = max(1, pingtime + err * 0.3)
    # print('==={:4.4f}'.format(durbuf), 'pingtime {:4.4f}'.format(pingtime))
    ping_itvl = int(pingtime*1000)
    return {'ping':'pong','interval':ping_itvl}
