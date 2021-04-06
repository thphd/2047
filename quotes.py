from app import app
from commons import *

import random

@app.route('/quotes')
def show_quotes():
    return render_template_g('quotes.html.jinja',
        page_title="语录",
    )

@stale_cache(ttr=10, ttl=900)
def get_quotes():
    quotes = aql('''
for i in entities

filter i.type=='famous_quotes' or i.type=='famous_quotes_v2'
sort i.t_c desc

let user = (for u in users filter u.uid==i.uid return u)[0]
return merge(i, {user})

//for j in i.doc
//return {quote:j[0], quoting:j[1], user, t_u:(i.t_u or i.t_c)}

    ''', silent=True)

    q = []
    for i in quotes:
        if i['type']=='famous_quotes':
            if isinstance(i['doc'], list):
                for j in i['doc']:
                    if len(j)>=2:
                        q.append(dict(
                            quote=j[0],
                            quoting=j[1],
                            user=i['user'],
                            t_u= i['t_e'] if 't_e' in i else i['t_c']
                        ))

        elif i['type']=='famous_quotes_v2':
            if 'quoting' in i['doc'] and 'quotes' in i['doc']:
                if isinstance(i['doc']['quotes'], list):
                    for j in i['doc']['quotes']:
                        q.append(dict(
                            quote=j,
                            quoting=i['doc']['quoting'],
                            user=i['user'],
                            t_u= i['t_e'] if 't_e' in i else i['t_c']
                        ))

    return q

def get_quote():
    quotes = get_quotes()
    return random.choice(quotes)
