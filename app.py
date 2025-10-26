from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import secrets
import os
import psycopg2
import psycopg2.extras
from io import BytesIO
import imghdr
from datetime import datetime

app = Flask(__name__)
app.config.from_pyfile('config.py')

# Initialize Flask-Mail
mail = Mail(app)

# Initialize Serializer for secure tokens
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])


def init_db():
        # Initialize Postgres DB and create tables if they don't exist
        conn = psycopg2.connect(app.config['DATABASE_URL'])
        cur = conn.cursor()

        # Users table
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
                                         id SERIAL PRIMARY KEY,
                                         username TEXT UNIQUE NOT NULL,
                                         email TEXT UNIQUE NOT NULL,
                                         first_name TEXT NOT NULL,
                                         last_name TEXT NOT NULL,
                                         section TEXT NOT NULL,
                                         lrn TEXT UNIQUE NOT NULL,
                                         password TEXT NOT NULL,
                                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

                                     )''')

        # Posts table (store file binary data in DB using bytea)
        cur.execute('''CREATE TABLE IF NOT EXISTS posts (
                                         id SERIAL PRIMARY KEY,
                                         user_id INTEGER NOT NULL,
                                         title TEXT NOT NULL,
                                         description TEXT,
                                         filename TEXT,
                                         filedata BYTEA,
                                         mimetype TEXT,
                                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                         FOREIGN KEY (user_id) REFERENCES users (id)
                                     )''')

        # If this app was previously using a posts table with 'filepath', ensure new columns exist.
        # ALTER TABLE ... ADD COLUMN IF NOT EXISTS is safe when upgrading an existing DB.
        cur.execute("ALTER TABLE posts ADD COLUMN IF NOT EXISTS filedata BYTEA")
        cur.execute("ALTER TABLE posts ADD COLUMN IF NOT EXISTS mimetype TEXT")

        conn.commit()
        cur.close()
        conn.close()

init_db()

def get_db_connection():
    # Return a new psycopg2 connection. Callers should close it.
    # Use RealDictCursor when creating cursors to get dict-like rows.
    conn = psycopg2.connect(app.config['DATABASE_URL'])
    return conn

def is_logged_in():
    return 'user_id' in session

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def is_image_file(filepath):
    """Check if the file is an image"""
    # Accept either a filename (with extension) or a mimetype string
    if not filepath:
        return False
    # If it's a mimetype like 'image/png'
    if isinstance(filepath, str) and filepath.startswith('image/'):
        return True
    # Otherwise treat as filename
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    try:
        return '.' in filepath and filepath.rsplit('.', 1)[1].lower() in allowed_extensions
    except Exception:
        return False

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
        dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        # Format it nicely like smoothhh butter
        return dt.strftime('%b %d, %Y at %H:%M')
    except:
        return value

app.jinja_env.filters['format_date'] = format_date
app.jinja_env.filters['get_file_icon'] = get_file_icon
app.jinja_env.filters['is_image_file'] = is_image_file

# Routes
@app.route('/')
def index():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('''
        SELECT posts.*, users.username 
        FROM posts 
        JOIN users ON posts.user_id = users.id 
        ORDER BY posts.created_at DESC
    ''')
    posts = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('index.html', posts=posts, is_image_file=is_image_file)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_logged_in():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        section = request.form['section']
        lrn = request.form['lrn']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if not lrn.isdigit() or len(lrn) != 12:
            flash('Invalid LRN format! Must be 12 digits.', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute('''INSERT INTO users 
                          (username, email, first_name, last_name, section, lrn, password) 
                          VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                        (username, email, first_name, last_name, section, lrn, hashed_password))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError as e:
            conn.rollback()
            msg = str(e)
            # Try to detect which unique constraint failed
            if 'username' in msg:
                flash('Username already exists!', 'error')
            elif 'email' in msg:
                flash('Email already registered!', 'error')
            elif 'lrn' in msg:
                flash('LRN already registered!', 'error')
            else:
                flash('Registration failed!', 'error')
        finally:
            cur.close()
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
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cur.fetchone()
        cur.close()
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
        filedata = None
        mimetype = None

        if file and file.filename:
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # read bytes into memory to store in DB
                file.stream.seek(0)
                filedata = file.read()
                mimetype = file.mimetype or None
                flash('File uploaded and stored in database!', 'success')
            else:
                flash('File type not allowed!', 'error')
                return render_template('post.html')

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO posts (user_id, title, description, filename, filedata, mimetype) VALUES (%s, %s, %s, %s, %s, %s)',
                 (session['user_id'], title, description, filename, psycopg2.Binary(filedata) if filedata else None, mimetype))
        conn.commit()
        cur.close()
        conn.close()

        flash('Your academic work has been shared!', 'success')
        return redirect(url_for('index'))
    
    return render_template('post.html')


