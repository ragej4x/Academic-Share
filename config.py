import os

SECRET_KEY = 'fk9lratv'

SESSION_TYPE = 'filesystem'
SESSION_PERMANENT = False

UPLOAD_FOLDER = 'static/uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt', 'zip'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'aczontongao@gmail.com' 
MAIL_PASSWORD = 'uyti cuta rzdy qoqx'  
MAIL_DEFAULT_SENDER = 'aczontongao@gmail.com'  



def get_file_icon(filename):
    if not filename:
        return 'file'
    
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    icon_mapping = {
        'pdf': 'file-pdf',
        'doc': 'file-word',
        'docx': 'file-word',
        'xls': 'file-excel',
        'xlsx': 'file-excel',
        'ppt': 'file-powerpoint',
        'pptx': 'file-powerpoint',
        'txt': 'file-text',
        'png': 'file-image',
        'jpg': 'file-image',
        'jpeg': 'file-image',
        'gif': 'file-image',
        'zip': 'file-archive',
        'rar': 'file-archive'
    }
    
    return icon_mapping.get(extension, 'file')

# Database
# Example: postgresql://user:password@host:port/dbname
# Prefer setting the DATABASE_URL environment variable in production.
def _load_env_file(path):
    """Simple loader for env-like file (KEY=VALUE per line)."""
    data = {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    data[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return data

# Try to read an env file named env.env (you provided this file) and
# fall back to environment variables. This builds a DATABASE_URL
# suitable for psycopg/psycopg2.
_env = _load_env_file(os.path.join(os.path.dirname(__file__), 'env.env'))

db_user = _env.get('user') or os.environ.get('DB_USER') or os.environ.get('USER') or 'postgres'
db_password = _env.get('password') or os.environ.get('DB_PASSWORD') or ''
db_host = _env.get('host') or os.environ.get('DB_HOST') or 'localhost'
db_port = _env.get('port') or os.environ.get('DB_PORT') or '5432'
db_name = _env.get('dbname') or os.environ.get('DB_NAME') or 'academic_share'

if db_password:
    DATABASE_URL = os.environ.get('DATABASE_URL') or f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
else:
    DATABASE_URL = os.environ.get('DATABASE_URL') or f'postgresql://{db_user}@{db_host}:{db_port}/{db_name}'

def is_image_file(filepath):
    if not filepath:
        return False
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filepath and filepath.rsplit('.', 1)[1].lower() in allowed_extensions