from commons import *
tf = time_factor = 0.99999985


spans = []
for i in range(8):
    p = 2
    b = 1
    a = 4
    spans.append([a*p**i+b if i else 0, a*p**(i+1)+b])

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

def avg_integrate(low, high):
    return integrate(low, high) / (high-low)

exponential_falloff_spans = _efs = []

for low,high in spans:
    avgi = avg_integrate(low*86400, high*86400)
    if __name__=='__main__':
        print(low, high, avgi)

    _efs.append((
        -low*86400, # later
        -high*86400, # earlier
        avgi, # factor
    ))

def get_exponential_falloff_spans_for_now():
    res = []
    for later, earlier, factor in _efs:
        res.append([time_iso_now(earlier),time_iso_now(later),factor])
        # res.append([time_iso_now(earlier),time_iso_now(later),factor])
    return res

if __name__ == '__main__':
    print(get_exponential_falloff_spans_for_now())
