from flask_sqlalchemy import SQLAlchemy
from app import app
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy(app)

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True,nullable=False)
    passhash = db.Column(db.String(256),nullable=False)
    name = db.Column(db.String(64),nullable=True)

    flags = db.relationship('Flag', back_populates='admin')

class Sponsor(db.Model):
    __tablename__ = 'sponsors'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128),unique=True,nullable=False)
    passhash = db.Column(db.String(256),nullable=False)
    name = db.Column(db.String(64),nullable=True)
    budget = db.Column(db.Integer,nullable=True)
    industry = db.Column(db.String(64), nullable=True)

    campaigns = db.relationship('Campaign', back_populates='sponsor')
    ad_requests = db.relationship('AdRequest', back_populates='sponsor')

class Influencer(db.Model):
    __tablename__ = 'influencers'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128),unique=True,nullable=False)
    passhash = db.Column(db.String(256),nullable=False)
    name = db.Column(db.String(64),nullable=True)
    category = db.Column(db.String(128),nullable=False)
    niche = db.Column(db.String(128),nullable=False)
    reach = db.Column(db.Integer)

    ad_requests = db.relationship('AdRequest', back_populates='influencer')

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    budget = db.Column(db.Integer)
    visibility = db.Column(db.String(64))  # Could be 'public' or 'private'
    goals = db.Column(db.Text)

    sponsor_id = db.Column(db.Integer, db.ForeignKey('sponsors.id'))
    sponsor = db.relationship('Sponsor', back_populates='campaigns')
    
    ad_requests = db.relationship('AdRequest', back_populates='campaign')

class AdRequest(db.Model):
    __tablename__ = 'ad_requests'
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'))
    influencer_id = db.Column(db.Integer, db.ForeignKey('influencers.id'))
    sponsor_id = db.Column(db.Integer, db.ForeignKey('sponsors.id')) 
    messages = db.Column(db.Text)
    requirements = db.Column(db.Text)
    payment_amount = db.Column(db.Integer)
    status = db.Column(db.String(64))  # Could be 'Pending', 'Accepted', 'Rejected'
    
    campaign = db.relationship('Campaign', back_populates='ad_requests')
    influencer = db.relationship('Influencer', back_populates='ad_requests')
    sponsor = db.relationship('Sponsor', back_populates='ad_requests')

class Flag(db.Model):
    __tablename__ = 'flags'
    id = db.Column(db.Integer, primary_key=True)
    reason = db.Column(db.Text, nullable=False)  # Reason for flagging
    entity_type = db.Column(db.String(64), nullable=False)  # Can be 'campaign' or 'user'
    entity_id = db.Column(db.Integer, nullable=False)  # The ID of the campaign or user being flagged
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'))  # Admin who flagged the item
    
    admin = db.relationship('Admin', back_populates='flags')

with app.app_context():
    db.create_all()
    #check if admin exists, else create admin
    admin = Admin.query.first()
    if not admin:
        password_hash = generate_password_hash('admin')
        admin=Admin(username='admin', passhash=password_hash, name='Admin')
        db.session.add(admin)
        db.session.commit()