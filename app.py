from flask import Flask
from flask import jsonify
import mysql.connector

app = Flask(__name__)

# Function to get a new connection to the database
def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="mohamed",
        password="mypassword",
        database="cross_word"
    )
    return connection

# Home Route
@app.route("/")
def home():
    return "Hello, Flask!"



# C : Consultation des definitions
@app.route("/word", defaults={"nb":10, "from_index":1})
@app.route("/word/<int:nb>", defaults={"from_index":1})
@app.route("/word/<int:nb>/<int:from_index>")
def get_words_collection(nb, from_index):
    db = get_db_connection()
    cursor = db.cursor()

    offset = from_index - 1
    cursor.execute("SELECT * FROM words LIMIT %s OFFSET %s", (nb, offset))
    result = cursor.fetchall()

    arrayOfObjects = []

    for res in result:
        cursor.execute("SELECT definition FROM definitions WHERE word_id = %s", (res[0],))
        definitions = cursor.fetchall()

        definition_list = [definition[0] for definition in definitions]

        word = {
            "Id": res[0],
            "Word": res[3],
            "definitions": definition_list
        }
        
        arrayOfObjects.append(word)

    cursor.close()
    db.close()
    return jsonify(arrayOfObjects)

# D : 

if __name__ == "__main__":
    app.run(debug=True)
