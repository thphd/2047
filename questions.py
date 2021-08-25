from commons import *
from api import *
from flask import g
import random
from app import app

def str2q(s):
    s = s.split('$')

    if len(s)!=6:
        raise Exception('not splitted into 6 parts')

    q = [t.strip() for t in s]
    question = q[0]
    choices = q[1:1+4].copy()
    category = q[5]

    qobj = dict(
        question=question,
        choices=choices,
        category=category,
        # uid=g.current_user['uid'],
        # t_c=tc,
    )
    return qobj

def q2str(q):
    return '\n$'.join([q['question']]+q['choices']+[q['category']])

def add_question(s):
    qobj = str2q(s)

    tc = time_iso_now()
    qobj['uid'] = g.logged_in['uid']
    qobj['t_c'] = tc

    aql('insert @k into questions', k=qobj)

def modify_question(qid, s):
    q = str2q(s)
    q['_key'] = qid
    q['t_u'] = time_iso_now()
    aql('update @k with @k in questions', k=q)

def find_question(qq):
    return aql('for i in questions filter i.question==@qq return i',qq=qq)

# def add_questions(s):
#     s = s.split('##')
#     for q in s:
#         add_question(q)

def choose_questions(seed, nquestions):
    rng = random.Random(seed)

    # num questions available
    nqa = aql('return length(for i in questions filter i.delete==null return i)', silent=True)[0]

    got_questions = []
    gqkeys = {}
    while len(got_questions)<nquestions:
        chosen_idx= rng.randint(0, nqa)
        q = aql(f'''
            for i in questions
            sort i._key
            limit {chosen_idx},1
            //let user = (for u in users filter u.uid==i.uid return u)[0]
            //return merge(i, {{user}})
            return i
        ''', silent=True)[0]

        if q['question'].startswith('!!'):
            continue

        if q['_key'] not in gqkeys:
            gqkeys[q['_key']] = 1
            got_questions.append(q)

    return got_questions

def make_exam(seed, nquestions):
    chosen = choose_questions(seed, nquestions)

    for q in chosen:
        random.shuffle(q['choices'])
    random.shuffle(chosen)

    return chosen

# add_questions(open('default_questions.txt','r',encoding='utf-8').read())

def insert_question(q):
    aql('''for i in @k insert i into questions''', k=[q])

aqlc.create_collection('exams')

min_pass_score = 3
num_questions = 5
time_to_submit = 20

@app.route('/exam')
def get_exam():
    ipstr = request.remote_addr
    timenow = time_iso_now()[:15] # every 10 min
    exam_questions = make_exam(ipstr+timenow, num_questions)
    exam = {}
    exam['questions'] = exam_questions
    exam['t_c'] = time_iso_now()
    inserted = aql('insert @k into exams return NEW',k=exam,silent=True)[0]

    return render_template_g(
        'exam.html.jinja',
        page_title='考试',
        exam=inserted,

    )

@app.route('/questions')
def list_questions():
    must_be_admin()

    qs = aql('''
    for i in questions sort i.t_c desc
    let user = (for u in users filter u.uid==i.uid return u)[0]
    return merge(i,{user})
    ''', silent=True)

    return render_template_g(
        'qs.html.jinja',
        page_title='题库',
        questions = qs,

    )

@app.route('/choice_stats')
def choice_stats():
    must_be_admin()

    cstat = get_choice_stats()

    return render_template_g(
        'choice_stats.html.jinja',
        page_title = '选项统计',
        cstat = cstat,
    )

@register('submit_exam')
def _():
    eid = es('examid')
    answers = g.j['answers']
    now = time_iso_now()

    exam = aql('for e in exams filter e._key==@eid return e', eid=eid)[0]
    if 'submitted' in exam and exam['submitted']:
        raise Exception('please do not re-submit to the same exam.')

    aql('update @k with {submitted:true} in exams', k=exam)

    if dfs(now) - dfs(exam['t_c']) > dttd(seconds=time_to_submit*60):
        raise Exception('time limit exceeded. please try again later')

    # from questions import qs, qsd

    total = len(answers)
    # assert total==5
    score = 0
    for idx, choice in enumerate(answers):
        if choice == -1:
            # -1 means no choice
            continue

        question = exam['questions'][idx]
        chosen = question['choices'][choice]

        found = find_question(question['question'])

        if not found:
            raise Exception('question not found in db')
        print(found)
        if chosen == found[0]['choices'][0]:
            # answer is correct
            score+=1

    print_err('score:', score)
    if score < min_pass_score:

        aql('insert @k into answersheets',k=dict(
            # invitaiton=code,
            examid=eid,
            answers=answers,
            t_c = now,
            passed = False,
            salt = get_current_salt(),
            score = score,
        ))
        raise Exception('your score is too low. please try again')

    # obtain an invitation code
    code = generate_invitation_code(None)

    aql('insert @k into answersheets',k=dict(
        invitaiton=code,
        examid=eid,
        answers=answers,
        t_c = now,
        passed = True,
        salt = get_current_salt(),
        score = score,
    ))

    return {'url':'/register?code='+code, 'code':code}

@register('add_question')
def _():
    must_be_admin()
    j = g.j
    qs = j['question']
    add_question(qs)
    return {'error':False}
@register('modify_question')
def _():
    must_be_admin()
    qv = g.j['question']
    qid = g.j['qid']
    modify_question(qid, qv)
    return {'error':False}

@stale_cache(ttr=10, ttl=3600)
def get_choice_stats():
    res = aql("""
for i in answersheets
sort i.t_c desc
filter i.examid!=null

let exam = (for e in exams filter e._key==i.examid return e)[0]

    for j in range(0, length(i.answers)-1)
    let ans = i.answers[j]
    let qid = exam.questions[j]._id

    or (for k in questions filter k.question==exam.questions[j].question
        return k._id)[0]

    filter qid

    let qchoice = exam.questions[j].choices[ans]

    // determine each choice is correct or not
    //let q = document(qid)
    //let correct = (qchoice == q.choices[0])?1:0

    //return {qchoice, correct, qid}

    collect aqid=qid aggregate tot=count(qid) into result_groups = qchoice
    let q = document(aqid)
    let cstat = (
        for qchoice in result_groups collect aqc=qchoice with count into n
        let fraction = n/tot
        sort fraction desc

        // determine each choice is correct or not
        let correct = (aqc == q.choices[0])?1:0
        return {choice:aqc, count:n, fraction, correct}
    )
    sort tot desc
    return {qid:aqid, question:q.question, uid:q.uid, choices:cstat, total:tot}
    """, silent=True)
    return res


if __name__ == '__main__':
    print(qs)
    print(make_exam('asdf', 3))
    #
    # for i in qs:
    #     insert_question(i)
