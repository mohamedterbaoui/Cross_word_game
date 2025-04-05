import mysql.connector
from mysql.connector import Error

# Connect to MySQL database
db = mysql.connector.connect(
    host = "localhost",
    user = "mohamed",
    password = "mypassword",
    database = "cross_word"
)

cursor = db.cursor()

# Creating the database tables
# 1. Words table : id | language | word
cursor.execute("""
    CREATE TABLE IF NOT EXISTS words (
        id INT AUTO_INCREMENT PRIMARY KEY,
        lang VARCHAR(10),
        word VARCHAR(255) NOT NULL,
        UNIQUE(word, lang)
    )
""")

# TODO : change table language and source are linked with the definition 
# not the word also key is word + language, 
# since the same word in different languages is different.

# 2. Definitions table : id | word_id FK | source | definition
cursor.execute("""
    CREATE TABLE IF NOT EXISTS definitions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        word_id INT,
        source VARCHAR(255),
        definition TEXT NOT NULL,
        FOREIGN KEY(word_id) REFERENCES words(id) ON DELETE CASCADE 
    )
""")

# 3. Players table :
# id | username | password | games_played | games_won | score | last_login
cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        games_played INT DEFAULT 0,
        games_won INT DEFAULT 0,
        score INT DEFAULT 0,
        last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
""")

# Commit creation of the tables
db.commit()

# Reading and inserting definitions from the file "def.txt"
with open("def.txt", "r", encoding="utf-8") as file:
    for line in file:
        parts = line.split("\t")

        lang, source, word = parts[:3]
        definitions = parts[3:]

        # inserting the word into words table
        # checking if a the word already exists
        cursor.execute("SELECT id FROM words WHERE word = %s AND lang = %s", (word, lang))
        result = cursor.fetchone()

        if result :
            # Getting the id of the word for inserting into definitions table
            word_id = result[0]
        else:
            cursor.execute("INSERT INTO words (lang, word) VALUES (%s, %s)", 
                            (lang, word))
            db.commit()
            word_id = cursor.lastrowid # getting the new word_id

        # inserting each definition into definitions table
        for definition in definitions:
            try:
                cursor.execute("INSERT INTO definitions (word_id, source, definition) VALUES (%s,%s, %s)",
                            (word_id, source, definition.strip()))
            except Error as e: 
                print(f"Error : {e}")
                db.rollback()
        
# Commit all inserts
db.commit()

# Closing the connection
cursor.close()
db.close()