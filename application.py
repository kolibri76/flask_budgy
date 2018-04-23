import os
import warnings
import shutil
from datetime import datetime, date
from flask import Flask, flash, redirect, render_template, url_for, abort, request, send_from_directory
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import func, extract, event
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, HiddenField, FloatField
from wtforms.fields.html5 import DateField, DecimalField
from wtforms.validators import InputRequired, Email, Length, EqualTo, Optional, AnyOf
# check wtforms patch for QuerySelectField -> https://github.com/wtforms/wtforms/issues/373
from wtforms.ext.sqlalchemy.fields import QuerySelectField
# flask-uploads uses werkzeugs secure_filename
from flask_uploads import UploadSet, IMAGES, DOCUMENTS, configure_uploads
from flask_admin import Admin
from flask_admin.base import MenuLink
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import rules


# General config parameters
project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "budgy.db"))
www_url = 'http://127.0.0.1:5000'
www_subpath = ''

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
# Flask Login
login = LoginManager(app)
login.login_view = 'login'
# SQLAlchemy config
app.config["SQLALCHEMY_DATABASE_URI"] = database_file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.config['BOOTSTRAP_SERVE_LOCAL'] = True
Bootstrap(app)
# flask-uploads config
app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024  # 3MBytes upload limit
app.config['UPLOADS_DEFAULT_DEST'] = project_dir + '/static/uploads/'
app.config['UPLOADS_DEFAULT_URL'] = www_url + www_subpath + '/static/uploads/'
app.config['UPLOADED_RECEIPTS_DEST'] = project_dir + '/static/uploads/Receipts/'
app.config['UPLOADED_RECEIPTS_URL'] = www_url + www_subpath + '/static/uploads/Receipts/'
app.config['UPLOADED_RECEIPTS_ALLOW'] = set([IMAGES, DOCUMENTS, 'pdf'])
uploaded_receipts = UploadSet('receipts')
configure_uploads(app, uploaded_receipts)

# Import DB models
from models import User, Ulog, Uaction, Transaction, Ttype, Tcategory

migrate = Migrate(app, db)


# http://flask.pocoo.org/snippets/35/ (only required if app is reverse proxied)
class ReverseProxied(object):
    '''Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    In nginx:
    location /myprefix {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /myprefix;
        }

    :param app: the WSGI application
    '''
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


app.wsgi_app = ReverseProxied(app.wsgi_app)


# Flask Admin configuration
# User log model View (index page)
class UlogModelView(ModelView):
    can_create = False
    can_edit = False
    can_delete = False
    column_list = ('timestamp', 'uaction.name', 'uaction.loglevel', 'user_id', 'details')
    column_labels = {'uaction.name': 'Action', 'uaction.loglevel': 'Log Level'}
    column_filters = ('uaction.loglevel', 'uaction.name', 'user_id')
    column_searchable_list = column_list
    column_default_sort = ('timestamp', True)

    # # https://github.com/flask-admin/flask-admin/issues/580
    def __init__(self, model, session, *args, **kwargs):
        super(UlogModelView, self).__init__(model, session, *args, **kwargs)
        self.static_folder = 'static'

    # Allow access for a certain user level
    def is_accessible(self):
        if current_user.is_authenticated:
            return current_user.level == 'admin'

    # redirect to login if not logged in
    def inaccessible_callback(self, name, **kwargs):
        if not self.is_accessible():
            flash('You don\'t have the necceary permission')
            return redirect(url_for('login', next=request.url))


