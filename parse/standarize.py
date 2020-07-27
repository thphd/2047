# such that the names of variables could live in harmony...

from parse import *

aqlc.create_collection('threads')
aqlcl('threads')
aqlc.create_collection('posts')
aqlcl('posts')

aqlc.create_collection('categories')
aqlcl('categories')

aqlc.create_collection('users')
aqlcl('users')

aqlc.create_collection('avatars')
aqlcl('avatars')

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
} into posts
''')

aql('''
for i in catlets
insert {
    cid:i.cid,
    name:i.name,
    brief:i.brief,
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
} into users
''')

aql('''
for i in userlets
insert {
uid:i.userID,
data:i.avatar,
} into avatars
''')

# create users whose posts got hidden(not included in backup).
aql('''
for p in posts

let u = (for u in users filter u.uid==p.uid return u)[0]

filter u==null

collect uid = p.uid

insert {name:'(Removed)', uid:uid} into users
''')
