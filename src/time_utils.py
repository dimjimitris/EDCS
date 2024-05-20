import time
import datetime as dt

def get_time():
    #t = dt.datetime.now(dt.UTC)
    #t = t.timestamp() * 1_000_000
    #return int(round(t))
    return time.time_ns()

def get_datetime():
    return dt.datetime.now(dt.UTC)