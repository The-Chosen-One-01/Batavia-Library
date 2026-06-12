from flask import Flask, render_template, redirect, request
import sqlite3

app = Flask(__name__)
DATABASE = 'batavia_library.db'
verified = False
userCounter = 20

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/about-us')
def about_us():
    return render_template("about_us.html")

@app.route('/sign-up')
def sign_up():
    return render_template('sign_up.html')

@app.route('/log-in')
def login():
    return render_template('login.html')

@app.post('/get_login_data')
def handle_login_data():
    username = str(request.form['username'])
    password = str(request.form['password'])

    verify = verification(username,password)
    if verify:
        return redirect('/')
    else: 
        return redirect('/login')
    
@app.post('/input_new_user')
def add_new_user():
    username = str(request.form['username'])
    password = str(request.form['password'])

    if find_user(username):
        return redirect('/sign-up')
    global userCounter
    userCounter += 1
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    query = f"insert into user values ('{userCounter}', '{username}', '{password}', 0);"
    cursor.execute(query)
    db.close()
    return redirect('/')

@app.route('/find-book',methods=['GET','POST'])
def find_book():
    found_books = None
    if request.method == 'POST':
        book = str(request.form['books'])
        db = sqlite3.connect(DATABASE)
        cursor = db.cursor()
        query = f"select books.ID, book_name, author, genre.genre from books left join genre on books.genre_ID = genre.ID where book_name like '%{book}%';"
        cursor.execute(query)
        found_books = cursor.fetchall()
        db.close()
    return render_template('find_book.html',found_books = found_books)

def verification(username, password):
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    query = f"select password from user where name = '{username}';"
    cursor.execute(query)
    actual_password = cursor.fetchone()[0]
    db.close()
    return password == actual_password

def find_user(user):
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    query = f"select * from user where name = '{user}';"
    cursor.execute(query)
    user_data = cursor.fetchone()
    db.close()
    return user_data == True

if __name__ == '__main__':
    app.run(debug="True")