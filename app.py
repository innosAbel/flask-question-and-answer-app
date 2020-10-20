from flask import Flask, render_template, g, request, session, url_for, redirect
from database import get_db
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

def get_user_data():
    user_result = None

    if 'user' in session:
        user = session['user']

        db = get_db()
        user_query = db.execute('SELECT * FROM users WHERE name = ?', [user])
        user_result = user_query.fetchone()
    return user_result

@app.route('/')
def index():
    user = get_user_data()
    db = get_db()

    query = db.execute('SELECT questions.id as question_id, questions.question_text, askers.name as asker_name, experts.name as expert_name FROM questions JOIN users as askers ON askers.id = questions.asked_by_id JOIN users as experts ON experts.id = questions.expert_id WHERE questions.answer_text IS NOT null')
    query_result = query.fetchall()

    return render_template('home.html', user=user, questions=query_result)

@app.route('/register', methods=['GET', 'POST'])
def register():
    user = get_user_data()

    if request.method == 'POST':
        db = get_db()

        query = db.execute('SELECT * FROM users WHERE name = ?', [request.form['name']])
        query_result = query.fetchone()
        if query_result:
            return render_template('register.html', user=user, error='User already exists!')

        hashed_password = generate_password_hash(request.form['password'], method='sha256')
        db.execute('INSERT INTO users (name, password, expert, admin) VALUES (?, ?, ?, ?)', [request.form['name'], hashed_password, 0, 0])
        db.commit()

        session['user'] = request.form['name']
        
        return redirect(url_for('index'))

    return render_template('register.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    user = get_user_data()

    if request.method == 'POST':
        db = get_db()

        name = request.form['name']
        password = request.form['password']

        user_query = db.execute('SELECT id, name, password FROM users WHERE name = ?', [name])
        user_result = user_query.fetchone()
        if user_result:
            if check_password_hash(user_result['password'], password):
                session['user'] = user_result['name']
                return redirect(url_for('index'))
            else:
                error: 'The password is incorrect!'
        else:
            error: 'The username is incorrect!'

    return render_template('login.html', user=user)

@app.route('/question/<question_id>')
def question(question_id):
    user = get_user_data()
    if not user:
        return redirect(url_for('login'))

    db = get_db()


    query = db.execute('SELECT questions.answer_text, questions.question_text, askers.name as asker_name, experts.name as expert_name FROM questions JOIN users as askers ON askers.id = questions.asked_by_id JOIN users as experts ON experts.id = questions.expert_id WHERE questions.id = ?', [question_id])
    query_result = query.fetchone()

    return render_template('question.html', user=user, question = query_result)

@app.route('/answer/<question_id>', methods=['GET', 'POST'])
def answer(question_id):
    user = get_user_data()
    if not user:
        return render_template('login.html')
    if user['expert'] == 0:
        return redirect(url_for('index'))
        
    db = get_db()

    if request.method == 'POST':
        db.execute('UPDATE questions SET answer_text = ? WHERE id = ?', [request.form['answer'], question_id])
        db.commit()
        return redirect(url_for('unanswered'))

    query = db.execute('SELECT * FROM questions WHERE id = ?', [question_id])
    question = query.fetchone()

    return render_template('answer.html', user=user, question=question)

@app.route('/ask', methods=['GET', 'POST'])
def ask():
    user = get_user_data()
    if not user:
        return redirect(url_for('login'))
    db = get_db()

    if request.method == 'POST':
        db.execute('INSERT INTO questions (question_text, asked_by_id, expert_id) VALUES (?,?,?)',[request.form['question'], user['id'],request.form['expert']])
        db.commit()

        return redirect(url_for('index'))        

    expert_query = db.execute('SELECT * FROM users WHERE expert = 1')
    expert_result = expert_query.fetchall()
    
    return render_template('ask.html', user=user, experts=expert_result)

@app.route('/unanswered')
def unanswered():
    user = get_user_data()
    if not user:
        return redirect(url_for('login'))

    if user['expert'] == 0:
        return redirect(url_for('index'))
        

    db = get_db()

    question_query = db.execute('SELECT questions.id, questions.question_text, users.name FROM questions JOIN users ON users.id = questions.asked_by_id WHERE questions.answer_text IS null AND questions.expert_id = ?',[user['id']])
    question_result = question_query.fetchall()

    return render_template('unanswered.html', user=user, questions=question_result)

@app.route('/users')
def users():
    user = get_user_data()
    if not user:
        return redirect(url_for('login'))
    if user['admin'] == 0:
        return redirect(url_for('index'))

    db = get_db()

    users_query = db.execute('SELECT * FROM users')
    users_result = users_query.fetchall()

    return render_template('users.html', user=user, users=users_result)

@app.route('/promote/<user_id>')
def promote(user_id):
    db = get_db()

    db.execute('UPDATE users SET expert = 1 WHERE id = ?', [user_id])
    db.commit()

    return redirect(url_for('users'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)