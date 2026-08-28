from flask import Flask, render_template, redirect, request, session
import sqlite3
from datetime import datetime, timedelta


app = Flask(__name__)
app.config['SECRET_KEY'] = 'iamthegoat'
DATABASE = 'batavia_library.db'
verified = False
USERNAME = 'Admin'
PASSWORD = 'ilovenickgurr'

@app.route('/')
def home():
    user = session.get('user')
    return render_template("home.html", user=user)

@app.errorhandler(404)
def page_not_found(e):
    user = session.get('user')
    return render_template("404_error.html", user = user)

@app.route('/about-us')
def about_us():
    user = session.get('user')
    return render_template("about_us.html", user=user)

#Sign Up Page & Processing
@app.route('/sign-up')
def sign_up():
    return render_template('sign_up.html')

@app.post('/input_new_user')
def add_new_user():
    username = str(request.form['username'])
    password = str(request.form['password'])

    if find_user(username):
        return render_template('sign_up.html',warning='Username')
    if len(password) < 5 or len(password) > 16:
        return render_template('sign_up.html',warning='Password')
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    query = f"insert into user (name, password, borrow_number) values ('{username}', '{encrypt(password)}', 0);"
    cursor.execute(query)
    db.commit()
    db.close()
    session['user'] = username
    return redirect('/')

def find_user(user):
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    query = f"select * from user where name = '{user}';"
    cursor.execute(query)
    user_data = cursor.fetchone()
    db.close()
    return user_data != None

#Log In data handling
@app.route('/log-in')
def login():
    return render_template('login.html',warning=None)

@app.post('/get_login_data')
def handle_login_data():
    username = str(request.form['username'])
    password = str(request.form['password'])

    verify = verification(username,password)
    if verify:
        session['user'] = username
        return redirect('/')
    else: 
        return render_template('login.html',warning=True)
    
def verification(username, password):
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    query = f"select password from user where name = '{username}';"
    cursor.execute(query)
    actual_password = cursor.fetchone()
    db.close()
    actual_password = actual_password[0] if actual_password else False
    return encrypt(password) == actual_password

@app.route('/find-book',methods=['GET','POST'])
def find_book():
    user = session.get('user')
    found_books = None
    book = None
    if request.method == 'POST':
        book = str(request.form['books'])
        db = sqlite3.connect(DATABASE)
        cursor = db.cursor()
        query = f"select books.ID, book_name, author, genre.genre from books left join genre on books.genre_ID = genre.ID where book_name like '%{book}%';"
        cursor.execute(query)
        found_books = cursor.fetchall()
        db.close()
        if not found_books:
            return render_template('find_book.html', found_books = None, user = user)  
    return render_template('find_book.html', found_books = found_books, user = user, book = book if request.method == 'POST' else None)

#Checkout Processing
@app.route('/checkout')
def checkout():
    return_date = clock()[1]
    user = session.get('user')
    if user == None:
        return redirect('/')
    return render_template('checkout.html',return_date = return_date, user = user, failed = None)

@app.route('/checkout-successful')
def post_checkout():
    user = session.get('user')
    failed = None
    return render_template('checkout_success.html', user = user, failed = failed)

@app.post('/process-checkout')
def process_checkout():
    book = str(request.form['book'])
    address = str(request.form['address'])
    username = session.get('user')
    all_IDs = find_IDs(username, book)
    if not all_IDs:
        return render_template('checkout_success.html', user = username, failed = book)
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    query = f"insert into borrow (user_ID, book_ID, genre_ID, address, borrow_date, borrow_due) values ({all_IDs[0]}, {all_IDs[1]}, {all_IDs[2]}, '{address}', '{clock()[0]}', '{clock()[1]}');"
    cursor.execute(query)
    query = f"UPDATE user SET borrow_number = borrow_number + 1 WHERE name = '{username}';"
    cursor.execute(query)
    db.commit()
    db.close()
    return redirect('/checkout-successful')
    
def find_IDs(username, book):
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    cursor.execute(f"select ID, genre_ID from books where book_name = '{book}';")
    results = cursor.fetchone()
    try:
        book_ID, genre_ID = results[0], results[1] 
        cursor.execute(f"select ID from user where name = '{username}';")
        name_ID = cursor.fetchone()[0]
        db.close()
        return (name_ID, book_ID, genre_ID)
    except Exception:
        return False

#Processing Return
@app.route('/return')
def return_books():
    user = session.get('user')
    if user == None:
        return redirect('/')
    return render_template('return.html', user = user, failed = None)

@app.post('/process-return')
def process_return():
    username = session.get('user')
    book = str(request.form['book'])
    all_IDs = find_IDs(username, book)
    if not all_IDs:
       return render_template('checkout_success.html', user = username, failed = book)
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    query = f"insert into return (user_ID, book_ID, return_date) values ({all_IDs[0]}, {all_IDs[1]},'{clock()[0]}');"
    cursor.execute(query)
    db.commit()
    db.close()
    return redirect('/return-successful')

@app.route('/return-successful')
def post_return():
    user = session.get('user')
    failed = None
    return render_template('return_successful.html', user = user, failed = failed)
    
#Log Out
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

#Encrypting Password
def encrypt(password):
    encrypted_password = ''
    for i in password:
        unicode_let = ord(i)
        unicode_let += 1
        encrypted_password += chr(unicode_let)
    return encrypted_password

def clock():
    today = datetime.now()
    a_month = today + timedelta(weeks=4)
    return (today.strftime("%d-%m-%Y"), a_month.strftime("%d-%m-%Y"))  

if __name__ == '__main__':
    app.run(debug="True")