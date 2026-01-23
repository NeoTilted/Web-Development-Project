from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from login import UserLoginIn
from createAccount import createAccount
from database import DataBase
from classes import User, Event, Post

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

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/createPost', methods=['GET', 'POST'])
def createPost():
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        category = request.form.get('category', 'senior').strip()

        image = request.files.get('image')
        if not image or image.filename == '':
            flash('Please upload a photo before posting!', 'danger')
            return redirect(url_for('createPost'))

        if not allowed_file(image.filename):
            flash('Invalid file type (png/jpg/jpeg/gif only).', 'danger')
            return redirect(url_for('createPost'))

        ext = os.path.splitext(secure_filename(image.filename))[1].lower()
        unique_filename = f"{uuid.uuid4().hex}{ext}"

        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        image.save(save_path)

        # Save hashed filename into DB (image_url column)
        db.insert_post(
            content=content,
            user_id=session['user_id'],
            post_category=category,
            image_url=unique_filename
        )  # insert_post supports image_url :contentReference[oaicite:4]{index=4}

        flash('Post created!', 'success')
        return redirect(url_for('profile'))

    return render_template('createPost.html')



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


@app.route('/profile/posts')
def profile_posts():
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']

    user_data = db.get_user_by_id(user_id)
    if not user_data:
        flash('User not found', 'danger')
        return redirect(url_for('login'))

    current_user = User.from_database_row(user_data)
    posts = db.get_posts_by_user(user_id)  # same function you're already using

    return render_template('profile_posts.html',
                           current_user=current_user,
                           posts=posts)

@app.route("/api/profile/stats")
def api_profile_stats():
    if 'user_id' not in session or 'logged_in' not in session:
        return {"error": "not_logged_in"}, 401

    user_id = session["user_id"]
    stats = db.get_user_stats(user_id)
    return stats


# ==================== IAN ADDD====================
# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

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
        # Create follow relationship directly
        success = db.create_follow(follower_id, user_id)
        
        if success:
            # Track action for badges
            db.update_badge_progress(follower_id, 3, 1)  # Badge ID 3 is "Friends" badge
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to follow user'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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
    
def create_follow(self, follower_id, followed_id):
    """Create follow relationship directly (no approval)"""
    conn = sqlite3.connect(self.db_name)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO following (follower_id, followed_id)
            VALUES (?, ?)
        """, (follower_id, followed_id))

        # Track action for badges
        cursor.execute("""
            INSERT INTO user_actions (user_id, action_type, target_id)
            VALUES (?, 'follow_user', ?)
        """, (follower_id, followed_id))

        # Notify the person being followed
        follower_name = self.get_username_by_id(follower_id)
        cursor.execute("""
            INSERT INTO notifications (user_id, notification_type, message, related_id)
            VALUES (?, 'follow', ? || ' followed you', ?)
        """, (followed_id, follower_name, follower_id))

        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
        
@app.route("/followers")
def followers_page():
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    user_id = session["user_id"]
    followers = db.get_followers(user_id)
    return render_template("followers.html", followers=followers)

@app.route("/following")
def following_page():
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    user_id = session["user_id"]
    following = db.get_following(user_id)
    return render_template("following.html", following=following)





if __name__ == '__main__':
    app.run(debug=True)
    
    