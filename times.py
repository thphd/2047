# everything time related

import datetime

dtdt = datetime.datetime
dtt = datetime.time
dtd = datetime.date
dtn = dtdt.now

# default time parsing
def dtdt_from_stamp(stamp):
    return dtdt.fromisoformat(stamp)

dfs = dtdt_from_stamp

# proper time formatting
# input: string iso timestamp
# output: string formatted time

def format_time(dtdt,s):
    return dtdt.strftime(s)

# default time formatting
def format_time_iso(dtdt):
    return dtdt.isoformat(timespec='seconds')[:19]
fti = format_time_iso

format_time_datetime = lambda s: format_time(dfs(s), '%Y-%m-%d %H:%M')
format_time_dateonly = lambda s: format_time(dfs(s), '%Y-%m-%d')
format_time_timeonly = lambda s: format_time(dfs(s), '%H:%M')

def format_time_dateifnottoday(s):
    dt = dfs(s)
    now = dtn()

    if now.date() > dt.date():
        return format_time_dateonly(s)
    else:
        return format_time_timeonly(s)

def time_iso_now():
    return format_time_iso(dtn())

if __name__ == '__main__':
    a = dtn()
    print(format_time_dateifnottoday(fti(a)))
    print(globals())
