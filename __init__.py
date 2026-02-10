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
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from login import UserLoginIn
from createAccount import createAccount
from database import DataBase
from classes import (
    User,
    Post,
    Event
)
import sqlite3
import os, uuid


app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key-here"
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

# Login Page
@app.route("/", methods=["GET", "POST"])
def login():
    user_login_form = UserLoginIn(request.form)

    if request.method == "POST" and user_login_form.validate():
        user_data = db.get_user_by_username(user_login_form.username.data)

        if user_data:
            user = User.from_database_row(user_data)

            if check_password_hash(user.get_password(), user_login_form.password.data):
                session["user_id"] = user.get_user_id()
                session["username"] = user.get_username()
                session["user_type"] = user.get_user_type()
                session["logged_in"] = True

                return redirect(url_for("home"))
            else:
                flash("Invalid username or password", "danger")
        else:
            flash("Invalid username or password", "danger")

    return render_template("login.html", form=user_login_form)

# Account Creation Page
@app.route("/createAccount", methods=["GET", "POST"])
def accountCreation():
    create_account_form = createAccount(request.form)
    if request.method == "POST" and create_account_form.validate():
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
            )

            flash("Account created successfully! Please login.", "success")
            return redirect(url_for("login"))

        except Exception as e:
            print(f"Error: {e}")
            flash("An error occurred. Please try again.", "danger")

    return render_template("createAccount.html", form=create_account_form)

# ==================== HOME PAGE (MERGED) ====================

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
    
    # Get posts from followed users (from 9.75kb version)
    feed_posts = db.get_followed_users_posts(current_user_id, limit=20)
    
    # Format posts for display - handle variable number of columns
    posts_list = []
    for post in feed_posts:
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
    
    # Get all posts (from 5.94kb version)
    posts = db.get_all_posts(limit=50)  # This should include image_url column
    events = db.get_all_events()

    return render_template('home.html', 
                         current_user=current_user, 
                         feed_posts=posts_list,
                         posts=posts, 
                         events=events)

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
            if ("senior" in filters or "youth" in filters) and not any(
                post[5] in ["senior", "youth"] for post in posts_data if len(post) > 5
            ):
                if "senior" in filters and "youth" in filters:
                    flash(
                        "No senior or youth posts found in the filtered results. Showing other posts instead.",
                        "warning",
                    )
                elif "senior" in filters:
                    flash(
                        "No senior posts found in the filtered results. Showing other posts instead.",
                        "warning",
                    )
                elif "youth" in filters:
                    flash(
                        "No youth posts found in the filtered results. Showing other posts instead.",
                        "warning",
                    )
    else:
        # Default: show random posts with images
        posts_data = db.get_posts_with_images(limit=per_page)
        if not posts_data:
            flash(
                "No posts with images found. Try creating a post with an image!", "info"
            )

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
        return jsonify({"success": False, "error": "Please login first"})

    user_id = session["user_id"]

    try:
        # Check if user already liked this post
        has_liked = db.has_user_liked_post(user_id, post_id)

        if has_liked:
            # Remove like from post
            success = db.unlike_post(user_id, post_id)
            if success:
                return jsonify(
                    {
                        "success": True,
                        "liked": False,
                        "like_count": db.get_post_like_count(post_id),
                    }
                )
        else:
            # Add like to post
            success = db.like_post(user_id, post_id)
            if success:
                return jsonify(
                    {
                        "success": True,
                        "liked": True,
                        "like_count": db.get_post_like_count(post_id),
                    }
                )

        return jsonify({"success": False, "error": "Operation failed"})
    except Exception as e:
        print(f"Error in like_post: {e}")
        return jsonify({"success": False, "error": str(e)})

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
                
                return jsonify({
                    'success': True,
                    'comment': new_comment,
                    'comment_count': comment_count
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

# =============== COMMENT REPLY METHODS ===============


    """Check how deep a comment is in the reply chain"""
    conn = db.connect(self.db_name)
    cursor = conn.cursor()
    
    depth = 0
    current_id = comment_id
    
    while current_id:
        cursor.execute('''
        SELECT parent_comment_id FROM comments WHERE comment_id = ?
        ''', (current_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            depth += 1
            current_id = result[0]
        else:
            break
    
    conn.close()
    return min(depth, 5)  # Limit depth to 5 levels

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
                
                return jsonify({
                    'success': True,
                    'reply': new_reply,
                    'comment_count': comment_count
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

@app.route('/api/like_post/<int:post_id>', methods=['POST'])
def api_like_post(post_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    
    try:
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE posts SET likes = likes + 1 WHERE post_id = ?', (post_id,))
        conn.commit()
        
        cursor.execute('''
        INSERT INTO user_actions (user_id, action_type, target_id)
        VALUES (?, 'like_post', ?)
        ''', (user_id, post_id))
        
        db.check_and_award_badges(user_id)
        
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
    session.clear()
    return redirect(url_for('login'))

# ==================== APPLICATION ENTRY POINT ====================

if __name__ == "__main__":
    app.run(debug=True)
