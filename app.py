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
            "Lg": res[1],
            "source": res[2],
            "Word": res[3],
            "definitions": definition_list
        }
        
        arrayOfWords.append(word)

    cursor.close()
    db.close()
    return {"words": arrayOfWords}

# D : Page web
# 1 : Display HTML Game
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

# 2 : Add definition game
@app.route("/jeu/def", defaults={"lg":"en", "time":60})
@app.route("/jeu/def/<lg>", defaults={"time":60})
@app.route("/jeu/def/<lg>/<int:time>")
def add_definition_game(lg, time):

    return "Hello"

# 3 : Display definitions using DataTables
@app.route("/dump", defaults={"step":10})
@app.route("/dump/<step>")
def dispaly_definitions_datatables(step):
    db = get_db_connection()
    cursor = db.cursor()

    # Get number of rows of words table
    cursor.execute("SELECT COUNT(*) FROM words")
    nb_words = cursor.fetchall()[0][0]

    cursor.close()
    db.close()

    # Getting the words collection
    words_object = get_words_collection(nb_words, 1)

    words = words_object["words"]

    # Building the table rows from the query result
    rows = ""
    for word in words:
        word_definitions = ""
        for definition in word["definitions"]:
            word_definitions+=definition + ", "

        rows += f"""
        <tr>
            <td>{word["Id"]}</td>
            <td>{word["Lg"]}</td>
            <td>{word["source"]}</td>
            <td>{word["Word"]}</td>
            <td>{word_definitions}</td>
        </tr>
        """
    
    # HTML to display the data in a datatable
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Definitions DataTable</title>
            <link
      rel="stylesheet"
      href="https://cdn.datatables.net/2.2.2/css/dataTables.dataTables.min.css"
    />
    </head>
    <body>
        <h1>Definitions</h1>
        <table id="definitionsTable" class="display">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>language</th>
                    <th>source</th>
                    <th>word</th>
                    <th>definitions</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>

        <!-- DataTables JS -->
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://cdn.datatables.net/2.2.2/js/dataTables.min.js"></script>

        <!-- Initialize DataTable -->
        <script>
        document.addEventListener("DOMContentLoaded", function () {{
            new DataTable("#definitionsTable", {{
                "pageLength": {step}  // Number of rows per page
            }});
        }});
        </script>
    </body>
    </html>
    """

    return html_content

# 4 : Documentation in an HTML page
@app.route("/doc")
def display_documentation():

    # Defining all the rules in an array
    routes = [
        {'endpoint': 'home', 'methods': 'GET', 'url': '/'},
        {'endpoint': 'show_player_stats', 'methods': 'GET', 'url': '/gamers/<joueur>'},
        {'endpoint': 'add_player', 'methods': 'GET', 'url': '/gamers/add/<joueur>/<pwd>'},
        {'endpoint': 'login', 'methods': 'GET', 'url': '/gamers/login/<joueur>/<pwd>'},
        {'endpoint': 'logout', 'methods': 'GET', 'url': '/gamers/logout/<joueur>/<pwd>'},
        {'endpoint': 'list_top_players', 'methods': 'GET', 'url': '/admin/top'},
        {'endpoint': 'delete_player', 'methods': 'GET', 'url': '/admin/delete/joueur/<joueur>'},
        {'endpoint': 'delete_definition', 'methods': 'GET', 'url': '/admin/delete/def/<id>'},
        {'endpoint': 'get_words_collection', 'methods': 'GET', 'url': '/word'},
        {'endpoint': 'get_HTML_game', 'methods': 'GET', 'url': '/jeu/word/'},
        {'endpoint': 'add_definition_game', 'methods': 'GET', 'url': '/jeu/def'},
        {'endpoint': 'dispaly_definitions_datatables', 'methods': 'GET', 'url': '/dump'},
        {'endpoint': 'display_documentation', 'methods': 'GET', 'url': '/doc'},
    ]
    

    # Create HTML content with all routes
    html_content = """
    <html>
    <head>
        <title>API Documentation</title>
    </head>
    <body>
        <h1>API Routes</h1>
        <table border="1">
            <thead>
                <tr>
                    <th>Endpoint</th>
                    <th>Methods</th>
                    <th>URL</th>
                </tr>
            </thead>
            <tbody>
    """

    for route in routes:
        html_content += f"""
        <tr>
            <td>{route['endpoint']}</td>
            <td>{route['methods']}</td>
            <td><a href="{route['url']}">{route['url']}</a></td>
        </tr>
        """

    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """

    return html_content

if __name__ == "__main__":
    app.run(debug=True)
