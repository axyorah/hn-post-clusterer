import os
import json
import bs4 as bs

def serialize_to_disc(corpus_dir, rows):
    os.makedirs(corpus_dir, exist_ok=True)
    
    for row in rows:
        # convert sql row obj to dct
        dct = dict()
        for key in row.keys():
            dct[key] = row.__getitem__(key)

        # parse children (story's comments are stored as an html doc)
        soup = bs.BeautifulSoup(dct['children'], 'lxml')
        dct['children'] = soup.text

        # write into a separate file
        jsoned = json.dumps(dct)
        with open(f'{corpus_dir}/{dct["story_id"]}.json', 'w') as f:
            f.write(jsoned)