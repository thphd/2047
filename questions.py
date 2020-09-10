from commons import *
from flask import g
import random

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

    nqa = aql('return length(for i in questions filter i.delete==null return i)', silent=True)[0]

    chosen_idx= rng.sample(range(nqa), nquestions)
    chosen_qs = []
    for i in chosen_idx:
        q = aql(f'''
            for i in questions
            sort i._key
            limit {i},1
            return i
        ''', silent=True)[0]
        chosen_qs.append(q)

    return chosen_qs

def make_exam(seed, nquestions):
    chosen = choose_questions(seed, nquestions)

    for q in chosen:
        random.shuffle(q['choices'])
    random.shuffle(chosen)

    return chosen

# add_questions(open('default_questions.txt','r',encoding='utf-8').read())

def insert_question(q):
    aql('''for i in @k insert i into questions''', k=[q])

if __name__ == '__main__':
    print(qs)
    print(make_exam('asdf', 3))
    #
    # for i in qs:
    #     insert_question(i)
