class User:
    def __init__(self, user_id, username, password, user_type, email=None, 
                 birth_date=None, age_group=None, bio=None, avatar_url=None):
        self.__user_id = user_id
        self.__username = username
        self.__password = password
        self.__user_type = user_type
        self.__email = email
        self.__birth_date = birth_date
        self.__age_group = age_group  # 'youth' or 'senior'
        self.__bio = bio
        self.__avatar_url = avatar_url
        self.__created_at = None
        self.__following = []
        self.__followers = []
        self.__pending_follow_requests = []
        self.__follow_requests_sent = []
        
    # Accessor methods
    def get_user_id(self):
        return self.__user_id
    def get_username(self):
        return self.__username
    def get_password(self):
        return self.__password
    def get_user_type(self):
        return self.__user_type
    def get_email(self):
        return self.__email
    def get_birth_date(self):
        return self.__birth_date
    def get_age_group(self):
        return self.__age_group
    def get_bio(self):
        return self.__bio
    def get_avatar_url(self):
        return self.__avatar_url
    def get_created_at(self):
        return self.__created_at
    def get_following(self):
        return self.__following
    def get_followers(self):
        return self.__followers
    def get_pending_follow_requests(self):
        return self.__pending_follow_requests
    def get_follow_requests_sent(self):
        return self.__follow_requests_sent
    
    # Mutator methods
    def set_user_id(self, user_id):
        self.__user_id = user_id
    def set_username(self, username):
        self.__username = username
    def set_password(self, password):
        self.__password = password
    def set_user_type(self, user_type):
        self.__user_type = user_type
    def set_email(self, email):
        self.__email = email
    def set_birth_date(self, birth_date):
        self.__birth_date = birth_date
    def set_age_group(self, age_group):
        self.__age_group = age_group
    def set_bio(self, bio):
        self.__bio = bio
    def set_avatar_url(self, avatar_url):
        self.__avatar_url = avatar_url
    def set_created_at(self, created_at):
        self.__created_at = created_at
    def add_following(self, user_id):
        if user_id not in self.__following:
            self.__following.append(user_id)
    def remove_following(self, user_id):
        if user_id in self.__following:
            self.__following.remove(user_id)
    def add_follower(self, user_id):
        if user_id not in self.__followers:
            self.__followers.append(user_id)
    def remove_follower(self, user_id):
        if user_id in self.__followers:
            self.__followers.remove(user_id)
    def add_pending_follow_request(self, user_id):
        if user_id not in self.__pending_follow_requests:
            self.__pending_follow_requests.append(user_id)
    def remove_pending_follow_request(self, user_id):
        if user_id in self.__pending_follow_requests:
            self.__pending_follow_requests.remove(user_id)
    def add_follow_request_sent(self, user_id):
        if user_id not in self.__follow_requests_sent:
            self.__follow_requests_sent.append(user_id)
    def remove_follow_request_sent(self, user_id):
        if user_id in self.__follow_requests_sent:
            self.__follow_requests_sent.remove(user_id)
    
    @classmethod
    def from_database_row(cls, row_data):
        """Create a User object from database row data"""
        return cls(
            user_id=row_data[0],
            username=row_data[1],
            password=row_data[2],
            user_type=row_data[3],
            email=row_data[4] if len(row_data) > 4 and row_data[4] else None,
            birth_date=row_data[5] if len(row_data) > 5 else None,
            age_group=row_data[6] if len(row_data) > 6 else None,
            bio=row_data[7] if len(row_data) > 7 else None,
            avatar_url=row_data[8] if len(row_data) > 8 else None
        )


class Post:
    def __init__(self, post_id, content, user_id, timestamp, likes=0, 
                 comments=None, post_category=None, post_prompt_id=None):
        self.__post_id = post_id
        self.__content = content
        self.__user_id = user_id
        self.__timestamp = timestamp
        self.__likes = likes
        self.__comments = comments if comments is not None else []
        self.__post_category = post_category  # 'youth' or 'senior'
        self.__post_prompt_id = post_prompt_id  # ID of the prompt that inspired this post
        
    # Accessor methods
    def get_post_id(self):
        return self.__post_id
    def get_content(self):
        return self.__content
    def get_user_id(self):
        return self.__user_id
    def get_timestamp(self):
        return self.__timestamp
    def get_likes(self):
        return self.__likes
    def get_comments(self):
        return self.__comments
    def get_post_category(self):
        return self.__post_category
    def get_post_prompt_id(self):
        return self.__post_prompt_id
    
    # Mutator methods
    def set_post_id(self, post_id):
        self.__post_id = post_id
    def set_content(self, content):
        self.__content = content
    def set_user_id(self, user_id):
        self.__user_id = user_id
    def set_timestamp(self, timestamp):
        self.__timestamp = timestamp
    def set_likes(self, likes):
        self.__likes = likes
    def add_like(self):
        self.__likes += 1
    def remove_like(self):
        if self.__likes > 0:
            self.__likes -= 1
    def add_comment(self, comment):
        self.__comments.append(comment)
    def set_post_category(self, post_category):
        self.__post_category = post_category
    def set_post_prompt_id(self, post_prompt_id):
        self.__post_prompt_id = post_prompt_id
    
    @classmethod
    def from_database_row(cls, row_data):
        """Create a Post object from database row data"""
        return cls(
            post_id=row_data[0],
            content=row_data[1],
            user_id=row_data[2],
            timestamp=row_data[3],
            likes=row_data[4] if len(row_data) > 4 else 0,
            post_category=row_data[5] if len(row_data) > 5 else None,
            post_prompt_id=row_data[6] if len(row_data) > 6 else None
        )


