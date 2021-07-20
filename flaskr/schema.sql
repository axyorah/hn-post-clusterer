-- DROP TABLE IF EXISTS story;
-- DROP TABLE IF EXISTS comment;
-- DROP TABLE IF EXISTS parent;

CREATE TABLE IF NOT EXISTS parent (
    parent_id INTEGER PRIMARY KEY NOT NULL,
    parent_type VARCHAR CHECK(parent_type IN ('story', 'comment')) NOT NULL
);

CREATE TABLE IF NOT EXISTS story (
    story_id INTEGER PRIMARY KEY,
    author VARCHAR,
    unix_time INTEGER,
    body VARCHAR,
    url VARCHAR,
    score INTEGER,
    title VARCHAR,
    descendants INTEGER
);

CREATE TABLE IF NOT EXISTS comment (
    comment_id INTEGER PRIMARY KEY,
    author VARCHAR,
    unix_time INTEGER,
    body VARCHAR,
    story_id INTEGER,
    FOREIGN KEY (parent_id) REFERENCES parent (parent_id)
);