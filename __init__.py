from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from login import UserLoginIn
from createAccount import createAccount
from database import DataBase
from classes import User, Post, Event, Badge, Following, FollowRequest, PostPrompt, Comment, UserAction
from flask import send_from_directory
import os, uuid
 

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

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#Changes
@app.route('/createPost', methods=['GET', 'POST'])
def createPost():
    app.config['UPLOAD_FOLDER'] = 'uploads'
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        image = request.files.get('image')
        content = request.form.get('content', '')
        post_category = request.form.get('category', 'senior')
        
        if not image or image.filename == '':
            flash('Please select an image', 'danger')
            return redirect(url_for('createPost'))
        
        if not allowed_file(image.filename):
            flash('Invalid file type. Allowed: png, jpg, jpeg, gif', 'danger')
            return redirect(url_for('createPost'))
        
        # Generate unique filename
        filename = secure_filename(image.filename)
        ext = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{ext}"  # This is hashed
        
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        image.save(save_path)
        
        # Save post data to database with the HASED filename
        try:
            post_id = db.insert_post(
                content=content,
                user_id=session['user_id'],
                post_category=post_category,
                image_url=unique_filename  # Make sure this is the hashed name!
            )

            return redirect(url_for('home'))
        except Exception as e:
            print(f"Error saving post: {e}")
            flash('Error creating post. Please try again.', 'danger')
            return redirect(url_for('createPost'))
    
    return render_template('createPost.html')

# Update the explore route to use image_url:
@app.route('/explore', methods=['GET'])
def explore():
    # Check if user is logged in
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    # Get filter parameters from request
    filters = request.args.getlist('filters')
    sort_by = request.args.get('sort', 'newest')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get posts based on filters
    if filters:
        posts_data = []
        for filter_type in filters:
            if filter_type == 'senior':
                senior_posts = db.get_posts_by_category('senior')
                posts_data.extend(senior_posts)
            elif filter_type == 'junior':
                junior_posts = db.get_posts_by_category('junior')
                posts_data.extend(junior_posts)
            elif filter_type == 'trending':
                trending_posts = db.get_trending_posts()
                posts_data.extend(trending_posts)
            elif filter_type == 'hot':
                hot_posts = db.get_hot_posts()
                posts_data.extend(hot_posts)
        
        # Remove duplicates
        seen = set()
        unique_posts = []
        for post in posts_data:
            post_id = post[0]
            if post_id not in seen:
                seen.add(post_id)
                unique_posts.append(post)
        
        posts_data = unique_posts
    else:
        # Get random posts with images by default
        posts_data = db.get_posts_with_images(limit=per_page)
    
    # Convert to Post objects and include image_url
    posts = []
    for post_data in posts_data:
        if len(post_data) >= 8:  # Check if we have enough data (including image_url)
            post = Post.from_database_row(post_data)
            # Get username for each post
            user_data = db.get_user_by_id(post.get_user_id())
            username = user_data[1] if user_data else "Unknown User"
            
            # Get comments count
            comments = db.get_comments_by_post(post.get_post_id())
            comment_count = len(comments) if comments else 0
            
            # Get image_url from the row
            image_url = post.get_image_url()
            
            posts.append({
                'post': post,
                'username': username,
                'comment_count': comment_count,
                'image_url': image_url
            })
    
    # Check if it's an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('posts_partial.html', posts=posts)
    
    return render_template('explore.html', posts=posts)

@app.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    app.config['UPLOAD_FOLDER'] = 'uploads'
    """Serve uploaded files from the uploads folder"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



#WONGDFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
import re
from werkzeug.security import generate_password_hash

def is_valid_email(email: str) -> bool:
    if not email:
        return True  # allow empty
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


@app.route('/profile')
def profile():
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Award any badges user qualifies for (based on actions)
    db.check_and_award_badges(user_id)  # exists in your DataBase :contentReference[oaicite:4]{index=4}

    user_data = db.get_user_by_id(user_id)  # exists :contentReference[oaicite:5]{index=5}
    if not user_data:
        flash('User not found', 'danger')
        return redirect(url_for('login'))

    current_user = User.from_database_row(user_data)  # exists :contentReference[oaicite:6]{index=6}
    badges = db.get_user_badges(user_id)              # exists :contentReference[oaicite:7]{index=7}
    posts = db.get_posts_by_user(user_id)             # exists :contentReference[oaicite:8]{index=8}
    stats = db.get_user_stats(user_id)                # exists :contentReference[oaicite:9]{index=9}

    return render_template('profile.html',
                           current_user=current_user,
                           badges=badges,
                           posts=posts,
                           stats=stats)


#WONGDFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
import re

@app.route('/profile/edit', methods=['POST'])
def edit_profile():
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    email = request.form.get('email', '').strip()
    bio = request.form.get('bio', '').strip()
    new_password = request.form.get('new_password', '').strip()

    # Validation (rubric: extensive validation + good messages)
    if len(bio) > 200:
        flash('Bio must be 200 characters or less.', 'danger')
        return redirect(url_for('profile'))

    if not is_valid_email(email):
        flash('Please enter a valid email format (example: name@gmail.com).', 'danger')
        return redirect(url_for('profile'))

    # Optional avatar upload
    avatar = request.files.get('avatar')
    avatar_url = None
    if avatar and avatar.filename:
        if not allowed_file(avatar.filename):
            flash('Avatar must be png/jpg/jpeg/gif only.', 'danger')
            return redirect(url_for('profile'))

        ext = os.path.splitext(secure_filename(avatar.filename))[1]
        unique_filename = f"avatar_{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        avatar.save(save_path)
        avatar_url = f"/static/uploads/{unique_filename}"

    # Optional password update
    hashed_password = None
    if new_password:
        if len(new_password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return redirect(url_for('profile'))
        hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256', salt_length=16)

    # Update in DB (function already exists)
    db.update_user(
        user_id=user_id,
        password=hashed_password,
        email=email if email != '' else None,
        bio=bio,
        avatar_url=avatar_url
    )  # db.update_user exists :contentReference[oaicite:10]{index=10}

    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))


@app.route('/follow/<int:target_id>', methods=['POST'])
def follow_user(target_id):
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    requester_id = session['user_id']
    if requester_id == target_id:
        flash("You can't follow yourself.", 'danger')
        return redirect(url_for('profile'))

    success = db.create_follow_request(requester_id, target_id)  # exists :contentReference[oaicite:11]{index=11}
    if success:
        flash('Follow request sent!', 'success')
    else:
        flash('Follow request already exists (or user not found).', 'warning')

    return redirect(url_for('profile'))


@app.route('/profile/delete', methods=['POST'])
def delete_account():
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    confirm = request.form.get('confirm', '').strip().lower()

    if confirm != 'delete':
        flash("Type 'delete' to confirm account deletion.", 'danger')
        return redirect(url_for('profile'))

    db.delete_user(user_id)  # exists :contentReference[oaicite:12]{index=12}
    session.clear()
    flash('Account deleted.', 'success')
    return redirect(url_for('login'))

#WONGDFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF







if __name__ == '__main__':
    app.run(debug=True)

