from termcolor import colored, cprint
import colorama

colorama.init()

def colored_print_generator(*a,**kw):
    def colored_print(*items,**incase):
        text = ' '.join(map(lambda i:str(i), items))

        # escape unsupported unicode in current encoding
        # (to prevent emojis from crashing CMD
        text = text.encode(encoding='gbk', errors='replace').decode(encoding='gbk')

        print(colored(text, *a,**kw),**incase)
    return colored_print

import pprint
def prettify(json):
    return pprint.pformat(json, indent=4, width=80, depth=None, compact=True)

cpg = colored_print_generator

print_info = cpg('green',)
print_debug = cpg('yellow')
print_up = cpg('yellow', attrs=['bold'])
print_down = cpg('cyan', attrs=['bold'])
print_err = cpg('red', attrs=['bold'])

if __name__ == '__main__':
    cpg = colored_print_generator
    printredcyan = cpg('red', 'on_cyan')

    printredcyan('red', 'on_cyan')
    print(prettify({'asd':'gerf','a':{'v':'b'}}))
