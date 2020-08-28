import re
import time

from commons import *

from flask import g

aqlc.create_collection('admins')
aqlc.create_collection('operations')
aqlc.create_collection('aliases')
aqlc.create_collection('histories')
aqlc.create_collection('votes')
aqlc.create_collection('messages')
aqlc.create_collection('conversations')
aqlc.create_collection('notifications')

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

def make_notification_names(names, from_uid, why, url, **kw):
    # names is a list of usernames
    d = dict(
        # to_uid=to_uid,
        from_uid=from_uid,
        why=why,
        url=url,
        t_c=time_iso_now(),
        **kw,
    )
    aql('''
    let uidlist = (
        for n in @names
        let user = (for i in users filter i.name==n return i)[0]
        return user.uid
    )
    let uids = remove_value(uidlist, null)

    for i in uids
    let d = merge({to_uid:i}, @k)
    upsert {to_uid:d.to_uid, from_uid:d.from_uid, why:d.why, url:d.url}
    insert d update {} into notifications
    ''', names=names, k=d, silent=True)

    aql('''
    let uidlist = (
        for n in @names
        let user = (for i in users filter i.name==n return i)[0]
        return user.uid
    )
    let uids = remove_value(uidlist, null)

    for uid in uids
    let user = (for u in users filter u.uid==uid return u)[0]

    update user with {
        nnotif: length(for n in notifications filter n.to_uid==user.uid and n.t_c>user.t_notif return n),
    } in users
    ''', names=names, silent=True)

def make_notification_uids(uids, from_uid, why, url, **kw):
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

def es(k):
    j = g.j
    return (str(j[k]) if (k in j) else None)

def ei(k):
    j = g.j
    return (int(j[k]) if (k in j) else None)

def get_user_by_name(name):
    res = aql('for u in users filter u.name==@n return u', n=name, silent=True)
    if len(res)>0:
        return res[0]
    else:
        return None

def get_user_by_id(id):
    res = aql('for u in users filter u.uid==@n return u', n=int(id), silent=True)
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

@register('test')
def _():
    # raise Exception('ouch')
    return {'double':int(g.j['a'])*2}

@register('login')
def _():
    uname = es('username')
    pwh = es('password_hash')

    # find user
    u = get_user_by_name(uname)

    if not u:
        raise Exception('username not found')

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

def insert_new_password_object(uid, pwh):
    # generate salt, hash the pw
    hashstr, saltstr = hash_w_salt(pwh)

    pwobj = dict(
        uid=uid,
        hashstr=hashstr,
        saltstr=saltstr,
    )

    aql('''insert @i into passwords''', i=pwobj)

@register('register')
def _():
    uname = es('username')
    pwh = es('password_hash')
    ik = es('invitation_code')

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
        update i with {active:false} in invitations''', ik=ik)

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

def content_length_check(content, allow_short=False):
    if len(content)>100000:
        raise Exception('content too long')
    if len(content)<4 and allow_short==False:
        raise Exception('content too short')

def title_length_check(title):
    if len(title)>45:
        raise Exception('title too long')
    if len(title)<3:
        raise Exception('title too short')

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

@register('post')
def _():
    if not g.current_user:
        raise Exception('you are not logged in')

    uid = g.current_user['uid']

    if 'delete' in g.current_user and g.current_user['delete']:
        raise Exception('your account has been banned')

    target_type, _id = parse_target(es('target'), force_int=False)

    # title = es('title').strip()

    content = es('content').strip()
    content_length_check(content)

    if target_type=='thread':
        _id = int(_id)
        # check if tid exists
        tid = _id
        thread = get_thread(tid)

        # check if user repeatedly submitted the same content
        lp = aql('for p in posts filter p.uid==@k sort p.t_c desc limit 1 return p',k=uid, silent=True)
        if len(lp) >= 1:
            if lp[0]['content'] == content:
                raise Exception('repeatedly posting same content')

        timenow = time_iso_now()

        newpost = dict(
            uid=uid,
            t_c=timenow,
            content=content,
            tid=tid,
        )
        inserted = aql('insert @p in posts return NEW', p=newpost)[0]

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
        if thread['uid']!=uid:
            make_notification_uids(
                uids=[thread['uid']],
                why='reply_thread',
                url=url,
                from_uid=uid,
            )

        update_thread_votecount(thread['tid'])
        update_user_votecount(g.current_user['uid'])

        return inserted

    elif target_type=='user': # send another user a new message
        _id = int(_id)

        target_uid = _id

        target_user = get_user_by_id(target_uid)
        if not target_user:
            raise Exception('uid not exist')

        # content_length_check(content)
        url = send_message(uid, target_uid, content)
        return {'url':url}

    elif target_type=='username': # send another user a new message
        _id =  _id

        target_user = get_user_by_name(_id)
        if not target_user:
            raise Exception('username not exist')
        target_uid = target_user['uid']

        # content_length_check(content)
        url = send_message(uid, target_uid, content)
        return {'url':url}

    elif target_type=='category':
        _id = int(_id)

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

        return inserted

    elif target_type == 'edit_thread':
        _id = int(_id)

        title = es('title').strip()
        title_length_check(title)

        thread = get_thread(_id)
        if not can_do_to(g.current_user,'edit',thread['uid']):
            raise Exception('insufficient priviledge')

        if 'title' in thread and title==thread['title']:
            if 'content' in thread and content==thread['content']:
                return {'url':'/t/{}'.format(_id)}

        timenow = time_iso_now()

        # update the current thread object
        newthread = dict(
            title = title,
            content = content,
            editor = g.current_user['uid'],
            t_e = timenow,
        )

        aql('for t in threads filter t.tid==@_id update t with @k in threads',
            _id=_id, k=newthread)

        # push the old thread object into histories
        del thread['_key']
        thread['type']='thread'
        thread['t_h']=timenow

        inserted = aql('insert @i into histories return NEW',i=thread)[0]
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
                from_uid=uid,
            )

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

        del post['_key']
        post['type']='post'
        post['t_h']=timenow

        inserted = aql('insert @i into histories return NEW',i=post)[0]
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
                from_uid=uid,
            )

        return inserted
    else:
        raise Exception('unsupported target type')

def update_thread_votecount(tid):
    res = aql('''
