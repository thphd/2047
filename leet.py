from commons import *
from api import *

from runcode import run_python_code
from leet_challenge import LeetChallenge, LeetChallenges

lcs = None

def delayed_init():
    global lcs
    lcs = LeetChallenges(os.path.dirname(os.path.abspath(__file__))+'/leet_challenges')

dispatch(delayed_init)

def get_everyone_submission_stat():
    stats = aql('''
    for i in challenge_submissions
    sort i.t_c desc
    collect lcn = i.lcn AGGREGATE uids = UNIQUE(i.uid)
    return {lcn, uids}
    ''')
    d = {k['lcn']:k['uids'] for k in stats}
    return d

def get_my_most_recent_sub_on(lcn):
    r = aql('for i in challenge_submissions \
    filter i.uid==@uid and i.lcn==@lcn sort i.t_c desc limit 1 return i',
    silent=True, lcn = lcn, uid = g.selfuid)
    return r[0] if r else None

def get_my_sub_on_every():
    r = aql('''
        for i in challenge_submissions
        filter i.uid==@uid
        collect g = i.lcn
        return g
    ''', silent=True, uid=g.selfuid)

    d = {i:True for i in r}
    return d

@app.route('/leet/<string:lcn>')
def leet_lcn(lcn):

    if lcn not in lcs.d:
        raise Exception('challenge not found')

    lc = lcs.d[lcn]
    lc.update()

    r = get_my_most_recent_sub_on(lcn)

    nlinesofcode = len(lc.user_code_reference.split('\n'))

    return render_template_g('leet_challenge.html.jinja',
        page_title=f'Challenge {lcn}',
        page_title_title=f'Challenge {lcn} {lc.name}',
        lcs = lcs,
        lcn = lcn,
        lc = lc,
        most_recent = r,
        loc = nlinesofcode,
    )


@app.route('/leet')
def leet():

    my_subs = get_my_sub_on_every()
    other_subs = get_everyone_submission_stat()

    return render_template_g('leet.html.jinja',
        page_title=f'Coding Challenges',
        lcs = lcs,
        my_subs = my_subs,
        other_subs = other_subs,
    )

aqlc.create_collection('challenge_submissions')

@register('runcode')
def _():
    must_be_logged_in()
    input_text = es('input')
    code = es('code')

    if len(code)>1000:
        raise Exception('代码太长')
    if len(input_text)>100:
        raise Exception('输入太长')

    tlr = key(g.current_user, 't_last_runcode')
    if tlr and tlr>time_iso_now(-10):
        raise Exception('两次运行代码间隔应大于10秒')

    else:
        aql('for i in users filter i.uid==@uid update i with {t_last_runcode:@t} in users', uid=g.selfuid, t=time_iso_now(), silent=True)

    lcn = es('challenge_name')
    is_submission = eb('is_submission')

    print(input_text)

    if lcn not in lcs.d:
        raise Exception('challenge not found')

    lc = lcs.d[lcn]
    lc.update()

    def pack(a,b):
        return {'error':a, 'result':b}

    try:
        if not is_submission:
            result_text = lc.eval_test(code, input_text)
        else:
            result_text = lc.eval_submit(code)
    except Exception as e:
        return pack(True, flask.escape(str(e)))
    else:
        if is_submission:
            aql('''
            insert @k in challenge_submissions
            ''', k=dict(
                uid = g.selfuid,
                t_c = time_iso_now(),
                lcn = lcn,
                code = code,
            ))

        return pack(False, flask.escape(str(result_text)))
