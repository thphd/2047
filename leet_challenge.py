import monkeypatch
import sys, os, inspect
from commons_static import *
from runcode import run_python_code
import re

challenge_props =cprops= '''
    name:
    description:
    user_code: code given to user
    user_code_reference: official answer
    test_cases: test cases string given to user
    test_cases_submit: used in submission
    comment:
'''.split('\n').filter(lambda l:len(l)>5) \
    .map(lambda l:l.split(':')).filter(lambda l:len(l)==2) \
    .map(lambda l:l[0].strip())

print(cprops)
props_exp = r'^(names):.*?$'.replace('names', cprops.join('|'))

def parse_leet_challenge(fn):
    cont = readfile(fn, 'r')
    lc = {}
    c = re.split(props_exp, cont, flags=re.M)
    for idx, s in enumerate(c):
        if s in cprops:
            section = c[idx+1].strip()
            res = re.match(r'```.*?\n((?:.|\n)*?)```', section)
            if res:
                # print(res[1])
                section = res[1].strip()
            lc[s] = section
    return lc

class Printer:
    def __init__(self):
        self.text = ''
    def __call__(self, *args):
        self.text += list(args).map(str).join(' ')+'\n'


def b2s(b):return b.decode('utf-8', errors='ignore')
def s2b(s):return s.encode('utf-8', errors='ignore')

assert s2b('hello') == b'hello'
assert b2s(b'hello') == 'hello'

class LeetChallenge:
    def __init__(self, fn):
        self.fn = fn
        if fn:
            self.update()

        # self.force_online = not get_environ('DEBUG')
        self.force_online = True

    def update(self):
        fn = self.fn
        d = parse_leet_challenge(fn)
        for k in d:
            self.__setattr__(k, d[k])

        if 'user_code' not in d:
            self.user_code = re.sub(
                r"^(\s*?)(\w.*?\s*?#\s*?yourcodehere.*?)$",
                r"\1# your code here",
                self.user_code_reference,
                flags = re.M,
            )
        if not hasattr(self, 'test_cases'):
            self.test_cases = ''
        if not hasattr(self, 'test_cases_submit'):
            self.test_cases_submit = ''


    def eval_test(self, user_code, test_input):
        test_input = s2b(test_input)

        if test_input:

            # reference
            rout, rerr = run_python_code(self.user_code_reference, test_input, online=False)
            if rerr: raise Exception(b2s(rout+rerr))

            # user
            uout, uerr = run_python_code(user_code, test_input, online=self.force_online)
            if uerr: raise Exception(b2s(uout+uerr))

            return f'期待输出:\n{b2s(rout)}{"-"*10}\n实际输出:\n{b2s(uout)}'

        else:

            # user
            uout, uerr = run_python_code(user_code, test_input, online=self.force_online)
            if uerr: raise Exception(b2s(uout+uerr))

            return b2s(uout)


    def eval_submit(self, user_code):
        test_input = self.test_cases_submit
        test_input = s2b(test_input)

        # reference
        rout, rerr = run_python_code(self.user_code_reference, test_input, online=False)
        if rerr: raise Exception(b2s(rout+rerr))

        # user
        uout, uerr = run_python_code(user_code, test_input, online=self.force_online)
        if uerr: raise Exception(b2s(uout+uerr))

        if uout==rout:
            return '提交通过'
        else:
            raise Exception(f'程序成功运行，但输出与预期不符')

    #--------

    # def eval_somecode(self, user_code, stdin='', online=False):
    #     totalcode = self.before_code +'\n'+user_code+'\n'+self.after_code
    #     err, result = run_python_code(totalcode, stdin_text=stdin, use_tio=online)
    #     return err, result
    #
    # def eval_submission(self, user_code):
    #     ref_err, ref_res = self.eval_somecode(
    #         self.user_code_reference, online=False)
    #     if ref_err:
    #         print('Error running user_code_reference')
    #         raise Exception(ref_err)
    #
    #     inq_err, inq_res = self.eval_somecode(user_code,
    #         online=self.force_online)
    #     return ref_err, ref_res, inq_err, inq_res
    #
    # def eval_test(self, user_code):
    #     inq_err, inq_res = self.eval_somecode(user_code,
    #         online=self.force_online)
    #     return inq_err, inq_res

    #---------

    @lru_cache()
    def get_preprocessor(self):
        return self.exec_code(self.test_case_preprocessor, 'eat')

    @lru_cache()
    def exec_code(self, code, want):
        globals = {}
        locals = {}
        exec(code, globals, locals)
        if want not in locals:
            raise Exception(f'所提交的代码中找不到 {want}')
        return locals[want]

    @lru_cache()
    def test_cases_from_string(self, s):
        cases = []
        eat = self.get_preprocessor()
        for i in s.split('\n'):
            try:
                res = eat(i)
            except Exception as e:
                print(e)
                raise Exception(f'输入格式不合法: "{i}"')
            else:
                if res:
                    cases.append(res)
        return cases

    def eval_solution_against_cases(self, solution_code, cases):
        Solution = self.exec_code(solution_code,'Solution')
        if not inspect.isclass(Solution):
            raise Exception('Solution is not a class')

        meths = inspect.getmembers(Solution, predicate=inspect.isfunction)
        if not meths:
            raise Exception('Solution has no methods')
        target_function = meths[0]

        outputs = []
        for idx, case in enumerate(cases):
            try:
                res = target_function[1](Solution, *case)
            except Exception as e:
                raise Exception(
                    str(e)+f'\ntest case {idx+1}/{len(case)}({case})got an error')
            else:
                # print(case, res)
                outputs.append(res)
        return outputs

    def take_user_test(self, code, cases_string):
        cases = self.test_cases_from_string(cases_string)
        user_code_outputs = self.eval_solution_against_cases(code, cases)
        ref_outputs = self.eval_solution_against_cases(
            self.user_code_reference, cases)

        print = Printer()

        for idx, case, uo, ro in zip(range(len(cases)), cases, user_code_outputs, ref_outputs):
            case_str = list(case).map(str).join(",")

            print(f'测试用例 ({idx+1}/{len(cases)}) 输入: {case_str}')
            sign = '√' if ro==uo else '×'
            print(f'期望: {ro} 输出: {uo} {sign}')

        return print.text

    def take_user_submission(self, code):
        cases = self.test_cases_from_string(self.test_cases_submit)
        user_code_outputs = self.eval_solution_against_cases(code, cases)
        ref_outputs = self.eval_solution_against_cases(
            self.user_code_reference, cases)

        print = Printer()

        for idx, case, uo, ro in zip(range(len(cases)), cases, user_code_outputs, ref_outputs):
            case_str = list(case).map(str).join(",")

            if ro!=uo:
                print(f'测试用例 ({idx+1}/{len(cases)}) 未通过\n输入 {case_str} 期望: {ro} 输出: {uo}')
                return True, print.text

        print(f'测试用例({len(cases)}/{len(cases)}) 全部通过.')
        return False, print.text

        # run_python_code()

    # def take_user_test_online(self, code, cases_string):
    #     import base64,pickle
    #
    #     def f():
    #         import base64,pickle
    #         packed = input()
    #         packed = base64.decode(packed)
    #         packed = pickle.loads()
    #
    #     packed = base64.encode(pickle.dumps([f, self, code, cases_string]))

