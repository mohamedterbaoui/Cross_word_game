from flask import Flask
from flask import jsonify
from flask import url_for
from flask import request
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()

import re
import mysql.connector
import hashlib, uuid
import os

app = Flask(__name__)
CORS(app)

# Dictionary to store active sessions 
sessions = {}

# Function to get a new connection to the database
def get_db_connection():
    connection = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    port=int(os.getenv("DB_PORT", 3306))
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
    # token = request.args.get("token")
    # if not token or token not in sessions:
    #     return "login to access player stats"
    
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SELECT username, games_played, games_won, score, last_login " \
                    "FROM players where username = %s", (joueur,))
    player_info = cursor.fetchone()

    if (player_info):
        player_stats = {
            "username" : player_info[0],
            "games_played" : player_info[1],
            "games_won" : player_info[2],
            "score" : player_info[3],
            "last_login" : player_info[4]
        }
    else :
        player_stats = "Player does not exist"

    cursor.close()
    db.close()
    return jsonify(player_stats)

# 2 : Signup of a new player
@app.route("/gamers/add/<joueur>/<pwd>")
def add_player(joueur, pwd):
    db = get_db_connection()
    cursor = db.cursor()

    # Checking if player already exists
    cursor.execute("SELECT username FROM players where username = %s", (joueur, ))
    result = cursor.fetchone()

    if result:
        return "username is already taken, please choose another one"

    # Validating the password
    if ( len(pwd) < 8 or len(pwd) > 64 ):
        return "Error adding player, " \
        "password is too short or too long (must be between 8 and 64 characters)"

    hashed_password = hashlib.sha256(pwd.encode()).hexdigest()

    cursor.execute("INSERT INTO players (username, password) " \
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

        cursor.execute("SELECT id FROM players WHERE username = %s AND password = %s", (joueur, hashed_pwd))
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

# Route to update score of a player
@app.route('/gamers/update_score', methods=['POST'])
def update_score():
    data = request.json
    
    if not data or 'username' not in data or 'score' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    username = data['username']
    game_score = data['score']
    
    try:
        # Get database connection
        db = get_db_connection()
        cursor = db.cursor()
        
        # First get the current score for the player
        cursor.execute("SELECT id, score FROM players WHERE username = %s", (username,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'error': 'User not found'}), 404
        
        player_id, current_score = result
        
        # Calculate new total score
        new_total_score = current_score + game_score
        
        # Update the player's score
        cursor.execute("UPDATE players SET score = %s WHERE id = %s", (new_total_score, player_id))
        db.commit()
        
        # Return the updated score information
        return jsonify({
            'message': 'Score updated successfully',
            'username': username,
            'game_score': game_score,
            'total_score': new_total_score
        }), 200
        
    except Exception as e:
        if db:
            db.rollback()
        return jsonify({'error': str(e)}), 500
    
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# B : Consultation admin
# 1 : top <nb> of players by score
@app.route("/admin/top", defaults={"nb":10})
@app.route("/admin/top/<int:nb>")
def list_top_players(nb):
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SELECT username, score FROM players ORDER BY score DESC LIMIT %s", (nb,))
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
    cursor.execute("DELETE FROM players WHERE username = %s", (joueur, ))

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
        cursor.execute("SELECT definition, source FROM definitions WHERE word_id = %s", (res[0],))
        definitions = cursor.fetchall()

        definition_list = [definition[0] for definition in definitions]
        sources_list = [definition[1] for definition in definitions]

        word = {
            "Id": res[0],
            "Lg": res[1],
            "Word": res[2],
            "definitions": definition_list,
            "source": sources_list
        }
        
        arrayOfWords.append(word)

    cursor.close()
    db.close()
    return {"words": arrayOfWords}

# Count the total number of words in our db
@app.route("/word/count")
def count_words():
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(DISTINCT id) FROM words")

    word_count = cursor.fetchone()

    cursor.close()
    db.close()

    return {"word_count" : word_count[0]}

# Get words that match the pattern
@app.route("/word/suggestions/<pattern>")
def get_suggestions(pattern):
    regex_pattern = pattern.replace("_", ".").lower()

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Only fetch words of same length
        cursor.execute("SELECT word FROM words WHERE CHAR_LENGTH(word) = %s", (len(pattern),))
        rows = cursor.fetchall()

        # Filter using regex in Python
        suggestions = [row["word"] for row in rows if re.match(f"^{regex_pattern}$", row["word"].lower())]

        return jsonify({"words": suggestions})
    
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


# D : Page web
# 1 : Display HTML Game
@app.route("/jeu/word/", defaults={"time":60, "lg":"en", "hint":10})
@app.route("/jeu/word/<int:time>", defaults={"lg":"en", "hint":10})
@app.route("/jeu/word/<int:time>/<lg>", defaults={"hint":10})
@app.route("/jeu/word/<int:time>/<lg>/<int:hint>")
def get_HTML_game(time, lg, hint):

    # link of the css file
    css_url = url_for('static', filename='styles.css')

    # link of the js file
    js_url = url_for('static', filename='script.js')

    # link for the images
    avatar_url = url_for('static', filename='img/avatar.png')
    clock_url = url_for('static', filename='img/clock.png')
    hint_url = url_for('static', filename='img/hint.png')
    trophy_url = url_for('static', filename='img/trophy.png')

    html_content = f"""
    <html>
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>Guess the Word Game</title>
            <link rel="stylesheet" href="{css_url}">
        </head>
        <body>
            <div class="container">
            <div class="control-btns">
                <button id="play">Play</button>
                <input
                type="text"
                id="username"
                placeholder="Enter your username"
                required
                />
            </div>
            <div class="game-window">
                <div class="stats">
                <div class="profile">
                    <div><img src="{avatar_url}" alt="profile_picture" /></div>
                    <h3>username</h3>
                </div>
                <div class="total-score">
                    <div><img src="{trophy_url}" alt="trophy icon" /></div>
                    <div id="total-score">Total score</div>
                </div>
                <div class="score">
                    <div class="score-label"></div>
                    <div class="score-bar">
                    <div class="score-fill" id="score-fill"></div>
                    </div>
                    <div id="points">60</div>
                </div>
                </div>
                <div class="word">
                <div id="word-description">word description</div>
                <div id="answer">
                    <div class="letter-boxes">
                    <input type="text" class="letter-box" maxlength="1" />
                    <input type="text" class="letter-box" maxlength="1" />
                    <input type="text" class="letter-box" maxlength="1" />
                    <input type="text" class="letter-box" maxlength="1" />
                    <input type="text" class="letter-box" maxlength="1" />
                    <input type="text" class="letter-box" maxlength="1" />
                    </div>
                </div>
                <div class="remaining-time">
                    <div><img src="{clock_url}" alt="clock_icon" /></div>
                    <div>time text</div>
                    <div id="hint-icon" style="visibility: hidden">
                    <img src="{hint_url}" alt="hint_icon" />
                    </div>
                </div>
                </div>
                <div class="suggestions-box" style="visibility: hidden">
                <h4>suggestions:</h4>
                <div class="suggestions" style="visibility: hidden"></div>
                </div>
            </div>
            </div>
        </body>

        <script>
            const GAME_CONFIG = {{
                time: {time},
                lang: "{lg}",
                hintInterval: {hint}
            }};
        </script>
        <script src="{js_url}"></script>
    </html>
    """

    return html_content

# add definition to the db
@app.route("/word/add_definition", methods=["POST"])
def add_definition():
    data = request.json
    word = data.get("word")
    definition = data.get("definition")
    player = data.get("player")

    if not all([word, definition, player]):
        return jsonify({"error": "Missing fields"}), 400

    # Check constraints
    if len(definition) < 5 or len(definition) > 200:
        return jsonify({"error": "Definition must be between 5 and 200 characters"}), 400

    db = get_db_connection()
    cursor = db.cursor()

    # Step 1: Check if player exists
    cursor.execute("SELECT username FROM players WHERE username = %s", (player,))
    player_exists = cursor.fetchone()

    if not player_exists:
        cursor.close()
        db.close()
        return jsonify({"error": "Player does not exist"}), 400

    # Step 2: Get word_id
    cursor.execute("SELECT id FROM words WHERE Word = %s", (word,))
    word_result = cursor.fetchone()

    if not word_result:
        cursor.close()
        db.close()
        return jsonify({"error": "Word not found"}), 400

    word_id = word_result[0]

    # Step 3: Check if definition already exists
    cursor.execute("SELECT id FROM definitions WHERE word_id = %s AND definition = %s", (word_id, definition))
    if cursor.fetchone():
        cursor.close()
        db.close()
        return jsonify({"error": "Definition already exists"}), 400

    # Step 4: Insert the definition
    cursor.execute(
        "INSERT INTO definitions (word_id, source, definition) VALUES (%s, %s, %s)",
        (word_id, player, definition)
    )
    db.commit()

    cursor.close()
    db.close()

    return jsonify({"success": True, "message": "Definition added successfully", "points": 5})


# 2 : Add definition game
@app.route("/jeu/def", defaults={"lg":"en", "time":60})
@app.route("/jeu/def/<lg>", defaults={"time":60})
@app.route("/jeu/def/<lg>/<int:time>")
def add_definition_game(lg, time):

    html_content = f"""
    <!DOCTYPE html>
    <html lang="{lg}">
    <head>
        <meta charset="UTF-8">
        <title>Definition Game</title>
        <link rel="stylesheet" href="{url_for('static', filename='style1.css')}">
    </head>
    <body>
        <div id="game-container">
            <p>Language: {lg}</p>
            <p>Time: {time} seconds</p>
            <div id="word-display">Loading word...</div>
            <form id="definition-form">
                <input type="text" id="definition-input" placeholder="Your definition..." required>
                <input type="text" id="player-name" placeholder="Username" required>
                <button type="submit">Submit</button>
            </form>
            <div id="messages"></div>
        </div>
        <script src="{url_for('static', filename='script1.js')}"></script>
        <script>const CONFIG = {{
        time : {time},
        lang : "{lg}"
        }}</script>
    </body>
    </html>
    """
    return html_content

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
        def_sources = ""
        for definition in word["definitions"]:
            word_definitions+=definition + ", "
        for source in word["source"]:
            def_sources+= source + ", "


        rows += f"""
        <tr>
            <td>{word["Id"]}</td>
            <td>{word["Lg"]}</td>
            <td>{word["Word"]}</td>
            <td>{word_definitions}</td>            
            <td>{def_sources}</td>
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
                    <th>word</th>
                    <th>definitions</th>
                    <th>sources</th>
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)