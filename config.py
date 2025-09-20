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

def is_image_file(filepath):
    if not filepath:
        return False
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filepath and filepath.rsplit('.', 1)[1].lower() in allowed_extensions