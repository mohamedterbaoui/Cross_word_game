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
# 1. Words table : id | language | source | word
cursor.execute("""
    CREATE TABLE IF NOT EXISTS words (
        id INT AUTO_INCREMENT PRIMARY KEY,
        lang VARCHAR(10),
        source VARCHAR(255),
        word VARCHAR(255) NOT NULL UNIQUE
    )
""")

# 2. Definitions table : id | word_id FK | definition
cursor.execute("""
    CREATE TABLE IF NOT EXISTS definitions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        word_id INT,
        definition TEXT NOT NULL,
        FOREIGN KEY(word_id) REFERENCES words(id) ON DELETE CASCADE 
    )
""")

# 3. Players table : 
# id | tagname | password | score | games_played | last_login
cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INT AUTO_INCREMENT PRIMARY KEY,
        tagname VARCHAR(255) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        score INT DEFAULT 0,
        games_played INT DEFAULT 0,
        last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
""")

# Commit creation of the tables
db.commit()

# Reading and inserting definitions from the file "def.txt"
with open("def.txt", "r", encoding="utf-8") as file:
    for line in file:
        parts = line.split("\t")
        print(parts)

        lang, source, word = parts[:3]
        definitions = parts[3:]

        # inserting the word into words table
        # checking if a the word already exists
        cursor.execute("SELECT id FROM words WHERE word = %s", (word, ))
        result = cursor.fetchone()

        if result :
            # Getting the id of the word for inserting into definitions table
            word_id = result[0]
        else:
            cursor.execute("INSERT INTO words (lang, source, word) VALUES (%s, %s, %s)", 
                            (lang, source, word))
            db.commit()
            word_id = cursor.lastrowid # getting the new word_id

        # inserting each definition into definitions table
        for definition in definitions:
            try:
                cursor.execute("INSERT INTO definitions (word_id, definition) VALUES (%s, %s)",
                            (word_id, definition.strip()))
            except Error as e: 
                print(f"Error : {e}")
                db.rollback()
        
# Commit all inserts
db.commit()

# Closing the connection
cursor.close()
db.close()