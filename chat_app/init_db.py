from app import app
from models import db, User, Channel, Message, Story

def init_db():
    with app.app_context():
        # Create all database tables
        db.create_all()
        
        # Add some test data if needed
        if not User.query.first():
            admin = User(username='admin', email='admin@chat.com')
            admin.set_password('admin123')
            db.session.add(admin)
            
            general = Channel(name='general', description='General discussions')
            db.session.add(general)
            
            db.session.commit()
            print("Database initialized with test data")

if __name__ == '__main__':
    init_db()