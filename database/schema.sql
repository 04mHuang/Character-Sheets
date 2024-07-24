CREATE DATABASE main_database;

USE main_database;

-- Users Table
CREATE TABLE Users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- People Table
CREATE TABLE People (
    person_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    birthday DATE,
    allergies TEXT,
    interests TEXT,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- Events Table
CREATE TABLE Events (
    event_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    person_id INT NOT NULL,
    event_name VARCHAR(100) NOT NULL,
    event_date DATE NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (person_id) REFERENCES People(person_id)
);

-- Groups Table
CREATE TABLE Groups (
    group_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    group_name VARCHAR(100) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- GroupMembers Table (Many-to-Many Relationship)
CREATE TABLE GroupMembers (
    group_id INT NOT NULL,
    person_id INT NOT NULL,
    PRIMARY KEY (group_id, person_id),
    FOREIGN KEY (group_id) REFERENCES Groups(group_id),
    FOREIGN KEY (person_id) REFERENCES People(person_id)
);
