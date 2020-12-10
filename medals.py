from commons import *
from api import *

@stale_cache(ttr=3, ttl=1800)
def get_medals():
    medals = QueryString('''
    let doc = document('counters/medals')

    let pgpmedalists = (for i in users
    filter i.pgp_login==true
    return i.name)

    let medals = append(doc.medals, {name:'非对称奖章', brief:"成功使用PGP签名登录2047的用户", list:pgpmedalists})

    for medal in medals

     let listusers = (
         for name in medal.list
         let u = (for i in users filter i.name==name return i)[0]
        sort u.t_c asc
         return u
     )

    return merge(medal, {listusers})
    ''', silent=True)

    medals = aql(medals)

    return medals

@stale_cache(ttr=3, ttl=1800)
def get_user_medals(uid):
    medals = get_medals()
    u = get_user_by_id(uid)
    res = []
    for medal in medals:
        for name in medal['list']:
            if name==u['name']:
                res.append(medal['name'])

    return res
