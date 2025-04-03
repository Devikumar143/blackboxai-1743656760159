from flask_socketio import emit
from models import db, Message, Channel, User
from datetime import datetime
from app import socketio

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join_channel')
def handle_join_channel(data):
    channel_id = data['channel_id']
    emit('user_joined', {'channel_id': channel_id}, broadcast=True)

@socketio.on('send_message')
def handle_send_message(data):
    # Extract mentions from message content
    mentions = []
    words = data['content'].split()
    for word in words:
        if word.startswith('@'):
            username = word[1:]
            user = User.query.filter_by(username=username).first()
            if user:
                mentions.append(user.id)
    
    message = Message(
        content=data['content'],
        user_id=data['user_id'],
        channel_id=data.get('channel_id'),
        recipient_id=data.get('recipient_id'),
        timestamp=datetime.utcnow(),
        mentions=mentions
    )

    db.session.add(message)
    db.session.commit()

    # Notify mentioned users
    for user_id in mentions:
        emit('new_mention', {
            'message_id': message.id,
            'content': message.content,
            'author_id': message.user_id,
            'channel_id': message.channel_id,
            'timestamp': message.timestamp.isoformat()
        }, room=f'user_{user_id}')
    
    emit('new_message', {
        'id': message.id,
        'content': message.content,
        'user_id': message.user_id,
        'timestamp': message.timestamp.isoformat()
    }, broadcast=True)

@socketio.on('typing')
def handle_typing(data):
    emit('user_typing', {
        'user_id': data['user_id'],
        'channel_id': data.get('channel_id'),
        'recipient_id': data.get('recipient_id')
    }, broadcast=True)

@socketio.on('add_reaction')
def handle_add_reaction(data):
    message = Message.query.get(data['message_id'])
    if not message.reactions:
        message.reactions = {}
    
    emoji = data['emoji']
    if emoji not in message.reactions:
        message.reactions[emoji] = []
    
    user_id = int(data['user_id'])
    if user_id in message.reactions[emoji]:
        message.reactions[emoji].remove(user_id)
        if not message.reactions[emoji]:
            del message.reactions[emoji]
    else:
        message.reactions[emoji].append(user_id)
    
    db.session.commit()
    
    emit('reaction_added', {
        'message_id': message.id,
        'emoji': emoji,
        'count': len(message.reactions.get(emoji, [])),
        'user_id': user_id
    }, broadcast=True)
