
from flask import Flask, render_template_string, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///forum.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    bio = db.Column(db.Text)
    profile_pic = db.Column(db.String(150), default='default.jpg')
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    threads = db.relationship('Thread', backref='author', lazy=True)
    posts = db.relationship('Post', backref='author', lazy=True)

class Thread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    posts = db.relationship('Post', backref='thread', lazy=True, cascade='all, delete-orphan')
    views = db.Column(db.Integer, default=0)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Reset database to ensure schema consistency
with app.app_context():
    db.drop_all()
    db.create_all()

# Base template components (header and footer)
BASE_HEADER = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}MAHKEME Forum{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        :root {
            --primary-color: #ff9500;
            --secondary-color: #343a40;
            --accent-color: #ff5555;
            --light-bg: #f8f9fa;
            --dark-bg: #212529;
            --card-bg: #2d3035;
            --text-light: #f8f9fa;
            --text-dark: #212529;
        }
        body {
            background-color: #121212;
            color: #e0e0e0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding-top: 80px;
            min-height: 100vh;
        }
        .forum-container {
            background-color: var(--card-bg);
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            padding: 25px;
            margin-bottom: 20px;
        }
        .thread-card, .post-card {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 149, 0, 0.2);
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }
        .thread-card:hover, .post-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 15px rgba(255, 149, 0, 0.25);
            border-color: var(--primary-color);
        }
        .btn-primary {
            background-color: var(--primary-color);
            border-color: var(--primary-color);
        }
        .btn-primary:hover {
            background-color: #e68500;
            border-color: #e68500;
        }
        .text-primary {
            color: var(--primary-color) !important;
        }
        a {
            color: var(--primary-color);
            text-decoration: none;
            transition: color 0.2s;
        }
        a:hover {
            color: #ffaa33;
        }
        .navbar-brand {
            font-weight: bold;
            font-size: 1.5rem;
        }
        .user-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid var(--primary-color);
        }
        .thread-title {
            font-size: 1.4rem;
            font-weight: 600;
            margin-bottom: 10px;
        }
        .thread-meta, .post-meta {
            font-size: 0.85rem;
            color: #adb5bd;
        }
        .badge-custom {
            background-color: var(--primary-color);
            color: var(--text-dark);
        }
        .form-control {
            background-color: #2c2f36;
            border: 1px solid #444;
            color: #e0e0e0;
        }
        .form-control:focus {
            background-color: #2c2f36;
            border-color: var(--primary-color);
            color: #e0e0e0;
            box-shadow: 0 0 0 0.25rem rgba(255, 149, 0, 0.25);
        }
        .intro-text {
            font-family: 'Courier New', monospace;
            color: #00ff00;
            text-shadow: 0 0 10px #00ff00;
            font-size: 1.2rem;
            line-height: 1.6;
        }
        .profile-header {
            background: linear-gradient(to right, #2d3035, #1a1a1a);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .profile-avatar {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid var(--primary-color);
            box-shadow: 0 0 15px rgba(255, 149, 0, 0.5);
        }
        .message-bubble {
            max-width: 75%;
            padding: 12px 16px;
            border-radius: 18px;
            margin-bottom: 10px;
            position: relative;
        }
        .message-sent {
            background-color: rgba(255, 149, 0, 0.2);
            margin-left: auto;
            border-bottom-right-radius: 4px;
        }
        .message-received {
            background-color: rgba(52, 58, 64, 0.4);
            margin-right: auto;
            border-bottom-left-radius: 4px;
        }
        .floating-btn {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background-color: var(--primary-color);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            z-index: 100;
            font-size: 1.5rem;
            transition: all 0.3s;
        }
        .floating-btn:hover {
            transform: scale(1.1);
            color: white;
        }
        .category-badge {
            background: linear-gradient(45deg, #ff9500, #ff5555);
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        footer {
            background-color: var(--dark-bg);
            padding: 30px 0;
            margin-top: 40px;
        }
        .alert {
            border: none;
            border-radius: 8px;
        }
        .pagination .page-link {
            background-color: var(--card-bg);
            border-color: #444;
            color: var(--primary-color);
        }
        .pagination .page-item.active .page-link {
            background-color: var(--primary-color);
            border-color: var(--primary-color);
            color: var(--text-dark);
        }
        .chat-messages {
            max-height: 400px;
            overflow-y: auto;
            padding: 10px;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('forum') }}">
                <i class="fas fa-fire"></i> MAHKEME Forum
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('forum') }}">Ana Sayfa</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#">Kategoriler</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#">Üyeler</a>
                    </li>
                </ul>
                <ul class="navbar-nav ms-auto">
                    {% if current_user.is_authenticated %}
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" data-bs-toggle="dropdown">
                            <img src="{{ url_for('static', filename='uploads/' + current_user.profile_pic) }}" width="30" height="30" class="rounded-circle me-2">
                            {{ current_user.username }}
                        </a>
                        <div class="dropdown-menu dropdown-menu-end">
                            <a class="dropdown-item" href="{{ url_for('user_profile', username=current_user.username) }}">Profilim</a>
                            <a class="dropdown-item" href="{{ url_for('profile') }}">Profil Düzenle</a>
                            <div class="dropdown-divider"></div>
                            <a class="dropdown-item" href="{{ url_for('logout') }}">Çıkış</a>
                        </div>
                    </li>
                    {% else %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('login') }}">Giriş</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('register') }}">Kayıt</a>
                    </li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
