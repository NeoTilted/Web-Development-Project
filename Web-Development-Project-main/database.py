import sqlite3
import json
import os 

class DataBase:
    def __init__(self, db_name='BondBuddies.db'):
        self.db_name = db_name
        self.init_database()
        self.create_default_data()

    def init_database(self):
        """Initialize the database and create tables if they don't exist"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Create users table with extended fields
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            user_type TEXT NOT NULL,
            email TEXT,
            birth_date DATE,
            age_group TEXT CHECK(age_group IN ('youth', 'senior')),
            bio TEXT,
            avatar_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create posts table with category
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            post_id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            likes INTEGER DEFAULT 0,
            post_category TEXT CHECK(post_category IN ('youth', 'senior')),
            post_prompt_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (post_prompt_id) REFERENCES post_prompts(prompt_id)
        )
        ''')

        # Create events table with game type
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            event_itinerary TEXT,
            event_duration INTEGER,
            event_date TIMESTAMP,
            location TEXT,
            max_participants INTEGER DEFAULT 10,
            user_id INTEGER NOT NULL,
            game_type TEXT,
            game_rules TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')

        # Create event_participants table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_participants (
            participation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            UNIQUE(event_id, user_id)
        )
        ''')

        # Create badges table with progress tracking
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS badges (
            badge_id INTEGER PRIMARY KEY AUTOINCREMENT,
            badge_name TEXT NOT NULL,
            badge_description TEXT,
            badge_type TEXT NOT NULL,
            criteria TEXT,
            progress_required INTEGER DEFAULT 1,
            progress_type TEXT DEFAULT 'count',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create user_badges table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_badges (
            user_badge_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            badge_id INTEGER NOT NULL,
            current_progress INTEGER DEFAULT 0,
            earned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (badge_id) REFERENCES badges(badge_id) ON DELETE CASCADE,
            UNIQUE(user_id, badge_id)
        )
        ''')

        # Create following table for accepted follows
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS following (
            following_id INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id INTEGER NOT NULL,
            followed_id INTEGER NOT NULL,
            follow_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (follower_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (followed_id) REFERENCES users(user_id) ON DELETE CASCADE,
            CHECK (follower_id != followed_id),
            UNIQUE(follower_id, followed_id)
        )
        ''')

        # Create follow_requests table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS follow_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            requester_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'rejected')),
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            responded_at TIMESTAMP,
            FOREIGN KEY (requester_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (target_id) REFERENCES users(user_id) ON DELETE CASCADE,
            UNIQUE(requester_id, target_id)
        )
        ''')

        # Create post_prompts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS post_prompts (
            prompt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_text TEXT NOT NULL,
            category TEXT,
            target_age_group TEXT DEFAULT 'senior',
            difficulty_level TEXT DEFAULT 'easy',
            times_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create comments table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')

        # Create user_actions table for tracking badge progress
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_actions (
            action_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            target_id INTEGER,
            action_data TEXT,
            performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')

        # Create notifications table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            notification_type TEXT NOT NULL,
            message TEXT NOT NULL,
            related_id INTEGER,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')

        conn.commit()
        conn.close()

    def create_default_data(self):
        """Create default badges and prompts"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Check if badges already exist
        cursor.execute('SELECT COUNT(*) FROM badges')
        badge_count = cursor.fetchone()[0]
        
        if badge_count == 0:
            # Create default badges from wireframes
            default_badges = [
                ('Talking is fun!', 'Comment on a post', 'social', 'comment_post', 1),
                ('Like a lover!', 'Like a post', 'social', 'like_post', 1),
                ('Friends', 'Follow a user', 'social', 'follow_user', 1),
                ('Sharing is caring', 'Share a post', 'social', 'share_post', 1),
                ('Event Enthusiast', 'Host or attend 5 events', 'event', 'participate_event', 5),
                ('Weekly Interaction', 'Interact with 5 different users this week', 'social', 'weekly_interaction', 5),
                ('Story Sharer', 'Share 3 stories this month', 'content', 'share_story', 3),
                ('Community Builder', 'Organize 2 community events', 'event', 'organize_event', 2)
            ]
            
            for badge in default_badges:
                cursor.execute('''
                INSERT INTO badges (badge_name, badge_description, badge_type, criteria, progress_required)
                VALUES (?, ?, ?, ?, ?)
                ''', badge)
        
        # Check if prompts already exist
        cursor.execute('SELECT COUNT(*) FROM post_prompts')
        prompt_count = cursor.fetchone()[0]
        
        if prompt_count == 0:
            # Create default post prompts for elderly
            default_prompts = [
                ('Share a fond memory from your youth', 'memory', 'senior'),
                ('What was your first job like?', 'work', 'senior'),
                ('Tell us about your favorite hobby', 'hobbies', 'senior'),
                ('Share a recipe from your family', 'food', 'senior'),
                ('What is the most beautiful place you have visited?', 'travel', 'senior'),
                ('What advice would you give to your younger self?', 'advice', 'senior'),
                ('Share a photo of your pet or favorite animal', 'pets', 'both'),
                ('What is your favorite book or movie?', 'entertainment', 'both'),
                ('What skill are you currently learning?', 'learning', 'youth'),
                ('Share your favorite study spot', 'education', 'youth'),
                ('What are your career aspirations?', 'career', 'youth'),
                ('Tell us about a recent achievement', 'achievement', 'both')
            ]
            
            for prompt in default_prompts:
                cursor.execute('''
                INSERT INTO post_prompts (prompt_text, category, target_age_group)
                VALUES (?, ?, ?)
                ''', prompt)
        
        conn.commit()
        conn.close()

    # =============== USER METHODS ===============

    def insert_user(self, username, password, user_type, email=None, 
                   birth_date=None, age_group=None, bio=None, avatar_url=None):
        """Insert a new user into the database"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO users (username, password, user_type, email, birth_date, age_group, bio, avatar_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (username, password, user_type, email, birth_date, age_group, bio, avatar_url))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id
    
    def get_user_by_id(self, user_id):
        """Retrieve a specific user by ID"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        return user_data
    
    def get_user_by_username(self, username):
        """Retrieve a specific user by Username"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user_data = cursor.fetchone()
        conn.close()
        return user_data

    def get_all_users(self):
        """Retrieve all users from the database"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users ORDER BY user_id')
        users_data = cursor.fetchall()
        conn.close()
        return users_data
    
    def get_users_by_age_group(self, age_group):
        """Retrieve users by age group (youth/senior)"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE age_group = ? ORDER BY username', (age_group,))
        users_data = cursor.fetchall()
        conn.close()
        return users_data
    
    def search_users(self, search_term):
        """Search users by username"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM users 
        WHERE username LIKE ? 
        ORDER BY username
        ''', (f'%{search_term}%',))
        users_data = cursor.fetchall()
        conn.close()
        return users_data
    
    def update_user(self, user_id, username=None, password=None, email=None, 
                   bio=None, avatar_url=None):
        """Update user information"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if username:
            updates.append("username = ?")
            params.append(username)
        if password:
            updates.append("password = ?")
            params.append(password)
        if email is not None:
            updates.append("email = ?")
            params.append(email)
        if bio is not None:
            updates.append("bio = ?")
            params.append(bio)
        if avatar_url is not None:
            updates.append("avatar_url = ?")
            params.append(avatar_url)
        
        if updates:
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
            cursor.execute(query, params)
            conn.commit()
        
        conn.close()
    
    def delete_user(self, user_id):
        """Delete a user from the database"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

    # =============== POST METHODS ===============

    def insert_post(self, content, user_id, post_category=None, post_prompt_id=None):
        """Insert a new post into the database"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO posts (content, user_id, post_category, post_prompt_id)
        VALUES (?, ?, ?, ?)
        ''', (content, user_id, post_category, post_prompt_id))
        post_id = cursor.lastrowid
        
        # Increment prompt usage if used
        if post_prompt_id:
            cursor.execute('''
            UPDATE post_prompts 
            SET times_used = times_used + 1 
            WHERE prompt_id = ?
            ''', (post_prompt_id,))
        
        # Track action for badges
        cursor.execute('''
        INSERT INTO user_actions (user_id, action_type, target_id)
        VALUES (?, 'create_post', ?)
        ''', (user_id, post_id))
        
        conn.commit()
        conn.close()
        return post_id
    
    def get_post_by_id(self, post_id):
        """Retrieve a specific post by ID"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT p.*, u.username 
        FROM posts p
        JOIN users u ON p.user_id = u.user_id
        WHERE p.post_id = ?
        ''', (post_id,))
        post_data = cursor.fetchone()
        conn.close()
        return post_data
    
    def get_posts_by_user(self, user_id, category=None):
        """Retrieve all posts by a specific user"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        query = '''
        SELECT p.*, u.username 
        FROM posts p
        JOIN users u ON p.user_id = u.user_id
        WHERE p.user_id = ?
        '''
        params = [user_id]
        
        if category:
            query += ' AND p.post_category = ?'
            params.append(category)
        
        query += ' ORDER BY p.timestamp DESC'
        
        cursor.execute(query, params)
        posts_data = cursor.fetchall()
        conn.close()
        return posts_data
    
    def get_all_posts(self, category=None, limit=50):
        """Retrieve all posts from the database"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        query = '''
        SELECT p.*, u.username 
        FROM posts p
        JOIN users u ON p.user_id = u.user_id
        WHERE 1=1
        '''
        params = []
        
        if category:
            query += ' AND p.post_category = ?'
            params.append(category)
        
        query += ' ORDER BY p.timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        posts_data = cursor.fetchall()
        conn.close()
        return posts_data
    
    def get_followed_posts(self, user_id):
        """Retrieve posts from users that the current user follows"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT p.*, u.username 
        FROM posts p
        JOIN users u ON p.user_id = u.user_id
        JOIN following f ON p.user_id = f.followed_id
        WHERE f.follower_id = ?
        ORDER BY p.timestamp DESC
        LIMIT 50
        ''', (user_id,))
        posts_data = cursor.fetchall()
        conn.close()
        return posts_data
    
    def like_post(self, post_id, user_id):
        """Like a post"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Increment like count
        cursor.execute('UPDATE posts SET likes = likes + 1 WHERE post_id = ?', (post_id,))
        
        # Track action for badges
        cursor.execute('''
        INSERT INTO user_actions (user_id, action_type, target_id)
        VALUES (?, 'like_post', ?)
        ''', (user_id, post_id))
        
        # Create notification for post owner
        cursor.execute('SELECT user_id FROM posts WHERE post_id = ?', (post_id,))
        post_owner = cursor.fetchone()
        if post_owner and post_owner[0] != user_id:
            cursor.execute('''
            INSERT INTO notifications (user_id, notification_type, message, related_id)
            VALUES (?, 'like', ? || ' liked your post', ?)
            ''', (post_owner[0], self.get_username_by_id(user_id), post_id))
        
        conn.commit()
        conn.close()
        return True
    
    def update_post(self, post_id, content=None, likes=None):
        """Update post information"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if content:
            updates.append("content = ?")
            params.append(content)
        if likes is not None:
            updates.append("likes = ?")
            params.append(likes)
        
        if updates:
            params.append(post_id)
            query = f"UPDATE posts SET {', '.join(updates)} WHERE post_id = ?"
            cursor.execute(query, params)
            conn.commit()
        
        conn.close()
    
    def delete_post(self, post_id):
        """Delete a post from the database"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM posts WHERE post_id = ?', (post_id,))
        conn.commit()
        conn.close()

    # =============== EVENT METHODS ===============

    def insert_event(self, event_name, event_itinerary, event_duration, 
                     event_date, location, max_participants, user_id,
                     game_type=None, game_rules=None):
        """Insert a new event into the database"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO events (event_name, event_itinerary, event_duration, 
                           event_date, location, max_participants, user_id, game_type, game_rules)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (event_name, event_itinerary, event_duration, event_date, 
              location, max_participants, user_id, game_type, game_rules))
        event_id = cursor.lastrowid
        
        # Track action for badges
        cursor.execute('''
        INSERT INTO user_actions (user_id, action_type, target_id)
        VALUES (?, 'create_event', ?)
        ''', (user_id, event_id))
        
        conn.commit()
        conn.close()
        return event_id
    
    def get_event_by_id(self, event_id):
        """Retrieve a specific event by ID"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT e.*, u.username as organizer
        FROM events e
        JOIN users u ON e.user_id = u.user_id
        WHERE e.event_id = ?
        ''', (event_id,))
        event_data = cursor.fetchone()
        conn.close()
        return event_data
    
    def get_events_by_user(self, user_id):
        """Retrieve all events created by a specific user"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT e.*, u.username as organizer
        FROM events e
        JOIN users u ON e.user_id = u.user_id
        WHERE e.user_id = ? 
        ORDER BY e.event_date
        ''', (user_id,))
        events_data = cursor.fetchall()
        conn.close()
        return events_data
    
    def get_all_events(self, game_type=None):
        """Retrieve all events from the database"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        query = '''
        SELECT e.*, u.username as organizer
        FROM events e
        JOIN users u ON e.user_id = u.user_id
        WHERE 1=1
        '''
        params = []
        
        if game_type:
            query += ' AND e.game_type = ?'
            params.append(game_type)
        
        query += ' ORDER BY e.event_date'
        
        cursor.execute(query, params)
        events_data = cursor.fetchall()
        conn.close()
        return events_data
    
    def get_events_by_game_type(self, game_type):
        """Get events by specific game type"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT e.*, u.username as organizer
        FROM events e
        JOIN users u ON e.user_id = u.user_id
        WHERE e.game_type = ?
        ORDER BY e.event_date
        ''', (game_type,))
        events = cursor.fetchall()
        conn.close()
        return events
    
    def add_event_participant(self, event_id, user_id):
        """Add a participant to an event"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO event_participants (event_id, user_id)
            VALUES (?, ?)
            ''', (event_id, user_id))
            
            # Track action for badges
            cursor.execute('''
            INSERT INTO user_actions (user_id, action_type, target_id)
            VALUES (?, 'participate_event', ?)
            ''', (user_id, event_id))
            
            # Create notification for event organizer
            cursor.execute('SELECT user_id FROM events WHERE event_id = ?', (event_id,))
            event_organizer = cursor.fetchone()
            if event_organizer and event_organizer[0] != user_id:
                cursor.execute('''
                INSERT INTO notifications (user_id, notification_type, message, related_id)
                VALUES (?, 'event_join', ? || ' joined your event', ?)
                ''', (event_organizer[0], self.get_username_by_id(user_id), event_id))
            
            conn.commit()
            success = True
        except sqlite3.IntegrityError:
            success = False  # User already registered or event doesn't exist
        conn.close()
        return success
    
    def get_event_participants(self, event_id):
        """Get all participants for an event"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT u.user_id, u.username, u.email, u.age_group, ep.joined_at
        FROM event_participants ep
        JOIN users u ON ep.user_id = u.user_id
        WHERE ep.event_id = ?
        ORDER BY ep.joined_at
        ''', (event_id,))
        participants = cursor.fetchall()
        conn.close()
        return participants

    # =============== BADGE METHODS ===============

    def get_badge_by_id(self, badge_id):
        """Retrieve a specific badge by ID"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM badges WHERE badge_id = ?', (badge_id,))
        badge_data = cursor.fetchone()
        conn.close()
        return badge_data
    
    def get_all_badges(self):
        """Retrieve all badges"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM badges ORDER BY badge_id')
        badges = cursor.fetchall()
        conn.close()
        return badges
    
    def assign_badge_to_user(self, user_id, badge_id):
        """Assign a badge to a user"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO user_badges (user_id, badge_id)
            VALUES (?, ?)
            ''', (user_id, badge_id))
            
            # Create notification
            cursor.execute('SELECT badge_name FROM badges WHERE badge_id = ?', (badge_id,))
            badge_name = cursor.fetchone()[0]
            cursor.execute('''
            INSERT INTO notifications (user_id, notification_type, message, related_id)
            VALUES (?, 'badge', 'You earned the ' || ? || ' badge!', ?)
            ''', (user_id, badge_name, badge_id))
            
            conn.commit()
            success = True
        except sqlite3.IntegrityError:
            success = False  # User already has this badge
        conn.close()
        return success
    
    def get_user_badges(self, user_id):
        """Get all badges for a user with progress"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT b.*, 
               ub.current_progress,
               ub.earned_date,
               CASE WHEN ub.user_id IS NOT NULL THEN 1 ELSE 0 END as earned
        FROM badges b
        LEFT JOIN user_badges ub ON b.badge_id = ub.badge_id AND ub.user_id = ?
        ORDER BY earned DESC, b.badge_id
        ''', (user_id,))
        
        badges = cursor.fetchall()
        conn.close()
        return badges
    
    def update_badge_progress(self, user_id, badge_id, progress_increment=1):
        """Update progress for a user's badge"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Get current progress
        cursor.execute('''
        SELECT current_progress FROM user_badges 
        WHERE user_id = ? AND badge_id = ?
        ''', (user_id, badge_id))
        
        result = cursor.fetchone()
        
        if result:
            current_progress = result[0]
            new_progress = current_progress + progress_increment
            
            cursor.execute('''
            UPDATE user_badges 
            SET current_progress = ?
            WHERE user_id = ? AND badge_id = ?
            ''', (new_progress, user_id, badge_id))
        else:
            # First time tracking this badge
            cursor.execute('''
            INSERT INTO user_badges (user_id, badge_id, current_progress)
            VALUES (?, ?, ?)
            ''', (user_id, badge_id, progress_increment))
        
        conn.commit()
        conn.close()

    # =============== FOLLOWING METHODS ===============

    def create_follow_request(self, requester_id, target_id):
        """Create a follow request (needs approval)"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO follow_requests (requester_id, target_id, status)
            VALUES (?, ?, 'pending')
            ''', (requester_id, target_id))
            
            # Create notification
            requester_name = self.get_username_by_id(requester_id)
            cursor.execute('''
            INSERT INTO notifications (user_id, notification_type, message, related_id)
            VALUES (?, 'follow_request', ? || ' sent you a follow request', ?)
            ''', (target_id, requester_name, requester_id))
            
            conn.commit()
            success = True
        except sqlite3.IntegrityError:
            success = False  # Request already exists
        conn.close()
        return success
    
    def respond_follow_request(self, request_id, response, target_id):
        """Accept or reject a follow request"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        if response == 'accept':
            # Get the requester_id
            cursor.execute('SELECT requester_id FROM follow_requests WHERE request_id = ? AND target_id = ?',
                         (request_id, target_id))
            result = cursor.fetchone()
            
            if result:
                requester_id = result[0]
                # Add to following table
                cursor.execute('''
                INSERT OR IGNORE INTO following (follower_id, followed_id)
                VALUES (?, ?)
                ''', (requester_id, target_id))
                
                # Track action for badges
                cursor.execute('''
                INSERT INTO user_actions (user_id, action_type, target_id)
                VALUES (?, 'follow_user', ?)
                ''', (requester_id, target_id))
                
                # Update request status
                cursor.execute('''
                UPDATE follow_requests 
                SET status = 'accepted', responded_at = CURRENT_TIMESTAMP
                WHERE request_id = ?
                ''', (request_id,))
                
                # Create notification for requester
                target_name = self.get_username_by_id(target_id)
                cursor.execute('''
                INSERT INTO notifications (user_id, notification_type, message, related_id)
                VALUES (?, 'follow_accept', ? || ' accepted your follow request', ?)
                ''', (requester_id, target_name, target_id))
                
                conn.commit()
                success = True
            else:
                success = False
        else:  # reject
            cursor.execute('''
            UPDATE follow_requests 
            SET status = 'rejected', responded_at = CURRENT_TIMESTAMP
            WHERE request_id = ? AND target_id = ?
            ''', (request_id, target_id))
            conn.commit()
            success = cursor.rowcount > 0
        
        conn.close()
        return success
    
    def get_pending_follow_requests(self, user_id):
        """Get all pending follow requests for a user"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT fr.request_id, fr.requester_id, u.username, u.avatar_url, fr.requested_at
        FROM follow_requests fr
        JOIN users u ON fr.requester_id = u.user_id
        WHERE fr.target_id = ? AND fr.status = 'pending'
        ORDER BY fr.requested_at DESC
        ''', (user_id,))
        requests = cursor.fetchall()
        conn.close()
        return requests
    
    def get_followers(self, user_id):
        """Get all followers of a user"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT u.user_id, u.username, u.avatar_url, u.age_group, f.follow_date
        FROM following f
        JOIN users u ON f.follower_id = u.user_id
        WHERE f.followed_id = ?
        ORDER BY f.follow_date DESC
        ''', (user_id,))
        followers = cursor.fetchall()
        conn.close()
        return followers
    
    def get_following(self, user_id):
        """Get all users that a user is following"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT u.user_id, u.username, u.avatar_url, u.age_group, f.follow_date
        FROM following f
        JOIN users u ON f.followed_id = u.user_id
        WHERE f.follower_id = ?
        ORDER BY f.follow_date DESC
        ''', (user_id,))
        following = cursor.fetchall()
        conn.close()
        return following
    
    def unfollow_user(self, follower_id, followed_id):
        """Unfollow a user"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        DELETE FROM following 
        WHERE follower_id = ? AND followed_id = ?
        ''', (follower_id, followed_id))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    def check_follow_status(self, follower_id, followed_id):
        """Check if one user follows another"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT 1 FROM following 
        WHERE follower_id = ? AND followed_id = ?
        ''', (follower_id, followed_id))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    def check_follow_request(self, requester_id, target_id):
        """Check if there's a pending follow request"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT request_id, status FROM follow_requests 
        WHERE requester_id = ? AND target_id = ?
        ''', (requester_id, target_id))
        result = cursor.fetchone()
        conn.close()
        return result

    # =============== COMMENT METHODS ===============

    def insert_comment(self, post_id, user_id, content):
        """Insert a new comment into the database"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO comments (post_id, user_id, content)
        VALUES (?, ?, ?)
        ''', (post_id, user_id, content))
        comment_id = cursor.lastrowid
        
        # Track action for badges
        cursor.execute('''
        INSERT INTO user_actions (user_id, action_type, target_id)
        VALUES (?, 'comment_post', ?)
        ''', (user_id, post_id))
        
        # Create notification for post owner
        cursor.execute('SELECT user_id FROM posts WHERE post_id = ?', (post_id,))
        post_owner = cursor.fetchone()
        if post_owner and post_owner[0] != user_id:
            cursor.execute('''
            INSERT INTO notifications (user_id, notification_type, message, related_id)
            VALUES (?, 'comment', ? || ' commented on your post', ?)
            ''', (post_owner[0], self.get_username_by_id(user_id), post_id))
        
        conn.commit()
        conn.close()
        return comment_id
    
    def get_comments_by_post(self, post_id):
        """Get all comments for a post"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT c.*, u.username, u.avatar_url
        FROM comments c
        JOIN users u ON c.user_id = u.user_id
        WHERE c.post_id = ?
        ORDER BY c.timestamp ASC
        ''', (post_id,))
        comments = cursor.fetchall()
        conn.close()
        return comments

    # =============== PROMPT METHODS ===============

    def insert_post_prompt(self, prompt_text, category, target_age_group='senior', difficulty_level='easy'):
        """Insert a new post prompt"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO post_prompts (prompt_text, category, target_age_group, difficulty_level)
        VALUES (?, ?, ?, ?)
        ''', (prompt_text, category, target_age_group, difficulty_level))
        prompt_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return prompt_id
    
    def get_prompts_for_user(self, age_group, limit=5):
        """Get post prompts suitable for a user's age group"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM post_prompts 
        WHERE target_age_group = ? OR target_age_group = 'both'
        ORDER BY times_used ASC, RANDOM()
        LIMIT ?
        ''', (age_group, limit))
        prompts = cursor.fetchall()
        conn.close()
        return prompts
    
    def get_all_prompts(self):
        """Get all post prompts"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM post_prompts ORDER BY category, target_age_group')
        prompts = cursor.fetchall()
        conn.close()
        return prompts

    # =============== NOTIFICATION METHODS ===============

    def get_notifications(self, user_id, unread_only=False):
        """Get notifications for a user"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        query = '''
        SELECT * FROM notifications 
        WHERE user_id = ?
        '''
        params = [user_id]
        
        if unread_only:
            query += ' AND is_read = 0'
        
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query, params)
        notifications = cursor.fetchall()
        conn.close()
        return notifications
    
    def mark_notification_read(self, notification_id):
        """Mark a notification as read"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE notifications 
        SET is_read = 1 
        WHERE notification_id = ?
        ''', (notification_id,))
        conn.commit()
        conn.close()
    
    def mark_all_notifications_read(self, user_id):
        """Mark all notifications as read for a user"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE notifications 
        SET is_read = 1 
        WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()

    # =============== HELPER METHODS ===============

    def get_username_by_id(self, user_id):
        """Get username by user ID"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT username FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def check_and_award_badges(self, user_id):
        """Check if user has earned any badges based on their actions"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Get user's actions count for each type
        cursor.execute('''
        SELECT action_type, COUNT(*) as count
        FROM user_actions
        WHERE user_id = ?
        GROUP BY action_type
        ''', (user_id,))
        
        actions = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Get all badges with their criteria
        cursor.execute('SELECT badge_id, criteria, progress_required FROM badges')
        badges = cursor.fetchall()
        
        for badge_id, criteria, progress_required in badges:
            # Check if badge matches user's actions
            if criteria and criteria in actions:
                if actions[criteria] >= progress_required:
                    # Award badge if not already awarded
                    cursor.execute('''
                    INSERT OR IGNORE INTO user_badges (user_id, badge_id, current_progress)
                    VALUES (?, ?, ?)
                    ''', (user_id, badge_id, actions[criteria]))
        
        conn.commit()
        conn.close()
    
    def get_user_stats(self, user_id):
        """Get statistics for a user"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        stats = {}
        
        # Post count
        cursor.execute('SELECT COUNT(*) FROM posts WHERE user_id = ?', (user_id,))
        stats['post_count'] = cursor.fetchone()[0]
        
        # Follower count
        cursor.execute('SELECT COUNT(*) FROM following WHERE followed_id = ?', (user_id,))
        stats['follower_count'] = cursor.fetchone()[0]
        
        # Following count
        cursor.execute('SELECT COUNT(*) FROM following WHERE follower_id = ?', (user_id,))
        stats['following_count'] = cursor.fetchone()[0]
        
        # Event count (created)
        cursor.execute('SELECT COUNT(*) FROM events WHERE user_id = ?', (user_id,))
        stats['event_count'] = cursor.fetchone()[0]
        
        # Badge count
        cursor.execute('SELECT COUNT(*) FROM user_badges WHERE user_id = ?', (user_id,))
        stats['badge_count'] = cursor.fetchone()[0]
        
        # Total likes received
        cursor.execute('''
        SELECT SUM(likes) FROM posts WHERE user_id = ?
        ''', (user_id,))
        stats['total_likes'] = cursor.fetchone()[0] or 0
        
        conn.close()
        return stats