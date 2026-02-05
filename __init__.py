"""Bond Buddies Flask App (Routes + Helpers)

This file groups routes by feature for easier presentation:
- Imports & configuration
- Authentication
- Home/Feed & Search
- Profile management
- Follow/Unfollow APIs
- Post management
- Event management
- Badge/Notification helpers

Note: Only formatting + comments were added; logic is unchanged."""

# ==================== IMPORTS & SETUP ====================

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from login import UserLoginIn
from createAccount import createAccount
from database import DataBase
from classes import User, Event
import sqlite3
import uuid
import os

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Check if the file extension is allowed"""
    if not filename:
        return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize database helper
db = DataBase()


# ==================== AUTHENTICATION ROUTES ====================

# Login Page
@app.route('/', methods=['GET', 'POST'])
def login():
    user_login_form = UserLoginIn(request.form)
    if request.method == 'POST' and user_login_form.validate():
        user_data = db.get_user_by_username(user_login_form.username.data)
        if user_data:
            user = User.from_database_row(user_data)
            if check_password_hash(user.get_password(), user_login_form.password.data):
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
            existing_user = db.get_user_by_username(create_account_form.username.data)
            if existing_user:
                flash('Username already exists!', 'danger')
                return render_template('createAccount.html', form=create_account_form)

            hashed_password = generate_password_hash(
                create_account_form.password.data,
                method='pbkdf2:sha256',
                salt_length=16
            )
            db.insert_user(
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


# ==================== MAIN APPLICATION ROUTES ====================

# Home Page (with feed from followed users)
@app.route('/home')
def home():
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    current_user_id = session['user_id']
    user_data = db.get_user_by_id(current_user_id)

    if not user_data:
        flash('User not found', 'danger')
        return redirect(url_for('login'))

    current_user = User.from_database_row(user_data)

    # Get posts from users that the current user follows
    feed_posts = db.get_followed_users_posts(current_user_id, limit=20)

    # Format posts for display - handle variable number of columns
    posts_list = []
    for post in feed_posts:
        # Check how many columns are returned
        if len(post) >= 8:  # Has at least the basic columns
            post_dict = {
                'post_id': post[0],
                'content': post[1],
                'user_id': post[2],
                'timestamp': post[3],
                'likes': post[4],
                'category': post[5],
                'prompt_id': post[6],
                'username': post[7],  # From the JOIN with users table
            }

            # Check if image_url exists (it would be at index 8)
            if len(post) > 8 and post[8] is not None:
                post_dict['image_url'] = post[8]
            else:
                post_dict['image_url'] = None

            # Check if avatar_url exists (it would be at index 9)
            if len(post) > 9 and post[9] is not None:
                post_dict['avatar_url'] = post[9]
            else:
                post_dict['avatar_url'] = None

            posts_list.append(post_dict)

    return render_template('home.html', current_user=current_user, feed_posts=posts_list)


# User Search
@app.route('/search')
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    query = request.args.get('query', '')
    logged_in_id = session.get('user_id')
    search_results = db.search_users(query)

    users = []
    for row in search_results:
        if row[0] != logged_in_id:
            users.append(User.from_database_row(row))

    return render_template('SearchResults.html', users=users, query=query)


# ==================== PROFILE MANAGEMENT ROUTES ====================

# Delete Account
@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' in session:
        db.delete_user(session['user_id'])
        session.clear()
        flash('Account deleted successfully', 'success')
    return redirect(url_for('login'))


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Edit Profile
@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    bio = (request.form.get('bio') or "").strip()
    email = (request.form.get('email') or "").strip()

    avatar = request.files.get('avatar')
    avatar_filename = None

    if avatar and avatar.filename:
        ext = os.path.splitext(secure_filename(avatar.filename))[1]
        unique_filename = f"avatar_{uuid.uuid4().hex}{ext}"

        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        avatar.save(save_path)

        # store ONLY filename
        avatar_filename = unique_filename

    # Use existing DB update function
    db.update_user(
        user_id=user_id,
        email=email,
        bio=bio,
        avatar_url=avatar_filename
    )

    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))

# Profile View
@app.route('/profile')
@app.route('/profile/<int:user_id>')
def profile(user_id=None):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # If no user_id provided, show current user's profile
    if user_id is None:
        user_id = session['user_id']

    user_data = db.get_user_by_id(user_id)
    if not user_data:
        flash('User not found', 'danger')
        return redirect(url_for('home'))

    target_user = User.from_database_row(user_data)

    # Get user stats
    stats = db.get_user_stats(user_id)

    # Get user badges
    badges_list = db.get_user_badges_with_progress(user_id)

    # Determine if viewing own profile
    viewing_own_profile = (session['user_id'] == user_id)

    # Get user's posts
    user_posts = db.get_posts_by_user(user_id)

    # Check follow status
    is_following = False
    if not viewing_own_profile:
        is_following = db.check_follow_status(session['user_id'], user_id)

    return render_template('profile.html',
                        current_user=target_user,
                        stats=stats,
                        badges=badges_list,
                        posts=user_posts,
                        viewing_own_profile=viewing_own_profile,
                        profile_user_id=user_id,
                        is_following=is_following)


# ==================== FOLLOW/UNFOLLOW API ENDPOINTS ====================

# API endpoint to follow a user
@app.route('/api/follow/<int:user_id>', methods=['POST'])
def api_follow_user(user_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    follower_id = session['user_id']

    if follower_id == user_id:
        return jsonify({'success': False, 'error': 'Cannot follow yourself'}), 400

    # Check if already following
    if db.check_follow_status(follower_id, user_id):
        return jsonify({'success': False, 'error': 'Already following'}), 400

    try:
        follow_created, new_action = db.create_follow(follower_id, user_id)

        if not follow_created:
            return jsonify({"success": False, "error": "Failed to follow user"}), 500

        badge_unlocked = False

        if new_action:
            badge_unlocked, prog, req = db.update_badge_progress(follower_id, 3, 1)

        payload = {
        "success": True,
        "is_following": True,
        "badge_unlocked": badge_unlocked
    }

        if badge_unlocked:
            payload.update({
            "iconSrc": url_for("static", filename="img/badges/friends.png"),
            "title": "Friends Badge Unlocked!",
            "subtitle": "🎉 Completed 🎉"
        })

        return jsonify(payload)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# API endpoint to unfollow a user
@app.route('/api/unfollow/<int:user_id>', methods=['POST'])
def api_unfollow_user(user_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    follower_id = session['user_id']

    try:
        success = db.unfollow_user(follower_id, user_id)

        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Not following this user'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# API endpoint to check follow status
@app.route('/api/check_follow/<int:user_id>', methods=['GET'])
def check_follow_status(user_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    follower_id = session['user_id']
    is_following = db.check_follow_status(follower_id, user_id)

    return jsonify({'success': True, 'is_following': is_following})


# ==================== POST MANAGEMENT ROUTES ====================

# Create Post
@app.route('/createPost', methods=['GET', 'POST'])
def createPost():
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Check if image exists in request
        if 'image' not in request.files:
            flash('No image part in request', 'danger')
            return redirect(url_for('createPost'))

        image = request.files['image']
        content = request.form.get('content', '').strip()
        category = request.form.get('category', 'senior')

        # Validate image
        if image.filename == '':
            flash('No selected file', 'danger')
            return redirect(url_for('createPost'))

        if not allowed_file(image.filename):
            flash('Invalid file type. Allowed: png, jpg, jpeg, gif', 'danger')
            return redirect(url_for('createPost'))

        # Save the image
        filename = secure_filename(image.filename)
        # Create unique filename
        unique_filename = str(uuid.uuid4()) + '_' + filename
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

        try:
            image.save(save_path)
        except Exception as e:
            flash(f'Error saving image: {str(e)}', 'danger')
            return redirect(url_for('createPost'))

        # Insert post into database
        try:
            # Check if db.insert_post accepts image_url parameter
            post_id = db.insert_post(
                content=content,
                user_id=session['user_id'],
                post_category=category,
                post_prompt_id=None,  # Optional: add prompt selection later
                image_url=unique_filename  # This is the new parameter
            )

            if post_id:
                flash('Post created successfully!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Failed to create post', 'danger')
                return redirect(url_for('createPost'))

        except Exception as e:
            print(f"Database error: {e}")
            # Try without image_url parameter (fallback)
            try:
                post_id = db.insert_post(
                    content=content,
                    user_id=session['user_id'],
                    post_category=category
                )
                flash('Post created without image!', 'warning')
                return redirect(url_for('home'))
            except Exception as e2:
                flash(f'Error creating post: {str(e2)}', 'danger')
                return redirect(url_for('createPost'))

    # GET request - show the form
    return render_template('createPost.html')

@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
def edit_post_route(post_id):
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    post = db.get_post_by_id(post_id)
    if not post:
        flash('Post not found', 'danger')
        return redirect(url_for('profile'))

    # post[2] = user_id in your DB structure
    if post[2] != session['user_id']:
        flash('You can only edit your own post.', 'danger')
        return redirect(url_for('profile'))

    if request.method == 'POST':
        new_content = request.form.get('content', '').strip()

        if not new_content:
            flash('Post content cannot be empty.', 'danger')
            return redirect(url_for('edit_post_route', post_id=post_id))

        db.update_post(post_id, new_content)
        flash('Post updated!', 'success')
        return redirect(url_for('profile'))

    return render_template('edit_post.html', post=post)


# ==================== POST API ENDPOINTS ====================

# API endpoint to delete a post
@app.route('/api/delete_post/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    try:
        # Check if user owns the post
        post_data = db.get_post_by_id(post_id)
        if not post_data:
            return jsonify({'success': False, 'error': 'Post not found'}), 404

        if post_data[2] != session['user_id']:  # post_data[2] is user_id
            return jsonify({'success': False, 'error': 'Not authorized to delete this post'}), 403

        db.delete_post(post_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# API endpoint to like a post
@app.route('/api/like_post/<int:post_id>', methods=['POST'])
def like_post(post_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    user_id = session['user_id']

    try:
        # Check if already liked
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()

        cursor.execute('UPDATE posts SET likes = likes + 1 WHERE post_id = ?', (post_id,))
        conn.commit()

        # Track action for badges
        cursor.execute('''
        INSERT INTO user_actions (user_id, action_type, target_id)
        VALUES (?, 'like_post', ?)
        ''', (user_id, post_id))

        # Check and award badges
        db.check_and_award_badges(user_id)

        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== APPLICATION ENTRY POINT ====================
if __name__ == '__main__':
    app.run(debug=True)