# User view
class UserModelView(ModelView):
    column_exclude_list = 'password_hash'
    form_excluded_columns = 'password_hash'
    column_searchable_list = ('email',)
    column_filters = ('level',)
    column_sortable_list = ('email', 'lastlogin')
    column_default_sort = ('lastlogin', True)
    form_columns = ('email', 'level', 'password_hash')
    # evtl. adding additional table with user roles makes sense
    form_choices = dict(
        level=[('user', 'user'), ('admin', 'admin'), ]
    )
    form_args = dict(
        email=dict(validators=[Email()]),
        level=dict(validators=[AnyOf(['user', 'admin'])]),

    )
    form_edit_rules = ('email', 'level', rules.Header('Reset Password'), 'new_password', 'confirm')
    form_create_rules = ('email', 'level', 'password')

    # Allow access for a certain user level
    def is_accessible(self):
        if current_user.is_authenticated:
            return current_user.level == 'admin'

    # redirect to login if not logged in
    def inaccessible_callback(self, name, **kwargs):
        if not self.is_accessible():
            flash('You don\'t have the necceary permission')
            return redirect(url_for('login', next=request.url))

    # extend form with additional password fields not contained in model (necessary for password handling)
    def scaffold_form(self):
        form_class = super(UserModelView, self).scaffold_form()
        form_class.password = PasswordField('Password', validators=[InputRequired(), Length(min=4, max=50)])
        form_class.new_password = PasswordField('New Password', validators=[Optional(), Length(min=4, max=50)])
        form_class.confirm = PasswordField('Confirm New Password')
        return form_class

    # define "create" form
    def create_model(self, form):
        model = self.model()
        form.populate_obj(model)
        model.set_password(form.password.data)
        self.session.add(model)
        self._on_model_change(form, model, True)
        self.session.commit()
        flash('New user created')

    # define "edit" form
    def update_model(self, form, model):
        form.populate_obj(model)
        if form.new_password.data:
            if form.new_password.data != form.confirm.data:
                flash('Passwords must match')
                return
            model.set_password(form.new_password.data)
            flash('Password changed')
        self.session.add(model)
        self._on_model_change(form, model, False)
        self.session.commit()
        flash('Changes saved')


# Transaction category view
class TcategoryModelView(ModelView):
    column_list = ('name', 'ttype.name')
    column_labels = {'ttype.name': 'Transaction Type'}
    form_excluded_columns = ('user', 'transactions', 'deleted')
    form_args = dict(
        default=dict(default=True, validators=[InputRequired()]),
    )

    def get_query(self):
        return self.session.query(self.model).filter(self.model.default == True)

    # Allow access for a certain user level
    def is_accessible(self):
        if current_user.is_authenticated:
            return current_user.level == 'admin'

    # redirect to login if not logged in
    def inaccessible_callback(self, name, **kwargs):
        if not self.is_accessible():
            flash('You don\'t have the necceary permission')
            return redirect(url_for('login', next=request.url))


# Generic view for views without special needs
class GenModelView(ModelView):
    can_create = False
    can_delete = False
    column_exclude_list = ('ttype',)
    form_excluded_columns = ('ulog', 'tcategories')

    # Allow access for a certain user level
    def is_accessible(self):
        if current_user.is_authenticated:
            return current_user.level == 'admin'

    # redirect to login if not logged in
    def inaccessible_callback(self, name, **kwargs):
        if not self.is_accessible():
            flash('You don\'t have the necceary permission')
            return redirect(url_for('login', next=request.url))


# Inititate the Flask-Admin Interface
admin = Admin(app, name='Budgy Admin',
              index_view=UlogModelView(Ulog, db.session, name='User Log',
                                       url='/admin', endpoint='admin'), template_mode='bootstrap3')
admin.add_link(MenuLink(name='Back to Budgy', url=www_subpath + '/'))
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', 'Fields missing from ruleset')
    admin.add_view(UserModelView(User, db.session, 'Users'))
admin.add_view(TcategoryModelView(Tcategory, db.session, 'Default Transaction Categories'))
admin.add_view(GenModelView(Uaction, db.session, 'User actions'))


# Helpers
# actions to be carried out after user creation
@event.listens_for(User, 'after_insert')
def after_insert_listener(mapper, connection, target):
    # copy default tcategories to user after user is created
    default_tcategories = Tcategory.query.filter_by(default=True, deleted=None).all()
    tcategory_table = Tcategory.__table__
    for tcategory in default_tcategories:
        connection.execute(tcategory_table.insert(), name=tcategory.name, user_id=target.id,
                           ttype_id=tcategory.ttype_id, default=False)
    print(f"default categories for user {target.email} copied")


