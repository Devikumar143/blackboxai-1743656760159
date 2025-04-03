from flask import Flask, jsonify, request, make_response, render_template
from flask_socketio import SocketIO
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-dev-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

# Initialize extensions
from models import db
db.init_app(app)
jwt = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Import models and socket events
from models import User, Message, Channel, Story
from socket_events import *

# API Routes
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/api')
def api_info():
    return jsonify({
        "status": "Chat API is running",
        "endpoints": {
            "auth": "/api/auth/login",
            "register": "/api/auth/register",
            "channels": "/api/channels",
            "users": "/api/users"
        }
    })

@app.route('/mentions')
@jwt_required()
def mentions():
    current_user = User.query.get(get_jwt_identity())
    page = request.args.get('page', 1, type=int)
    filter_type = request.args.get('filter', 'all')
    sort_order = request.args.get('sort', 'newest')
    per_page = 10
    
    mentions_query = Message.query.filter(
        Message.mentions.contains([current_user.id])
    )
    
    if filter_type == 'unread':
        mentions_query = mentions_query.filter(Message.read == False)
    elif filter_type == 'read':
        mentions_query = mentions_query.filter(Message.read == True)
    
    if sort_order == 'oldest':
        mentions_query = mentions_query.order_by(Message.timestamp.asc())
    else:  # default to newest first
        mentions_query = mentions_query.order_by(Message.timestamp.desc())
    
    mentions = mentions_query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Mark mentions as read when viewing the page
    unread_mentions = [m for m in mentions if not m.read]
    for mention in unread_mentions:
        mention.read = True
    db.session.commit()
    
    return render_template('mentions.html', 
                         mentions=mentions,
                         unread_mentions=len(unread_mentions),
                         filter=filter_type,
                         sort=sort_order)

@app.route('/api/users/search')
@jwt_required()
def search_users():
    query = request.args.get('q', '')
    users = User.query.filter(User.username.ilike(f'%{query}%')).limit(5).all()
    return jsonify([{
        'id': user.id,
        'username': user.username,
        'avatar_url': user.avatar_url
    } for user in users])

@app.route('/profile')
@jwt_required()
def profile():
    current_user = User.query.get(get_jwt_identity())
    return render_template('profile.html', current_user=current_user)

@app.route('/api/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    current_user = User.query.get(get_jwt_identity())
    data = request.get_json()
    
    if 'avatar_url' in data:
        current_user.avatar_url = data['avatar_url']
    if 'bio' in data:
        current_user.bio = data['bio']
    
    db.session.commit()
    return jsonify({
        'message': 'Profile updated',
        'avatar_url': current_user.avatar_url,
        'bio': current_user.bio
    })

@app.route('/channels')
@jwt_required()
def channels_list():
    channels = Channel.query.all()
    return render_template('channels.html', channels=channels)

@app.route('/channels/<int:channel_id>')
@jwt_required()
def channel_detail(channel_id):
    channel = Channel.query.get_or_404(channel_id)
    return render_template('channels.html', 
                         channels=Channel.query.all(),
                         current_channel=channel)

@app.route('/api/channels', methods=['POST'])
@jwt_required()
def create_channel():
    data = request.get_json()
    channel = Channel(
        name=data['name'],
        description=data.get('description', '')
    )
    db.session.add(channel)
    db.session.commit()
    return jsonify({
        "id": channel.id,
        "name": channel.name,
        "description": channel.description
    }), 201

@app.route('/api/mentions/mark_all_read', methods=['POST'])
@jwt_required()
def mark_all_mentions_read():
    current_user = User.query.get(get_jwt_identity())
    page = request.args.get('page', None, type=int)
    
    filter_type = request.args.get('filter', None)
    query = Message.query.filter(
        Message.mentions.contains([current_user.id]),
        Message.read == False
    )
    
    if filter_type == 'unread':
        pass  # Already filtering for unread
    elif filter_type == 'read':
        query = query.filter(False)  # Shouldn't happen since button hidden
    
    if page:
        unread_mentions = query.paginate(page=page, per_page=10, error_out=False).items
    else:
        unread_mentions = query.all()
    
    for mention in unread_mentions:
        mention.read = True
    db.session.commit()
    
    return jsonify({
        "message": f"Marked {len(unread_mentions)} mentions as read",
        "count": len(unread_mentions)
    })

@app.route('/api/mentions/<int:message_id>/mark_unread', methods=['POST'])
@jwt_required()
def mark_mention_unread(message_id):
    current_user = User.query.get(get_jwt_identity())
    message = Message.query.filter(
        Message.id == message_id,
        Message.mentions.contains([current_user.id])
    ).first_or_404()
    
    message.read = False
    db.session.commit()
    
    return jsonify({
        "message": "Marked as unread",
        "id": message.id
    })

@app.route('/api/channels')
@jwt_required()
def get_channels():
    channels = Channel.query.all()
    return jsonify([{
        "id": channel.id,
        "name": channel.name,
        "description": channel.description
    } for channel in channels])

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already exists"}), 400
    
    user = User(
        username=data['username'],
        email=data['email']
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        "message": "User created successfully",
        "user": {
            "id": user.id,
            "username": user.username
        }
    })

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({"error": "Invalid credentials"}), 401
    
    access_token = create_access_token(identity=user.id)
    return jsonify({
        "access_token": access_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "avatar_url": user.avatar_url
        }
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)