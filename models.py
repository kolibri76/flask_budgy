from application import db
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from application import login


@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# User related tables
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    level = db.Column(db.String(120), nullable=False)
    lastlogin = db.Column(db.DateTime)
    tcategories = db.relationship('Tcategory', cascade="all, delete", back_populates='user')
    transactions = db.relationship('Transaction', cascade="all, delete", back_populates='user')

    def __repr__(self):
        return '<user {}>'.format(self.email)

    # generate and check password hashes
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# User Log
class Ulog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, server_default=func.now())
    action_id = db.Column(db.Integer, db.ForeignKey('uaction.id'), nullable=False)
    uaction = db.relationship('Uaction', backref='ulog', lazy='select')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    details = db.Column(db.String(120))


# User actions
class Uaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), index=False, unique=True, nullable=False)
    loglevel = db.Column(db.String(120))

    def __repr__(self):
        return '<action {}>'.format(self.name)


# Transaction related tables
# Transactions
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, nullable=False, server_default=func.now())
    modified = db.Column(db.DateTime)
    date = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='transactions', lazy='select')
    tcategory_id = db.Column(db.Integer, db.ForeignKey('tcategory.id'), nullable=False)
    tcategory = db.relationship('Tcategory', backref='transactions', lazy='select')
    details = db.Column(db.String(500))
    attachment_name = db.Column(db.String(500))
    attachment_url = db.Column(db.String(500))
    amount = db.Column(db.Float)
    geo_lat = db.Column(db.Float)
    geo_lng = db.Column(db.Float)

    def __repr__(self):
        return '<transaction {}>'.format(self.id)


# Transaction categories
class Tcategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deleted = db.Column(db.DateTime)
    default = db.Column(db.Boolean, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    ttype_id = db.Column(db.Integer, db.ForeignKey('ttype.id'), nullable=False)
    ttype = db.relationship('Ttype', backref='tcategories', lazy='select')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='tcategories', lazy='select')

    def __repr__(self):
        return '<Category {}>'.format(self.name)


# Transaction types
class Ttype(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return '<t_type {}>'.format(self.name)
