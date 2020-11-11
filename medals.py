from commons import *

@stale_cache(ttr=3, ttl=300)
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
