from flask import Flask
from flask import jsonify
import mysql.connector

app = Flask(__name__)

# Connecting to the database
db = mysql.connector.connect(
    host = "localhost",
    user = "mohamed",
    password = "mypassword",
    database = "cross_word"
)

cursor = db.cursor()

# Home Route
@app.route("/")
def home():
    return "Hello, Flask!"



# C : Consultation des definitions
@app.route("/word", defaults={"nb":10, "from_index":1})
@app.route("/word/<int:nb>", defaults={"from_index":1})
@app.route("/word/<int:nb>/<int:from_index>")
def get_words_collection(nb, from_index):
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
            "Language": res[1],
            "Source": res[2],
            "Word": res[3],
            "definitions": definition_list
        }
        
        arrayOfObjects.append(word)

    return jsonify(arrayOfObjects)

# Closing the connection when the app is shut down
@app.teardown_appcontext
def close_connection(exception):
    cursor.close()
    db.close()

if __name__ == "__main__":
    app.run(debug=True)
