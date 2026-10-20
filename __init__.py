from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from login import UserLoginIn
from createAccount import createAccount
from forgotPassword import ForgotPasswordForm, ResetPasswordForm
from changePassword import ChangePasswordForm
from database import DataBase
import smtplib
from email.message import EmailMessage
from classes import (
    User,
    Post,
    Event
)
import sqlite3
import os, uuid
import re
import time
from datetime import datetime
from collections import defaultdict
from functools import wraps
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

user_like_timestamps = defaultdict(float)
LIKE_COOLDOWN_SECONDS = 1.0  # 1 second cooldown

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key-here"
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ADMIN_CREATION_KEY='your_super_secure_random_key_here'
ADMIN_SECRET_HASH='sha256_hash_of_the_key'

# Initialize database helper
db = DataBase()
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

# ===================== DATABASE CONNECTION HELPER =====================
def get_db_connection():
    DATABASE = 'bond_buddies.db'
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def allowed_file(filename):

    """Check if the file extension is allowed"""

    if not filename:

        return False

    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== AUTHENTICATION ROUTES ====================

@app.route("/", methods=["GET", "POST"])
def login():
    user_login_form = UserLoginIn(request.form)
    show_deleted_modal = False

    if request.method == "POST" and user_login_form.validate():
        username = user_login_form.username.data
        password = user_login_form.password.data
        
        print(f"Login attempt for username: {username}")
        
        # First check if this is a deleted account
        deleted_account = db.check_deleted_account(username)
        if deleted_account:
            print(f"Deleted account detected: {deleted_account}")
            # Store deletion info in session for one-time display
            session['deleted_account_message'] = {
                'reason': deleted_account['reason'],
                'date': deleted_account['deletion_date'],
                'username': deleted_account['username'],
                'user_id': deleted_account.get('user_id', 'Unknown')
            }
            flash('This account has been deleted. Please contact support for more information.', 'danger')
            show_deleted_modal = True
            # Re-render the login form with the modal flag
            return render_template("login.html", form=user_login_form, show_deleted_modal=show_deleted_modal)
        
        # Regular login flow
        user_data = db.get_user_by_username(username)

        if user_data:
            user = User.from_database_row(user_data)

            if check_password_hash(user.get_password(), password):
                session["user_id"] = user.get_user_id()
                session["username"] = user.get_username()
                session["user_type"] = user.get_user_type()
                session["logged_in"] = True
                
                # Check for active warnings
                warning_status = db.check_user_warning_status(user.get_user_id())
                if warning_status['total_active_warnings'] > 0:
                    session['has_active_warnings'] = True
                    session['warning_count'] = warning_status['total_active_warnings']
                    session['strike_count'] = warning_status['strike_count']
                    
                    recent_warnings = db.get_user_warnings(user.get_user_id(), active_only=True)
                    if recent_warnings and len(recent_warnings) > 0:
                        session['latest_warning_reason'] = recent_warnings[0][1]
                        session['latest_warning_date'] = recent_warnings[0][4]
                else:
                    session['has_active_warnings'] = False

                # Check if user is admin
                if user.get_user_type() == 'admin':
                    flash("Welcome, Administrator!", "success")
                    return redirect(url_for("admin_dashboard"))
                
                return redirect(url_for("home"))
            else:
                flash("Invalid username or password", "danger")
        else:
            flash("Invalid username or password", "danger")

    return render_template("login.html", form=user_login_form, show_deleted_modal=show_deleted_modal)

@app.route('/clear_deleted_message', methods=['POST'])
def clear_deleted_message():
    """Clear the deleted account message from session"""
    session.pop('deleted_account_message', None)
    return jsonify({'success': True})

@app.route('/clear_warning_message', methods=['POST'])
def clear_warning_message():
    """Clear the warning message flag but keep warning data if needed"""
    # We keep the warning data in session for the duration of the session
    # but we mark that it's been shown
    session['warning_shown'] = True
    return jsonify({'success': True})

# Account Creation Page
@app.route("/createAccount", methods=["GET", "POST"])
def accountCreation():
    create_account_form = createAccount(request.form)
    
    if request.method == "POST":
        if create_account_form.validate():
            try:
                existing_user = db.get_user_by_username(create_account_form.username.data)
                if existing_user:
                    flash("Username already exists!", "danger")
                    return render_template("createAccount.html", form=create_account_form)

                hashed_password = generate_password_hash(
                    create_account_form.password.data,
                    method="pbkdf2:sha256",
                    salt_length=16,
                )

                user_id = db.insert_user(
                    username=create_account_form.username.data,
                    password=hashed_password,
                    user_type=create_account_form.user_type.data,
                    email=create_account_form.email.data
                )

                flash("Account created successfully! Please login.", "success")
                return redirect(url_for("login"))

            except Exception as e:
                print(f"Error: {e}")
                flash("An error occurred. Please try again.", "danger")
        else:
            # Flash each field validation error
            for field_name, errors in create_account_form.errors.items():
                for error in errors:
                    flash(f"{error}", "danger")

    return render_template("createAccount.html", form=create_account_form)

# ==== ETHAN FORGOT PASSWORD  + email sending ===

@app.route('/forgotPassword', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm(request.form)
    if request.method == "POST" and form.validate():
        email = form.email.data
        user = db.get_user_by_email(email)

        # Always flash the same message to prevent info leak
        flash("If an account with that email exists, a reset link has been sent.", "info")

        if user:
            user_id = user[0]  # assuming user_id is at index 0
            token = s.dumps(email, salt="password-reset-salt")
            
            # Save the token in DB (for one-time use)
            db.set_reset_token(user_id, token)
            
            reset_link = url_for("reset_password", token=token, _external=True)

            # Create email
            msg = EmailMessage()
            msg['Subject'] = "Bond Buddies Password Reset"
            msg['From'] = "bondbuddiespublicity@gmail.com"
            msg['To'] = email
        
            # Plain-text fallback
            msg.set_content(f"Hi {user[1]},\n\n"
                            f"We received a request to reset your Bond Buddies password.\n"
                            f"Reset link: {reset_link}\n\n"
                            "If you did not request this, ignore this email.\n"
                            "This link is one-time use only.\n\n"
                            "Thanks,\nBond Buddies Team")

            # Full HTML content as main body
            msg.add_alternative(f"""
                <html>
                  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <p>Hi {user[1]},</p>

                    <p>We received a request to reset your <strong>Bond Buddies</strong> account password.</p>

                    <p>To reset your password, click the button below:</p>

                    <p>
                      <a href="{reset_link}" style="display:inline-block;padding:12px 25px;
                         background-color:#007bff;color:white;text-decoration:none;border-radius:5px;font-weight:bold;">
                         Reset My Password
                      </a>
                    </p>

                    <p>This link is valid for <strong>one-time use only</strong>. If you did not request a password reset, you can safely ignore this email — your password will remain unchanged.</p>

                    <p>Thank you for using Bond Buddies!</p>

                    <p>Best regards,<br>
                       The Bond Buddies Team</p>
                  </body>
                </html>
                """, subtype='html')

            # Send email
            try:
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                    smtp.login("bondbuddiespublicity@gmail.com", "hwpx days ikjs nzhr")
                    smtp.send_message(msg)
                print(f"Reset link sent to {email}: {reset_link}")
                return redirect(url_for("login"))
            except Exception as e:
                print(f"Email sending failed: {e}")

    return render_template("forgotPassword.html", form=form)

# Flask-Mail config (example for Gmail)
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='bondbuddiespublicity@gmail.com',
    MAIL_PASSWORD='hwpx days ikjs nzhr',
    MAIL_DEFAULT_SENDER='bondbuddiespublicity@gmail.com'
)

