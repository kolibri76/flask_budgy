from flask_script import Manager

from application import app, db
from models import User, Uaction, Ttype, Tcategory

manager = Manager(app)

@manager.command
# seed default data if table user exists and table is empty
def init_db():
    tables = db.engine.table_names()
    if "user" in tables:
        if not User.query.get(1):
            actions = {'Login sucess': 'Info', 'Login failed': 'Warning', 'Registration sucess': 'Info',
                       'Registration failed': 'Warning', 'Transaction added': 'Info', 'Transaction changed': 'Info',
                       'Transaction deleted': 'Info', 'Tcategory added': 'Info', 'Tcategory changed': 'Info',
                       'Tcategory deleted': 'Info'}
            for k, v in actions.items():
                val = Uaction(name=k, loglevel=v)
                db.session.add(val)
                db.session.commit()
            types = ['Receipts', 'Expenditures']
            for typ in types:
                val = Ttype(name=typ)
                db.session.add(val)
                db.session.commit()
            r_cats = ['Sallary', 'Gift', 'Other']
            for cat in r_cats:
                val = Tcategory(name=cat, ttype_id=1, default=True)
                db.session.add(val)
                db.session.commit()
            e_cats = ['Sport', 'Car', 'Food']
            for cat in e_cats:
                val = Tcategory(name=cat, ttype_id=2, default=True)
                db.session.add(val)
                db.session.commit()
            u = User(email='admin@budgy.tld', level='admin')
            db.session.add(u)
            u.set_password('password')
            db.session.commit()
            print("records successfully created")
        else:
            print("database is not empty")
    else:
        print("Database or required tables do not exist yet")


if __name__ == "__main__":
    manager.run()
