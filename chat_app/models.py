from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    bio = db.Column(db.String(500))
    avatar_url = db.Column(db.String(200))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('Message', 
                             backref='author', 
                             lazy=True,
                             foreign_keys='Message.user_id')
    stories = db.relationship('Story', backref='user', lazy=True)
    mentioned_in = db.relationship('Message', 
                                 backref='mentioned_users',
                                 lazy=True,
                                 foreign_keys='Message.mentions')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    reactions = db.Column(db.JSON, default={})
    mentions = db.Column(db.JSON, default=[])
    read = db.Column(db.Boolean, default=False)

class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200))
    messages = db.relationship('Message', backref='channel', lazy=True)

class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    expiration_time = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24))