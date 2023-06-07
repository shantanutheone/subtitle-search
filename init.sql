CREATE TABLE subtitles (
    movie_id INT NOT NULL,
    movie_name VARCHAR(255) NOT NULL,
    line_id INT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (movie_id, line_id)
);
