from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import sqlite3
import imghdr
from datetime import datetime

app = Flask(__name__)
app.config.from_pyfile('config.py')

# Database initialization
def init_db():
    conn = sqlite3.connect('academic_share.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Posts table
    c.execute('''CREATE TABLE IF NOT EXISTS posts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  title TEXT NOT NULL,
                  description TEXT,
                  filename TEXT,
                  filepath TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect('academic_share.db')
    conn.row_factory = sqlite3.Row
    return conn

# Check if user is logged in
def is_logged_in():
    return 'user_id' in session

# Check allowed file types
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Check if file is an image
def is_image_file(filepath):
    """Check if the file is an image"""
    if not filepath or not os.path.exists(filepath):
        return False
    image_type = imghdr.what(filepath)
    return image_type is not None

# Get appropriate icon for file type
def get_file_icon(filename):
    """Return appropriate Font Awesome icon based on file type"""
    if not filename:
        return "file"
    
    ext = filename.lower().split('.')[-1]
    icon_map = {
        'pdf': 'file-pdf',
        'doc': 'file-word',
        'docx': 'file-word',
        'txt': 'file-alt',
        'zip': 'file-archive',
        'rar': 'file-archive',
        'png': 'file-image',
        'jpg': 'file-image',
        'jpeg': 'file-image',
        'gif': 'file-image'
    }
    return icon_map.get(ext, 'file')

# Format date for display
def format_date(value):
    if value is None:
        return ""
    try:
        # Parse the database timestamp
        dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        # Format it nicely
        return dt.strftime('%b %d, %Y at %H:%M')
    except:
        return value

app.jinja_env.filters['format_date'] = format_date
app.jinja_env.filters['get_file_icon'] = get_file_icon

# Routes
@app.route('/')
def index():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    posts = conn.execute('''
        SELECT posts.*, users.username 
        FROM posts 
        JOIN users ON posts.user_id = users.id 
        ORDER BY posts.created_at DESC
    ''').fetchall()
    conn.close()
    
    return render_template('index.html', posts=posts, is_image_file=is_image_file)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_logged_in():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                         (username, hashed_password))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists!', 'error')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/post', methods=['GET', 'POST'])
def post():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        file = request.files['file']
        
        if not title:
            flash('Title is required!', 'error')
            return render_template('post.html')
        
        filename = None
        filepath = None
        
        if file and file.filename:
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                flash('File uploaded successfully!', 'success')
            else:
                flash('File type not allowed!', 'error')
                return render_template('post.html')
        
        conn = get_db_connection()
        conn.execute('INSERT INTO posts (user_id, title, description, filename, filepath) VALUES (?, ?, ?, ?, ?)',
                     (session['user_id'], title, description, filename, filepath))
        conn.commit()
        conn.close()
        
        flash('Your academic work has been shared!', 'success')
        return redirect(url_for('index'))
    
    return render_template('post.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)