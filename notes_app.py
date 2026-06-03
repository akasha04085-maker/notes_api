import jwt
import datetime
import sqlite3
from functools import wraps
from flask import Flask, request, jsonify 

app = Flask(__name__)

SECRET_KEY = "mysecretkey"

DB_NAME = 'notes.db'
def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute('''
                CREATE TABLE IF NOT EXISTS notes(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    content TEXT
                    )
                ''')
    conn.commit()
    conn.close()
    
@app.route('/login', methods=['POST'])
def login():
    
    data = request.get_json()
    
    username = data.get('username')
    password = data.get('password')
    
    if username == 'admin' and password == 'admin@132':
        token = jwt.encode({
            'user': username,
            'exp': datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
        },SECRET_KEY, algorithm="HS256")
        
        return jsonify({
            "status": "success",
            "token": token
        }),200
        
    return jsonify({
        "status": "error",
        "message": "Invalid credentials"
    }),401
    
def token_required(f):
    @wraps(f)
    
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token  and token.startswith("Bearer "):
            token = token.split(" ")[1]
            return jsonify({
                "status": "error",
                "message": "Token missing"
            }), 401
        
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({
                "status": "error",
                "message": "Invalid or expired token"
            }), 401
        
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token"}), 401
        
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@token_required
def home():
    return "Notes API Running"

@app.route('/add_note', methods=['POST'])
@token_required
def add_note():
    
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "Title is required"
            }), 400
    
    title = data.get('title')
    content = data.get('content')
    
    conn = sqlite3.connect(DB_NAME)
    
    conn.execute(
        "INSERT INTO notes (title, content) VALUES (?, ?)",(title, content)
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({
        "status": "success",
        "message": "Notes added successfully"
    }),201
    
@app.route('/notes', methods=['GET'])
@token_required
def get_notes():
    
    conn = sqlite3.connect(DB_NAME)
    
    cursor = conn.execute("SELECT * FROM notes")
    
    notes = []
    
    for row in cursor:
        notes.append({
            "id": row[0],
            "title": row[1],
            "content": row[2]
        })
        
    conn.close()
    return jsonify({
        "status": "success",
        "data": notes
    }), 200

@app.route('/delete_note/<int:id>', methods=['DELETE'])
@token_required
def delete_note(id):
    
    conn = sqlite3.connect(DB_NAME)
    
    conn.execute("DELETE FROM notes WHERE id = ?", (id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        "message": "Note deleted successfully"
    })
    
@app.route('/update_note/<int:id>', methods=['PUT'])
@token_required
def update_note(id):
    
    data = request.get_json()
    
    title = data.get('title')
    content = data.get('content')
    
    conn = sqlite3.connect(DB_NAME)
    
    cursor = conn.execute(
        "UPDATE notes SET title = ?, content = ? WHERE id = ?", (title, content, id)
    )
    
    if cursor.rowcount == 0:
        return jsonify({"error": "Note not founded"}), 400
    
    conn.commit()
    conn.close()
    
    return jsonify({
        "message": "Note updated successfully"
    })
    
@app.route('/notes/<int:id>', methods=['PUT'])
@token_required
def update_note_put(id):
    
    data = request.get_json()
    
    title = data.get('title')
    content = data.get('content')
    
    conn = sqlite3.connect(DB_NAME)
    
    cursor = conn.execute("SELECT * FROM notes WHERE id = ?", (id,))
    note = cursor.fetchone()
    
    if not note:
        conn.close()
        return jsonify({"status": "error", "message": "Note not found"}), 404
    
    conn.execute(
        "UPDATE notes SET title = ?, content = ? WHERE id = ?", (title, content, id)
    )
    conn.commit()
    conn.close()
    
    return jsonify({
        "status": "success",
        "message": "Note updated successfully"
    })
    
@app.route('/notes/<int:id>', methods=['DELETE'])
@token_required
def delete_note_delete(id):
    
    conn = sqlite3.connect(DB_NAME)
    
    cursor = conn.execute("SELECT * FROM notes WHERE id = ?", (id,))
    note = cursor.fetchone()
    
    if not note:
        conn.close()
        return jsonify({"status": "error", "message": "Note not found"}), 404
    
    
    conn.execute("DELETE FROM notes WHERE id = ?", (id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        "status": "success",
        "message": "Note deleted successfully" 
    }), 200 

if __name__ == '__main__':
    init_db()
    app.run(debug=True)