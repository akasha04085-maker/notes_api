import os
import jwt
import bcrypt
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
                    content TEXT,
                    created_at TEXT
                    )
                ''')
    
    conn.execute('''
                CREATE TABLE IF NOT EXISTS users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT
                )
                ''')
    conn.execute('''
                CREATE TABLE IF NOT EXISTS login_logs(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    login_time TEXT,
                    status TEXT
                );
                ''')
    print(os.path.abspath(DB_NAME))
    conn.commit()
    conn.close()
    
@app.route('/users')
def get_users():
    conn = sqlite3.connect(DB_NAME)
    
    cursor = conn.execute("SELECT id, username, password FROM users")
    
    users = []
    
    for row in cursor:
        users.append({
            "id": row[0],
            "username": row[1],
            "password": row[2]
        })
    conn.close()
    return jsonify(users)
@app.route('/register', methods=['post'])
def register():
    
    data = request.get_json()
    
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({
            "status": "error",
            "message": "username and password are required"
        }),400
        
    conn = sqlite3.connect(DB_NAME)
    try:
        hashed_password = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        conn.execute(
            "INSERT INTO users (username,password) VALUES (?, ?)",
            (username, hashed_password)
        )
        conn.commit()
        return jsonify({
            "status": "success",
            "message": "user registered successfully"
        }),201
        
    except sqlite3.IntegrityError:
        return jsonify({
            "status": "error",
            "message": "Username already exists"
        }),400
    
    finally:
        conn.close()
    
@app.route('/login', methods=['POST'])
def login():
    
    data = request.get_json()
    
    username = data.get('username')
    password = data.get('password')
    
    
    if not username or not password:
        return jsonify({
            "status": "error",
            "message": "username and password are required"
        }),400
    
    conn = sqlite3.connect(DB_NAME)  
    
    cursor = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, password)
    )
    
    user = cursor.fetchone()
    if user:
        status = "Success"
    else:
        status = "Failed"
        
    conn.execute(
    "INSERT INTO login_logs (username, login_time, status) VALUES (?, ?, ?)",
    (
        username,
        datetime.datetime.now().isoformat(),
        status
    )
)
    conn.commit()
    conn.close()
    
    if user:
        
    
        token = jwt.encode({
            'user': username,
            'exp': datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
        },
        SECRET_KEY, 
        algorithm="HS256"
        )
        
        return jsonify({
            "status": "success",
            "token": token
        }),200
        
    return jsonify({
        "status": "error",
        "message": "Invalid Invalid username or password"
        }),401
    
def token_required(f):
    @wraps(f)
    
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({
                "status": "error",
                "message": "Token missing"
            }), 401
            
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
        
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
    
    if not title or not content:
        return jsonify({
        "status": "error",
        "message": "Title and content are required"
    }), 400
    
    conn = sqlite3.connect(DB_NAME)
    
    create_at = datetime.datetime.now().isoformat()
    conn.execute(
        "INSERT INTO notes (title, content, created_at) VALUES (?, ?, ?)",(title, content, create_at)
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
    
    sort = request.args.get('sort', 'id')
    
    page = int(request.args.get('page', 1))
    
    limit = int(request.args.get('limit', 2))
    
    offset = (page - 1) * limit
    
    conn = sqlite3.connect(DB_NAME)
    
    if sort not in ['id', 'title']:
        sort = 'id'
    
    query = f"SELECT * FROM notes ORDER BY {sort} ASC LIMIT ? OFFSET ?"
    
    cursor = conn.execute(query, (limit, offset))
    
    notes = []
    
    for row in cursor:
        notes.append({
            "id": row[0],
            "title": row[1],
            "content": row[2],
            "created_at": row[3]
        })
        
    conn.close()
    return jsonify({
        "status": "success",
        "page": page,
        "limit": limit,
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
    
@app.route('/login_logs', methods=['GET'])
@token_required
def login_logs():
    
    conn = sqlite3.connect(DB_NAME)
    
    cursor = conn.execute(
        "SELECT * FROM login_logs ORDER BY id DESC"
    )
    
    logs = []
    
    for row in cursor:
        logs.append({
            "id": row[0],
            "username": row[1],
            "login_time": row[2],
            "status": row[3]
        })
        
    conn.close()
    return jsonify(logs)
    
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
    
@app.route('/search', methods=['GET'])
@token_required
def search_notes():
    
    title = request.args.get('title')
    
    conn = sqlite3.connect(DB_NAME)
    
    cursor = conn.execute(
        "SELECT * FROM notes WHERE title LIKE ?",
        (f"%{title}%",)
    )
    
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
    })
    

if __name__ == '__main__':
    init_db()
    app.run(debug=True)