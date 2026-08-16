CREATE TABLE IF NOT EXISTS books (
    book_id INTEGER PRIMARY KEY,
    title TEXT,
    author TEXT,
    author_birth_year INTEGER,
    author_death_year INTEGER,
    language TEXT,
    subjects TEXT,
    download_count INTEGER,
    my_rating INTEGER,
    date_added TEXT,
    reviewer TEXT,
    recommend INTEGER
);