mail = Mail(app)

s = URLSafeTimedSerializer(app.secret_key)

def generate_token(email):
    return s.dumps(email, salt='password-reset-salt')

def verify_token(token, expiration=3600):
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=expiration)
    except:
        return None
    return email

@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    form = ResetPasswordForm(request.form)
    
    # Fetch user by token
    user = db.get_user_by_reset_token(token)
    if not user:
        flash("This reset link is invalid or has already been used.", "danger")
        return redirect(url_for("login"))
    
    if request.method == "POST" and form.validate():
        new_password = form.password.data
        current_hashed_password = user[2]  # Assuming password is index 2 in users table

        # ======================
        # Password validation
        # ======================
        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$'
        if not re.match(pattern, new_password):
            flash("Invalid password. Must be at least 8 characters, with uppercase, lowercase, number, and special character.", "danger")
            return render_template("resetPassword.html", form=form)

        # ======================
        # Prevent reusing old password
        # ======================
        if check_password_hash(current_hashed_password, new_password):
            flash("You cannot reuse your previous password. Please choose a new one.", "danger")
            return render_template("resetPassword.html", form=form)

        # ======================
        # Hash new password and update
        # ======================
        hashed_password = generate_password_hash(new_password, method="pbkdf2:sha256", salt_length=16)
        db.update_user(user_id=user[0], password=hashed_password)
        
        # Clear the reset token to prevent reuse
        db.clear_reset_token(user[0])

        flash("Your password has been reset successfully! Please log in with your new password.", "success")
        return redirect(url_for("login"))

    return render_template("resetPassword.html", form=form)

@app.route("/changepassword", methods=["GET", "POST"])
def change_password():
    form = ChangePasswordForm(request.form)

    # Get current user from session
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in to change your password.", "danger")
        return redirect(url_for("login"))

    # Fetch user from DB
    user = db.get_user_by_id(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("login"))

    current_hashed_password = user[2]  # Assuming password is at index 2

    if request.method == "POST" and form.validate():
        current_password_input = form.current_password.data
        new_password = form.new_password.data

        # ======================
        # 1️⃣ Check current password
        # ======================
        if not check_password_hash(current_hashed_password, current_password_input):
            flash("Your current password is incorrect.", "danger")
            return render_template("changePassword.html", form=form)

        # ======================
        # 2️⃣ Validate new password syntax
        # ======================
        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$'
        if not re.match(pattern, new_password):
            flash(
                "New password is invalid. Must be at least 8 characters long and include "
                "1 uppercase letter, 1 lowercase letter, 1 number, and 1 special character.",
                "danger"
            )
            return render_template("changePassword.html", form=form)

        # ======================
        # 3️⃣ Prevent reusing current password
        # ======================
        if check_password_hash(current_hashed_password, new_password):
            flash("New password cannot be the same as your current password.", "danger")
            return render_template("changePassword.html", form=form)

        # ======================
        # 4️⃣ Hash and update
        # ======================
        hashed_new_password = generate_password_hash(
            new_password, method="pbkdf2:sha256", salt_length=16
        )
        db.update_user(user_id=user_id, password=hashed_new_password)

        # Optional: log out user after password change
        session.pop("user_id", None)
        flash("Password changed successfully! Please login again.", "success")
        return redirect(url_for("login"))

    return render_template("changePassword.html", form=form)

# ==================== HOME PAGE (MERGED) ====================

@app.route('/home')
def home():
    # Must be logged in
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    current_user_id = session['user_id']
    user_data = db.get_user_by_id(current_user_id)

    if not user_data:
        flash('User not found', 'danger')
        return redirect(url_for('login'))

    current_user = User.from_database_row(user_data)
    
    # -------- Get blocked users list from database --------
    try:
        # This gets both users I blocked AND users who blocked me
        blocked_users = db.get_blocked_user_ids(current_user_id)
        blocked_users_set = set(blocked_users) if blocked_users else set()
        print(f"Blocked users for {current_user_id}: {blocked_users_set}")  # Debug print
    except Exception as e:
        print(f"Error getting blocked users: {e}")
        blocked_users_set = set()
    
    # Get initial posts (excluding blocked users)
    initial_posts = []
    try:
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()
        
        # Build query with blocked users exclusion
        if blocked_users_set:
            placeholders = ','.join(['?'] * len(blocked_users_set))
            query = f'''
                SELECT p.*, u.username, u.avatar_url, 
                       CASE WHEN f.followed_id IS NOT NULL THEN 1 ELSE 0 END as is_followed
                FROM posts p
                JOIN users u ON p.user_id = u.user_id
                LEFT JOIN following f ON f.follower_id = ? AND f.followed_id = p.user_id
                WHERE p.user_id NOT IN ({placeholders})
                ORDER BY is_followed DESC, p.timestamp DESC
                LIMIT 10
            '''
            params = [current_user_id] + list(blocked_users_set)
        else:
            query = '''
                SELECT p.*, u.username, u.avatar_url, 
                       CASE WHEN f.followed_id IS NOT NULL THEN 1 ELSE 0 END as is_followed
                FROM posts p
                JOIN users u ON p.user_id = u.user_id
                LEFT JOIN following f ON f.follower_id = ? AND f.followed_id = p.user_id
                ORDER BY is_followed DESC, p.timestamp DESC
                LIMIT 10
            '''
            params = [current_user_id]
        
        cursor.execute(query, params)
        posts_data = cursor.fetchall()
        
        # Debug: Print which users' posts are being shown
        shown_users = set()
        for post in posts_data:
            shown_users.add(post[2])  # user_id is at index 2
        print(f"Showing posts from users: {shown_users}")
        
        for post in posts_data:
            timestamp = post[3]
            formatted_time = timestamp
            try:
                if timestamp:
                    dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                    formatted_time = dt.strftime('%d-%m-%Y, %H:%M')
            except:
                pass
    
            post_dict = {
                'post_id': post[0],
                'content': post[1],
                'user_id': post[2],
                'timestamp': formatted_time,
                'likes': post[4],
                'category': post[5],
                'prompt_id': post[6],
                'image_url': post[7] if len(post) > 7 and post[7] else None,
                'username': post[8],
                'avatar_url': post[9] if len(post) > 9 and post[9] else None,
                'is_followed': post[10] if len(post) > 10 else False,
                'user_has_liked': db.get_user_like_status(current_user_id, post[0])
            }
            initial_posts.append(post_dict)
        
        conn.close()
    except Exception as e:
        print(f"Error loading initial posts: {e}")
    
    # Get events data (excluding events from blocked users)
    formatted_events = []
    upcoming_events_data = []
    show_tutorial_prompt = not db.has_seen_tutorial(current_user_id)
    
    try:
        # Get all events
        all_events = db.get_all_events()
        
        # Filter out events from blocked users
        for event in all_events:
            # Check if event organizer is blocked
            if event[7] in blocked_users_set:
                continue
                
            event_dict = {
                'event_id': event[0],
                'event_name': event[1],
                'event_itinerary': event[2],
                'event_duration': event[3],
                'event_date': event[4],
                'location': event[5],
                'max_participants': event[6],
                'user_id': event[7],
                'game_type': event[8],
                'game_rules': event[9],
                'organizer': event[10] if len(event) > 10 else 'Unknown',
                'participants_count': event[11] if len(event) > 11 else 0,
                'has_joined': db.has_user_joined_event(current_user_id, event[0])
            }
            formatted_events.append(event_dict)
        
        # Get upcoming events
        upcoming_events = db.get_upcoming_events()
        for event in upcoming_events:
            # Check if event organizer is blocked
            if event[7] in blocked_users_set:
                continue
                
            event_dict = {
                'event_id': event[0],
                'event_name': event[1],
                'event_date': event[4],
                'location': event[5],
                'organizer': event[10] if len(event) > 10 else 'Unknown'
            }
            upcoming_events_data.append(event_dict)
            
    except Exception as e:
        print(f"Error loading events: {e}")
        flash("Could not load events", "warning")
    
    return render_template(
        'home.html',
        current_user=current_user,
        feed_posts=initial_posts,
        events=formatted_events,
        upcoming_events=upcoming_events_data,
        show_tutorial_prompt=show_tutorial_prompt
    )
    
