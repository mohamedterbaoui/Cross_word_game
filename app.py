from flask import Flask
from flask import jsonify
from flask import url_for
from flask import request

import mysql.connector
import hashlib, uuid

app = Flask(__name__)

# TODO : change the column name in the SELECTS replace (tagname) -> (username)

# TODO : Maybe add a permission or role to the players table or an admin table?

# Dictionary to store active sessions 
sessions = {}

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
    return "Hello, Cross Word!"

# A : Gestion des joueurs
# 1 : retrieving player stats
@app.route("/gamers/<joueur>")
def show_player_stats(joueur):
    # Check if player is logged in before showing the stats
    token = request.args.get("token")
    if not token or token not in sessions:
        return "login to access player stats"
    
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SELECT tagname, games_played, games_won, score, last_login " \
                    "FROM players where tagname = %s", (joueur,))
    player_info = cursor.fetchone()

    if (player_info):
        player_stats = {
            "1.username" : player_info[0],
            "2.games_played" : player_info[1],
            "3.games_won" : player_info[2],
            "4.score" : player_info[3],
            "5.last_login" : player_info[4]
        }
    else :
        player_stats = "Player does not exist"

    cursor.close()
    db.close()
    return jsonify(player_stats)

# 2 : Adding a player to the database
@app.route("/gamers/add/<joueur>/<pwd>")
def add_player(joueur, pwd):
    db = get_db_connection()
    cursor = db.cursor()

    # Checking if player already exists
    cursor.execute("SELECT tagname FROM players where tagname = %s", (joueur, ))
    result = cursor.fetchone()

    if result:
        return "username is already taken, please choose another one"

    # Validating the password
    if ( len(pwd) < 8 or len(pwd) > 64 ):
        return "Error adding player, " \
        "password is too short or too long (must be between 8 and 64 characters)"

    hashed_password = hashlib.sha256(pwd.encode()).hexdigest()

    cursor.execute("INSERT INTO players (tagname, password) " \
    "VALUES (%s, %s)", (joueur, hashed_password))

    db.commit()

    player_id = cursor.lastrowid

    # Create session token to automatically log the player after creation
    # Generate random unique token
    token = str(uuid.uuid4())
    sessions[token] = {"id": player_id, "username":joueur}


    cursor.close()
    db.close()

    return {
        "message": "Player added successfully.",
        "player_id": player_id,
        "session_token":token
    }

# 3 : Login route
@app.route("/gamers/login/<joueur>/<pwd>")
def login(joueur, pwd):
    # check if user is not logged in
    token = request.args.get("token")
    if not token or token not in sessions:
        # Check if there is a player with the (username, pwd) pair
        db = get_db_connection()
        cursor = db.cursor()

        hashed_pwd = hashlib.sha256(pwd.encode()).hexdigest()

        cursor.execute("SELECT id FROM players WHERE tagname = %s AND password = %s", (joueur, hashed_pwd))
        result = cursor.fetchone()

        if not result:
            return "Player does not exist, try another username/password combination"

        player_id = result[0]

        new_token = str(uuid.uuid4())
        sessions[new_token] = {"id":player_id, "username":joueur}

        return {
            "message": "Player logged in successfully",
            "player_id":player_id,
            "session_token":new_token
        }
    
    return "Player is already logged in"

# 4 : Logout route
@app.route("/gamers/logout/<joueur>/<pwd>")
def logout(joueur, pwd):
    # chech if user is logged in or not
    token = request.args.get("token")
    if not token or token not in sessions:
        return "Player is already logged out"
    
    # Otherwise delete token
    del sessions[token]
    return "Player logged out successfully"


# B : Consultation admin
# 1 : top <nb> of players by score
@app.route("/admin/top", defaults={"nb":10})
@app.route("/admin/top/<int:nb>")
def list_top_players(nb):
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SELECT tagname, score FROM players ORDER BY score DESC LIMIT %s", (nb,))
    result = cursor.fetchall()

    scores = []
    for res in result:
        score = {
            "username": res[0],
            "score":res[1]
        }
        scores.append(score)

    db.close()
    cursor.close()

    return { "top_players": scores }

# 2 : Delete player
@app.route("/admin/delete/joueur/<joueur>")
def delete_player(joueur):
    db = get_db_connection()
    cursor = db.cursor()

    # Delete player
    cursor.execute("DELETE FROM players WHERE tagname = %s", (joueur, ))

    db.commit()

    cursor.close()
    db.close()

    return {
        "message":"player deleted successfully",
        "username": joueur
    }

# 3 : Delete definition
@app.route("/admin/delete/def/<id>")
def delete_definition(id):
    db = get_db_connection()
    cursor = db.cursor()

    # Delete definition
    cursor.execute("DELETE FROM definitions WHERE id = %s", (id,))

    db.commit()

    cursor.close()
    db.close()

    return {
        "message":"definition deleted successfully",
        "definition_id": id
    }



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

    arrayOfWords = []

    for res in result:
        cursor.execute("SELECT definition FROM definitions WHERE word_id = %s", (res[0],))
        definitions = cursor.fetchall()

        definition_list = [definition[0] for definition in definitions]

        word = {
            "Id": res[0],
            "Word": res[3],
            "definitions": definition_list
        }
        
        arrayOfWords.append(word)

    cursor.close()
    db.close()
    return {"words": arrayOfWords }

# D : Page web du jeu
@app.route("/jeu/word/", defaults={"time":60, "lg":"en", "hint":10})
def get_HTML_game(time, lg, hint):

    # link of the css file
    css_url = url_for('static', filename='styles.css')

    # link of the js file
    js_url = url_for('static', filename='script.js')

    html_content = f"""
    <html>
        <head>
            <title>Game</title>
            <link rel="stylesheet" href="{css_url}">
        </head>
        <body>
            <h1 class="header">Guess the Word Game</h1>
            <p>Language: {lg}</p>
            <p>Time: {time} seconds</p>
            <p>Hint Interval: {hint} seconds</p>
            <!-- Other game HTML and JS code -->
        </body>
        <script src="{js_url}"></script>
    </html>
    """

    return html_content

if __name__ == "__main__":
    app.run(debug=True)
