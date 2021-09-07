def content_length_check(content, allow_short=False):
    maxlen = 40000
    if len(content)>maxlen:
        raise Exception('content too long {}/{}'.format(len(content), maxlen))
    if (len(content)<2 and allow_short==False) or len(content)==0:
        raise Exception('content too short')

def title_length_check(title):
    if len(title)>140:
        raise Exception('title too long')
    if len(title)<2:
        raise Exception('title too short')
