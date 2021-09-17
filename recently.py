from numba import jit

from commons import *

tf = time_factor = 0.99999985

spans = []
for i in range(11):
    p = 1.5
    b = -9
    a = 10
    spans.append([a*p**i+b if i else 0, a*p**(i+1)+b])

def avg_integrate(low, high):
    return integrate(low, high) / (high-low)

def integrate(low, high, fact=tf):
    '''
    integrate 0.9^x from 1 to 10
    '''
    def antid(x):
        return fact**x / math.log(fact)

    return antid(high) - antid(low)

if __name__ == '__main__':
    print(spans)
    print(integrate(1, 10, .9))

    for low,high in spans:
        avgi = avg_integrate(low*86400, high*86400)
        if __name__=='__main__':
            print(f'{low:.4f}, {high:.4f}, {avgi:.4f}')

exponential_falloff_spans = _efs = []

for low,high in spans:
    avgi = avg_integrate(low*86400, high*86400)

    _efs.append((
        -low*86400, # later
        -high*86400, # earlier
        avgi, # factor
    ))

def get_exponential_falloff_spans_for_now():
    return [
        [time_iso_now(earlier), time_iso_now(later), factor]
            for i, (later, earlier, factor) in enumerate(_efs)
    ]

if __name__ == '__main__':
    print(str(get_exponential_falloff_spans_for_now()).replace("'", '"'))

if __name__ == '__main__':
    timethis('$get_exponential_falloff_spans_for_now()')
