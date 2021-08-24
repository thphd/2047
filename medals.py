from commons import *
from api import *

@stale_cache(ttr=15, ttl=1800)
def get_medals():
    medals = QueryString('''
    let doc = document('counters/medals')
    let doc_medals = doc.medals

    let pgpmedalists = (for i in users
    filter i.pgp_login==true
    sort i.t_c asc
    return i)

    let high_ts = (for i in users filter i.trust_score>(1600/1000000)
    sort i.trust_score desc
    return i)

    let custom_medals_merged = [
        {name:'非对称奖章', brief:"成功使用PGP签名登录2047的用户", listusers:pgpmedalists},
        {name:'SAT满分', brief:"信用分大于1600的用户", listusers:high_ts},
    ]

    let doc_medals_merged = (
        for medal in doc_medals
        let listusers = (
            for name in medal.list
            let u = (for i in users filter i.name==name return i)[0]
            sort u.t_c asc
            return u
        )
        return merge(medal, {listusers})
    )
    let combined_medals = append(doc_medals_merged, custom_medals_merged)

    for medal in combined_medals
        return medal

    ''', silent=True)

    medals = aql(medals)

    for medald in medals:
        medald['uids'] = []
        for user in medald['listusers']:
            medald['uids'].append(user['uid'])

    return medals

@stale_cache(ttr=3, ttl=1800)
def get_user_medals(uid):
    medals = get_medals()
    u = get_user_by_id(uid)
    res = []

    uname = key(u, 'name')
    for medal in medals:
        if key(medal, 'list'):
            for name in medal['list']:
                if name==uname:
                    res.append(medal['name'])
        elif key(medal, 'listusers'):
            for name in medal['listusers'].map(lambda k:k['name']):
                if name==uname:
                    res.append(medal['name'])

    return res
