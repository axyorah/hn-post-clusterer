DROP TABLE IF EXISTS story;
DROP TABLE IF EXISTS comment;

CREATE TABLE story (
    story_id INTEGER PRIMARY KEY,
    deleted INTEGER,
    author VARCHAR,
    unix_time INTEGER,
    body VARCHAR,
    dead INTEGER,
    url VARCHAR,
    score INTEGER,
    title VARCHAR,
    descendants INTEGER
);

CREATE TABLE comment (
    comment_id INTEGER PRIMARY KEY,
    deleted INTEGER,
    author VARCHAR,
    unix_time INTEGER,
    body VARCHAR,
    dead INTEGER,
    story_id INTEGER,
    FOREIGN KEY (story_id) REFERENCES story (story_id)
);