class Event:
    def __init__(self, event_id, event_name, event_itinerary, event_duration,
                 event_date, location, max_participants, user_id, 
                 game_type=None, game_rules=None, participants=None):
        self.__event_id = event_id
        self.__event_name = event_name
        self.__event_itinerary = event_itinerary
        self.__event_duration = event_duration
        self.__event_date = event_date
        self.__location = location
        self.__max_participants = max_participants
        self.__user_id = user_id  # Event creator/organizer
        self.__game_type = game_type  # 'mahjong', 'blackjack', 'big2', 'other'
        self.__game_rules = game_rules
        self.__participants = participants if participants is not None else []
        
    # Accessor methods
    def get_event_id(self):
        return self.__event_id
    def get_event_name(self):
        return self.__event_name
    def get_event_itinerary(self):
        return self.__event_itinerary
    def get_event_duration(self):
        return self.__event_duration
    def get_event_date(self):
        return self.__event_date
    def get_location(self):
        return self.__location
    def get_max_participants(self):
        return self.__max_participants
    def get_user_id(self):
        return self.__user_id
    def get_game_type(self):
        return self.__game_type
    def get_game_rules(self):
        return self.__game_rules
    def get_participants(self):
        return self.__participants
    
    # Mutator methods
    def set_event_id(self, event_id):
        self.__event_id = event_id
    def set_event_name(self, event_name):
        self.__event_name = event_name
    def set_event_itinerary(self, event_itinerary):
        self.__event_itinerary = event_itinerary
    def set_event_duration(self, event_duration):
        self.__event_duration = event_duration
    def set_event_date(self, event_date):
        self.__event_date = event_date
    def set_location(self, location):
        self.__location = location
    def set_max_participants(self, max_participants):
        self.__max_participants = max_participants
    def set_user_id(self, user_id):
        self.__user_id = user_id
    def set_game_type(self, game_type):
        self.__game_type = game_type
    def set_game_rules(self, game_rules):
        self.__game_rules = game_rules
    def add_participant(self, user_id):
        if len(self.__participants) < self.__max_participants and user_id not in self.__participants:
            self.__participants.append(user_id)
            return True
        return False
    def remove_participant(self, user_id):
        if user_id in self.__participants:
            self.__participants.remove(user_id)
            return True
        return False
    
    @classmethod
    def from_database_row(cls, row_data):
        """Create an Event object from database row data"""
        return cls(
            event_id=row_data[0],
            event_name=row_data[1],
            event_itinerary=row_data[2],
            event_duration=row_data[3],
            event_date=row_data[4],
            location=row_data[5],
            max_participants=row_data[6],
            user_id=row_data[7],
            game_type=row_data[8] if len(row_data) > 8 else None,
            game_rules=row_data[9] if len(row_data) > 9 else None
        )