# actions to be carried out after user deletion
@event.listens_for(User, 'after_delete')
def after_delete_listener(mapper, connection, target):
    # delete users attachments if available
    shutil.rmtree(app.config['UPLOADED_RECEIPTS_DEST'] + str(target.id), ignore_errors=True)
    # deletion of users child db objects like transactions & categories is covered by db functionality
    # see models.py


# add user login timestamp
def login_timestamp():
    row = User.query.filter_by(id=current_user.id).one()
    row.lastlogin = func.now()
    db.session.add(row)
    db.session.commit()


# User Log entries
def add_user_log(action_id, details, **kwargs):

    user_id = kwargs.get('user_id', None)

    if current_user.is_authenticated:
        user_id = current_user.id
    elif user_id:
        user_id = user_id
    else:
        user_id = None

    row = Ulog(timestamp=func.now(), action_id=action_id, user_id=user_id, details=details)
    db.session.add(row)
    db.session.commit()


# Flask Form classes
# User Login
class LoginForm(FlaskForm):
    email = StringField('email', validators=[Email()], render_kw={"placeholder": "email"})
    password = PasswordField("password", validators=[InputRequired(), Length(min=4, max=50)],
                             render_kw={"placeholder": "Password"})
    remember_me = BooleanField('remember me')
    submit = SubmitField('Login')


# User change password
class ChangePwForm(FlaskForm):
    password = PasswordField("password", validators=[InputRequired(), Length(min=4, max=50)],
                             render_kw={"placeholder": "Existing Password"})
    new_password = PasswordField('password',
                                 validators=[InputRequired(), EqualTo('confirm', 'New Passwords must match'),
                                             Length(min=1, max=50)], render_kw={"placeholder": "New Password"})
    confirm = PasswordField('confirm', validators=[InputRequired()], render_kw={"placeholder": "Confirm New Password"})
    submit = SubmitField('Reset password')


# User Registration
class RegistrationForm(FlaskForm):
    email = StringField('email', validators=[Email()], render_kw={"placeholder": "Email"})
    password = PasswordField('password', validators=[InputRequired(), EqualTo('confirm', 'Passwords must match'),
                                                     Length(min=1, max=50)], render_kw={"placeholder": "Password"})
    confirm = PasswordField('confirm', validators=[InputRequired()], render_kw={"placeholder": "Confirm Password"})
    submit = SubmitField('Register')


# Transaction Edit
class EditTransactionForm(FlaskForm):
    id = HiddenField("Transaction ID")
    ttype_id = HiddenField("Transaction Type ID")
    # query_factory for QuerySelectFields in route(s)
    tcategory = QuerySelectField('Category', validators=[InputRequired()], get_label='name')
    date = DateField('Date', format='%Y-%m-%d', default=date.today, render_kw={"placeholder": "Amount"})
    amount = DecimalField('Amount', validators=[InputRequired()], render_kw={"placeholder": "00.00"})
    details = StringField('Details', validators=[Optional()], render_kw={"placeholder": "Details"})
    attachment = FileField('Receipt', validators=[Optional(), FileAllowed(uploaded_receipts, 'Only Images & Docs!')])
    geo_lat = FloatField('Latitude', validators=[Optional()], render_kw={"placeholder": "0.0"})
    geo_lng = FloatField('Longitude', validators=[Optional()], render_kw={"placeholder": "0.0"})
    submit = SubmitField('Submit')


# Transaction Category Edit
class EditTCategegoryForm(FlaskForm):
    id = HiddenField('TCategory ID')
    # query_factory for QuerySelectFields in route(s)
    ttype = QuerySelectField('Transaction Type', get_label='name')
    name = StringField('Category Name', validators=[InputRequired(), Length(min=1, max=100)],
                       render_kw={"placeholder": 'My new category'})
    submit = SubmitField('Submit')


