import requests as rq
import datetime
import time

URL_ID = 'https://hacker-news.firebaseio.com/v0/item/{}.json?print=pretty'
URL_MAXID = 'https://hacker-news.firebaseio.com/v0/maxitem.json?print=pretty'

def date2ts(year, month, day):
    date = datetime.date(year=year, month=month, day=day)
    timetpl = date.timetuple()
    return int(time.mktime(timetpl))

def get_first_id_on_day(year, month, day):
    def helper(item_id):
        res = rq.get(URL_ID.format(item_id))
        while not res.ok or not res.json().get('time'):
            res = rq.get(URL_ID.format(item_id + 1))
        return res.json()['time']
    
    target_ts = date2ts(year, month, day)
    maxid = rq.get(URL_MAXID).json()
    
    lo, hi = 1, maxid    
    while lo <= hi:
        mi = (lo + hi) // 2        
        ts = helper(mi)
        if ts > target_ts:
            hi = mi - 1
        else:
            lo = mi + 1
            
    return hi + 1