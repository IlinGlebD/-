from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
from models import db, User, Message
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


# Создание администратора при первом запуске
def create_admin():
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()


create_admin()


@app.before_request
def make_session_permanent():
    session.permanent = True


# Декораторы для проверки прав доступа
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Требуются права администратора')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# Маршруты
@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.is_admin:
            return redirect(url_for('admin_panel'))
        return redirect(url_for('users_list'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким логином уже существует')
            return redirect(url_for('register'))

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Регистрация успешна! Теперь вы можете войти.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            flash('Вход выполнен успешно!')
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы')
    return redirect(url_for('index'))


@app.route('/users')
@login_required
def users_list():
    if session.get('is_admin'):
        return redirect(url_for('admin_panel'))

    users = User.query.filter(User.id != session['user_id']).all()
    return render_template('users.html', users=users)


@app.route('/chat/<int:user_id>')
@login_required
def chat(user_id):
    receiver = User.query.get_or_404(user_id)
    current_user_id = session['user_id']

    # Получаем сообщения между текущим пользователем и выбранным пользователем
    messages = Message.query.filter(
        ((Message.sender_id == current_user_id) & (Message.receiver_id == user_id) & 
         (Message.deleted_by_sender == False)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user_id) & 
         (Message.deleted_by_receiver == False))
    ).order_by(Message.timestamp.asc()).all()

    return render_template('chat.html', receiver=receiver, messages=messages)


@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    receiver_id = request.form['receiver_id']
    content = request.form['content']

    if content.strip():
        message = Message(
            sender_id=session['user_id'],
            receiver_id=receiver_id,
            content=content.strip()
        )
        db.session.add(message)
        db.session.commit()

    return redirect(url_for('chat', user_id=receiver_id))


@app.route('/delete_message/<int:message_id>')
@login_required
def delete_message(message_id):
    message = Message.query.get_or_404(message_id)
    current_user_id = session['user_id']

    if message.sender_id == current_user_id:
        message.deleted_by_sender = True
    elif message.receiver_id == current_user_id:
        message.deleted_by_receiver = True
    else:
        flash('У вас нет прав для удаления этого сообщения')
        return redirect(url_for('index'))

    # Если сообщение удалено обоими пользователями, удаляем его полностью
    if message.deleted_by_sender and message.deleted_by_receiver:
        db.session.delete(message)

    db.session.commit()
    flash('Сообщение удалено')

    # Определяем, с кем был чат для возврата
    if message.sender_id == current_user_id:
        return redirect(url_for('chat', user_id=message.receiver_id))
    else:
        return redirect(url_for('chat', user_id=message.sender_id))


@app.route('/admin')
@admin_required
def admin_panel():
    users = User.query.all()
    return render_template('admin.html', users=users)


@app.route('/admin/delete_user/<int:user_id>')
@admin_required
def delete_user(user_id):
    if user_id == session['user_id']:
        flash('Нельзя удалить собственный аккаунт')
        return redirect(url_for('admin_panel'))

    user = User.query.get_or_404(user_id)

    # Удаляем все сообщения пользователя
    Message.query.filter(
        (Message.sender_id == user_id) | (Message.receiver_id == user_id)
    ).delete()

    db.session.delete(user)
    db.session.commit()
    flash('Пользователь удален')
    return redirect(url_for('admin_panel'))


@app.route('/admin/edit_user/<int:user_id>', methods=['POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    new_username = request.form['username']

    if new_username and new_username != user.username:
        if User.query.filter_by(username=new_username).first():
            flash('Пользователь с таким логином уже существует')
        else:
            user.username = new_username
            db.session.commit()
            flash('Данные пользователя обновлены')

    return redirect(url_for('admin_panel'))