# ==================== HOME PAGE API FOR INFINITE SCROLL ====================

@app.route('/api/home_posts')
def api_home_posts():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    current_user_id = session['user_id']
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    offset = (page - 1) * per_page
    
    # -------- Get blocked users list from database --------
    try:
        blocked_users = db.get_blocked_user_ids(current_user_id)
        blocked_users_set = set(blocked_users) if blocked_users else set()
    except Exception as e:
        print(f"Error getting blocked users: {e}")
        blocked_users_set = set()
    
    try:
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()
        
        # Build query with blocked users exclusion
        if blocked_users_set:
            placeholders = ','.join(['?'] * len(blocked_users_set))
            query = f'''
                SELECT p.*, u.username, u.avatar_url, 
                       CASE WHEN f.followed_id IS NOT NULL THEN 1 ELSE 0 END as is_followed
                FROM posts p
                JOIN users u ON p.user_id = u.user_id
                LEFT JOIN following f ON f.follower_id = ? AND f.followed_id = p.user_id
                WHERE p.user_id NOT IN ({placeholders})
                ORDER BY is_followed DESC, p.timestamp DESC
                LIMIT ? OFFSET ?
            '''
            params = [current_user_id] + list(blocked_users_set) + [per_page, offset]
        else:
            query = '''
                SELECT p.*, u.username, u.avatar_url, 
                       CASE WHEN f.followed_id IS NOT NULL THEN 1 ELSE 0 END as is_followed
                FROM posts p
                JOIN users u ON p.user_id = u.user_id
                LEFT JOIN following f ON f.follower_id = ? AND f.followed_id = p.user_id
                ORDER BY is_followed DESC, p.timestamp DESC
                LIMIT ? OFFSET ?
            '''
            params = [current_user_id, per_page, offset]
        
        cursor.execute(query, params)
        posts_data = cursor.fetchall()
        
        # Format posts
        posts_list = []
        for post in posts_data:
            timestamp = post[3]
            formatted_time = timestamp
            try:
                if timestamp:
                    dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                    formatted_time = dt.strftime('%d-%m-%Y, %H:%M')
            except:
                pass
    
            post_dict = {
                'post_id': post[0],
                'content': post[1],
                'user_id': post[2],
                'timestamp': formatted_time,
                'likes': post[4],
                'category': post[5],
                'prompt_id': post[6],
                'image_url': post[7] if len(post) > 7 and post[7] else None,
                'username': post[8],
                'avatar_url': post[9] if len(post) > 9 and post[9] else None,
                'is_followed': post[10] if len(post) > 10 else False,
                'user_has_liked': db.get_user_like_status(current_user_id, post[0])
            }
            posts_list.append(post_dict)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'posts': posts_list,
            'has_more': len(posts_data) == per_page
        })
    except Exception as e:
        print(f"Error in api_home_posts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== EXPLORE PAGE ====================

#-------------------------------------NJJ---------------------------------------------------------
@app.route("/explore", methods=["GET"])
def explore():
    # Check if user is logged in
    if "user_id" not in session or "logged_in" not in session:
        flash("Please login first", "warning")
        return redirect(url_for("login"))

    # Get filter parameters from request
    filters = request.args.getlist("filters")
    sort_by = request.args.get("sort", "newest")
    page = request.args.get("page", 1, type=int)
    per_page = 10

    # Get posts based on filters
    posts_data = []
    filter_messages = []

    # Process each filter type
    if filters:
        for filter_type in filters:
            if filter_type == "senior":
                # Fetch posts with senior category
                senior_posts = db.get_posts_by_category("senior")
                if senior_posts:
                    posts_data.extend(senior_posts)
                    filter_messages.append(f"Found {len(senior_posts)} senior posts")
                else:
                    filter_messages.append("No senior posts found")

            elif filter_type == "youth":
                # Fetch posts with youth category
                youth_posts = db.get_posts_by_category("youth")
                if youth_posts:
                    posts_data.extend(youth_posts)
                    filter_messages.append(f"Found {len(youth_posts)} youth posts")
                else:
                    filter_messages.append("No youth posts found")

            elif filter_type == "trending":
                # Fetch trending posts (based on likes/comments)
                trending_posts = db.get_trending_posts()
                if trending_posts:
                    posts_data.extend(trending_posts)
                    filter_messages.append(
                        f"Found {len(trending_posts)} trending posts"
                    )
                else:
                    filter_messages.append("No trending posts found")

            elif filter_type == "hot":
                # Fetch hot posts (recent popular posts)
                hot_posts = db.get_hot_posts()
                if hot_posts:
                    posts_data.extend(hot_posts)
                    filter_messages.append(f"Found {len(hot_posts)} hot posts")
                else:
                    filter_messages.append("No hot posts found")

        # Remove duplicate posts (if multiple filters match same posts)
        if posts_data:
            seen = set()
            unique_posts = []
            for post in posts_data:
                post_id = post[0] if post else None
                if post_id and post_id not in seen:
                    seen.add(post_id)
                    unique_posts.append(post)
            posts_data = unique_posts

            # Warn if senior/youth filters didn't find matching posts
    else:
        # Default: show random posts with images
        posts_data = db.get_posts_with_images(limit=per_page)

    # Convert database rows to Post objects with additional info
    posts = []
    if posts_data:
        for post_data in posts_data:
            if len(post_data) >= 8:  # Check if we have complete post data
                # Convert database row to Post object
                post = Post.from_database_row(post_data)
                
                # Get username for post author
                user_data = db.get_user_by_id(post.get_user_id())
                username = user_data[1] if user_data else "Unknown User"

                # Count comments for this post
                comments = db.get_comments_by_post(post.get_post_id())
                comment_count = len(comments) if comments else 0

                # Get image URL for display
                image_url = post.get_image_url()

                # Check if current user has liked this post
                user_has_liked = False
                if "user_id" in session:
                    user_has_liked = db.get_user_like_status(
                        session["user_id"], post.get_post_id()
                    )

                # Bundle all post data for template
                posts.append(
                    {
                        "post": post,
                        "username": username,
                        "comment_count": comment_count,
                        "image_url": image_url,
                        "user_has_liked": user_has_liked,
                    }
                )

    # Handle AJAX requests (return only posts HTML)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("explore_posts.html", posts=posts)

    # Render full page for regular requests
    return render_template('explore.html', posts=posts, filter_messages=filter_messages, 
                       current_username=session.get('username', ''))

# Like/Unlike Post
@app.route("/like_post/<int:post_id>", methods=["POST"])
def like_post(post_id):
    # Check user authentication
    if "user_id" not in session or "logged_in" not in session:
        return jsonify({"success": False, "error": "Please login first"}), 401

    user_id = session["user_id"]
    conn = None
    cursor = None

    did_like = False  # True only when user performs a LIKE (not unlike)

    try:
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()

        # Check if post exists
        cursor.execute("SELECT 1 FROM posts WHERE post_id = ?", (post_id,))
        if cursor.fetchone() is None:
            return jsonify({"success": False, "error": "Post not found"}), 404

        # Check if user already liked this post
        cursor.execute("""
            SELECT 1 FROM post_likes
            WHERE user_id = ? AND post_id = ?
        """, (user_id, post_id))
        has_liked = cursor.fetchone() is not None

        if has_liked:
            # Remove like
            cursor.execute(
                "DELETE FROM post_likes WHERE user_id = ? AND post_id = ?",
                (user_id, post_id)
            )
            cursor.execute(
                "UPDATE posts SET likes = CASE WHEN likes > 0 THEN likes - 1 ELSE 0 END WHERE post_id = ?",
                (post_id,)
            )
        else:
            # Add like
            did_like = True
            cursor.execute(
                "INSERT INTO post_likes (user_id, post_id) VALUES (?, ?)",
                (user_id, post_id)
            )
            cursor.execute(
                "UPDATE posts SET likes = likes + 1 WHERE post_id = ?",
                (post_id,)
            )

        conn.commit()

        # Get updated like count (still using same connection)
        cursor.execute("SELECT likes FROM posts WHERE post_id = ?", (post_id,))
        row = cursor.fetchone()
        like_count = row[0] if row else 0

        # Close DB first so badge update won't get locked
        conn.close()
        conn = None

        # Update Like badge AFTER closing the like transaction
        badge_unlocked = False
        badge_title = None
        badge_subtitle = None

        if did_like:
            try:
                unlocked_now, prog, req = db.update_badge_progress(user_id, badge_id=2, progress_increment=1)

                if unlocked_now:
                    badge_unlocked = True
                    badge_title = "Like a lover!"
                    badge_subtitle = "You liked your first post!"
                    badge_icon = "/static/img/badges/lover.png"
            except Exception as e:
                    print(f"Badge update error: {e}")

        return jsonify({
    "success": True,
    "liked": not has_liked,
    "like_count": like_count,
    "badge_unlocked": badge_unlocked,
    "title": badge_title,
    "subtitle": badge_subtitle,
    "iconSrc": badge_icon if badge_unlocked else None
})



    except sqlite3.IntegrityError as e:
        print(f"IntegrityError in like_post: {e}")
        try:
            if cursor:
                cursor.execute("SELECT likes FROM posts WHERE post_id = ?", (post_id,))
                row = cursor.fetchone()
                like_count = row[0] if row else 0
            else:
                like_count = 0
        except Exception:
            like_count = 0
        return jsonify({
            "success": True,
            "liked": True,
            "like_count": like_count
        })

    except Exception as e:
        print(f"Error in like_post: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


@app.route('/get_comments/<int:post_id>', methods=['GET'])
def get_comments(post_id):
    # Check user authentication
    if 'user_id' not in session or 'logged_in' not in session:
        return jsonify({'success': False, 'error': 'Please login first'})
    
    try:
        # Fetch all comments with replies for this post
        comments_data = db.get_comments_with_replies(post_id)
        
        # Format comments with readable timestamps
        formatted_comments = []
        for comment in comments_data:
            formatted_comment = {
                'comment_id': comment['comment_id'],
                'post_id': comment['post_id'],
                'user_id': comment['user_id'],
                'content': comment['content'],
                'parent_comment_id': comment['parent_comment_id'],
                'timestamp': comment['timestamp'],
                'username': comment['username'],
                'avatar_url': comment['avatar_url'],
                'reply_count': comment['reply_count'],
                'replies': comment['replies'],
                'formatted_time': format_timestamp(comment['timestamp'])
            }
            formatted_comments.append(formatted_comment)
        
        # Count total comments
        def count_total_comments(comments_list):
            total = 0
            for comment in comments_list:
                total += 1
                if comment['replies']:
                    total += count_total_comments(comment['replies'])
            return total
        
        total_comments = count_total_comments(formatted_comments)
        
        return jsonify({
            'success': True,
            'comments': formatted_comments,
            'comment_count': total_comments
        })
    except Exception as e:
        print(f"Error in get_comments: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Add Comment
@app.route('/add_comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    # Check user authentication
    if 'user_id' not in session or 'logged_in' not in session:
        return jsonify({'success': False, 'error': 'Please login first'})
    
    user_id = session['user_id']
    content = request.json.get('content', '').strip()
    
    # Validate comment content
    if not content:
        return jsonify({'success': False, 'error': 'Comment cannot be empty'})
    
    if len(content) > 1000:
        return jsonify({'success': False, 'error': 'Comment is too long (max 1000 characters)'})
    
    try:
        # Insert comment into database
        comment_id = db.insert_comment(post_id, user_id, content)
        
        if comment_id:
            # Get the new comment with full details
            comment_data = db.get_comment_by_id(comment_id)
            
            if comment_data:
                # Format timestamp as "Just now" for new comments
                timestamp = comment_data[4]
                formatted_time = "Just now"
                
                new_comment = {
                    'comment_id': comment_data[0],
                    'username': comment_data[5] if len(comment_data) > 5 else "Unknown User",
                    'content': comment_data[3],
                    'timestamp': timestamp,
                    'formatted_time': formatted_time,
                    'avatar_url': comment_data[6] if len(comment_data) > 6 else None
                }
                
                # Get updated comment count for the post
                comment_count = db.get_comment_count_by_post(post_id)

# ---- BADGE: Comment badge (badge_id = 1) ----
                badge_unlocked = False
                badge_title = None
                badge_subtitle = None
                badge_icon = None

                try:
                    unlocked_now, prog, req = db.update_badge_progress(user_id, badge_id=1, progress_increment=1)
                    if unlocked_now:
                        badge_unlocked = True
                        badge_title = "Badge unlocked!"
                        badge_subtitle = "Talking is fun!"
                        badge_icon = "/static/img/badges/comment.png"  # put your image here
                except Exception as e:
                    print(f"Comment badge error: {e}")

                return jsonify({
    'success': True,
    'comment': new_comment,
    'comment_count': comment_count,
    'badge_unlocked': badge_unlocked,
    'title': badge_title,
    'subtitle': badge_subtitle,
    'iconSrc': badge_icon
})


        return jsonify({'success': False, 'error': 'Failed to add comment'})
    except Exception as e:
        print(f"Error in add_comment: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Update Comment
@app.route('/update_comment/<int:comment_id>', methods=['PUT'])
def update_comment(comment_id):
    # Check user authentication
    if 'user_id' not in session or 'logged_in' not in session:
        return jsonify({'success': False, 'error': 'Please login first'})
    
    user_id = session['user_id']
    content = request.json.get('content', '').strip()
    
    # Validate updated content
    if not content:
        return jsonify({'success': False, 'error': 'Comment cannot be empty'})
    
    if len(content) > 1000:
        return jsonify({'success': False, 'error': 'Comment is too long (max 1000 characters)'})
    
    try:
        # Update comment in database (checks if user owns the comment)
        success = db.update_comment(comment_id, user_id, content)
        
        if success:
            # Get the updated comment details
            comment_data = db.get_comment_by_id(comment_id)
            if comment_data:
                updated_comment = {
                    'comment_id': comment_data[0],
                    'username': comment_data[5] if len(comment_data) > 5 else "Unknown User",
                    'content': comment_data[3],
                    'timestamp': comment_data[4],
                    'formatted_time': format_timestamp(comment_data[4]),
                    'avatar_url': comment_data[6] if len(comment_data) > 6 else None
                }
                
                return jsonify({
                    'success': True,
                    'comment': updated_comment
                })
        
        return jsonify({'success': False, 'error': 'Failed to update comment'})
    except Exception as e:
        print(f"Error in update_comment: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Delete Comment
@app.route('/delete_comment/<int:comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    # Check user authentication
    if 'user_id' not in session or 'logged_in' not in session:
        return jsonify({'success': False, 'error': 'Please login first'})
    
    user_id = session['user_id']
    
    try:
        # Get comment details before deletion
        comment_data = db.get_comment_by_id(comment_id)
        if not comment_data:
            return jsonify({'success': False, 'error': 'Comment not found'})
        
        # Get post_id for updating comment count
        post_id = comment_data[1]
        
        # Delete comment (checks if user owns the comment)
        success = db.delete_comment(comment_id, user_id)
        
        if success:
            # Get updated comment count for the post
            comment_count = db.get_comment_count_by_post(post_id)
            
            return jsonify({
                'success': True,
                'comment_count': comment_count
            })
        
        return jsonify({'success': False, 'error': 'Failed to delete comment or unauthorized'})
    except Exception as e:
        print(f"Error in delete_comment: {e}")
        return jsonify({'success': False, 'error': str(e)})

def format_timestamp(timestamp):
    """
    Convert database timestamp to human-readable relative time.
    Examples: "2h ago", "3d ago", "Just now"
    """
    from datetime import datetime
    try:
        # Parse timestamp string to datetime object
        if isinstance(timestamp, str):
            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        elif hasattr(timestamp, 'strftime'):
            dt = timestamp
        else:
            return "Recently"
        
        # Calculate time difference from now 
        now = datetime.now()
        diff = now - dt
        
        # Return appropriate time unit
        if diff.days > 365:
            years = diff.days // 365
            return f"{years}y ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months}mo ago"
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"
    except:
        return "Recently"

# Add Reply to Comment
@app.route('/add_reply/<int:post_id>/<int:parent_comment_id>', methods=['POST'])
def add_reply(post_id, parent_comment_id):
    # Check user authentication
    if 'user_id' not in session or 'logged_in' not in session:
        return jsonify({'success': False, 'error': 'Please login first'})

    user_id = session['user_id']
    content = request.json.get('content', '').strip()

    # Validate reply content
    if not content:
        return jsonify({'success': False, 'error': 'Reply cannot be empty'})

    if len(content) > 1000:
        return jsonify({'success': False, 'error': 'Reply is too long (max 1000 characters)'})

    try:
        # Insert reply into database
        comment_id = db.insert_comment_reply(post_id, user_id, content, parent_comment_id)

        if comment_id:
            # Get the new reply with full details
            reply_data = db.get_comment_by_id(comment_id)

            if reply_data:
                # Format timestamp as "Just now" for new replies
                timestamp = reply_data[4]
                formatted_time = "Just now"

                new_reply = {
                    'comment_id': reply_data[0],
                    'username': reply_data[5] if len(reply_data) > 5 else "Unknown User",
                    'content': reply_data[3],
                    'timestamp': timestamp,
                    'formatted_time': formatted_time,
                    'avatar_url': reply_data[6] if len(reply_data) > 6 else None,
                    'is_reply': True,
                    'parent_comment_id': parent_comment_id
                }

                # Get updated comment count for the post
                comment_count = db.get_comment_count_by_post(post_id)

                # ---- BADGE: Comment badge (badge_id = 1) ----
                badge_unlocked = False
                badge_title = None
                badge_subtitle = None
                badge_icon = None

                try:
                    unlocked_now, prog, req = db.update_badge_progress(
                        user_id, badge_id=1, progress_increment=1
                    )
                    if unlocked_now:
                        badge_unlocked = True
                        badge_title = "Badge unlocked!"
                        badge_subtitle = "Talking is fun!"
                        badge_icon = "/static/img/badges/comment.png"
                except Exception as e:
                    print(f"Reply badge error: {e}")

                return jsonify({
                    'success': True,
                    'reply': new_reply,
                    'comment_count': comment_count,
                    'badge_unlocked': badge_unlocked,
                    'title': badge_title,
                    'subtitle': badge_subtitle,
                    'iconSrc': badge_icon
                })

        return jsonify({'success': False, 'error': 'Failed to add reply'})
    except Exception as e:
        print(f"Error in add_reply: {e}")
        return jsonify({'success': False, 'error': str(e)})



# Get Comment Replies
@app.route('/get_replies/<int:parent_comment_id>', methods=['GET'])
def get_replies(parent_comment_id):
    # Check user authentication
    if 'user_id' not in session or 'logged_in' not in session:
        return jsonify({'success': False, 'error': 'Please login first'})
    
    try:
        # Fetch all replies for this comment
        replies_data = db.get_replies_to_comment(parent_comment_id)
        
        # Format timestamps
        for reply in replies_data:
            reply['formatted_time'] = format_timestamp(reply['timestamp'])
        
        return jsonify({
            'success': True,
            'replies': replies_data
        })
    except Exception as e:
        print(f"Error in get_replies: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/report_comment', methods=['POST'])
def report_comment():
    """API endpoint for users to report comments"""
    if 'user_id' not in session or 'logged_in' not in session:
        return jsonify({'success': False, 'error': 'Please login first'}), 401
    
    data = request.get_json()
    comment_id = data.get('comment_id')
    reason = data.get('reason', '').strip()
    
    if not comment_id:
        return jsonify({'success': False, 'error': 'Comment ID required'}), 400
    
    if not reason:
        return jsonify({'success': False, 'error': 'Please provide a reason for reporting'}), 400
    
    if len(reason) > 500:
        return jsonify({'success': False, 'error': 'Reason is too long (max 500 characters)'}), 400
    
    user_id = session['user_id']
    
    # Check if comment exists
    comment_data = db.get_comment_by_id(comment_id)
    if not comment_data:
        return jsonify({'success': False, 'error': 'Comment not found'}), 404
    
    # Check if user is reporting their own comment
    if comment_data[2] == user_id:
        return jsonify({'success': False, 'error': 'You cannot report your own comment'}), 400
    
    success, report_count = db.report_comment(comment_id, user_id, reason)
    
    if success:
        return jsonify({
            'success': True, 
            'message': 'Comment reported successfully. Thank you for helping keep our community safe!',
            'report_count': report_count
        })
    else:
        return jsonify({'success': False, 'error': 'You have already reported this comment'}), 400

#-------------------------------------Leandro---------------------------------------------------------
@app.route('/events', methods=['GET', 'POST'])
def events():
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        event_name = request.form.get('event_name', '').strip()
        location = request.form.get('location', '').strip()
        event_itinerary = request.form.get('event_itinerary', '').strip()
        event_date = request.form.get('event_date', '').strip()  # datetime-local string

        event_duration_raw = request.form.get('event_duration', '').strip()
        max_participants_raw = request.form.get('max_participants', '').strip()

        if not event_name or not location or not event_date:
            flash('Please fill in Event Name, Location, and Date/Time.', 'danger')
            return redirect(url_for('events'))

        event_duration = int(event_duration_raw) if event_duration_raw.isdigit() else None
        max_participants = int(max_participants_raw) if max_participants_raw.isdigit() else 10

        try:
            db.insert_event(
                event_name=event_name,
                event_itinerary=event_itinerary,
                event_duration=event_duration,
                event_date=event_date,
                location=location,
                max_participants=max_participants,
                user_id=session['user_id'],
                game_type=None,
                game_rules=None
            )
            flash('Event created successfully!', 'success')
            return redirect(url_for('events'))
        except Exception as e:
            print(f"Error saving event: {e}")
            flash('Error creating event. Please try again.', 'danger')
            return redirect(url_for('events'))

    return render_template('events.html')
@app.route('/preview_event', methods=['POST'])
def preview_event():
    """Preview event details before final submission"""
    if 'user_id' not in session or 'logged_in' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    # Get form data
    event_name = request.form.get('event_name', '').strip()
    location = request.form.get('location', '').strip()
    event_itinerary = request.form.get('event_itinerary', '').strip()
    event_date = request.form.get('event_date', '').strip()
    event_duration_raw = request.form.get('event_duration', '').strip()
    max_participants_raw = request.form.get('max_participants', '').strip()
    
    # Validate required fields
    if not event_name or not location or not event_date:
        return jsonify({'success': False, 'error': 'Please fill in all required fields'}), 400
    
    # Format duration and participants
    event_duration = int(event_duration_raw) if event_duration_raw.isdigit() else None
    max_participants = int(max_participants_raw) if max_participants_raw.isdigit() else 10
    
    # Format date for display
    formatted_date = event_date
    try:
        from datetime import datetime
        dt = datetime.strptime(event_date, '%Y-%m-%dT%H:%M')
        formatted_date = dt.strftime('%d-%m-%Y, %H:%M')
    except:
        pass
    
    # Get current username for organizer
    username = session.get('username', 'You')
    
    return jsonify({
        'success': True,
        'event': {
            'event_name': event_name,
            'location': location,
            'event_itinerary': event_itinerary,
            'event_date': formatted_date,
            'event_duration': event_duration,
            'max_participants': max_participants,
            'organizer': username
        }
    })

# ==================== EVENT JOIN API ====================

@app.route('/api/join_event/<int:event_id>', methods=['POST'])
def api_join_event(event_id):
    """API endpoint for joining an event"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    
    try:
        # Check if event exists
        event_data = db.get_event_by_id(event_id)
        if not event_data:
            return jsonify({'success': False, 'error': 'Event not found'}), 404
        
        # Check if user is the event organizer
        if event_data[7] == user_id:  # user_id is at index 7
            return jsonify({'success': False, 'error': 'You cannot join your own event'}), 400
        
        # Check if user already joined
        if db.has_user_joined_event(user_id, event_id):
            return jsonify({'success': False, 'error': 'Already joined this event'}), 400
        
        # Add participant
        success, message = db.add_event_participant(event_id, user_id)
        
        if success:
            # Get updated participant count
            participant_count = db.get_event_participants_count(event_id)
            
            # Check and award badges
            db.check_and_award_badges(user_id)
            
            return jsonify({
                'success': True,
                'message': message,
                'participant_count': participant_count,
                'event_id': event_id
            })
        else:
            return jsonify({'success': False, 'error': message}), 400
            
    except Exception as e:
        print(f"Error in api_join_event: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== SEARCH FUNCTIONALITY ====================

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

@app.route('/profile')
@app.route('/profile/<int:user_id>')
def profile(user_id=None):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if user_id is None:
        user_id = session['user_id']
    
    user_data = db.get_user_by_id(user_id)
    if not user_data:
        flash('User not found', 'danger')
        return redirect(url_for('home'))
    
    target_user = User.from_database_row(user_data)
    
    stats = db.get_user_stats(user_id)
    
    badges_list = db.get_user_badges_with_progress(user_id)
    
    viewing_own_profile = (session['user_id'] == user_id)
    
    user_posts = db.get_posts_by_user(user_id)
    
    is_following = False
    is_blocking = False
    is_blocked_by_profile_owner = False
    
    if not viewing_own_profile:
        is_following = db.check_follow_status(session['user_id'], user_id)
        is_blocking = db.is_blocking(session['user_id'], user_id)
        is_blocked_by_profile_owner = db.is_blocking(user_id, session['user_id'])
    
    return render_template('profile.html', 
                        current_user=target_user, 
                        stats=stats,
                        badges=badges_list,
                        posts=user_posts,
                        viewing_own_profile=viewing_own_profile,
                        profile_user_id=user_id,
                        is_following=is_following,
                        is_blocking=is_blocking,
                        is_blocked_by_profile_owner=is_blocked_by_profile_owner)

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

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' in session:
        db.delete_user(session['user_id'])
        session.clear()
        flash('Account deleted successfully', 'success')
    return redirect(url_for('login'))
# ==================== FOLLOW/UNFOLLOW API ENDPOINTS ====================

@app.route('/api/follow/<int:user_id>', methods=['POST'])
def api_follow_user(user_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    follower_id = session['user_id']
    
    if follower_id == user_id:
        return jsonify({'success': False, 'error': 'Cannot follow yourself'}), 400
    
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
        return jsonify({'success': False, 'error': str(e)}), 500

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

@app.route('/api/check_follow/<int:user_id>', methods=['GET'])
def check_follow_status(user_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    follower_id = session['user_id']
    is_following = db.check_follow_status(follower_id, user_id)
    
    return jsonify({'success': True, 'is_following': is_following})
# ===============================
# BLOCK / UNBLOCK (AJAX)
# ===============================
@app.route('/api/block/<int:user_id>', methods=['POST'])
def api_block_user(user_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    blocker_id = session['user_id']
    
    # Cannot block yourself
    if blocker_id == user_id:
        return jsonify({'success': False, 'error': 'Cannot block yourself'}), 400
    
    try:
        # Check if already blocking using your function name
        if db.is_blocking(blocker_id, user_id):
            return jsonify({'success': False, 'error': 'Already blocking this user'}), 400
            
        success = db.create_block(blocker_id, user_id)
        if success:
            return jsonify({'success': True, 'is_blocking': True}), 200
        else:
            return jsonify({'success': False, 'error': 'Failed to block user'}), 500
    except Exception as e:
        print(f"Error in api_block_user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/unblock/<int:user_id>', methods=['POST'])
def api_unblock_user(user_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    blocker_id = session['user_id']
    
    try:
        # Check if actually blocking using your function name
        if not db.is_blocking(blocker_id, user_id):
            return jsonify({'success': False, 'error': 'Not blocking this user'}), 400
            
        success = db.remove_block(blocker_id, user_id)
        if success:
            return jsonify({'success': True, 'is_blocking': False}), 200
        else:
            return jsonify({'success': False, 'error': 'Failed to unblock user'}), 500
    except Exception as e:
        print(f"Error in api_unblock_user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Backwards-compatible endpoint
@app.route('/block_toggle/<int:user_id>', methods=['POST'])
def block_toggle(user_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    blocker_id = session['user_id']
    
    if blocker_id == user_id:
        return jsonify({'success': False, 'error': 'Cannot block yourself'}), 400
        
    try:
        currently = db.is_blocking(blocker_id, user_id)
        if currently:
            success = db.remove_block(blocker_id, user_id)
            return jsonify({'success': success, 'is_blocking': False})
        else:
            success = db.create_block(blocker_id, user_id)
            return jsonify({'success': success, 'is_blocking': True})
    except Exception as e:
        print(f"Error in block_toggle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== POST MANAGEMENT ROUTES ====================

@app.route('/createPost', methods=['GET', 'POST'])
def createPost():
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        category = request.form.get('category', 'senior').strip()

        image = request.files.get('image')

        ext = os.path.splitext(secure_filename(image.filename))[1].lower()
        unique_filename = f"{uuid.uuid4()}{ext}"

        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        image.save(save_path)

        # 1️⃣ Insert post
        db.insert_post(
            content=content,
            user_id=session['user_id'],
            post_category=category,
            image_url=unique_filename
        )

        # 2️⃣ Update "Create Post" badge — ALWAYS updates profile
        badge_unlocked = False
        try:
            unlocked_now, progress, required = db.update_badge_progress(
                user_id=session['user_id'],
                badge_id=4,   # Create Post badge
                progress_increment=1
            )
            badge_unlocked = unlocked_now
        except Exception as e:
            print(f"Create post badge error: {e}")

        # 3️⃣ Return JSON for AJAX (popup + profile update)
        return jsonify({
            "success": True,
            "badge_unlocked": badge_unlocked,
            "iconSrc": "/static/img/badges/post.png",
            "title": "Badge unlocked!",
            "subtitle": "Creating Post"
        })

    return render_template('createPost.html')




def get_db_connection():
    conn = sqlite3.connect('BondBuddies.db')
    conn.row_factory = sqlite3.Row  # allows post['content'] instead of post[1]
    return conn

@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
def edit_post_route(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE post_id=?', (post_id,)).fetchone()

    if not post:
        conn.close()
        return redirect(url_for('profile'))

    # Ensure the user owns the post
    if post['user_id'] != session['user_id']:
        conn.close()
        return redirect(url_for('profile'))

    if request.method == 'POST':
        content = request.form['content'].strip()
        category = request.form['category']

        # Handle image upload
        file = request.files.get('image')
        if file and file.filename != '' and allowed_file(file.filename):
            # Generate a unique filename using UUID
            ext = os.path.splitext(secure_filename(file.filename))[1].lower()
            filename = f"{uuid.uuid4().hex}{ext}"

            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
        else:
            # Keep existing file if no new upload
            filename = post['image_url']

        # Update post with new content, category, and image
        conn.execute('''
            UPDATE posts
            SET content = ?, post_category = ?, image_url = ?
            WHERE post_id = ?
        ''', (content, category, filename, post_id))
        conn.commit()
        conn.close()
        return redirect(url_for('profile'))

    # GET request: render edit page
    conn.close()
    return render_template('editPost.html', post=post)

# ---------------- Normal POST route for deleting (form submit) ----------------
@app.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post_route(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    post = db.get_post_by_id(post_id)
    if not post:
        return redirect(url_for('profile'))

    if post[2] != session['user_id']:
        return redirect(url_for('profile'))

    db.delete_post(post_id)
    # Redirect back to profile after deletion
    return redirect(url_for('profile'))

# ---------------- API route for AJAX deletion ----------------
@app.route('/api/delete_post/<int:post_id>', methods=['POST','DELETE'])
@app.route('/api/delete_post/<int:post_id>/', methods=['DELETE'])
def delete_post_api(post_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    post = db.get_post_by_id(post_id)
    if not post:
        return jsonify({'success': False, 'error': 'Post not found'}), 404

    if post[2] != session['user_id']:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    # Delete the post
    db.delete_post(post_id)

    return jsonify({'success': True})

# ==================== POST API ENDPOINTS ====================

@app.route('/api/delete_post/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    try:
        post_data = db.get_post_by_id(post_id)
        if not post_data:
            return jsonify({'success': False, 'error': 'Post not found'}), 404
        
        if post_data[2] != session['user_id']:
            return jsonify({'success': False, 'error': 'Not authorized to delete this post'}), 403
        
        db.delete_post(post_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/logout')
def logout():
    # Clear all warning-related session data
    session.pop('has_active_warnings', None)
    session.pop('warning_count', None)
    session.pop('strike_count', None)
    session.pop('latest_warning_reason', None)
    session.pop('latest_warning_date', None)
    
    session.clear()
    return redirect(url_for('login'))

# ==================== APPLICATION ENTRY POINT ====================

# ==================== ADMIN ROUTES ====================
def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'logged_in' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        
        if session.get('user_type') != 'admin':
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('home'))
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@admin_required
def admin_dashboard():
    # Check if user is admin
    if 'user_id' not in session or 'logged_in' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    if session.get('user_type') != 'admin':
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('home'))
    
    # Get admin statistics
    stats = {
        'total_users': db.get_total_user_count(),
        'total_posts': db.get_total_post_count(),
        'total_events': db.get_total_event_count(),
        'recent_signups': db.get_recent_users(limit=10),
        'recent_posts': db.get_recent_posts(limit=10),
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/report')
@admin_required
def admin_report():
    """Admin page for viewing and moderating reported content"""
    if 'user_id' not in session or session.get('user_type') != 'admin':
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('home'))
    
    # Get pending reported comments
    pending_reports = db.get_pending_reported_comments(limit=100)
    
    # Convert tuple data to dictionaries with named keys
    formatted_reports = []
    for report in pending_reports:
        formatted_reports.append({
            'report_id': report[0],
            'comment_id': report[1],
            'reporter_id': report[2],
            'reason': report[3],
            'reported_at': report[4],
            'status': report[5],
            'commenter_id': report[6],
            'comment_content': report[7],
            'post_id': report[8],
            'comment_timestamp': report[9],
            'commenter_username': report[10],
            'reporter_username': report[11],
            'post_content': report[12],
            'post_author_id': report[13],
            'post_author_username': report[14],
            'total_reports': report[15]
        })
    
    # Get warning statistics - DON'T convert it, it's already a dict
    warning_stats = db.get_warning_statistics()
    
    # Format active warnings as dictionaries
    active_warnings_raw = db.get_all_active_warnings()
    formatted_warnings = []
    for warning in active_warnings_raw:
        formatted_warnings.append({
            'warning_id': warning[0],
            'user_id': warning[1],
            'username': warning[2],
            'reason': warning[3],
            'warning_type': warning[4],
            'warning_count': warning[5],
            'issued_at': warning[6],
            'expires_at': warning[7],
            'issued_by': warning[8],
            'admin_username': warning[9]
        })

    return render_template('admin/report.html', 
                         reports=formatted_reports,
                         warning_stats=warning_stats,
                         active_warnings=formatted_warnings)  # Pass formatted warnings

@app.route('/admin/report/resolve/<int:report_id>', methods=['POST'])
@admin_required
def resolve_report(report_id):
    """Resolve a specific comment report"""
    if 'user_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    data = request.get_json()
    action = data.get('action')  # 'dismiss' or 'reviewed'
    admin_notes = data.get('admin_notes', '').strip()
    
    if action not in ['dismiss', 'reviewed']:
        return jsonify({'success': False, 'error': 'Invalid action'}), 400
    
    status = 'dismissed' if action == 'dismiss' else 'reviewed'
    admin_id = session['user_id']
    
    success = db.resolve_comment_report(report_id, admin_id, status, admin_notes)
    
    if success:
        # Get report details for response
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT rc.comment_id, u.username, rc.reason
        FROM reported_comments rc
        JOIN comments c ON rc.comment_id = c.comment_id
        JOIN users u ON c.user_id = u.user_id
        WHERE rc.report_id = ?
        ''', (report_id,))
        result = cursor.fetchone()
        conn.close()
        
        comment_id = result[0] if result else None
        commenter_username = result[1] if result else None
        report_reason = result[2] if result else None
        
        return jsonify({
            'success': True, 
            'message': f'Report {status} successfully',
            'report_id': report_id,
            'status': status,
            'comment_id': comment_id,
            'commenter_username': commenter_username,
            'report_reason': report_reason
        })
    else:
        return jsonify({'success': False, 'error': 'Failed to resolve report'}), 500

@app.route('/admin/report/dismiss_all/<int:comment_id>', methods=['POST'])
@admin_required
def dismiss_all_reports(comment_id):
    """Dismiss all pending reports for a specific comment"""
    if 'user_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    data = request.get_json()
    admin_notes = data.get('admin_notes', 'All reports dismissed by admin')
    admin_id = session['user_id']
    
    count = db.dismiss_all_reports_for_comment(comment_id, admin_id, admin_notes)
    
    return jsonify({
        'success': True, 
        'message': f'Dismissed {count} report(s) for this comment',
        'dismissed_count': count,
        'comment_id': comment_id
    })

# ==================== ADMIN WARNING MANAGEMENT ====================
@app.route('/admin/issue_warning', methods=['POST'])
@admin_required
def issue_warning():
    """Issue a warning to a user"""
    if 'user_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    reason = data.get('reason', '').strip()
    warning_type = data.get('warning_type', 'comment')
    comment_id = data.get('comment_id')
    post_id = data.get('post_id')
    expires_days = data.get('expires_days', 30)
    report_id = data.get('report_id')  # Optional: to resolve associated report
    
    if not user_id or not reason:
        return jsonify({'success': False, 'error': 'User ID and reason are required'}), 400
    
    if len(reason) > 500:
        return jsonify({'success': False, 'error': 'Reason is too long (max 500 characters)'}), 400
    
    admin_id = session['user_id']
    
    # Don't allow warning yourself
    if user_id == admin_id:
        return jsonify({'success': False, 'error': 'You cannot issue a warning to yourself'}), 400
    
    success, warning_count, warning_id = db.issue_warning(
        user_id, admin_id, reason, warning_type, comment_id, post_id, expires_days
    )
    
    if success:
        # If this warning is associated with a report, resolve that report
        if report_id:
            db.resolve_comment_report(report_id, admin_id, 'reviewed', f'Warning issued - {reason[:50]}')
        
        # Get user info
        user_data = db.get_user_by_id(user_id)
        username = user_data[1] if user_data else 'Unknown'
        
        # Determine restriction level based on warning count
        restriction = None
        if warning_count >= 5:
            restriction = "Account flagged for deletion review"
        elif warning_count >= 4:
            restriction = "30-day suspension"
        elif warning_count >= 3:
            restriction = "7-day posting restriction"
        elif warning_count >= 2:
            restriction = "3-day posting restriction"
        
        return jsonify({
            'success': True,
            'message': f'Warning issued to {username}',
            'warning_id': warning_id,
            'warning_count': warning_count,
            'strike_count': warning_count,
            'restriction': restriction,
            'username': username,
            'user_id': user_id
        })
    else:
        return jsonify({'success': False, 'error': 'Failed to issue warning'}), 500

@app.route('/admin/delete_user_with_reason', methods=['POST'])
@admin_required
def delete_user_with_reason():
    """Delete a user account with a provided reason"""
    if 'user_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    data = request.get_json()
    print(f"Delete request data: {data}")  # Debug print
    
    user_id = data.get('user_id')
    reason = data.get('reason', '').strip()
    report_id = data.get('report_id')
    
    print(f"user_id: {user_id}, reason: {reason}, report_id: {report_id}")
    
    if not user_id or not reason:
        return jsonify({'success': False, 'error': 'User ID and reason are required'}), 400
    
    if len(reason) > 500:
        return jsonify({'success': False, 'error': 'Reason is too long (max 500 characters)'}), 400
    
    admin_id = session['user_id']
    
    # Don't allow deleting yourself
    if user_id == admin_id:
        return jsonify({'success': False, 'error': 'You cannot delete your own account through this interface'}), 400
    
    # Get user info before deletion for response
    user_data = db.get_user_by_id(user_id)
    username = user_data[1] if user_data else 'Unknown'
    
    try:
        # Call the enhanced delete_user_with_reason
        success, message = db.delete_user_with_reason(user_id, admin_id, reason)
        
        print(f"Delete result - success: {success}, message: {message}")
        
        if success:
            # If this deletion is associated with a report, resolve that report
            if report_id:
                db.resolve_comment_report(report_id, admin_id, 'reviewed', f'User account deleted - {reason[:50]}')
            
            return jsonify({
                'success': True, 
                'message': f'User {username} has been permanently deleted',
                'username': username,
                'user_id': user_id,
                'reason': reason
            })
        else:
            return jsonify({'success': False, 'error': message}), 500
    except Exception as e:
        print(f"Exception in delete_user_with_reason: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/admin/revoke_warning/<int:warning_id>', methods=['POST'])
@admin_required
def revoke_warning(warning_id):
    """Revoke an active warning"""
    if 'user_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    admin_id = session['user_id']
    
    success = db.revoke_warning(warning_id, admin_id)
    
    if success:
        return jsonify({'success': True, 'message': 'Warning revoked successfully'})
    else:
        return jsonify({'success': False, 'error': 'Warning not found or already revoked'}), 404

@app.route('/admin/user_warnings/<int:user_id>', methods=['GET'])
@admin_required
def get_user_warnings(user_id):
    """Get all warnings for a specific user"""
    if 'user_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    warnings = db.get_user_warnings(user_id, active_only=False)
    warning_status = db.check_user_warning_status(user_id)
    user_data = db.get_user_by_id(user_id)
    
    user_info = {
        'user_id': user_id,
        'username': user_data[1] if user_data else 'Unknown',
        'user_type': user_data[3] if user_data else 'Unknown'
    }
    
    formatted_warnings = []
    for w in warnings:
        formatted_warnings.append({
            'warning_id': w[0],
            'reason': w[1],
            'warning_type': w[2],
            'warning_count': w[3],
            'issued_at': w[4],
            'expires_at': w[5],
            'is_active': w[6],
            'issued_by': w[7],
            'related_comment': w[8] if len(w) > 8 else None,
            'related_post': w[9] if len(w) > 9 else None
        })
    
    return jsonify({
        'success': True,
        'user': user_info,
        'warnings': formatted_warnings,
        'status': warning_status
    })

@app.route('/admin/users')
@admin_required
def admin_users():
    if 'user_id' not in session or session.get('user_type') != 'admin':
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('home'))
    
    users = db.get_all_users_with_stats()
    return render_template('admin/users.html', users=users)

@app.route('/admin/posts')
@admin_required
def admin_posts():
    if 'user_id' not in session or session.get('user_type') != 'admin':
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('home'))
    
    posts = db.get_all_posts_with_details()
    return render_template('admin/posts.html', posts=posts)

@app.route('/admin/events')
@admin_required
def admin_events():
    if 'user_id' not in session or session.get('user_type') != 'admin':
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('home'))
    
    events = db.get_all_events_with_details()
    return render_template('admin/events.html', events=events)

# Admin actions
@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    if 'user_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    if user_id == session['user_id']:
        return jsonify({'success': False, 'error': 'Cannot delete yourself'}), 400
    
    data = request.get_json()
    reason = data.get('reason', '').strip()
    
    if not reason:
        return jsonify({'success': False, 'error': 'Deletion reason is required'}), 400
    
    if len(reason) > 500:
        return jsonify({'success': False, 'error': 'Reason is too long (max 500 characters)'}), 400
    
    admin_id = session['user_id']
    
    try:
        # Use the delete_user_with_reason function instead of delete_user
        success, message = db.delete_user_with_reason(user_id, admin_id, reason)
        
        if success:
            return jsonify({
                'success': True, 
                'message': message,
                'reason': reason
            })
        else:
            return jsonify({'success': False, 'error': message}), 500
    except Exception as e:
        print(f"Error deleting user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/delete_post/<int:post_id>', methods=['POST'])
@admin_required
def admin_delete_post(post_id):
    if 'user_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'})
    
    try:
        db.delete_post(post_id)
        return jsonify({'success': True, 'message': 'Post deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/delete_event/<int:event_id>', methods=['POST'])
@admin_required
def admin_delete_event(event_id):
    if 'user_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'})
    
    try:
        db.delete_event(event_id)
        return jsonify({'success': True, 'message': 'Event deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/tutorial_choice', methods=['POST'])
def tutorial_choice():
    if 'user_id' not in session or 'logged_in' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    data = request.get_json() or {}
    choice = data.get('choice')  # "yes" or "no"

    # mark seen no matter what (so it never prompts again)
    db.mark_tutorial_seen(session['user_id'])

    return jsonify({'success': True, 'open_tutorial': (choice == 'yes')})

@app.errorhandler(404)
def page_not_found(e):
    # Note that you set the 404 status explicitly here
    return render_template('error404.html'), 404

if __name__ == "__main__":
    app.run(debug=True)



