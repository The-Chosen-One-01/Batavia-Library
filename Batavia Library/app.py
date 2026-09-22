# The code below is the flask code of the library

#Importing necessary modules
from flask import Flask, render_template, redirect, request, session
import sqlite3
from datetime import datetime, timedelta
from difflib import SequenceMatcher

#Initialising constants
app = Flask(__name__)
app.config['SECRET_KEY'] = 'iamthegoat'
DATABASE = 'batavia_library.db'

# --- Main app router function --- 
@app.route('/')
def home():
    user = session.get('user')
    return render_template("home.html", user=user)

# --- 404 Error handler (no page is found) --- 
@app.errorhandler(404)
def page_not_found(e):
    user = session.get('user')
    return render_template("404_error.html", user=user)

# --- About us router ---
@app.route('/about-us')
def about_us():
    user = session.get('user')
    return render_template("about_us.html", user=user)

# --- Sign up and data processing ---

# Sign up page router
@app.route('/sign-up')
def sign_up():
    return render_template('sign_up.html')

# Adding new user to the database
@app.post('/input_new_user')
def add_new_user():
    username = str(request.form['username'])
    password = str(request.form['password'])

    if find_user(username):
        return render_template('sign_up.html', warning='Username')
    if len(password) < 5 or len(password) > 16:
        return render_template('sign_up.html', warning='Password')
        
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    query = "INSERT INTO user (name, password, borrow_number) VALUES (?, ?, 0);"
    cursor.execute(query, (username, encrypt(password)))
    db.commit()
    db.close()
    
    session['user'] = username
    return redirect('/')

# Finding user that has the same username as the new user
def find_user(user):
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    query = "SELECT * FROM user WHERE name = ?;"
    cursor.execute(query, (user,))
    user_data = cursor.fetchone()
    db.close()
    return user_data is not None

# Enrypting password for both signing up and logging in
def encrypt(password):
    return ''.join(chr(ord(i) + 1) for i in password)

# --- Log in and data handling ---

# Log in page router
@app.route('/log-in', methods=['GET', 'POST'])
def login():
    result = None
    if request.method == 'POST':
        username = str(request.form.get('username', ''))
        password = str(request.form.get('password', ''))
        result = handle_login_data(username, password)

        if result == 'valid':
            return redirect('/')
            
    return render_template('login.html', warning=result)

# Log in data handling
def handle_login_data(username, password):
    verify = verification(username, password)

    if verify:
        session['user'] = username
        result = 'valid'
    elif verify == 'No Account':
        result = 'No Account'
    else:
        result = 'Wrong Information'

    return result

# Log in data verification
def verification(username, password):
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    query = "SELECT password FROM user WHERE name = ?;"
    cursor.execute(query, (username,))
    result = cursor.fetchone()
    db.close()
    
    if result is None:
        return "No Account"
        
    actual_password = result[0]
    if encrypt(password) == actual_password:
        return True
    return "Wrong Information"

# --- Log Out ---
@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('cart', None)
    return redirect('/')
    
# --- FIND & SEARCH BOOKS ---

# Find book page router
@app.route('/find-book', methods=['GET', 'POST'])
def find_book():
    user = session.get('user')
    found_books = None
    book = None
    if request.method == 'POST':
        book = str(request.form['books'])
        found_books = handle_search_result(book)
        
        if not found_books:
            return render_template('find_book.html', found_books=None, user=user, failed=book)
            
    return render_template('find_book.html', found_books=found_books, user=user, book=book if request.method == 'POST' else None, failed=None)

# Handle search result
def handle_search_result(book):
    db = sqlite3.connect(DATABASE)
    db.create_function("SIMILARITY", 2, similarity_ratio)
    cursor = db.cursor()
    query = "SELECT books.ID, book_name, author, genre.genre FROM books LEFT JOIN genre ON books.genre_ID = genre.ID WHERE SIMILARITY(book_name, ?) > 0.6;"
    cursor.execute(query, (book,))
    found_books = cursor.fetchall()
    db.close()
    return found_books

# Finding the similarity between the searched book and the actual book
def similarity_ratio(book1, book2):
    if not book1 or not book2:
        return 0.0
    if book1 in book2 or book2 in book1:
        return 1.0
    return SequenceMatcher(None, book1.lower().strip(), book2.lower().strip()).ratio()

# --- Cart handling system ---

