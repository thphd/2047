from commons import *

@stale_cache(ttr=3, ttl=1800)
def get_medals():
    medals = QueryString('''
    let doc = document('counters/medals')

    for medal in doc.medals

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
    q = QueryString('''
        let doc = document('counters/medals')
        let username = (for i in users filter i.uid==@uid return i)[0].name

        for medal in doc.medals
        for name in medal.list
        filter name==username
        return medal.name
    ''', uid=uid, silent=True)
    return aql(q)
