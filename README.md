# HN Post Clusterer

Simple one-page app that attempts to bring some extra order to [HN](https://news.ycombinator.com/) posts by clustering similar posts together:

- fetches post and comment metadata from HN and stores it locally to SQLite db;
- clusters posts filtered by date, number of comments and score into given number of clusters;
- prints some basic statistics about clustering results; 
as well as visualizes all posts as points in 2D space
- prints titles/urls for all posts from a selected cluster

## What's under the hood
### Clustering
In short: to find similar posts we perform the k-means clustering on each post comments converted to number arrays with the help of transformers.

The exact procedure is as follows: 
- for each post collect all relevant *comments*,
- convert these comments to *number arrays* that Machine Learning algorithms can work with.
  > These number array are called *embeddings*, and we'll obtain them by passing each comment sentence-by-sentence to [DistilRoBERTa](https://huggingface.co/sentence-transformers/all-distilroberta-v1) transformer and averaging the results for each post. The transformer that we'll use was pretrained on such datasets as [Reddit Comments](https://github.com/PolyAI-LDN/conversational-datasets/tree/master/reddit), [WikiAnswers](https://github.com/afader/oqa#wikianswers-corpus) and [Yahoo Answers](https://www.kaggle.com/soumikrakshit/yahoo-answers-dataset), so we can exoect it to perform reasonably well on our data, too.

- reduce the *dimensionality* of embedding.
  > This is needed because clustering algorithm that we use doesn't work too well in high-dimensional setting. Each embedding generated by DistilRoBERTa is a 768-dimensional vector, and this is definitely not optimal for clustering. So we use a simple linear technique [PCA](https://en.wikipedia.org/wiki/Principal_component_analysis) to find 100 orthogonal vectors in 768-dimensional space along which our data varies the most and project our original data onto this 100-dimensional space.

- cluster these reduced post embeddings with the help of k-Means clustering.

### Stack
This is essentially a [Flask](https://flask.palletsprojects.com/en/2.0.x/) app, so all the server side is written in python, 
while all the client side uses JavaScript. Metadata on HN posts and comments is stored locally in SQLite database. All figures are rendered with the help of [plotly/dash](https://plotly.com/dash/). General page layout is prettified with the help of [Boostrap](https://getbootstrap.com/).

## Setup
You need to have [python3.7](https://www.python.org/downloads/) or higher. Additionally, 
sentence transformer used in this project to generate comment embeddings is quite demanding on memory, so you'd need to have at least 8GB RAM.

To set this project up locally open your terminal/command prompt and run the following commands:
- clone this repo:
```bash
$ git clone https://github.com/axyorah/hn-post-clusterer.git
```

- create fresh python virtual environment for this project by; to do that go to the project root and run:
  - if you're on Linux or Mac:
  ```bash
  $ python3 -m venv venv
  ```
  - if you're on Windows:
  ```bash
  py -3 -m venv venv
  ```

- activate the environment:
  - If you're on Linux or Mac run:
  ```bash
  $ source venv/bin/activate
  ````
  - if you're on Windows run:
  ```bash
  venv\Scripts\activate.bat
  ```

- install all the python dependencies listed in `requirements.txt` by using "local" pip:
```bash
$ venv/bin/pip3 install -r requirements.txt
```

- start flask app:
  - on Linux or Mac:
  ```bash
  export FLASK_APP=flaskr
  export FLASK_ENV=development
  flask init-db
  flask run
  ```
  - on Windows:
  ```bash
  set FLASK_APP=flaskr
  set FLASK_ENV=development
  flask init-db
  flask run
  ```

- in your browser go to `localhost:5000` and follow the instructions. Do note that to begin with clustering you'd first need to populate your local database with at least 100 posts with 5+ comments. It might take a while to fetch them over internet. Luckily, you'd only need to do it once.