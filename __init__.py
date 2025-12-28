from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from login import UserLoginIn
from createAccount import createAccount
from database import DataBase
from classes import User, Post, Event, Badge, Following, FollowRequest, PostPrompt, Comment, UserAction

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here' 

# Initialize database helper
db = DataBase()

#Login Page
@app.route('/', methods=['GET', 'POST'])
def login():
    user_login_form = UserLoginIn(request.form)
    
    if request.method == 'POST' and user_login_form.validate():
        user_data = db.get_user_by_username(user_login_form.username.data)

        if user_data:
            user = User.from_database_row(user_data)
            
            # Check the password hash
            if check_password_hash(user.get_password(), user_login_form.password.data):
                # Set session variables for the logged-in user
                session['user_id'] = user.get_user_id()
                session['username'] = user.get_username()
                session['user_type'] = user.get_user_type()
                session['logged_in'] = True
                
                return redirect(url_for('home'))
            else:
                flash('Invalid username or password', 'danger')
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html', form=user_login_form)

# Account Creation Page
@app.route('/createAccount', methods=['GET', 'POST'])
def accountCreation():
    create_account_form = createAccount(request.form)
    if request.method == 'POST' and create_account_form.validate():
        try:
            # Check if username already exists
            existing_user = db.get_user_by_username(create_account_form.username.data)
            if existing_user:
                flash('Username already exists!', 'danger')
                return render_template('createAccount.html', form=create_account_form)
            
            # Insert user into database
            hashed_password = generate_password_hash(
                create_account_form.password.data,
                method='pbkdf2:sha256',
                salt_length=16
            )

            user_id = db.insert_user(
                username=create_account_form.username.data,
                password=hashed_password,
                user_type=create_account_form.user_type.data
            )

            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"Error: {e}")
            flash('An error occurred. Please try again.', 'danger')

    return render_template('createAccount.html', form=create_account_form)

# Home Page
@app.route('/home')
def home():
    # Check if user is logged in
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    # Get current user's ID from session
    current_user_id = session['user_id']
    
    # Get only the current user from database
    user_data = db.get_user_by_id(current_user_id)  # You need to create this function
    
    if not user_data:
        flash('User not found', 'danger')
        return redirect(url_for('login'))
    
    # Convert to User object
    current_user = User.from_database_row(user_data)
    
    # Pass only the current user to template
    return render_template('home.html', current_user=current_user)

if __name__ == '__main__':
    app.run(debug=True)