@app.route('/post/<int:post_id>')
def view_post(post_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('''
        SELECT posts.*, users.username 
        FROM posts 
        JOIN users ON posts.user_id = users.id 
        WHERE posts.id = %s AND posts.user_id = %s
    ''', (post_id, session['user_id']))
    post = cur.fetchone()
    cur.close()
    conn.close()
    
    if post is None:
        flash('Post not found or you do not have permission to view it!', 'error')
        return redirect(url_for('index'))
    
    return render_template('view_post.html', post=post, is_image_file=is_image_file, get_file_icon=get_file_icon)

@app.route('/post/<int:post_id>/edit', methods=['POST'])
def edit_post(post_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM posts WHERE id = %s', (post_id,))
    post = cur.fetchone()

    if post is None or post['user_id'] != session['user_id']:
        cur.close()
        conn.close()
        flash('You cannot edit this post!', 'error')
        return redirect(url_for('index'))
    
    title = request.form['title']
    description = request.form['description']
    file = request.files['file']
    
    if file and file.filename:
        if allowed_file(file.filename):
            # store bytes in DB
            filename = secure_filename(file.filename)
            file.stream.seek(0)
            filedata = file.read()
            mimetype = file.mimetype or None
        else:
            conn.close()
            flash('File type not allowed!', 'error')
            return redirect(url_for('view_post', post_id=post_id))
    else:
        filename = post['filename']
        filedata = post.get('filedata')
        mimetype = post.get('mimetype')
    
    cur.execute('''
        UPDATE posts 
        SET title = %s, description = %s, filename = %s, filedata = %s, mimetype = %s 
        WHERE id = %s
    ''', (title, description, filename, psycopg2.Binary(filedata) if filedata else None, mimetype, post_id))
    conn.commit()
    cur.close()
    conn.close()
    
    flash('Post updated successfully!', 'success')
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/post/<int:post_id>/delete')
def delete_post(post_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM posts WHERE id = %s', (post_id,))
    post = cur.fetchone()

    if post is None or post['user_id'] != session['user_id']:
        cur.close()
        conn.close()
        flash('You cannot delete this post!', 'error')
        return redirect(url_for('index'))

    # file is stored in DB (filedata); just delete the row
    cur.execute('DELETE FROM posts WHERE id = %s', (post_id,))
    conn.commit()
    cur.close()
    conn.close()
    
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('index'))


@app.route('/posts')
def posts():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('''
        SELECT posts.*, users.username 
        FROM posts 
        JOIN users ON posts.user_id = users.id 
        WHERE posts.user_id = %s
        ORDER BY posts.created_at DESC
    ''', (session['user_id'],))
    posts = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('posts.html', posts=posts, is_image_file=is_image_file, get_file_icon=get_file_icon)

@app.route('/download/<filename>')
def download_file(filename):
    if not is_logged_in():
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT filename, filedata, mimetype FROM posts WHERE filename = %s', (filename,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row or not row[1]:
            flash('File not found!', 'error')
            return redirect(url_for('index'))

        fname, filedata, mimetype = row[0], row[1], row[2]
        return send_file(BytesIO(filedata), as_attachment=True, download_name=fname, mimetype=mimetype)
    except Exception as e:
        flash('Error downloading file!', 'error')
        return redirect(url_for('index'))


def send_reset_email(user_email, token):
    msg = Message('Password Reset Request',
                  recipients=[user_email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)

@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if is_logged_in():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            token = s.dumps(email, salt='password-reset-salt')

            send_reset_email(email, token)

            flash('An email has been sent with instructions to reset your password.', 'info')
            return redirect(url_for('login'))
        else:
            flash('No account found with that email address.', 'error')
    
    return render_template('reset_request.html')

@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if is_logged_in():
        return redirect(url_for('index'))
    
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=3600) 
    except:
        flash('That is an invalid or expired token', 'error')
        return redirect(url_for('reset_request'))
    
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_token.html', token=token)
        
        conn = get_db_connection()
        cur = conn.cursor()
        hashed_password = generate_password_hash(password)
        cur.execute('UPDATE users SET password = %s WHERE email = %s', (hashed_password, email))
        conn.commit()
        cur.close()
        conn.close()

        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
        
    return render_template('reset_token.html', token=token)

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)
