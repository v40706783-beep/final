from flask import Flask, render_template, request, redirect, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from datetime import datetime
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from sqlalchemy import UniqueConstraint

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///main.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
csrf = CSRFProtect(app)
db = SQLAlchemy(app)
manager = LoginManager(app)
manager.login_view = 'login'

# Association table for CodeSnippet <-> Tag many-to-many
snippet_tags = db.Table('snippet_tags',
    db.Column('snippet_id', db.Integer, db.ForeignKey('code_snippet.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_banned = db.Column(db.Boolean, default=False)

    snippets = db.relationship('CodeSnippet', backref='author', lazy=True, foreign_keys='CodeSnippet.author_id')
    comments = db.relationship('Comment', backref='author', lazy=True, foreign_keys='Comment.author_id')

    def __repr__(self):
        return f'<User {self.username}>'


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    snippets = db.relationship('CodeSnippet', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    usage_count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<Tag {self.name}>'


class CodeSnippet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    code = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    views_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    rejection_reason = db.Column(db.Text)
    moderated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    moderated_at = db.Column(db.DateTime)
    likes_count = db.Column(db.Integer, default=0)
    dislikes_count = db.Column(db.Integer, default=0)
    reports_count = db.Column(db.Integer, default=0)
    report_moderation_status = db.Column(db.String(20), default='approved')  # approved, pending, rejected (для жалоб)
    report_moderated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    report_moderated_at = db.Column(db.DateTime)
    report_moderation_reason = db.Column(db.Text)
    resubmit_comment = db.Column(db.Text)  # Комментарий пользователя при повторной отправке
    is_edited = db.Column(db.Boolean, default=False)  # True если сниппет был отредактирован после публикации

    tags = db.relationship('Tag', secondary=snippet_tags, lazy='subquery',
                           backref=db.backref('snippets', lazy=True))
    comments = db.relationship('Comment', backref='snippet', lazy=True, foreign_keys='Comment.snippet_id', cascade='all, delete-orphan')
    views = db.relationship('SnippetView', backref='snippet', lazy=True, foreign_keys='SnippetView.snippet_id', cascade='all, delete-orphan')
    files = db.relationship('SnippetFile', backref='snippet', lazy=True, order_by='SnippetFile.order', cascade='all, delete-orphan')
    links = db.relationship('SnippetLink', backref='snippet', lazy=True, order_by='SnippetLink.order', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<CodeSnippet {self.title}>'


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    snippet_id = db.Column(db.Integer, db.ForeignKey('code_snippet.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    level = db.Column(db.Integer, default=0)
    is_deleted = db.Column(db.Boolean, default=False)
    likes_count = db.Column(db.Integer, default=0)
    dislikes_count = db.Column(db.Integer, default=0)
    reports_count = db.Column(db.Integer, default=0)
    moderation_status = db.Column(db.String(20), default='approved')  # approved, pending, rejected
    moderated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    moderated_at = db.Column(db.DateTime)
    moderation_reason = db.Column(db.Text)

    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy=True)

    def __repr__(self):
        return f'<Comment {self.id}>'


class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    snippet_id = db.Column(db.Integer, db.ForeignKey('code_snippet.id'))
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    is_like = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'snippet_id', name='unique_user_snippet_vote'),
        UniqueConstraint('user_id', 'comment_id', name='unique_user_comment_vote'),
    )


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    snippet_id = db.Column(db.Integer, db.ForeignKey('code_snippet.id'))
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    reason = db.Column(db.String(50))  # spam, inappropriate, dangerous (for snippets)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'snippet_id', name='unique_user_snippet_report'),
        UniqueConstraint('user_id', 'comment_id', name='unique_user_comment_report'),
    )


class SnippetView(db.Model):
    """Модель для отслеживания уникальных просмотров сниппетов"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # None для анонимных
    snippet_id = db.Column(db.Integer, db.ForeignKey('code_snippet.id'), nullable=False)
    ip_address = db.Column(db.String(45))  # Для анонимных пользователей
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Уникальные индексы для предотвращения дублирования
    # Для авторизованных пользователей проверяем только user_id + snippet_id
    # Для анонимных пользователей проверяем только ip_address + snippet_id (где user_id IS NULL)
    __table_args__ = (
        UniqueConstraint('user_id', 'snippet_id', name='unique_user_snippet_view'),
    )

    def __repr__(self):
        return f'<SnippetView user_id={self.user_id} snippet_id={self.snippet_id}>'


class SnippetFile(db.Model):
    """Модель для хранения файлов в сниппете"""
    id = db.Column(db.Integer, primary_key=True)
    snippet_id = db.Column(db.Integer, db.ForeignKey('code_snippet.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50))  # Язык программирования для подсветки
    order = db.Column(db.Integer, default=0)  # Порядок отображения
    file_type = db.Column(db.String(20), default='text')  # text, uploaded, link
    file_size = db.Column(db.Integer)  # Размер файла в байтах (для загруженных файлов)
    mime_type = db.Column(db.String(100))  # MIME тип файла
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SnippetFile {self.filename}>'


class SnippetLink(db.Model):
    """Модель для хранения ссылок на внешние проекты"""
    id = db.Column(db.Integer, primary_key=True)
    snippet_id = db.Column(db.Integer, db.ForeignKey('code_snippet.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    link_type = db.Column(db.String(50))  # github, gitlab, codepen, jsfiddle, other
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SnippetLink {self.title}>'


@manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.admin:
            flash('Требуются права администратора.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def init_categories():
    if Category.query.count() == 0:
        categories = [
            'Web', 'Python', 'JavaScript', 'Malware Analysis', 'Reverse Engineering',
            'Exploits', 'Algorithms', 'Data Structures', 'Other'
        ]
        for name in categories:
            db.session.add(Category(name=name))
        db.session.commit()


def recalculate_views():
    """Пересчитывает количество просмотров для всех сниппетов на основе уникальных записей"""
    snippets = CodeSnippet.query.all()
    for snippet in snippets:
        unique_views = SnippetView.query.filter_by(snippet_id=snippet.id).count()
        snippet.views_count = unique_views
    db.session.commit()
    print(f"Пересчитаны просмотры для {len(snippets)} сниппетов")


def record_unique_view(snippet_id, user_id=None, ip_address=None):
    """
    Записывает уникальный просмотр сниппета
    Возвращает True если просмотр был засчитан, False если уже существует
    """
    try:
        if user_id:
            # Для авторизованных пользователей проверяем только по user_id
            existing_view = SnippetView.query.filter_by(
                user_id=user_id, 
                snippet_id=snippet_id
            ).first()
            
            if not existing_view:
                new_view = SnippetView(
                    user_id=user_id,
                    snippet_id=snippet_id,
                    ip_address=ip_address
                )
                db.session.add(new_view)
                return True
        else:
            # Для анонимных пользователей проверяем по IP
            if ip_address:
                existing_view = SnippetView.query.filter_by(
                    ip_address=ip_address,
                    snippet_id=snippet_id,
                    user_id=None
                ).first()
                
                if not existing_view:
                    new_view = SnippetView(
                        user_id=None,
                        snippet_id=snippet_id,
                        ip_address=ip_address
                    )
                    db.session.add(new_view)
                    return True
        
        return False
        
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при записи просмотра: {e}")
        return False


@app.route('/')
def index():
    init_categories()
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '')
    category_id = request.args.get('category', type=int)
    sort = request.args.get('sort', 'newest')

    query = CodeSnippet.query.filter_by(status='approved')
    if search:
        query = query.filter(
            db.or_(
                CodeSnippet.title.contains(search),
                CodeSnippet.description.contains(search)
            )
        )
    if category_id:
        query = query.filter_by(category_id=category_id)

    if sort == 'liked':
        query = query.order_by(CodeSnippet.likes_count.desc())
    elif sort == 'viewed':
        query = query.order_by(CodeSnippet.views_count.desc())
    else:
        query = query.order_by(CodeSnippet.created_at.desc())

    snippets = query.paginate(page=page, per_page=10)
    categories = Category.query.all()
    return render_template('index.html', snippets=snippets, categories=categories, search=search, sort=sort)


@app.route('/hot')
def hot():
    from datetime import timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    snippets = CodeSnippet.query.filter(
        CodeSnippet.status == 'approved',
        CodeSnippet.created_at >= week_ago
    ).order_by(CodeSnippet.likes_count.desc()).limit(20).all()
    return render_template('hot.html', snippets=snippets)


@app.route('/upload-file', methods=['POST'])
@login_required
def upload_file():
    """Загрузка файла через AJAX"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не выбран'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    # Проверяем размер файла (максимум 1MB)
    if len(file.read()) > 1024 * 1024:
        return jsonify({'error': 'Файл слишком большой (максимум 1MB)'}), 400
    
    file.seek(0)  # Возвращаемся к началу файла
    
    # Проверяем расширение файла
    allowed_extensions = {
        'txt', 'py', 'js', 'html', 'css', 'java', 'cpp', 'c', 'h', 'php', 
        'rb', 'go', 'rs', 'ts', 'jsx', 'tsx', 'vue', 'sql', 'sh', 'bat',
        'json', 'xml', 'yaml', 'yml', 'md', 'rst', 'ini', 'cfg', 'conf'
    }
    
    filename = file.filename.lower()
    if not any(filename.endswith('.' + ext) for ext in allowed_extensions):
        return jsonify({'error': 'Неподдерживаемый тип файла'}), 400
    
    try:
        # Читаем содержимое файла
        content = file.read().decode('utf-8')
        
        # Определяем язык программирования по расширению
        language_map = {
            'py': 'python', 'js': 'javascript', 'ts': 'typescript',
            'html': 'html', 'css': 'css', 'java': 'java',
            'cpp': 'cpp', 'c': 'cpp', 'h': 'cpp',
            'php': 'php', 'rb': 'ruby', 'go': 'go',
            'rs': 'rust', 'jsx': 'javascript', 'tsx': 'typescript',
            'vue': 'javascript', 'sql': 'sql', 'sh': 'bash',
            'bat': 'batch', 'json': 'json', 'xml': 'xml',
            'yaml': 'yaml', 'yml': 'yaml', 'md': 'markdown'
        }
        
        extension = filename.split('.')[-1]
        language = language_map.get(extension, 'other')
        
        return jsonify({
            'filename': file.filename,
            'content': content,
            'language': language,
            'file_type': 'uploaded',
            'file_size': len(content),
            'mime_type': file.content_type or 'text/plain'
        })
        
    except UnicodeDecodeError:
        return jsonify({'error': 'Файл должен быть в кодировке UTF-8'}), 400
    except Exception as e:
        return jsonify({'error': f'Ошибка при чтении файла: {str(e)}'}), 500


@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_snippet():
    if current_user.is_banned:
        flash('Ваш аккаунт заблокирован.', 'danger')
        return redirect(url_for('index'))

    init_categories()
    categories = Category.query.all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        code = request.form.get('code', '').strip()
        category_id = request.form.get('category_id', type=int)
        tag_names = [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()][:10]
        
        # Получаем данные о файлах из JSON
        import json
        files_data = request.form.get('files_data', '[]')
        links_data = request.form.get('links_data', '[]')
        
        try:
            files_list = json.loads(files_data)
            links_list = json.loads(links_data)
        except Exception as e:
            files_list = []
            links_list = []

        if not title:
            flash('Название обязательно.', 'danger')
            return render_template('create.html', categories=categories)

        if not category_id:
            flash('Выберите категорию.', 'danger')
            return render_template('create.html', categories=categories)

        # Проверяем, есть ли хотя бы один файл, код или ссылка
        if not code and not files_list and not links_list:
            flash('Добавьте хотя бы один файл с кодом или ссылку на проект.', 'danger')
            return render_template('create.html', categories=categories)

        if len(files_list) > 20:
            flash('Максимум 20 файлов. Для больших проектов используйте ссылку на GitHub/GitLab.', 'danger')
            return render_template('create.html', categories=categories)

        snippet = CodeSnippet(
            title=title,
            description=description,
            code=code,  # Оставляем для обратной совместимости
            category_id=category_id,
            author_id=current_user.id,
            status='pending'
        )

        for name in tag_names:
            tag = Tag.query.filter_by(name=name).first()
            if not tag:
                tag = Tag(name=name)
                db.session.add(tag)
                db.session.flush()
            tag.usage_count += 1
            snippet.tags.append(tag)

        db.session.add(snippet)
        db.session.flush()  # Получаем ID сниппета
        
        # Добавляем файлы
        for idx, file_data in enumerate(files_list):
            if file_data.get('filename') and file_data.get('content'):
                snippet_file = SnippetFile(
                    snippet_id=snippet.id,
                    filename=file_data['filename'],
                    content=file_data['content'],
                    language=file_data.get('language', ''),
                    file_type=file_data.get('file_type', 'text'),
                    file_size=file_data.get('file_size', len(file_data['content'])),
                    mime_type=file_data.get('mime_type', 'text/plain'),
                    order=idx
                )
                db.session.add(snippet_file)

        # Добавляем ссылки
        for idx, link_data in enumerate(links_list):
            if link_data.get('title') and link_data.get('url'):
                snippet_link = SnippetLink(
                    snippet_id=snippet.id,
                    title=link_data['title'],
                    url=link_data['url'],
                    description=link_data.get('description', ''),
                    link_type=link_data.get('link_type', 'other'),
                    order=idx
                )
                db.session.add(snippet_link)

        db.session.commit()
        flash('Ваш сниппет отправлен на модерацию.', 'success')
        return redirect(url_for('snippet', id=snippet.id))

    return render_template('create.html', categories=categories)


@app.route('/post/<int:id>')
def snippet(id):
    snippet = CodeSnippet.query.get_or_404(id)
    if snippet.status != 'approved' and (not current_user.is_authenticated or (current_user.id != snippet.author_id and not current_user.admin)):
        flash('Этот сниппет недоступен.', 'danger')
        return redirect(url_for('index'))

    # Система уникальных просмотров
    user_id = current_user.id if current_user.is_authenticated else None
    ip_address = request.environ.get('REMOTE_ADDR')
    
    view_counted = record_unique_view(snippet.id, user_id, ip_address)
    
    if view_counted:
        snippet.views_count += 1
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при обновлении счетчика просмотров: {e}")

    comments = Comment.query.filter_by(snippet_id=id, parent_id=None).order_by(Comment.created_at).all()

    def get_user_vote(obj_type, obj_id):
        if not current_user.is_authenticated:
            return None
        if obj_type == 'snippet':
            v = Vote.query.filter_by(user_id=current_user.id, snippet_id=obj_id).first()
        else:
            v = Vote.query.filter_by(user_id=current_user.id, comment_id=obj_id).first()
        return v.is_like if v else None

    user_snippet_vote = get_user_vote('snippet', id) if current_user.is_authenticated else None
    return render_template('snippet.html', snippet=snippet, comments=comments, user_snippet_vote=user_snippet_vote)


@app.route('/post/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_snippet(id):
    try:
        snippet = CodeSnippet.query.get_or_404(id)
        if snippet.author_id != current_user.id:
            flash('Доступ запрещён. Только автор может редактировать сниппет.', 'danger')
            return redirect(url_for('snippet', id=id))

        init_categories()
        categories = Category.query.all()
        
        # Преобразуем файлы и ссылки в словари для JSON сериализации
        files_data = []
        for file in snippet.files:
            files_data.append({
                'id': file.id,
                'filename': file.filename,
                'content': file.content,
                'language': file.language or '',
                'file_type': file.file_type or 'text',
                'file_size': file.file_size or len(file.content),
                'mime_type': file.mime_type or 'text/plain'
            })
        
        links_data = []
        for link in snippet.links:
            links_data.append({
                'id': link.id,
                'title': link.title,
                'url': link.url,
                'description': link.description or '',
                'link_type': link.link_type or 'other'
            })
        
        # Создаем копию сниппета с преобразованными данными
        snippet.files_json = files_data
        snippet.links_json = links_data
        
    except Exception as e:
        print(f"ERROR in edit_snippet GET: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Ошибка при загрузке страницы редактирования: {str(e)}', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        new_title = request.form.get('title', '').strip()
        new_description = request.form.get('description', '').strip()
        new_code = request.form.get('code', '').strip()
        category_id = request.form.get('category_id', type=int)
        tag_names = [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()][:10]
        resubmit_comment = request.form.get('resubmit_comment', '').strip()
        
        import json
        files_data = request.form.get('files_data', '[]')
        links_data = request.form.get('links_data', '[]')
        try:
            files_list = json.loads(files_data)
            links_list = json.loads(links_data)
        except:
            files_list = []
            links_list = []

        if not new_title:
            flash('Название обязательно.', 'danger')
            return render_template('edit_snippet.html', snippet=snippet, categories=categories)

        if not new_code and not files_list and not links_list:
            flash('Добавьте хотя бы один файл с кодом или ссылку на проект.', 'danger')
            return render_template('edit_snippet.html', snippet=snippet, categories=categories)

        if len(files_list) > 20:
            flash('Максимум 20 файлов. Для больших проектов используйте ссылку на GitHub/GitLab.', 'danger')
            return render_template('edit_snippet.html', snippet=snippet, categories=categories)

        # Проверяем, изменилось ли что-то
        old_tag_names = sorted([t.name for t in snippet.tags])
        new_tag_names = sorted(tag_names)

        old_files = sorted(
            [{'filename': f.filename, 'content': f.content, 'language': f.language or ''} for f in snippet.files],
            key=lambda x: x['filename']
        )
        new_files = sorted(
            [{'filename': f.get('filename',''), 'content': f.get('content',''), 'language': f.get('language','')} for f in files_list if f.get('filename') and f.get('content')],
            key=lambda x: x['filename']
        )

        old_links = sorted(
            [{'title': l.title, 'url': l.url} for l in snippet.links],
            key=lambda x: x['url']
        )
        new_links = sorted(
            [{'title': l.get('title',''), 'url': l.get('url','')} for l in links_list if l.get('title') and l.get('url')],
            key=lambda x: x['url']
        )

        nothing_changed = (
            new_title == snippet.title and
            new_description == (snippet.description or '') and
            new_code == (snippet.code or '') and
            (category_id == snippet.category_id or not category_id) and
            old_tag_names == new_tag_names and
            old_files == new_files and
            old_links == new_links
        )

        if nothing_changed:
            flash('Вы не внесли никаких изменений.', 'warning')
            return render_template('edit_snippet.html', snippet=snippet, categories=categories)

        # Применяем изменения
        snippet.title = new_title
        snippet.description = new_description
        snippet.code = new_code
        if category_id:
            snippet.category_id = category_id

        try:
            # Обновляем теги
            for tag in list(snippet.tags):
                tag.usage_count -= 1
                if tag.usage_count <= 0:
                    db.session.delete(tag)
                snippet.tags.remove(tag)

            for name in tag_names:
                tag = Tag.query.filter_by(name=name).first()
                if not tag:
                    tag = Tag(name=name)
                    db.session.add(tag)
                    db.session.flush()
                tag.usage_count += 1
                snippet.tags.append(tag)

            # Удаляем старые файлы и ссылки
            SnippetFile.query.filter_by(snippet_id=snippet.id).delete()
            SnippetLink.query.filter_by(snippet_id=snippet.id).delete()
            
            # Добавляем новые файлы
            for idx, file_data in enumerate(files_list):
                if file_data.get('filename') and file_data.get('content'):
                    snippet_file = SnippetFile(
                        snippet_id=snippet.id,
                        filename=file_data['filename'],
                        content=file_data['content'],
                        language=file_data.get('language', ''),
                        file_type=file_data.get('file_type', 'text'),
                        file_size=file_data.get('file_size', len(file_data['content'])),
                        mime_type=file_data.get('mime_type', 'text/plain'),
                        order=idx
                    )
                    db.session.add(snippet_file)

            # Добавляем новые ссылки
            for idx, link_data in enumerate(links_list):
                if link_data.get('title') and link_data.get('url'):
                    snippet_link = SnippetLink(
                        snippet_id=snippet.id,
                        title=link_data['title'],
                        url=link_data['url'],
                        description=link_data.get('description', ''),
                        link_type=link_data.get('link_type', 'other'),
                        order=idx
                    )
                    db.session.add(snippet_link)

            # После редактирования всегда отправляем на модерацию
            if snippet.status == 'rejected' and resubmit_comment:
                snippet.resubmit_comment = resubmit_comment
            elif snippet.status == 'approved':
                snippet.resubmit_comment = None

            was_approved = snippet.status == 'approved'
            snippet.is_edited = was_approved  # помечаем как отредактированный только если был опубликован
            snippet.status = 'pending'
            snippet.moderated_by = None
            snippet.moderated_at = None
            flash('Сниппет обновлён и отправлен на модерацию.', 'success')

            db.session.commit()
            return redirect(url_for('snippet', id=id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении сниппета: {str(e)}', 'danger')
            return render_template('edit_snippet.html', snippet=snippet, categories=categories)

    try:
        return render_template('edit_snippet.html', snippet=snippet, categories=categories)
    except Exception as e:
        print(f"ERROR rendering edit template: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Ошибка при отображении формы редактирования: {str(e)}', 'danger')
        return redirect(url_for('snippet', id=id))


@app.route('/post/<int:id>/delete', methods=['POST'])
@login_required
def delete_snippet(id):
    try:
        snippet = CodeSnippet.query.get_or_404(id)
        if snippet.author_id != current_user.id and not current_user.admin:
            flash('Доступ запрещён.', 'danger')
            return redirect(url_for('index'))

        try:
            # Удаляем все связанные данные в правильном порядке
            
            # 1. Удаляем просмотры
            SnippetView.query.filter_by(snippet_id=snippet.id).delete()
            
            # 2. Удаляем голоса
            Vote.query.filter_by(snippet_id=snippet.id).delete()
            
            # 3. Удаляем жалобы
            Report.query.filter_by(snippet_id=snippet.id).delete()
            
            # 4. Удаляем комментарии (и их голоса/жалобы)
            comments = Comment.query.filter_by(snippet_id=snippet.id).all()
            for comment in comments:
                Vote.query.filter_by(comment_id=comment.id).delete()
                Report.query.filter_by(comment_id=comment.id).delete()
                db.session.delete(comment)
            
            # 5. Удаляем файлы и ссылки (должны удаляться автоматически через cascade, но делаем явно)
            SnippetFile.query.filter_by(snippet_id=snippet.id).delete()
            SnippetLink.query.filter_by(snippet_id=snippet.id).delete()
            
            # 6. Обновляем счетчики тегов
            for tag in list(snippet.tags):
                tag.usage_count -= 1
                if tag.usage_count <= 0:
                    db.session.delete(tag)

            # 7. Удаляем сам сниппет
            db.session.delete(snippet)
            db.session.commit()
            flash('Сниппет удалён.', 'success')
        except Exception as e:
            db.session.rollback()
            print(f"ERROR deleting snippet: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Ошибка при удалении сниппета: {str(e)}', 'danger')
            return redirect(url_for('snippet', id=id))
        
        return redirect(url_for('index'))
    except Exception as e:
        print(f"ERROR in delete_snippet: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Ошибка: {str(e)}', 'danger')
        return redirect(url_for('index'))


@app.route('/post/<int:id>/vote', methods=['POST'])
@login_required
def vote_snippet(id):
    snippet = CodeSnippet.query.get_or_404(id)
    if snippet.status != 'approved':
        return jsonify({'error': 'Not found'}), 404

    is_like = request.json.get('is_like') if request.is_json else (request.form.get('is_like') == 'true')
    vote = Vote.query.filter_by(user_id=current_user.id, snippet_id=id).first()

    if vote:
        if vote.is_like == is_like:
            db.session.delete(vote)
            if is_like:
                snippet.likes_count -= 1
            else:
                snippet.dislikes_count -= 1
        else:
            if vote.is_like:
                snippet.likes_count -= 1
                snippet.dislikes_count += 1
            else:
                snippet.dislikes_count -= 1
                snippet.likes_count += 1
            vote.is_like = is_like
    else:
        vote = Vote(user_id=current_user.id, snippet_id=id, is_like=is_like)
        db.session.add(vote)
        if is_like:
            snippet.likes_count += 1
        else:
            snippet.dislikes_count += 1

    db.session.commit()
    return jsonify({'likes': snippet.likes_count, 'dislikes': snippet.dislikes_count})


@app.route('/comment/<int:id>/vote', methods=['POST'])
@login_required
def vote_comment(id):
    try:
        comment = Comment.query.get_or_404(id)
        is_like = request.json.get('is_like') if request.is_json else (request.form.get('is_like') == 'true')
        vote = Vote.query.filter_by(user_id=current_user.id, comment_id=id).first()

        if vote:
            if vote.is_like == is_like:
                db.session.delete(vote)
                if is_like:
                    comment.likes_count -= 1
                else:
                    comment.dislikes_count -= 1
            else:
                if vote.is_like:
                    comment.likes_count -= 1
                    comment.dislikes_count += 1
                else:
                    comment.dislikes_count -= 1
                    comment.likes_count += 1
                vote.is_like = is_like
        else:
            vote = Vote(user_id=current_user.id, comment_id=id, is_like=is_like)
            db.session.add(vote)
            if is_like:
                comment.likes_count += 1
            else:
                comment.dislikes_count += 1

        db.session.commit()
        return jsonify({
            'likes': comment.likes_count, 
            'dislikes': comment.dislikes_count,
            'success': True
        })
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка голосования за комментарий {id}: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@app.route('/post/<int:id>/comment', methods=['POST'])
@login_required
def add_comment(id):
    if current_user.is_banned:
        flash('Ваш аккаунт заблокирован.', 'danger')
        return redirect(url_for('snippet', id=id))

    snippet = CodeSnippet.query.get_or_404(id)
    content = request.form.get('content', '').strip()
    parent_id = request.form.get('parent_id', type=int)

    if not content:
        flash('Комментарий не может быть пустым.', 'danger')
        return redirect(url_for('snippet', id=id))

    level = 0
    if parent_id:
        parent = Comment.query.get(parent_id)
        if parent and parent.snippet_id == id:
            level = parent.level + 1

    comment = Comment(
        content=content,
        author_id=current_user.id,
        snippet_id=id,
        parent_id=parent_id or None,
        level=level
    )
    db.session.add(comment)
    db.session.commit()
    flash('Комментарий добавлен.', 'success')
    return redirect(url_for('snippet', id=id) + f'#comment-{comment.id}')


@app.route('/comment/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_comment(id):
    comment = Comment.query.get_or_404(id)
    if comment.author_id != current_user.id:
        flash('Доступ запрещён.', 'danger')
        return redirect(url_for('snippet', id=comment.snippet_id))

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            comment.content = content
            db.session.commit()
            flash('Комментарий обновлён.', 'success')
        return redirect(url_for('snippet', id=comment.snippet_id) + f'#comment-{comment.id}')

    return render_template('edit_comment.html', comment=comment)


@app.route('/comment/<int:id>/delete', methods=['POST'])
@login_required
def delete_comment(id):
    comment = Comment.query.get_or_404(id)
    if comment.author_id != current_user.id and not current_user.admin:
        flash('Доступ запрещён. Только автор может удалить комментарий.', 'danger')
        return redirect(url_for('snippet', id=comment.snippet_id))

    snippet_id = comment.snippet_id
    
    # Проверяем, есть ли ответы на этот комментарий
    replies = Comment.query.filter_by(parent_id=comment.id).count()
    
    if replies > 0:
        # Если есть ответы, помечаем как удаленный, но не удаляем физически
        comment.is_deleted = True
        comment.content = "[Комментарий удален автором]"
        db.session.commit()
        flash('Комментарий помечен как удаленный.', 'info')
    else:
        # Если нет ответов, удаляем физически
        db.session.delete(comment)
        db.session.commit()
        flash('Комментарий удален.', 'success')
    
    return redirect(url_for('snippet', id=snippet_id))


@app.route('/post/<int:id>/report', methods=['POST'])
@login_required
def report_snippet(id):
    snippet = CodeSnippet.query.get_or_404(id)
    reason = request.form.get('reason', 'other')
    if reason not in ('spam', 'inappropriate', 'dangerous', 'other'):
        reason = 'other'

    existing = Report.query.filter_by(user_id=current_user.id, snippet_id=id).first()
    if existing:
        flash('Вы уже жаловались на этот сниппет.', 'warning')
    else:
        report = Report(user_id=current_user.id, snippet_id=id, reason=reason)
        db.session.add(report)
        snippet.reports_count += 1
        
        # Если накопилось 15 жалоб, отправляем на модерацию
        if snippet.reports_count >= 15 and snippet.report_moderation_status == 'approved':
            snippet.report_moderation_status = 'pending'
            flash('Сниппет отправлен на модерацию из-за множественных жалоб.', 'info')
        else:
            flash('Спасибо за жалобу.', 'success')
            
        db.session.commit()
    return redirect(url_for('snippet', id=id))


@app.route('/comment/<int:id>/report', methods=['POST'])
@login_required
def report_comment(id):
    comment = Comment.query.get_or_404(id)
    existing = Report.query.filter_by(user_id=current_user.id, comment_id=id).first()
    if existing:
        flash('Вы уже жаловались на этот комментарий.', 'warning')
    else:
        report = Report(user_id=current_user.id, comment_id=id)
        db.session.add(report)
        comment.reports_count += 1
        
        # Если накопилось 15 жалоб, отправляем на модерацию
        if comment.reports_count >= 15 and comment.moderation_status == 'approved':
            comment.moderation_status = 'pending'
            flash('Комментарий отправлен на модерацию из-за множественных жалоб.', 'info')
        else:
            flash('Спасибо за жалобу.', 'success')
            
        db.session.commit()
    return redirect(url_for('snippet', id=comment.snippet_id) + f'#comment-{id}')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        if not username or len(username) < 3:
            flash('Имя пользователя должно быть не менее 3 символов.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Это имя пользователя уже занято.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Пароль должен быть не менее 6 символов.', 'danger')
            return render_template('register.html')

        if password != password2:
            flash('Пароли не совпадают.', 'danger')
            return render_template('register.html')

        user = User(
            username=username,
            password=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Аккаунт создан. Добро пожаловать!', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('Неверное имя пользователя или пароль.', 'danger')
            return render_template('login.html')

        if user.is_banned:
            flash('Ваш аккаунт заблокирован.', 'danger')
            return render_template('login.html')

        if check_password_hash(user.password, password):
            login_user(user)
            flash('С возвращением!', 'success')
            next_page = request.args.get('next') or url_for('index')
            return redirect(next_page)

        flash('Неверное имя пользователя или пароль.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    flash('Вы вышли из аккаунта.', 'info')
    return redirect(url_for('index'))


@app.route('/profile/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    snippets = CodeSnippet.query.filter_by(author_id=user.id, status='approved').order_by(CodeSnippet.created_at.desc()).all()
    return render_template('profile.html', profile_user=user, snippets=snippets)


@app.route('/my-snippets')
@login_required
def my_snippets():
    snippets = CodeSnippet.query.filter_by(author_id=current_user.id).order_by(CodeSnippet.created_at.desc()).all()
    return render_template('my_snippets.html', snippets=snippets)


@app.route('/admin/moderate', methods=['GET', 'POST'])
@login_required
@admin_required
def moderate():
    if request.method == 'POST':
        action_type = request.form.get('action_type')  # snippet, comment, report_snippet, report_comment
        item_id = request.form.get('item_id', type=int)
        action = request.form.get('action')  # approve, reject
        reason = request.form.get('rejection_reason', '').strip()

        if action_type == 'snippet':
            snippet = CodeSnippet.query.get(item_id)
            if snippet and snippet.status == 'pending':
                if action == 'approve':
                    snippet.status = 'approved'
                    snippet.rejection_reason = None
                elif action == 'reject':
                    snippet.status = 'rejected'
                    snippet.rejection_reason = reason or 'No reason provided.'
                snippet.resubmit_comment = None
                snippet.is_edited = False
                snippet.moderated_by = current_user.id
                snippet.moderated_at = datetime.utcnow()
                db.session.commit()
                flash('Действие модерации применено к сниппету.', 'success')
                
        elif action_type == 'report_snippet':
            snippet = CodeSnippet.query.get(item_id)
            if snippet and snippet.report_moderation_status == 'pending':
                if action == 'approve':
                    snippet.report_moderation_status = 'approved'
                    snippet.report_moderation_reason = None
                elif action == 'reject':
                    snippet.report_moderation_status = 'rejected'
                    snippet.report_moderation_reason = reason or 'Жалобы признаны обоснованными.'
                    # Можно дополнительно скрыть сниппет или изменить его статус
                snippet.report_moderated_by = current_user.id
                snippet.report_moderated_at = datetime.utcnow()
                db.session.commit()
                flash('Жалоба на сниппет рассмотрена.', 'success')
                
        elif action_type == 'report_comment':
            comment = Comment.query.get(item_id)
            if comment and comment.moderation_status == 'pending':
                if action == 'approve':
                    comment.moderation_status = 'approved'
                    comment.moderation_reason = None
                elif action == 'reject':
                    comment.moderation_status = 'rejected'
                    comment.moderation_reason = reason or 'Жалобы признаны обоснованными.'
                    comment.is_deleted = True  # Скрываем комментарий
                comment.moderated_by = current_user.id
                comment.moderated_at = datetime.utcnow()
                db.session.commit()
                flash('Жалоба на комментарий рассмотрена.', 'success')

    # Получаем все элементы для модерации
    pending_snippets = CodeSnippet.query.filter_by(status='pending').order_by(CodeSnippet.created_at).all()
    reported_snippets = CodeSnippet.query.filter_by(report_moderation_status='pending').order_by(CodeSnippet.reports_count.desc()).all()
    reported_comments = Comment.query.filter_by(moderation_status='pending').order_by(Comment.reports_count.desc()).all()
    
    return render_template('moderate.html', 
                         pending_snippets=pending_snippets,
                         reported_snippets=reported_snippets,
                         reported_comments=reported_comments)


@app.route('/snippet/<int:snippet_id>/file/<int:file_id>/download')
def download_public_file(snippet_id, file_id):
    """Публичное скачивание файла сниппета"""
    snippet = CodeSnippet.query.get_or_404(snippet_id)
    
    # Проверяем, что сниппет одобрен или пользователь - автор
    if snippet.status != 'approved' and (not current_user.is_authenticated or current_user.id != snippet.author_id):
        flash('Этот сниппет недоступен.', 'danger')
        return redirect(url_for('index'))
    
    file = SnippetFile.query.filter_by(id=file_id, snippet_id=snippet_id).first_or_404()
    
    from flask import Response
    import mimetypes
    
    # Определяем MIME-тип на основе расширения файла
    mime_type, _ = mimetypes.guess_type(file.filename)
    if not mime_type:
        mime_type = 'text/plain'
    
    response = Response(
        file.content,
        mimetype=mime_type,
        headers={
            'Content-Disposition': f'attachment; filename="{file.filename}"',
            'Content-Type': mime_type
        }
    )
    
    return response


@app.route('/snippet/<int:snippet_id>/files/download-all')
def download_all_public_files(snippet_id):
    """Публичное скачивание всех файлов сниппета как ZIP архива"""
    snippet = CodeSnippet.query.get_or_404(snippet_id)
    
    # Проверяем, что сниппет одобрен или пользователь - автор
    if snippet.status != 'approved' and (not current_user.is_authenticated or current_user.id != snippet.author_id):
        flash('Этот сниппет недоступен.', 'danger')
        return redirect(url_for('index'))
    
    if not snippet.files:
        flash('У этого сниппета нет файлов для скачивания.', 'warning')
        return redirect(url_for('snippet', id=snippet_id))
    
    import zipfile
    import io
    from flask import Response
    
    # Создаем ZIP архив в памяти
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file in snippet.files:
            # Добавляем файл в архив
            zip_file.writestr(file.filename, file.content.encode('utf-8'))
    
    zip_buffer.seek(0)
    
    # Создаем безопасное имя для архива
    safe_title = ''.join(c for c in snippet.title if c.isalnum() or c in (' ', '-', '_')).strip()
    archive_name = f"snippet_{snippet.id}_{safe_title}.zip"
    
    response = Response(
        zip_buffer.getvalue(),
        mimetype='application/zip',
        headers={
            'Content-Disposition': f'attachment; filename="{archive_name}"'
        }
    )
    
    return response


@app.route('/admin/snippet/<int:snippet_id>/file/<int:file_id>/download')
@login_required
@admin_required
def download_snippet_file(snippet_id, file_id):
    """Скачивание файла сниппета для модерации"""
    snippet = CodeSnippet.query.get_or_404(snippet_id)
    file = SnippetFile.query.filter_by(id=file_id, snippet_id=snippet_id).first_or_404()
    
    from flask import Response
    
    # Определяем MIME-тип на основе расширения файла
    import mimetypes
    mime_type, _ = mimetypes.guess_type(file.filename)
    if not mime_type:
        mime_type = 'text/plain'
    
    response = Response(
        file.content,
        mimetype=mime_type,
        headers={
            'Content-Disposition': f'attachment; filename="{file.filename}"',
            'Content-Type': mime_type
        }
    )
    
    return response


@app.route('/admin/snippet/<int:snippet_id>/files/download-all')
@login_required
@admin_required
def download_all_snippet_files(snippet_id):
    """Скачивание всех файлов сниппета как ZIP архива"""
    snippet = CodeSnippet.query.get_or_404(snippet_id)
    
    if not snippet.files:
        flash('У этого сниппета нет файлов для скачивания.', 'warning')
        return redirect(url_for('moderate'))
    
    import zipfile
    import io
    from flask import Response
    
    # Создаем ZIP архив в памяти
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file in snippet.files:
            # Добавляем файл в архив
            zip_file.writestr(file.filename, file.content.encode('utf-8'))
    
    zip_buffer.seek(0)
    
    # Создаем безопасное имя для архива
    safe_title = ''.join(c for c in snippet.title if c.isalnum() or c in (' ', '-', '_')).strip()
    archive_name = f"snippet_{snippet.id}_{safe_title}.zip"
    
    response = Response(
        zip_buffer.getvalue(),
        mimetype='application/zip',
        headers={
            'Content-Disposition': f'attachment; filename="{archive_name}"'
        }
    )
    
    return response


@app.route('/admin/snippet/<int:snippet_id>/preview')
@login_required
@admin_required
def preview_snippet_files(snippet_id):
    """Предпросмотр файлов сниппета для модерации"""
    snippet = CodeSnippet.query.get_or_404(snippet_id)
    return render_template('admin_snippet_preview.html', snippet=snippet)


@app.route('/admin/stats')
@login_required
@admin_required
def admin_stats():
    """Статистика просмотров для администраторов"""
    # Топ сниппетов по просмотрам
    top_snippets = CodeSnippet.query.filter_by(status='approved').order_by(
        CodeSnippet.views_count.desc()
    ).limit(10).all()
    
    # Общая статистика
    total_snippets = CodeSnippet.query.filter_by(status='approved').count()
    total_views = db.session.query(db.func.sum(CodeSnippet.views_count)).filter_by(status='approved').scalar() or 0
    total_unique_views = SnippetView.query.count()
    
    # Статистика по пользователям (топ активных просмотрщиков)
    user_views = db.session.query(
        User.username,
        db.func.count(SnippetView.id).label('view_count')
    ).join(SnippetView, User.id == SnippetView.user_id).group_by(User.id).order_by(
        db.func.count(SnippetView.id).desc()
    ).limit(10).all()
    
    return render_template('admin_stats.html', 
                         top_snippets=top_snippets,
                         total_snippets=total_snippets,
                         total_views=total_views,
                         total_unique_views=total_unique_views,
                         user_views=user_views)

BASE_URL = "http://127.0.0.1:5000"
# --- Public API ---

@app.route('/api/snippets')
def api_snippets():
    page = request.args.get('page', 1, type=int)
    snippets = CodeSnippet.query.filter_by(status='approved') \
        .order_by(CodeSnippet.created_at.desc()) \
        .paginate(page=page, per_page=20, error_out=False)
    return jsonify([{
        'id': s.id,
        'title': s.title,
        'author': s.author.username,
        'category': s.category.name,
        'tags': [t.name for t in s.tags],
        'views': s.views_count,
        'likes': s.likes_count,
        'created_at': s.created_at.isoformat(),
    } for s in snippets.items])

@app.route('/tag/<name>')
def by_tag(name):
    tag = Tag.query.filter_by(name=name).first_or_404()
    page = request.args.get('page', 1, type=int)
    snippets = CodeSnippet.query.filter(
        CodeSnippet.status == 'approved',
        CodeSnippet.tags.any(Tag.name == name)
    ).order_by(CodeSnippet.created_at.desc()).paginate(page=page, per_page=10)
    return render_template('by_tag.html', tag=tag, snippets=snippets)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        init_categories()
    app.run(debug=True)
