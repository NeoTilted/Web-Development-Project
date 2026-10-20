#!/usr/bin/env python3
"""
SECURE ADMIN ACCOUNT CREATION SCRIPT
Run this script directly via command line only.
"""

import sqlite3
import sys
import getpass
from werkzeug.security import generate_password_hash
import hashlib
import secrets

def create_admin_account():
    """Create an admin account via secure command-line interface"""
    
    print("\n" + "="*50)
    print("ADMIN ACCOUNT CREATION TOOL")
    print("="*50)
    print("\n⚠️  WARNING: This tool creates admin-level accounts.")
    print("   Only authorized personnel should use this.\n")
    
    # Verify authorization
    auth_code = getpass.getpass("Enter admin creation authorization code: ")
    
    # You can set an environment variable or use a fixed hash
    expected_hash = hashlib.sha256(b"a").hexdigest()
    if hashlib.sha256(auth_code.encode()).hexdigest() != expected_hash:
        print("\n❌ Authorization failed!")
        sys.exit(1)
    
    # Get admin details
    print("\n" + "-"*50)
    admin_username = input("Admin username: ").strip()
    
    if not admin_username:
        print("❌ Username required!")
        sys.exit(1)
    
    # Check if username already exists
    db_name = 'BondBuddies.db'
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM users WHERE username = ?', (admin_username,))
    if cursor.fetchone():
        print(f"❌ Username '{admin_username}' already exists!")
        conn.close()
        sys.exit(1)
    
    # Get password with confirmation
    while True:
        admin_password = getpass.getpass("Admin password (min 12 chars): ")
        confirm_password = getpass.getpass("Confirm password: ")
        
        if len(admin_password) < 12:
            print("❌ Password must be at least 12 characters!")
            continue
            
        if admin_password != confirm_password:
            print("❌ Passwords don't match!")
            continue
            
        # Check password strength
        if not any(c.isupper() for c in admin_password):
            print("❌ Password must contain uppercase letters!")
            continue
        if not any(c.islower() for c in admin_password):
            print("❌ Password must contain lowercase letters!")
            continue
        if not any(c.isdigit() for c in admin_password):
            print("❌ Password must contain numbers!")
            continue
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in admin_password):
            print("❌ Password must contain special characters!")
            continue
            
        break
    
    admin_email = input("Admin email (optional): ").strip() or None
    
    # Hash the password
    hashed_password = generate_password_hash(
        admin_password,
        method="pbkdf2:sha256",
        salt_length=16,
    )
    
    # Insert admin user
    try:
        cursor.execute('''
        INSERT INTO users (username, password, user_type, email, age_group, bio)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            admin_username, 
            hashed_password, 
            'admin', 
            admin_email, 
            'senior',
            'System Administrator'
        ))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        print(f"\n✅ Admin account '{admin_username}' created successfully!")
        print(f"   User ID: {user_id}")
        print(f"   User Type: Admin")
        print(f"   Email: {admin_email or 'Not set'}")
        print("\n⚠️  IMPORTANT:")
        print("   1. Store credentials securely")
        print("   2. Enable 2FA if available")
        print("   3. Use strong, unique password")
        print("   4. Log in at: /login")
        
        # Log the creation (for audit trail)
        with open('admin_creation.log', 'a') as log_file:
            log_file.write(f"[{datetime.now()}] Admin created: {admin_username} (ID: {user_id})\n")
            
    except Exception as e:
        print(f"❌ Error creating admin account: {e}")
        conn.rollback()
    finally:
        conn.close()

def list_admin_accounts():
    """List all existing admin accounts"""
    db_name = 'BondBuddies.db'
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT user_id, username, email, created_at 
    FROM users 
    WHERE user_type = 'admin'
    ORDER BY created_at
    ''')
    
    admins = cursor.fetchall()
    conn.close()
    
    print("\n" + "="*50)
    print("EXISTING ADMIN ACCOUNTS")
    print("="*50)
    
    if not admins:
        print("No admin accounts found.")
        return
    
    for admin in admins:
        print(f"\nID: {admin[0]}")
        print(f"Username: {admin[1]}")
        print(f"Email: {admin[2] or 'Not set'}")
        print(f"Created: {admin[3]}")
    
    print(f"\nTotal: {len(admins)} admin account(s)")

def reset_admin_password():
    """Reset an existing admin's password"""
    db_name = 'BondBuddies.db'
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # List admins
    cursor.execute('SELECT user_id, username FROM users WHERE user_type = "admin"')
    admins = cursor.fetchall()
    
    if not admins:
        print("No admin accounts found.")
        return
    
    print("\nSelect admin to reset:")
    for idx, admin in enumerate(admins, 1):
        print(f"{idx}. {admin[1]} (ID: {admin[0]})")
    
    try:
        choice = int(input("\nEnter number: ")) - 1
        if choice < 0 or choice >= len(admins):
            print("Invalid choice!")
            return
            
        admin_id, admin_username = admins[choice]
        
        # Get new password
        while True:
            new_password = getpass.getpass(f"New password for {admin_username}: ")
            confirm = getpass.getpass("Confirm password: ")
            
            if new_password != confirm:
                print("Passwords don't match!")
                continue
                
            if len(new_password) < 12:
                print("Password must be at least 12 characters!")
                continue
                
            break
        
        # Hash and update
        hashed_password = generate_password_hash(
            new_password,
            method="pbkdf2:sha256",
            salt_length=16,
        )
        
        cursor.execute(
            'UPDATE users SET password = ? WHERE user_id = ?',
            (hashed_password, admin_id)
        )
        
        conn.commit()
        print(f"✅ Password for {admin_username} has been reset.")
        
    except ValueError:
        print("Invalid input!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    from datetime import datetime
    
    print("\nBond Buddies - Admin Management")
    print("="*50)
    
    while True:
        print("\nOptions:")
        print("1. Create new admin account")
        print("2. List existing admin accounts")
        print("3. Reset admin password")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            create_admin_account()
            break
        elif choice == '2':
            list_admin_accounts()
        elif choice == '3':
            reset_admin_password()
        elif choice == '4':
            print("Exiting...")
            break
        else:
            print("Invalid option!")    