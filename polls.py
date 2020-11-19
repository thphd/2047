import monkeypatch
from commons import *

test_post = '''
each poll in the form of:

<poll>

question1
##writein, maxchoices=3
$choice1
$choice2
$choice3
$choice4

</poll>
'''

test_text = '''
question1
##writein, maxchoices=3
$choice1
$choice2
$choice3
$choice4
'''

strip = lambda s:s.strip()

def str2p(s):
    parts = s.split('$').map(strip)
    q = parts[0].split('##').map(strip)
    choices = parts[1:]

    if len(choices)<2:
        raise Exception('you need at least 2 choices')

    opts = {}

    writein = False
    maxchoices = 1
    # _key = None

    if len(q)>1:
        opts = q[1]
        opts = opts.split(',')
        opts = [k.split('=').map(strip) for k in opts]
        opts = {k[0]:(k[1] if len(k)>1 else True) for k in opts}

        writein = key(opts,'writein') or writein
        maxchoices = int(key(opts,'maxchoices') or maxchoices)
        # _key = key(opts, '_key') or _key

    maxchoices = max(1, maxchoices)

    q = q[0]

    return dict(
        question=q,
        writein=writein,
        maxchoices=maxchoices,
        choices=choices,
    )

def p2str(poll):
    s = f'''{poll['question']}\n##writein={'true' if poll['writein'] else ""}, maxchoices={poll['maxchoices']}\n'''

    s+= '\n'.join(['$'+i for i in poll['choices']])
    return s

aqlc.create_collection('polls')
aqlc.create_collection('poll_votes')

from flask import g

# create or update a poll
def create_or_update_poll(poll):
    if '_key' not in poll:
        # create new
        poll['t_c'] = time_iso_now()
        poll['t_u'] = poll['t_c']
        poll['uid'] = g.selfuid
        newpoll = aql('''
            insert @p in polls return NEW
        ''', p=poll)[0]
    else:
        poll['t_u'] = time_iso_now()
        newpoll = aql('''
            update @p in polls return NEW
        ''', p=poll)[0]
    return newpoll

# def render_poll(s):
#     poll = parse_poll(s)

def add_poll(s):
    poll = str2p(s)
    create_or_update_poll(poll)

def modify_poll(qid, s):
    poll = str2p(s)
    poll['_key'] = qid
    create_or_update_poll(poll)

def add_poll_vote(id, choice, delete=False):
    uid = g.selfuid

    poll = aql('for i in polls filter i._key==@k return i',k=id)
    if not poll:
        raise Exception(f'poll {id} does not exist')
    poll = poll[0]

    mc = poll['maxchoices']

    votes = aql('''
    for i in poll_votes
    filter i.uid==@uid and i.pollid==@k
    return i
    ''', uid=uid, k=id)

    if delete:
        for v in votes:
            if v['choice']==choice: # found
                aql('remove @v in poll_votes', v=v)
                return
        raise Exception('cant delete votes you havent cast')

    else:
        if choice in [v['choice'] for v in votes]:
            raise Exception(f'option {choice} chosen already')

        if mc>1: # multiple
            if len(votes) >= mc:
                raise Exception(f'you can make at most {mc} choices')

        else: # single
            if len(votes):
                vote = votes[0]
                aql('''
                remove @v in poll_votes
                ''', v=vote)

        aql('insert @v into poll_votes', v=dict(
            t_c=time_iso_now(),
            uid=uid,
            choice=choice,
            pollid=poll['_key'],
        ))

get_poll_q = QueryString('''
let votes = (
for j in poll_votes
filter j.pollid==poll._key
collect choice = j.choice with count into k
return {choice, nvotes:k}
)

let nvoters = length(
for j in poll_votes
filter j.pollid==poll._key
collect uid = j.uid with count into k
return k
)

let selfvotes = (
for j in poll_votes
filter j.pollid==poll._key and j.uid==@uid
return j
)

return merge(poll, {votes, nvoters, selfvotes})
''')

def poll_postprocess(poll):
    choices = poll['choices'] # available choices
    votes = poll['votes'] # available votes
    nvoters = poll['nvoters']
    selfvotes = poll['selfvotes']

    d = {}

    for c in choices:
        if c not in d:
            d[c] = {'text': c}

    for v in votes:
        vc = v['choice']
        if vc not in d:
            d[vc] = {'text': vc, 'nvotes':v['nvotes']}
        else:
            d[vc]['nvotes'] = v['nvotes']

    for v in selfvotes:
        vc = v['choice']
        if vc in d:
            d[vc]['self_voted'] = True

    poll['choices_postprocessed'] = [d[k] for k in d]

def get_poll(id, selfuid):
    q = QueryString('''
    let poll = (for i in polls filter i._key==@k return i)[0]
    ''', k=id) + get_poll_q + QueryString(uid=g.selfuid)
    
    ans = aql(q, silent=True)
    poll_postprocess(ans[0])
    return ans[0]

# from flask import render_template
# def render_poll(poll):
#     return render_template('poll_one.html.jinja', poll=poll)

if __name__ == '__main__':
    poll = str2p(test_text)
    print(poll)

    poll = p2str(poll)
    print(poll)

    poll = str2p(poll)
    print(poll)

    # render_poll(get_poll('38311091', -1))