# Routes
# protect users receipts from beeing viewed by anonymous or other logged in users or admins
@app.route('/static/uploads/Receipts/<sub_dir>/<filename>', methods=['GET'])
@login_required
def send_img(sub_dir, filename):
    # only provide access dir receipt if current user id is identical to subdir name
    if sub_dir != str(current_user.id):
        abort(403)
    path = os.path.join(app.config['UPLOADED_RECEIPTS_DEST'], sub_dir)
    print(path)
    return send_from_directory(path, filename)


@app.route('/category_add', methods=['GET', 'POST'])
@login_required
def category_add():

    form = EditTCategegoryForm()
    #  Set forms Ttype QuerySelectField
    form.ttype.query = Ttype.query.all()

    if form.validate_on_submit():
        row = Tcategory(default=False, name=form.name.data, ttype_id=form.ttype.data.id, user_id=current_user.id)
        db.session.add(row)
        db.session.commit()
        add_user_log(8, f'tcategory_id: {row.id}')
        flash('Category added')
        return redirect(url_for('category_overview'))

    return render_template('category_edit.html', title='Add category', form=form)


@app.route('/category_edit/<int:tcategory_id>', methods=['GET', 'POST'])
@login_required
def category_edit(tcategory_id):

    row = Tcategory.query.filter_by(id=tcategory_id, deleted=None).first_or_404()

    if row.user_id == current_user.id:
        form = EditTCategegoryForm(obj=row)
        form.ttype.query = Ttype.query.filter_by(id=row.ttype_id).all()

        if form.validate_on_submit():
            row.name = form.name.data
            db.session.add(row)
            db.session.commit()
            add_user_log(9, f'tcategory_id: {row.id}')
            flash('Category changed')

            return redirect(url_for('category_overview'))
    else:
        abort(403)

    return render_template('category_edit.html', title='Add category', form=form, edit=True)


@app.route('/category_del/<int:tcategory_id>', methods=['GET'])
@login_required
def category_del(tcategory_id):

    row = Tcategory.query.filter_by(id=tcategory_id).first_or_404()

    if row.user_id == current_user.id:
        row.deleted = func.now()
        db.session.add(row)
        db.session.commit()
        add_user_log(10, f'tcategory_id: {row.id}')
        flash('Category deleted')
        return redirect(url_for('category_overview'))
    else:
        abort(403)


@app.route('/category_overview', methods=['GET'])
@login_required
def category_overview():

    rows = Tcategory.query.filter_by(user_id=current_user.id, deleted=None).all()

    return render_template('category_overview.html', title='Category Overview', rows=rows)


@app.route('/transaction_add/<int:ttype_id>', methods=['GET', 'POST'])
@login_required
def transaction_add(ttype_id):

    # Verify transaction type exists
    Ttype.query.filter_by(id=ttype_id).first_or_404()
    # Set form
    form = EditTransactionForm()
    # Set forms Tcategory QuerySelectField
    form.tcategory.query = Tcategory.query.filter_by(user_id=current_user.id, ttype_id=ttype_id, deleted=None).all()

    if form.validate_on_submit():
        # change operator for expenditure
        if ttype_id == 2:
            form.amount.data = -form.amount.data
        # set attachment variables (in case no attachment is added)
        attachment_name = None
        attachment_url = None
        # process attachment
        if form.attachment.data:
            attachment_name = uploaded_receipts.save(request.files['attachment'], folder=str(current_user.id))
            attachment_url = uploaded_receipts.url(attachment_name)
        # add new record
        row = Transaction(date=form.date.data, user_id=current_user.id,
                          tcategory_id=form.tcategory.data.id,
                          amount=form.amount.data, details=form.details.data,
                          attachment_name=attachment_name, attachment_url=attachment_url,
                          geo_lat=form.geo_lat.data, geo_lng=form.geo_lng.data)
        db.session.add(row)
        db.session.commit()
        # logging + user info
        add_user_log(5, f'transaction_id: {row.id}')
        flash('Transaction added')

        return redirect(url_for('index'))

    return render_template('transaction_edit.html', title='Add transaction', form=form, ttype_id=ttype_id)


