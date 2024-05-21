import time
import datetime as dt


def get_time():
    """
    Description: Get the current time in nanoseconds
    """
    return time.time_ns()


def get_datetime():
    """
    Description: Get the current datetime in UTC
    """
    return dt.datetime.now(dt.UTC)
