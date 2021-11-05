import requests as rq
import datetime
import time

URL_ID = 'https://hacker-news.firebaseio.com/v0/item/{}.json?print=pretty'
URL_MAXID = 'https://hacker-news.firebaseio.com/v0/maxitem.json?print=pretty'

def date2ts(year: int, month: int, day: int) -> int:
    """
    return timestamp corresponding to date given by (year, month, day)
    """
    date = datetime.date(year=year, month=month, day=day)
    timetpl = date.timetuple()
    return int(time.mktime(timetpl))

def id2ts(item_id: int) -> int:
    """
    get timestamp of hn item with specified id
    """
    res = rq.get(URL_ID.format(item_id))
    while not res.ok or not res.json().get('time'):
        item_id += 1
        res = rq.get(URL_ID.format(item_id))
    return res.json()['time']

def check(year: int, month: int, day: int, item_id: int) -> bool:
    """
    confirm that hn item with specified id was posted on date
    specified by (year, month, day)
    """
    ts = id2ts(item_id)
    d = datetime.datetime.fromtimestamp(ts)    
    print(f'first id on {year}/{month}/{day}: {item_id} ({d.year}/{d.month}/{d.day})')            

    return year == d.year and month == d.month and day == d.day      

def get_first_id_on_day(year: int, month: int, day: int) -> int:
    """
    returns first hn item id (story or comment) on specified date;
    date specified as as (year, month, day) tuple if ints (1-based indexing), 
    e.g. (2021, 1, 1) is 1st January 2021;
    impossible dates (e.g., 31st February 2021) or future date (e.g., 1st January 3021)
    will raise errors
    """
    # convert date to timestamp
    target_ts = date2ts(year, month, day)
    max_id = rq.get(URL_MAXID).json()
    max_ts = id2ts(max_id)

    if target_ts > max_ts:
        raise ValueError('Specified date is out of range')
    
    # use binary search to find first id higher than timestamp
    lo, hi = 1, max_id    
    while lo <= hi:
        mi = (lo + hi) // 2        
        ts = id2ts(mi)
        if target_ts > ts:
            lo = mi + 1
        else:
            hi = mi - 1

    #print(check(year, month, day, hi+1))          
    return hi + 1