# Adding book to cart
@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    if 'user' not in session:
        return redirect('/log-in')
    book_title = request.form.get('book')
    if book_title:
        if 'cart' not in session:
            session['cart'] = []
        cart = session['cart']
        if book_title not in cart:
            cart.append(book_title)
            session['cart'] = cart
    return redirect('/checkout')

# Adding searched book to cart (from find book)
@app.route('/add-to-cart-link')
def add_to_cart_link():
    if 'user' not in session:
        return redirect('/log-in')
    book_title = request.args.get('book')
    if book_title:
        if 'cart' not in session:
            session['cart'] = []
        cart = session['cart']
        if book_title not in cart:
            cart.append(book_title)
            session['cart'] = cart
    return redirect('/checkout')

# Removing book from cart
@app.route('/remove-from-cart/<book_name>')
def remove_from_cart(book_name):
    if 'cart' in session:
        cart = session['cart']
        if book_name in cart:
            cart.remove(book_name)
            session['cart'] = cart
    return redirect('/checkout')

# --- Checkout processing ---
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    dates = clock()
    return_date = dates[1]
    user = session.get('user')
    condition = 'before'
    failed_books = []
    
    if user is None:
        return redirect('/log-in')
        
    cart_items = session.get('cart', [])

    if request.method == 'POST':
        address = str(request.form.get('address', ''))
        if not cart_items:
            return redirect('/checkout')
            
        db = sqlite3.connect(DATABASE)
        cursor = db.cursor()
        
        for book in cart_items:
            all_IDs = find_IDs_with_cursor(cursor, user, book)
            if not all_IDs:
                failed_books.append(book)
                continue
                
            query_borrow = "INSERT INTO borrow (user_ID, book_ID, genre_ID, address, borrow_date, borrow_due) VALUES (?, ?, ?, ?, ?, ?);"
            cursor.execute(query_borrow, (all_IDs[0], all_IDs[1], all_IDs[2], address, dates[0], dates[1]))
            
            query_user = "UPDATE user SET borrow_number = borrow_number + 1 WHERE name = ?;"
            cursor.execute(query_user, (user,))
            
        db.commit()
        db.close()
        
        if len(failed_books) == 0:
            session.pop('cart', None)
            condition = 'after'
        else:
            condition = 'partial_failed'

    return render_template('checkout.html', return_date=return_date, user=user, cart_items=cart_items, failed_books=failed_books, condition=condition)

def find_IDs_with_cursor(cursor, username, book):
    cursor.execute("SELECT ID, genre_ID FROM books WHERE book_name = ?;", (book,))
    results = cursor.fetchone()
    if not results:
        return False
    try:
        book_ID, genre_ID = results[0], results[1] 
        cursor.execute("SELECT ID FROM user WHERE name = ?;", (username,))
        name_ID = cursor.fetchone()[0]
        return (name_ID, book_ID, genre_ID)
    except Exception:
        return False

def clock():
    today = datetime.now()
    a_month = today + timedelta(weeks=4)
    return (today.strftime("%d-%m-%Y"), a_month.strftime("%d-%m-%Y")) 


# --- PROCESSING RETURN ---
@app.route('/return', methods=['GET', 'POST'])
def return_books():
    user = session.get('user')
    book = None
    condition = 'before'
    if user is None:
        return redirect('/')
    if request.method == 'POST':
        book = str(request.form['book'])
        condition = process_return(book, user)
    return render_template('return.html', user=user, book=book, condition=condition)

def process_return(book, user):
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    all_IDs = find_IDs_with_cursor(cursor, user, book)

    if not all_IDs:
        db.close()
        return 'failed'
    
    user_id, book_id, genre_id = all_IDs

    # Checking if the user is currently borrowing this book
    cursor.execute(
        "SELECT ID FROM borrow WHERE user_ID = ? AND book_ID = ? LIMIT 1;", 
        (user_id, book_id)
    )
    borrow_record = cursor.fetchone()

    # If book is not borrowed, then the return will fail
    if not borrow_record:
        db.close()
        return 'failed' # User never borrowed this book or already returned it!
        
    borrow_id = borrow_record[0]

    # Putting the return detail onto the 'return' table
    query_return = "INSERT INTO return (user_ID, book_ID, return_date) VALUES (?, ?, ?);"
    cursor.execute(query_return, (user_id, book_id, clock()[0]))
    
    # Deleting the old borrow return detail
    cursor.execute("DELETE FROM borrow WHERE ID = ?;", (borrow_id,))

    db.commit()
    db.close()
    return 'after'
 

if __name__ == '__main__':
    app.run(debug=True)
