from flask import Flask, render_template, redirect, request
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
Scss(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# Data Class ~ Row of Data
class MyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(100), nullable=False)
    complete = db.Column(db.Integer, default=0)
    due_date = db.Column(db.DateTime, nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"Task {self.id}"


# Data Class ~ Row of Data
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


@app.route('/')
def index():
    return render_template('index.html')


# Home Page
@app.route('/my-tasks', methods=['GET', 'POST'])
def my_task():
    # Add a Task
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
    # See all tasks
    else:
        tasks = MyTask.query.order_by(MyTask.created).all()
        return render_template('my-tasks.html', tasks=tasks)


# https://www.google.com/pageone/2/task
# Delete Task
@app.route('/delete-my-task/<int:id>')
def delete(id:int):
    delete_task = MyTask.query.get_or_404(id)
    try:
        db.session.delete(delete_task)
        db.session.commit()
        return redirect('/my-tasks')
    except Exception as e:
        return f"ERROR: {e}"


@app.route('/finance', methods=['GET', 'POST'])
def finance():
    # Add a Transaction
    if request.method == 'POST':
        current_title = request.form['title']
        current_description = request.form['description']
        current_amount = float(request.form['amount'])
        current_category = request.form['category']
        current_date = datetime.strptime(request.form['date'], '%Y-%m-%d')

        # Calculate the new balance
        last_transaction = Financial.query.order_by(Financial.id.desc()).first()
        current_balance = last_transaction.balance if last_transaction else 1500.00
        new_balance = current_balance - current_amount

        new_transaction = Financial(description=current_description, amount=current_amount,
                                    category=current_category, title=current_title, balance=new_balance
                                    , date=current_date)
        try:
            db.session.add(new_transaction)
            db.session.commit()
            return redirect('/finance')
        except Exception as e:
            print(f"ERROR: {e}")
            return f"ERROR: {e}"
    else:
        transactions = Financial.query.order_by(Financial.date).all()
        return render_template('finance.html', transactions=transactions)


@app.route('/delete-finance/<int:id>')
def delete_finance(id:int):
    delete_transaction = Financial.query.get_or_404(id)
    try:
        db.session.delete(delete_transaction)
        db.session.commit()
        return redirect('/finance')
    except Exception as e:
        return f"ERROR: {e}"


@app.route('/edit-finance/<int:id>', methods=['GET', 'POST'])
def update_finance(id:int):
    transaction = Financial.query.get_or_404(id)
    if request.method == 'POST':
        transaction.title = request.form['title']
        transaction.description = request.form['description']
        transaction.amount = request.form['amount']
        transaction.category = request.form['category']
        transaction.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        transaction.balance = request.form['balance']
        try:
            db.session.commit()
            return redirect('/finance')
        except Exception as e:
            return f"ERROR: {e}"
    else:
        return render_template('edit-finance.html', transaction=transaction)

# Edit Task
@app.route("/edit-my-task/<int:id>", methods=['GET', 'POST'])
def update(id:int):
    task = MyTask.query.get_or_404(id)
    if request.method == 'POST':
        task.content = request.form['content']
        task.due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%d')
        try:
            db.session.commit()
            return redirect('/')
        except Exception as e:
            return f"ERROR: {e}"
    else:
        return render_template('edit-my-tasks.html', task=task)


if __name__ == "__main__":
    app.run(debug=True)
