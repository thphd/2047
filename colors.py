from termcolor import colored, cprint
import colorama

colorama.init()

import logger_config
import logging
logger = logging.getLogger('2047')

import threading

# _pq = []
# _pqc = threading.Condition()

def qprint(*a,**kw):
    to_print = ' '.join((str(i) for i in a))
    logger.info(to_print)

    # with _pqc:
    #     _pq.append((a, kw))
    #     _pqc.notify()

def async_printer():
    while 1:
        with _pqc:
            while len(_pq)==0:
                _pqc.wait()
            a,kw = _pq.pop(0)
            # print(*a, **kw)
            to_print = ' '.join((str(i) for i in a))
            logger.info(to_print)

# def dispatch(f):
#     t = threading.Thread(target=f, daemon=True)
#     t.start()

# dispatch(async_printer)

def restrict_gbk(text):
    # escape unsupported unicode in gbk
    # (to prevent emojis from crashing CMD
    return text.encode(encoding='gbk', errors='replace').decode(encoding='gbk')

def colored_print_generator(*a,**kw):
    def colored_print(*items,**incase):
        text = ' '.join((str(i) for i in items))
        text = restrict_gbk(text)

        qprint(colored(text, *a,**kw),**incase)
    return colored_print

def colored_format_generator(*a,**kw):
    def colored_format(s):
        text = restrict_gbk(s)

        return colored(text, *a,**kw)
    return colored_format

import pprint
def prettify(json):
    return pprint.pformat(json, indent=4, width=80, depth=None, compact=True)

cpg = colored_print_generator
cfg = colored_format_generator

print_info = cpg('green',)
print_debug = cpg('yellow')
print_up = cpg('yellow', attrs=['bold'])
print_down = cpg('cyan', attrs=['bold'])
print_err = cpg('red', attrs=['bold'])

colored_info = cfg('green',)
colored_debug = cfg('yellow')
colored_up = cfg('yellow', attrs=['bold'])
colored_down = cfg('cyan', attrs=['bold'])
colored_err = cfg('red', attrs=['bold'])

if __name__ == '__main__':
    cpg = colored_print_generator
    printredcyan = cpg('red', 'on_cyan')

    printredcyan('red', 'on_cyan')
    print(prettify({'asd':'gerf','a':{'v':'b'}}))
