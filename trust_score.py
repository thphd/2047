from flask import *
from api import *
from app import app

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