@app.route('/transaction_edit/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def transaction_edit(transaction_id):

    row = Transaction.query.filter_by(id=transaction_id).first_or_404()

    if row.user_id == current_user.id:
        if row.tcategory.ttype_id == 2:
            row.amount = abs(row.amount)
        row.ttype_id = row.tcategory.ttype_id
        form = EditTransactionForm(obj=row)
        form.tcategory.query = Tcategory.query.filter_by(user_id=current_user.id,
                                                         ttype_id=row.tcategory.ttype_id, deleted=None).all()

        if form.validate_on_submit():
            if int(form.ttype_id.data) == 2:
                form.amount.data = -form.amount.data
            # set attachment variables (in case no attachment is added)
            attachment_name = row.attachment_name
            attachment_url = row.attachment_url
            # process attachment
            if form.attachment.data:
                attachment_name = uploaded_receipts.save(request.files['attachment'], folder=str(current_user.id))
                attachment_url = uploaded_receipts.url(attachment_name)
            row.tcategory_id = form.tcategory.data.id
            row.date = form.date.data
            row.details = form.details.data
            row.attachment_name = attachment_name
            row.attachment_url = attachment_url
            row.amount = form.amount.data
            row.geo_lat = form.geo_lat.data
            row.geo_lng = form.geo_lng.data
            row.modified = func.now()
            db.session.add(row)
            db.session.commit()
            add_user_log(6, f'transaction_id: {row.id}')
            flash('Transaction changed')
            return redirect(url_for('index'))

        return render_template('transaction_edit.html', title='Change transaction', form=form, edit=True,
                               attachment_name=row.attachment_name, attachment_url=row.attachment_url)
    else:
        abort(403)


@app.route('/transaction_delete/<int:transaction_id>', methods=['GET'])
@login_required
def transaction_delete(transaction_id):

    row = Transaction.query.filter_by(id=transaction_id).first_or_404()

    if row.user_id == current_user.id:

        db.session.delete(row)
        db.session.commit()
        add_user_log(7, f'transaction_id: {row.id}')
        flash('Transaction deleted')
        return redirect(url_for('index'))

    else:
        abort(403)


@app.route('/transaction_view/<int:transaction_id>', methods=['GET'])
@login_required
def transaction_view(transaction_id):

    row = Transaction.query.filter_by(id=transaction_id).first_or_404()

    if row.user_id == current_user.id:
        if row.tcategory.ttype_id == 2:
            row.amount = abs(row.amount)
        row.ttype_id = row.tcategory.ttype_id
        form = EditTransactionForm(obj=row)
        form.tcategory.query = Tcategory.query.filter_by(user_id=current_user.id,
                                                         ttype_id=row.tcategory.ttype_id, deleted=None).all()

        return render_template('transaction_detail.html', title='View transaction', form=form, transaction_id=row.id,
                               attachment_name=row.attachment_name, attachment_url=row.attachment_url)
    else:
        abort(403)


@app.route('/transaction_overview/', defaults={'ttype_id': None}, methods=['GET'])
@app.route('/transaction_overview/<int:ttype_id>', methods=['GET'])
@login_required
def transaction_overview(ttype_id):

    if ttype_id:
            title = Ttype.query.filter_by(id=ttype_id).first_or_404().name
    else:
        title = 'Overview'

    if ttype_id:
        rows = Transaction.query.join(Tcategory)\
                          .filter(Tcategory.ttype_id == ttype_id, Transaction.user_id == current_user.id,
                                  extract('month', Transaction.date) == datetime.now().month)\
                          .order_by(Transaction.date.desc(), Transaction.id.desc())
    else:
        rows = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc())

    return render_template('transaction_overview.html', title=title, rows=rows, ttype_id=ttype_id)


