# last id: 27750841

import requests as rq
import datetime as dt
import json

def main():
    fname = "flaskr/static/utils/id2ts.txt"
    with open(fname, "w") as f:    
        f.write("id\ttimestamp\n")

    ok, hn_id, delta_id = True, 1, 5000
    while ok and delta_id > 0:
        url = f"https://hacker-news.firebaseio.com/v0/item/{hn_id}.json?print=pretty"
        res = rq.get(url)
        dct = json.loads(res.text)
        ok = dct is not None
        if ok:
            hn_id += delta_id
            if dct.get("id") is not None and dct.get("time") is not None:                    
                print(dct["id"], dt.datetime.fromtimestamp(int(dct["time"])))
                with open(fname, "a") as f:
                    f.write(f"{dct['id']}\t{dct['time']}\n")
        else:
            delta_id //= 2
            hn_id -= delta_id

if __name__ == "__main__":
    main()