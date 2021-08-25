from flask import *
from api import *
from app import app

from antispam import st

limits = []

for i in [0,25,50,75,100,150,200,250,300,400,500,600,800,1000,
    1200,1500,2000,3000,4000,6000,10000,20000]:
    # print(i, dlp_ts(i),dlt_ts(i))

    limits.append((i, dlp_ts(i), dlt_ts(i), False))

@app.route('/trust_score_explained')
def ts_explain():

    mylimits = limits.copy()

    if g.selfuid>0:
        myts = trust_score_format(g.current_user)
        lp = dlp_ts(myts)
        lt = dlt_ts(myts)

        j = []
        flag = 0
        for tup in mylimits:
            if myts<=tup[0] and flag==0:
                flag = 1
                j.append((myts, lp, lt, True))
            j.append(tup)

        if flag==0:
            flag = 1
            j.append((myts, lp, lt, True))

        mylimits = j

    return render_template_g('ts_expl.html.jinja',
        page_title = '社会信用分与发言限制对照',
        limits = mylimits,
    )

@lru_cache()
def get_spamwords():
    wl = len(st.spamgoods)
    words = [(k,logp) for idx,(k,logp) in enumerate(st.spamgoods.items())
        if idx**2.114514*8964 % 1 < ((abs(logp)-2)/7)**1.72323
    ]
    words.sort(key=lambda a:-a[1])
    return wl, words

@app.route('/anti_spam_explained')
def as_explain():
    wl, words = get_spamwords()
    return render_template_g('ts_expl.html.jinja',
        page_title = 'Spam Classifier Dictionary',
        # limits = mylimits,
        spam_words = words,
        spam_words_length = wl,
    )
