import requests as rq
import datetime
import time

URL_ID = 'https://hacker-news.firebaseio.com/v0/item/{}.json?print=pretty'
URL_MAXID = 'https://hacker-news.firebaseio.com/v0/maxitem.json?print=pretty'

def check(year, month, day, item_id):
    def helper(item_id):
        res = rq.get(URL_ID.format(item_id))
        while not res.ok or not res.json().get('time'):
            res = rq.get(URL_ID.format(item_id + 1))
        return res.json()['time']

    ts = helper(item_id)
    d = datetime.datetime.fromtimestamp(ts)    
    print(f'first id on {year}/{month}/{day}: {item_id} ({d.year}/{d.month}/{d.day})')            

    return year == d.year and month == d.month and day == d.day
      

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
    max_id = rq.get(URL_MAXID).json()
    max_ts = helper(max_id)

    if target_ts > max_ts:
        raise ValueError('Specified date is out of range')
    
    lo, hi = 1, max_id    
    while lo <= hi:
        mi = (lo + hi) // 2        
        ts = helper(mi)
        if target_ts > ts:
            lo = mi + 1
        else:
            hi = mi - 1

    #print(check(year, month, day, hi+1))          
    return hi + 1