@app.route('/')
@login_required
def index():

    return redirect(url_for('chart_actual_month'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        row = User.query.filter_by(email=form.email.data).first()
        if row is None or not row.check_password(form.password.data):
            flash('Invalid email or password')
            if row:
                add_user_log(2, f'user: {row.email}', user_id=row.id)
            else:
                add_user_log(2, f'unknown user: {form.email.data}')
            return redirect(url_for('login'))
        login_user(row, remember=form.remember_me.data)
        add_user_log(1, f'user: {row.email}')
        login_timestamp()
        flash('Successfully logged in')
        return redirect(request.args.get('next') or url_for('index'))
    return render_template('user_login.html', title='Login', form=form)


@app.route('/change_passwd', methods=['GET', 'POST'])
@login_required
def change_passwd():
    form = ChangePwForm()
    if form.validate_on_submit():
        row = User.query.filter_by(id=current_user.id).one()
        if not row.check_password(form.password.data):
            flash('Invalid existing password')
            return redirect(url_for('change_passwd'))
        row.set_password(form.new_password.data)
        db.session.add(row)
        db.session.commit()
        flash('Password reset successful')
        return redirect(request.args.get('next') or url_for('index'))
    return render_template('user_passwd.html', title='Set password', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    # add user to database if not existing
    form = RegistrationForm()
    if form.validate_on_submit():
        row = User(email=form.email.data, level='user')
        # Verify if user already exists
        user_exist = User.query.filter_by(email=form.email.data).first()
        if user_exist and user_exist.email == row.email:
            add_user_log(4, f'user already registered: {form.email.data}')
            flash('User already registered')
        else:
            # add user to db and login user
            db.session.add(row)
            row.set_password(form.password.data)
            db.session.commit()
            flash('Registration successful')
            login_user(row)
            login_timestamp()
            add_user_log(3, f'user: {form.email.data}')

            # copy default data to user (to provide later adjustments)
            # see

            # redirect user to index
            return redirect(url_for('index'))

    # render register form
    return render_template('user_register.html', title='Register', form=form)


@app.route('/chart_actual_month/', defaults={'ttype_id': None}, methods=['GET'])
@app.route('/chart_actual_month/<int:ttype_id>', methods=['GET'])
@login_required
def chart_actual_month(ttype_id, chart_id='chart_ID', chart_type='column', chart_height=350):

    if not ttype_id:
        ttype_id = 2
    ttype_name = Ttype.query.filter_by(id=ttype_id).first_or_404().name
    title = 'Overview ' + ttype_name + ' actual month'

    # db query - total expenditures per category for current user and actual month
    rows = db.session.query(Transaction, func.sum(Transaction.amount).label('total_amount'))\
                     .join(Tcategory)\
                     .filter(Tcategory.ttype_id == ttype_id, Transaction.user_id == current_user.id, extract('month',
                             Transaction.date) == datetime.now().month)\
                     .group_by(Transaction.tcategory_id).all()

    # convert data for high charts
    lst_data = []
    lst_categories = []
    for row in rows:
        # turn expenditures into absolute value
        if row.Transaction.tcategory.ttype_id == 2:
            lst_data.append(abs(row.total_amount))
        else:
            lst_data.append(row.total_amount)
        lst_categories.append(row.Transaction.tcategory.name)

    # chart parameters
    chart = {"renderTo": chart_id, "type": chart_type, "height": chart_height, }
    series = [{"name": 'Actual month', "data": lst_data}]
    chart_title = {"text": 'Expenditures ' + datetime.now().strftime("%B-%Y")}
    chart_subtitle = {'text': 'Total spent actual:' + str(sum(lst_data))}
    x_axis = {"categories": lst_categories}
    y_axis = {"title": {"text": 'Amount'}}

    # render chart
    return render_template('chart.html', title=title, chartID=chart_id, chart=chart, series=series,
                           chart_title=chart_title, chart_subtitle=chart_subtitle, xAxis=x_axis, yAxis=y_axis)


if __name__ == "__main__":
    app.run(host='127.0.0.1', debug=True)