'''

BASE_FOOTER = '''
    </div>
    <footer class="mt-5">
        <div class="container">
            <div class="row">
                <div class="col-md-6">
                    <h5>MAHKEME Forum</h5>
                    <p> İFŞALA GEÇ XD</p>
                </div>
                <div class="col-md-6 text-end">
                    <p>&copy; 2025 MAHKEME Forum. Tüm hakları saklıdır.</p>
                    <div class="social-links">
                        <a href="#" class="me-2"><i class="fab fa-github fa-lg"></i></a>
                        <a href="#" class="me-2"><i class="fab fa-twitter fa-lg"></i></a>
                        <a href="#" class="me-2"><i class="fab fa-discord fa-lg"></i></a>
                    </div>
                </div>
            </div>
        </div>
    </footer>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl)
        });
        function scrollChatToBottom() {
            const chatContainer = document.querySelector('.chat-messages');
            if (chatContainer) {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }
        document.addEventListener('DOMContentLoaded', function() {
            scrollChatToBottom();
        });
    </script>
    {% block scripts %}{% endblock %}
</body>
</html>
'''

# Routes
@app.route('/')
def home():
    return render_template_string(BASE_HEADER + '''
<div id="intro" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: black; z-index: 9999; display: flex; justify-content: center; align-items: center;">
    <pre id="intro-text" class="intro-text"></pre>
</div>
<script>
    const introText = `root@kali:~$ sudo systemctl start mahkeme-forum
[OK] Initializing mahkeme Forum Network...
[OK] System Root Login Successful
[OK] Accessing Cehennem Interface...`;
    const introElement = document.getElementById('intro-text');
    let i = 0;
    const typingSpeed = 30;
    function typeWriter() {
        if (i < introText.length) {
            introElement.textContent += introText.charAt(i);
            i++;
            setTimeout(typeWriter, typingSpeed);
        } else {
            const remainingTime = 4000 - (i * typingSpeed);
            setTimeout(() => {
                window.location.href = "{{ url_for('forum') }}";
            }, remainingTime > 0 ? remainingTime : 0);
        }
    }
    typeWriter();
</script>
''' + BASE_FOOTER, title='MAHKEME Forum - Ana Sayfa')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Kullanıcı adı ve şifre zorunludur!', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Bu kullanıcı adı zaten alınmış!', 'danger')
            return redirect(url_for('register'))
        user = User(
            username=username, 
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))
    return render_template_string(BASE_HEADER + '''
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="forum-container">
            <h2 class="text-center mb-4"><i class="fas fa-user-plus me-2"></i>Kayıt Ol</h2>
            <form method="POST">
                <div class="mb-3">
                    <label for="username" class="form-label">Kullanıcı Adı</label>
                    <input type="text" class="form-control" id="username" name="username" required>
                </div>
                <div class="mb-4">
                    <label for="password" class="form-label">Şifre</label>
                    <input type="password" class="form-control" id="password" name="password" required>
                </div>
                <button type="submit" class="btn btn-primary w-100 py-2">Kayıt Ol</button>
            </form>
            <div class="text-center mt-3">
                Zaten hesabınız var mı? <a href="{{ url_for('login') }}">Giriş yapın</a>
            </div>
        </div>
    </div>
</div>
''' + BASE_FOOTER, title='Kayıt Ol - MAHKEME Forum')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Kullanıcı adı ve şifre zorunludur!', 'danger')
            return redirect(url_for('login'))
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            flash('Başarıyla giriş yaptınız!', 'success')
            return redirect(next_page or url_for('forum'))
        flash('Kullanıcı adı veya şifre hatalı!', 'danger')
    return render_template_string(BASE_HEADER + '''
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="forum-container">
            <h2 class="text-center mb-4"><i class="fas fa-sign-in-alt me-2"></i>Giriş Yap</h2>
            <form method="POST">
                <div class="mb-3">
                    <label for="username" class="form-label">Kullanıcı Adı</label>
                    <input type="text" class="form-control" id="username" name="username" required>
                </div>
                <div class="mb-4">
                    <label for="password" class="form-label">Şifre</label>
                    <input type="password" class="form-control" id="password" name="password" required>
                </div>
                <button type="submit" class="btn btn-primary w-100 py-2">Giriş Yap</button>
            </form>
            <div class="text-center mt-3">
                Hesabınız yok mu? <a href="{{ url_for('register') }}">Kayıt olun</a>
            </div>
        </div>
    </div>
</div>
''' + BASE_FOOTER, title='Giriş Yap - MAHKEME Forum')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Başarıyla çıkış yaptınız.', 'info')
    return redirect(url_for('forum'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.bio = request.form.get('bio', '')
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                current_user.profile_pic = filename
        db.session.commit()
        flash('Profiliniz güncellendi!', 'success')
        return redirect(url_for('user_profile', username=current_user.username))
    return render_template_string(BASE_HEADER + '''
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="forum-container">
            <h2 class="mb-4"><i class="fas fa-user-edit me-2"></i>Profil Düzenle</h2>
            <div class="text-center mb-4">
                <img src="{{ url_for('static', filename='uploads/' + current_user.profile_pic) }}" 
                     class="profile-avatar" alt="Profil Fotoğrafı">
            </div>
            <form method="POST" enctype="multipart/form-data">
                <div class="mb-3">
                    <label for="bio" class="form-label">Biyografi</label>
                    <textarea class="form-control" id="bio" name="bio" rows="4">{{ current_user.bio or '' }}</textarea>
                </div>
                <div class="mb-4">
                    <label for="profile_pic" class="form-label">Profil Fotoğrafı</label>
                    <input class="form-control" type="file" id="profile_pic" name="profile_pic">
                </div>
                <button type="submit" class="btn btn-primary w-100 py-2">Değişiklikleri Kaydet</button>
            </form>
        </div>
    </div>
</div>
''' + BASE_FOOTER, title='Profil Düzenle - MAHKEME Forum', current_user=current_user)

@app.route('/user/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    threads = Thread.query.filter_by(user_id=user.id).order_by(Thread.created_at.desc()).limit(5).all()
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).limit(5).all()
    return render_template_string(BASE_HEADER + '''
<div class="profile-header">
    <div class="row align-items-center">
        <div class="col-md-3 text-center">
            <img src="{{ url_for('static', filename='uploads/' + user.profile_pic) }}" 
                 class="profile-avatar" alt="{{ user.username }}">
        </div>
        <div class="col-md-9">
            <h2>{{ user.username }}</h2>
            <p class="mb-2"><i class="fas fa-calendar-alt me-2"></i>Üyelik: {{ user.join_date.strftime('%d.%m.%Y') }}</p>
            {% if user.bio %}
            <p class="mb-0">{{ user.bio }}</p>
            {% else %}
            <p class="text-muted">Bu kullanıcı henüz bir biyografi eklememiş.</p>
            {% endif %}
        </div>
    </div>
</div>
<div class="row">
    <div class="col-md-6">
        <div class="forum-container">
            <h4 class="mb-4"><i class="fas fa-file-alt me-2"></i>Son Başlıklar</h4>
            {% if threads %}
                {% for thread in threads %}
                <div class="thread-card">
                    <h5><a href="{{ url_for('thread', thread_id=thread.id) }}">{{ thread.title }}</a></h5>
                    <p class="thread-meta">{{ thread.created_at.strftime('%d.%m.%Y %H:%M') }}</p>
                </div>
                {% endfor %}
            {% else %}
                <p class="text-muted">Bu kullanıcı henüz başlık oluşturmamış.</p>
            {% endif %}
        </div>
    </div>
    <div class="col-md-6">
        <div class="forum-container">
            <h4 class="mb-4"><i class="fas fa-comments me-2"></i>Son Yorumlar</h4>
            {% if posts %}
                {% for post in posts %}
                <div class="post-card">
                    <p>{{ post.content[:100] }}{% if post.content|length > 100 %}...{% endif %}</p>
                    <p class="thread-meta">
                        <a href="{{ url_for('thread', thread_id=post.thread_id) }}">Konuya git</a> • 
                        {{ post.created_at.strftime('%d.%m.%Y %H:%M') }}
                    </p>
                </div>
                {% endfor %}
            {% else %}
                <p class="text-muted">Bu kullanıcı henüz yorum yapmamış.</p>
            {% endif %}
        </div>
    </div>
</div>
{% if current_user.is_authenticated and current_user.id != user.id %}
<a href="{{ url_for('chat', user_id=user.id) }}" class="floating-btn" data-bs-toggle="tooltip" title="Mesaj Gönder">
    <i class="fas fa-comment"></i>
</a>
{% endif %}
''' + BASE_FOOTER, title=f'{user.username} - MAHKEME Forum', user=user, threads=threads, posts=posts, current_user=current_user)

@app.route('/forum')
def forum():
    threads = Thread.query.order_by(Thread.updated_at.desc()).all()
    return render_template_string(BASE_HEADER + '''
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2><i class="fas fa-fire me-2"></i>Son Konular</h2>
    {% if current_user.is_authenticated %}
    <a href="{{ url_for('create_thread') }}" class="btn btn-primary">
        <i class="fas fa-plus me-1"></i> Yeni Konu
    </a>
    {% endif %}
</div>
<div class="forum-container">
    {% if threads %}
        {% for thread in threads %}
        <div class="thread-card">
            <div class="row">
                <div class="col-md-8">
                    <h4 class="thread-title">
                        <a href="{{ url_for('thread', thread_id=thread.id) }}">{{ thread.title }}</a>
                    </h4>
                    <p class="thread-meta">
                        <img src="{{ url_for('static', filename='uploads/' + thread.author.profile_pic) }}" 
                             class="user-avatar me-2" width="30" height="30">
                        <a href="{{ url_for('user_profile', username=thread.author.username) }}">{{ thread.author.username }}</a> • 
                        {{ thread.created_at.strftime('%d.%m.%Y %H:%M') }} • 
                        {{ thread.views }} görüntüleme
                    </p>
                </div>
                <div class="col-md-4 text-end">
                    <span class="badge bg-secondary me-2">{{ thread.posts|length }} yorum</span>
                    <span class="category-badge">Genel</span>
                </div>
            </div>
        </div>
        {% endfor %}
    {% else %}
        <div class="text-center py-4">
            <i class="fas fa-comments fa-3x mb-3 text-muted"></i>
            <h4 class="text-muted">Henüz hiç konu bulunmuyor</h4>
            <p>İlk konuyu oluşturmak için <a href="{{ url_for('create_thread') }}">tıklayın</a>.</p>
        </div>
    {% endif %}
</div>
''' + BASE_FOOTER, title='Forum - MAHKEME Forum', threads=threads, current_user=current_user)

@app.route('/create_thread', methods=['GET', 'POST'])
@login_required
def create_thread():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        if not title or not content:
            flash('Başlık ve içerik zorunludur!', 'danger')
            return redirect(url_for('create_thread'))
        thread = Thread(
            title=title, 
            content=content, 
            user_id=current_user.id
        )
        db.session.add(thread)
        db.session.commit()
        flash('Konunuz başarıyla oluşturuldu!', 'success')
        return redirect(url_for('thread', thread_id=thread.id))
    return render_template_string(BASE_HEADER + '''
<div class="row justify-content-center">
    <div class="col-md-10">
        <div class="forum-container">
            <h2 class="mb-4"><i class="fas fa-plus-circle me-2"></i>Yeni Konu Oluştur</h2>
            <form method="POST">
                <div class="mb-3">
                    <label for="title" class="form-label">Başlık</label>
                    <input type="text" class="form-control" id="title" name="title" required>
                </div>
                <div class="mb-4">
                    <label for="content" class="form-label">İçerik</label>
                    <textarea class="form-control" id="content" name="content" rows="8" required></textarea>
                </div>
                <button type="submit" class="btn btn-primary py-2 px-4">Konuyu Oluştur</button>
                <a href="{{ url_for('forum') }}" class="btn btn-secondary py-2 px-4 ms-2">İptal</a>
            </form>
        </div>
    </div>
</div>
''' + BASE_FOOTER, title='Yeni Konu - MAHKEME Forum', current_user=current_user)

@app.route('/thread/<int:thread_id>', methods=['GET', 'POST'])
def thread(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    thread.views += 1
    db.session.commit()
    if request.method == 'POST' and current_user.is_authenticated:
        content = request.form.get('content')
        if not content:
            flash('Yorum içeriği boş olamaz!', 'danger')
            return redirect(url_for('thread', thread_id=thread_id))
        post = Post(
            content=content, 
            user_id=current_user.id, 
            thread_id=thread_id
        )
        db.session.add(post)
        thread.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Yorumunuz gönderildi!', 'success')
        return redirect(url_for('thread', thread_id=thread_id))
    posts = Post.query.filter_by(thread_id=thread_id).order_by(Post.created_at.asc()).all()
    return render_template_string(BASE_HEADER + '''
<div class="forum-container mb-4">
    <nav aria-label="breadcrumb">
        <ol class="breadcrumb">
            <li class="breadcrumb-item"><a href="{{ url_for('forum') }}">Forum</a></li>
            <li class="breadcrumb-item active">{{ thread.title }}</li>
        </ol>
    </nav>
    <div class="thread-card mb-4">
        <div class="d-flex align-items-start">
            <div class="flex-shrink-0 me-3">
                <img src="{{ url_for('static', filename='uploads/' + thread.author.profile_pic) }}" 
                     class="user-avatar" width="50" height="50" alt="{{ thread.author.username }}">
            </div>
            <div class="flex-grow-1">
                <h3 class="thread-title">{{ thread.title }}</h3>
                <div class="thread-content mb-3">
                    {{ thread.content|replace('\n', '<br>')|safe }}
                </div>
                <div class="thread-meta">
                    <a href="{{ url_for('user_profile', username=thread.author.username) }}" class="fw-bold">{{ thread.author.username }}</a> • 
                    {{ thread.created_at.strftime('%d.%m.%Y %H:%M') }} • 
                    {{ thread.views }} görüntüleme
                </div>
            </div>
        </div>
    </div>
    <h4 class="mb-3">{{ posts|length }} Yorum</h4>
    {% for post in posts %}
    <div class="post-card mb-3">
        <div class="d-flex align-items-start">
            <div class="flex-shrink-0 me-3">
                <img src="{{ url_for('static', filename='uploads/' + post.author.profile_pic) }}" 
                     class="user-avatar" width="40" height="40" alt="{{ post.author.username }}">
            </div>
            <div class="flex-grow-1">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <a href="{{ url_for('user_profile', username=post.author.username) }}" class="fw-bold">{{ post.author.username }}</a>
                    <span class="text-muted small">{{ post.created_at.strftime('%d.%m.%Y %H:%M') }}</span>
                </div>
                <div class="post-content">
                    {{ post.content|replace('\n', '<br>')|safe }}
                </div>
            </div>
        </div>
    </div>
    {% endfor %}
    {% if current_user.is_authenticated %}
    <div class="mt-4">
        <h5 class="mb-3">Yorum Yap</h5>
        <form method="POST">
            <div class="mb-3">
                <textarea class="form-control" name="content" rows="4" placeholder="Yorumunuzu buraya yazın..." required></textarea>
            </div>
            <button type="submit" class="btn btn-primary">Gönder</button>
        </form>
    </div>
    {% else %}
    <div class="alert alert-info mt-4">
        Yorum yapmak için <a href="{{ url_for('login') }}">giriş yapmalısınız</a>.
    </div>
    {% endif %}
</div>
''' + BASE_FOOTER, title=f'{thread.title} - MAHKEME Forum', thread=thread, posts=posts, current_user=current_user)

@app.route('/chat/<int:user_id>', methods=['GET', 'POST'])
@login_required
def chat(user_id):
    receiver = User.query.get_or_404(user_id)
    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            msg = Message(
                content=content, 
                sender_id=current_user.id, 
                receiver_id=user_id
            )
            db.session.add(msg)
            db.session.commit()
            flash('Mesajınız gönderildi!', 'success')
        else:
            flash('Mesaj içeriği boş olamaz!', 'danger')
        return redirect(url_for('chat', user_id=user_id))
    Message.query.filter_by(sender_id=user_id, receiver_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()
    return render_template_string(BASE_HEADER + '''
<div class="forum-container">
    <h2 class="mb-4"><i class="fas fa-comments me-2"></i>{{ receiver.username }} ile Mesajlaşma</h2>
    <div class="chat-messages">
        {% for message in messages %}
        <div class="message-bubble {% if message.sender_id == current_user.id %}message-sent{% else %}message-received{% endif %}">
            <div class="d-flex justify-content-between align-items-center mb-1">
                <a href="{{ url_for('user_profile', username=(current_user.username if message.sender_id == current_user.id else receiver.username)) }}" class="fw-bold">
                    {{ current_user.username if message.sender_id == current_user.id else receiver.username }}
                </a>
                <span class="text-muted small">{{ message.created_at.strftime('%d.%m.%Y %H:%M') }}</span>
            </div>
            <p class="mb-0">{{ message.content|replace('\n', '<br>')|safe }}</p>
        </div>
        {% endfor %}
    </div>
    <div class="mt-4">
        <h5 class="mb-3">Mesaj Gönder</h5>
        <form method="POST">
            <div class="mb-3">
                <textarea class="form-control" name="content" rows="3" placeholder="Mesajınızı yazın..." required></textarea>
            </div>
            <button type="submit" class="btn btn-primary">Gönder</button>
        </form>
    </div>
</div>
<script>
    document.addEventListener('DOMContentLoaded', function() {
        scrollChatToBottom();
    });
</script>
''' + BASE_FOOTER, title=f'Mesaj: {receiver.username} - MAHKEME Forum', receiver=receiver, messages=messages, current_user=current_user)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

