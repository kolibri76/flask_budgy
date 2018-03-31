from datetime import datetime
from application import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    log = db.relationship('Ulog', backref='user', lazy='dynamic')

    def __repr__(self):
        return '<user {}>'.format(self.email)


class Ulog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    action_id = db.Column(db.Integer, db.ForeignKey('action.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    uaction_id = db.Column(db.Integer, db.ForeignKey('uaction.id'))


class Uaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), index=False, unique=True)
    description = db.Column(db.String(120),'uaction', lazy='dynamic')



