CREATE DATABASE main_database;

USE main_database;

/* make a table to hold the users of the application */
CREATE TABLE Users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

/* make a table to hold the people the user wants to keep track of */
CREATE TABLE People (
    name VARCHAR(100) NOT NULL,
    birthday DATE,
    allergies TEXT,
    interests TEXT,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);