let t = (for i in threads filter i.tid==@_id return i)[0]

let upv= length(for v in votes filter v.type=='thread' and v.id==t.tid and v.vote==1 return v)
let nreplies = length(for p in posts filter p.tid==t.tid return p)
let t_u = ((for p in posts filter p.tid==t.tid and p.delete==null sort p.t_c desc limit 1 return p)[0].t_c or t.t_c)

update t with {votes:upv, nreplies, t_u} in threads return NEW
    ''', _id=int(tid), silent=True)

    return res[0]

def update_post_votecount(pid):
    res = aql('''
let t = (for i in posts filter i._key==@_id return i)[0]
let upv = length(for v in votes filter v.type=='post' and v.id==@_id2 and v.vote==1 return 1)
update t with {votes:upv} in posts return NEW
    ''', _id=str(pid), _id2=int(pid), silent=True)

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
    } in users
    ''', uid=int(uid), silent=True)

@register('update_votecount')
def _():
    if not g.current_user: raise Exception('you are not logged in')
    target_type,_id = parse_target(es('target'))

    if target_type=='thread':
        update_thread_votecount(_id)
    elif target_type=='post':
        update_post_votecount(_id)
    else:
        raise Exception('target_type not supported')
    return {'ok':'done'}

updateable_personal_info = [
    ('brief', '个人简介（80字符）'),
    ('url', '个人URL（80字符）'),
    ('showcase', '个人主页展示帖子或评论（例如“t7113”或者“p247105”，中间逗号或空格隔开），暂限4项'),
]

@register('update_personal_info')
def _():
    if not g.current_user: raise Exception('you are not logged in')

    upd=dict()
    for item,explain in updateable_personal_info:
        if item not in g.j:
            continue

        value = es(item)

        # if item=='brief' or item=='showcase':
        if len(value)>80:
            raise Exception('brief/showcase/url should not be longer than 80 chars')

        upd[item] = value

    aql('for u in users filter u.uid==@uid update u with @upd in users return NEW',
        uid=g.current_user['uid'], upd=upd, silent=True)

    return {'error':False}

@register('cast_vote')
def _():
    if not g.current_user: raise Exception('you are not logged in')
    target_type,_id = parse_target(es('target'))
    vote_number = int(es('vote'))

    # assert vote_number in [0, 1, -1]
    assert vote_number in [0, 1]

    if target_type=='thread':
        thread = get_thread(_id)

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
            )
            # put in db
            n = aql('insert @i into votes return NEW',i=vobj,silent=True)[0]

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
            n = aql('update @k with @o in votes return NEW',k=vote,o=vobj,silent=True)[0]

        update_thread_votecount(_id)

        update_user_votecount(thread['uid'])
        update_user_votecount(g.current_user['uid'])
        return {'ok':vote_number}

    elif target_type=='post':
        post = get_post(_id)

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
            )
            # put in db
            n = aql('insert @i into votes return NEW',i=vobj,silent=True)[0]

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
            n = aql('update @k with @o in votes return NEW',k=vote,o=vobj,silent=True)[0]

        update_post_votecount(_id)

        update_user_votecount(post['uid'])
        update_user_votecount(g.current_user['uid'])
        return {'ok':vote_number}

    else:
        raise Exception('target type unsupported')

@register('mark_delete')
def _():
    if not g.current_user:
        raise Exception('you are not logged in')
    uobj = g.current_user
    uid = uobj['uid']

    target = es('target')
    target_type,_id = parse_target(target)

    # get target obj
    if 'post' in target_type:
        _id = str(_id)
        pobj = get_post(_id)

    elif 'thread' in target_type:
        pobj = get_thread(_id)

    else:
        raise Exception('target type not supported')

    if not can_do_to(uobj,'delete',pobj['uid']):
        raise Exception('you don\'t have the required permissions for this operation')

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

    else:
        raise Exception('target type not supported')

    aql('insert @k in operations',k={
        'uid':uid,
        'op':'mark_delete',
        'target':target,
        't_c':time_iso_now(),
    })

    return upd[0]

@register('render')
def _():
    if not g.current_user: raise Exception('you are not logged in')

    content = es('content').strip()
    content_length_check(content, allow_short=True)

    return {'html':convert_markdown(content)}

import os, base64
def r8():return os.urandom(8)

@register('generate_invitation_code')
def _():
    if not g.current_user: raise Exception('you are not logged in')
    uid = g.current_user['uid']

    invs = aql('''for i in invitations
        filter i.uid==@k and i.active == true
        return i''',
        k=uid, silent=True)

    if len(invs)>=num_max_used_invitation_codes:
        raise Exception('you can only generate so much unused invitation code({})'.format(num_max_used_invitation_codes))

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
def _():
    j = g.j

    if not g.current_user: raise Exception('you are not logged in')
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
    if not g.current_user: raise Exception('you are not logged in')
    if not g.current_user['admin']:
        raise Exception("you are not admin")

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

@register('add_alias')
def _():
    j = g.j
    # @掀翻小池塘
    if not g.current_user: raise Exception('you are not logged in')
    if not g.current_user['admin']:
        raise Exception("you are not admin")

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

# feedback regulated ping service
# average 1 ping every 3 sec
lastping = time.time()
pingtime = 1.
durbuf = 0
@register('ping')
def _():
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