class Badge:
    def __init__(self, badge_id, badge_name, badge_description, badge_type, 
                 criteria=None, progress_required=1, progress_type="count", 
                 user_id=None, earned_date=None, current_progress=0):
        self.__badge_id = badge_id
        self.__badge_name = badge_name
        self.__badge_description = badge_description
        self.__badge_type = badge_type
        self.__criteria = criteria  # JSON string or description
        self.__progress_required = progress_required
        self.__progress_type = progress_type  # 'count', 'percentage', 'boolean'
        self.__user_id = user_id
        self.__earned_date = earned_date
        self.__current_progress = current_progress
        
    # Accessor methods
    def get_badge_id(self):
        return self.__badge_id
    def get_badge_name(self):
        return self.__badge_name
    def get_badge_description(self):
        return self.__badge_description
    def get_badge_type(self):
        return self.__badge_type
    def get_criteria(self):
        return self.__criteria
    def get_progress_required(self):
        return self.__progress_required
    def get_progress_type(self):
        return self.__progress_type
    def get_user_id(self):
        return self.__user_id
    def get_earned_date(self):
        return self.__earned_date
    def get_current_progress(self):
        return self.__current_progress
    
    # Mutator methods
    def set_badge_id(self, badge_id):
        self.__badge_id = badge_id
    def set_badge_name(self, badge_name):
        self.__badge_name = badge_name
    def set_badge_description(self, badge_description):
        self.__badge_description = badge_description
    def set_badge_type(self, badge_type):
        self.__badge_type = badge_type
    def set_criteria(self, criteria):
        self.__criteria = criteria
    def set_progress_required(self, progress_required):
        self.__progress_required = progress_required
    def set_progress_type(self, progress_type):
        self.__progress_type = progress_type
    def set_user_id(self, user_id):
        self.__user_id = user_id
    def set_earned_date(self, earned_date):
        self.__earned_date = earned_date
    def set_current_progress(self, current_progress):
        self.__current_progress = current_progress
    def increment_progress(self, amount=1):
        self.__current_progress += amount
    
    def is_completed(self):
        if self.__progress_type == "boolean":
            return self.__current_progress >= 1
        return self.__current_progress >= self.__progress_required
    
    def get_progress_percentage(self):
        if self.__progress_type == "boolean":
            return 100 if self.__current_progress >= 1 else 0
        if self.__progress_required == 0:
            return 0
        return min(100, (self.__current_progress / self.__progress_required) * 100)
    
    @classmethod
    def from_database_row(cls, row_data):
        """Create a Badge object from database row data"""
        return cls(
            badge_id=row_data[0],
            badge_name=row_data[1],
            badge_description=row_data[2],
            badge_type=row_data[3],
            criteria=row_data[4] if len(row_data) > 4 else None,
            progress_required=row_data[5] if len(row_data) > 5 else 1,
            progress_type=row_data[6] if len(row_data) > 6 else "count",
            user_id=row_data[7] if len(row_data) > 7 else None,
            earned_date=row_data[8] if len(row_data) > 8 else None,
            current_progress=row_data[9] if len(row_data) > 9 else 0
        )


class Following:
    def __init__(self, following_id, follower_id, followed_id, follow_date):
        self.__following_id = following_id
        self.__follower_id = follower_id
        self.__followed_id = followed_id
        self.__follow_date = follow_date
        
    # Accessor methods
    def get_following_id(self):
        return self.__following_id
    def get_follower_id(self):
        return self.__follower_id
    def get_followed_id(self):
        return self.__followed_id
    def get_follow_date(self):
        return self.__follow_date
    
    # Mutator methods
    def set_following_id(self, following_id):
        self.__following_id = following_id
    def set_follower_id(self, follower_id):
        self.__follower_id = follower_id
    def set_followed_id(self, followed_id):
        self.__followed_id = followed_id
    def set_follow_date(self, follow_date):
        self.__follow_date = follow_date
    
    @classmethod
    def from_database_row(cls, row_data):
        """Create a Following object from database row data"""
        return cls(
            following_id=row_data[0],
            follower_id=row_data[1],
            followed_id=row_data[2],
            follow_date=row_data[3]
        )


class FollowRequest:
    def __init__(self, request_id, requester_id, target_id, status="pending", 
                 requested_at=None, responded_at=None):
        self.__request_id = request_id
        self.__requester_id = requester_id
        self.__target_id = target_id
        self.__status = status  # 'pending', 'accepted', 'rejected'
        self.__requested_at = requested_at
        self.__responded_at = responded_at
        
    # Accessor methods
    def get_request_id(self):
        return self.__request_id
    def get_requester_id(self):
        return self.__requester_id
    def get_target_id(self):
        return self.__target_id
    def get_status(self):
        return self.__status
    def get_requested_at(self):
        return self.__requested_at
    def get_responded_at(self):
        return self.__responded_at
    
    # Mutator methods
    def set_request_id(self, request_id):
        self.__request_id = request_id
    def set_requester_id(self, requester_id):
        self.__requester_id = requester_id
    def set_target_id(self, target_id):
        self.__target_id = target_id
    def set_status(self, status):
        self.__status = status
    def set_requested_at(self, requested_at):
        self.__requested_at = requested_at
    def set_responded_at(self, responded_at):
        self.__responded_at = responded_at
    
    @classmethod
    def from_database_row(cls, row_data):
        """Create a FollowRequest object from database row data"""
        return cls(
            request_id=row_data[0],
            requester_id=row_data[1],
            target_id=row_data[2],
            status=row_data[3],
            requested_at=row_data[4],
            responded_at=row_data[5] if len(row_data) > 5 else None
        )


