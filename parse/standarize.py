# such that the names of variables could live in harmony...

from parse import *

def cl(colname):
    # aqlcl(colname)
    aqlcl(colname, 'filter i.imp==true')

aqlc.create_collection('threads')
cl('threads')

aqlc.create_collection('posts')
cl('posts')

aqlc.create_collection('categories')
cl('categories')

aqlc.create_collection('users')
cl('users')

aqlc.create_collection('avatars')
cl('avatars')

aqlc.create_collection('counters')
cl('counters')

aqlc.create_collection('invitations')
cl('invitations')

aqlc.create_collection('passwords')
cl('passwords')

if 1:
    aql('''
    for i in postlets insert {
        tid:i.aid,
        cid:i.cid,
        uid:i.authorID,
        t_c:i.addTime,
        t_u:i.date,
        tags:i.tags,
        title:i.title,
        content:i.content,
        imp:true,
    } into threads
    ''')


    aql('''
    for j in postlets
    for i in j.comments
    insert {
        uid:i.authorID,
        t_c:i.addTime,
        content:i.content,
        tid:j.aid,
        imp:true,
    } into posts
    ''')

    aql('''
    for i in catlets
    insert {
        cid:i.cid,
        name:i.name,
        brief:i.brief,
        imp:true,
    } into categories
    ''')

    aql('''
    for i in userlets
    insert {
        uid:i.userID,
        name:i.userName,
        t_c:i.regTime,
        url:i.userURL,
        brief:i.brief,
        imp:true,
    } into users
    ''')

    aql('''
    for i in userlets
    insert {
    uid:i.userID,
    data:i.avatar,
    imp:true,
    } into avatars
    ''')

    # create users whose posts got hidden(not included in backup).
    aql('''
    for p in posts

    let u = (for u in users filter u.uid==p.uid return u)[0]

    filter u==null

    collect uid = p.uid

    insert {name:'(Removed)', uid:uid,
        imp:true,
    } into users
    ''')

    aql('insert @i into threads', i={
        "tid": 7000,
        "cid": 4,
        "uid": 1,
        "t_c": "2020-07-26T11:14:00",
        "t_u": "2020-07-26T11:14:00",
        "tags": [
          "图片"
        ],
        "title": "请大家保持耐心",
        "content": "我（不是小二，是他的一个好朋友）正在很努力地恢复2049论坛的所有功能。由于没有原始数据库（如果你们知道哪里有，请去github合适地方反馈一下），并不能直接拿2049的代码来用，才决定自己写。",
        'imp':True,
    })

    aql('''
        let lt = (for t in threads sort t.tid desc limit 1 return t)[0]
        let lu = (for u in users sort u.uid desc limit 1 return u)[0]
        insert {_key:'counters', tid:lt.tid+100, uid:lu.uid+100, imp:True} into counters
    ''')

    aql('''
        insert {_key:"genesis", active:true, imp:true} into invitations
    ''')
