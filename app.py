from flask import Flask, render_template, redirect, request, session, current_app
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from flask_principal import Principal, Permission, RoleNeed, identity_loaded, UserNeed, Identity, AnonymousIdentity, identity_changed
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey'
login_manager = LoginManager(app)
login_manager.login_view = 'login'
principal = Principal(app)
Scss(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

accounting_permissions = Permission(RoleNeed('accounting'))
management_permissions = Permission(RoleNeed('management'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    identity.user = current_user
    if hasattr(current_user, 'id'):
        identity.provides.add(UserNeed(current_user.id))
    if hasattr(current_user, 'roles'):
        for role in current_user.roles:
            identity.provides.add(RoleNeed(role.name))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    roles = db.relationship('Role', secondary='user_roles', backref=db.backref('users', lazy='dynamic'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)

user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)

class MyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(100), nullable=False)
    complete = db.Column(db.Integer, default=0)
    due_date = db.Column(db.DateTime, nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"Task {self.id}"

class Financial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    title = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    balance = db.Column(db.Float, default=1500.00)

    def __repr__(self) -> str:
        return f"Financial {self.id}"

with app.app_context():
    db.create_all()  # Ensure the table is created

# Add roles to the database (run this once)
# with app.app_context():
#     if not Role.query.filter_by(name='accounting').first():
#         db.session.add(Role(name='accounting'))
#     if not Role.query.filter_by(name='management').first():
#         db.session.add(Role(name='management'))
#     db.session.commit()

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/my-tasks', methods=['GET', 'POST'])
@login_required
@management_permissions.require(http_exception=403)
def my_task():
    if request.method == 'POST':
        current_task = request.form['content']
        current_due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%d')
        new_task = MyTask(content=current_task, due_date=current_due_date)
        try:
            db.session.add(new_task)
            db.session.commit()
            return redirect('/my-tasks')
        except Exception as e:
            print(f"ERROR: {e}")
            return f"ERROR: {e}"
    else:
        tasks = MyTask.query.order_by(MyTask.created).all()
        return render_template('my-tasks.html', tasks=tasks)

@app.route('/delete-my-task/<int:id>')
def delete(id: int):
    delete_task = MyTask.query.get_or_404(id)
    try:
        db.session.delete(delete_task)
        db.session.commit()
        return redirect('/my-tasks')
    except Exception as e:
        return f"ERROR: {e}"

@app.route('/finance', methods=['GET', 'POST'])
@login_required
@accounting_permissions.require(http_exception=403)
def finance():
    if request.method == 'POST':
        current_title = request.form['title']
        current_description = request.form['description']
        current_amount = float(request.form['amount'])
        current_category = request.form['category']
        current_date = datetime.strptime(request.form['date'], '%Y-%m-%d')

        last_transaction = Financial.query.order_by(Financial.id.desc()).first()
        current_balance = last_transaction.balance if last_transaction else 1500.00
        new_balance = current_balance - current_amount

        new_transaction = Financial(description=current_description, amount=current_amount,
                                    category=current_category, title=current_title, balance=new_balance,
                                    date=current_date)
        try:
            db.session.add(new_transaction)
            db.session.commit()
            return redirect('/finance')
        except Exception as e:
            print(f"ERROR: {e}")
            return f"ERROR: {e}"
    else:
        transactions = Financial.query.order_by(Financial.date).all()
        current_balance = transactions[-1].balance if transactions else 1500.00
        return render_template('finance.html', transactions=transactions, current_balance=current_balance)

@app.route('/delete-finance/<int:id>')
def delete_finance(id: int):
    delete_transaction = Financial.query.get_or_404(id)
    try:
        db.session.delete(delete_transaction)
        db.session.commit()
        return redirect('/finance')
    except Exception as e:
        return f"ERROR: {e}"

@app.route('/edit-finance/<int:id>', methods=['GET', 'POST'])
def update_finance(id: int):
    transaction = Financial.query.get_or_404(id)
    if request.method == 'POST':
        transaction.title = request.form['title']
        transaction.description = request.form['description']
        transaction.amount = request.form['amount']
        transaction.category = request.form['category']
        transaction.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        try:
            db.session.commit()
            return redirect('/finance')
        except Exception as e:
            return f"ERROR: {e}"
    else:
        return render_template('edit-finance.html', transaction=transaction)

@app.route("/edit-my-task/<int:id>", methods=['GET', 'POST'])
def update(id: int):
    task = MyTask.query.get_or_404(id)
    if request.method == 'POST':
        task.content = request.form['content']
        task.due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%d')
        try:
            db.session.commit()
            return redirect('/my-tasks')
        except Exception as e:
            return f"ERROR: {e}"
    else:
        return render_template('edit-my-task.html', task=task)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            identity_changed.send(current_app._get_current_object(), identity=Identity(user.id))
            return redirect('/')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)
    identity_changed.send(current_app._get_current_object(), identity=AnonymousIdentity())
    return redirect('/')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        roles = request.form.getlist('roles')  # Get multiple roles from the form

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return 'Username already exists!'

        new_user = User(username=username)
        new_user.set_password(password)

        for role_name in roles:
            role = Role.query.filter_by(name=role_name).first()
            if role:
                new_user.roles.append(role)

        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect('/login')
        except Exception as e:
            return f"ERROR: {e}"
    roles = Role.query.all()
    return render_template('register.html', roles=roles)

if __name__ == "__main__":
    app.run(debug=True)