class PostPrompt:
    def __init__(self, prompt_id, prompt_text, category, target_age_group="senior", 
                 difficulty_level="easy", times_used=0, created_at=None):
        self.__prompt_id = prompt_id
        self.__prompt_text = prompt_text
        self.__category = category  # e.g., "memory", "daily_life", "hobbies"
        self.__target_age_group = target_age_group  # 'senior', 'youth', or 'both'
        self.__difficulty_level = difficulty_level
        self.__times_used = times_used
        self.__created_at = created_at
        
    # Accessor methods
    def get_prompt_id(self):
        return self.__prompt_id
    def get_prompt_text(self):
        return self.__prompt_text
    def get_category(self):
        return self.__category
    def get_target_age_group(self):
        return self.__target_age_group
    def get_difficulty_level(self):
        return self.__difficulty_level
    def get_times_used(self):
        return self.__times_used
    def get_created_at(self):
        return self.__created_at
    
    # Mutator methods
    def set_prompt_id(self, prompt_id):
        self.__prompt_id = prompt_id
    def set_prompt_text(self, prompt_text):
        self.__prompt_text = prompt_text
    def set_category(self, category):
        self.__category = category
    def set_target_age_group(self, target_age_group):
        self.__target_age_group = target_age_group
    def set_difficulty_level(self, difficulty_level):
        self.__difficulty_level = difficulty_level
    def set_times_used(self, times_used):
        self.__times_used = times_used
    def increment_usage(self):
        self.__times_used += 1
    def set_created_at(self, created_at):
        self.__created_at = created_at
    
    @classmethod
    def from_database_row(cls, row_data):
        """Create a PostPrompt object from database row data"""
        return cls(
            prompt_id=row_data[0],
            prompt_text=row_data[1],
            category=row_data[2],
            target_age_group=row_data[3] if len(row_data) > 3 else "senior",
            difficulty_level=row_data[4] if len(row_data) > 4 else "easy",
            times_used=row_data[5] if len(row_data) > 5 else 0,
            created_at=row_data[6] if len(row_data) > 6 else None
        )


class Comment:
    def __init__(self, comment_id, post_id, user_id, content, timestamp, username=None):
        self.__comment_id = comment_id
        self.__post_id = post_id
        self.__user_id = user_id
        self.__content = content
        self.__timestamp = timestamp
        self.__username = username
        
    # Accessor methods
    def get_comment_id(self):
        return self.__comment_id
    def get_post_id(self):
        return self.__post_id
    def get_user_id(self):
        return self.__user_id
    def get_content(self):
        return self.__content
    def get_timestamp(self):
        return self.__timestamp
    def get_username(self):
        return self.__username
    
    # Mutator methods
    def set_comment_id(self, comment_id):
        self.__comment_id = comment_id
    def set_post_id(self, post_id):
        self.__post_id = post_id
    def set_user_id(self, user_id):
        self.__user_id = user_id
    def set_content(self, content):
        self.__content = content
    def set_timestamp(self, timestamp):
        self.__timestamp = timestamp
    def set_username(self, username):
        self.__username = username
    
    @classmethod
    def from_database_row(cls, row_data):
        """Create a Comment object from database row data"""
        return cls(
            comment_id=row_data[0],
            post_id=row_data[1],
            user_id=row_data[2],
            content=row_data[3],
            timestamp=row_data[4],
            username=row_data[5] if len(row_data) > 5 else None
        )


class UserAction:
    def __init__(self, action_id, user_id, action_type, target_id=None, 
                 action_data=None, performed_at=None):
        self.__action_id = action_id
        self.__user_id = user_id
        self.__action_type = action_type  # 'like_post', 'comment_post', 'follow_user', 'share_post', 'participate_event'
        self.__target_id = target_id
        self.__action_data = action_data
        self.__performed_at = performed_at
        
    # Accessor methods
    def get_action_id(self):
        return self.__action_id
    def get_user_id(self):
        return self.__user_id
    def get_action_type(self):
        return self.__action_type
    def get_target_id(self):
        return self.__target_id
    def get_action_data(self):
        return self.__action_data
    def get_performed_at(self):
        return self.__performed_at
    
    # Mutator methods
    def set_action_id(self, action_id):
        self.__action_id = action_id
    def set_user_id(self, user_id):
        self.__user_id = user_id
    def set_action_type(self, action_type):
        self.__action_type = action_type
    def set_target_id(self, target_id):
        self.__target_id = target_id
    def set_action_data(self, action_data):
        self.__action_data = action_data
    def set_performed_at(self, performed_at):
        self.__performed_at = performed_at
    
    @classmethod
    def from_database_row(cls, row_data):
        """Create a UserAction object from database row data"""
        return cls(
            action_id=row_data[0],
            user_id=row_data[1],
            action_type=row_data[2],
            target_id=row_data[3] if len(row_data) > 3 else None,
            action_data=row_data[4] if len(row_data) > 4 else None,
            performed_at=row_data[5] if len(row_data) > 5 else None
        )