if __name__ == '__main__':
    lc = LeetChallenge(False)
    lc.user_code_reference = '''
class Solution:
    def square(self,a):
        return a*a
    '''
    lc.test_cases = '''
1
2
3
    '''
    lc.test_cases_submit = '''
998
999
1000
    '''
    lc.test_case_preprocessor = '''
def eat(s): # function should return tuples used as function params
    s = s.strip()
    if s: return (int(s),)
    return False

    '''
    # lc.
    # print(lc.test_cases_from_string(lc.test_cases))
    # lc.reference_eval(lc.test_cases_from_string(lc.test_cases))

    print(lc.take_user_test(lc.user_code_reference, lc.test_cases))
    print(lc.take_user_submission(lc.user_code_reference))

    print(lc.take_user_test(lc.user_code_reference.replace('*','+'), lc.test_cases))
    print(lc.take_user_submission(lc.user_code_reference.replace('*','+')))

class LeetChallenges:
    def __init__(self, dirname):
        fns = os.listdir(dirname).filter(lambda l:l.endswith('.md'))
        fullfns = fns.map(lambda l:os.path.abspath(dirname+'/'+l))

        self.l = []
        self.d = {}

        # print(fns, fullfns)
        for fn, fullfn in zip(fns, fullfns):
            print(fn, fullfn)
            
            lc = LeetChallenge(fullfn)

            forefn = fn.split('_')[0]

            self.l.append(forefn)
            self.d[forefn] = lc

        self.l.sort()

# lcs = LeetChallenges(os.path.dirname(__file__)+'./leet_challenges')

# if __name__ == '__main__':
#     print(lcs.l)
