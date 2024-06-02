import time
import datetime as dt


def get_time():
    """
    Description: Get the current time in nanoseconds
    """
    res = time.time_ns()
    # java long is 64 bits, so we truncate the result to 64 bits
    return res & 0xFFFFFFFFFFFFFFFF


def get_datetime():
    """
    Description: Get the current datetime in UTC
    """
    return dt.datetime.now(dt.UTC)
