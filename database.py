import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List, Tuple

class Database:
    def __init__(self, db_name: str = "referral_bot.db"):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                credits INTEGER DEFAULT 0,
                total_referrals INTEGER DEFAULT 0,
                joined_date TEXT,
                FOREIGN KEY (referred_by) REFERENCES users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                date TEXT,
                FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                FOREIGN KEY (referred_id) REFERENCES users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS redemptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                redemption_code TEXT UNIQUE,
                credits_used INTEGER,
                date TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE,
                channel_name TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        cursor.execute('''
            INSERT OR IGNORE INTO settings (key, value) 
            VALUES ('start_message', '🎉 Welcome to Referral Bot!\n\nEarn credits by referring friends:\n• 5 credits per referral\n• Redeem at 300 credits\n\nUse /help to see all commands.')
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id: int, username: Optional[str], first_name: str, referred_by: Optional[int] = None) -> str:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if cursor.fetchone():
            conn.close()
            return None
        
        referral_code = str(uuid.uuid4())[:8]
        joined_date = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, referral_code, referred_by, joined_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, referral_code, referred_by, joined_date))
        
        if referred_by:
            cursor.execute('''
                INSERT INTO referrals (referrer_id, referred_id, date)
                VALUES (?, ?, ?)
            ''', (referred_by, user_id, joined_date))
            
            cursor.execute('''
                UPDATE users SET credits = credits + 5, total_referrals = total_referrals + 1
                WHERE user_id = ?
            ''', (referred_by,))
        
        conn.commit()
        conn.close()
        return referral_code
    
    def get_user(self, user_id: int) -> Optional[dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'user_id': row[0],
                'username': row[1],
                'first_name': row[2],
                'referral_code': row[3],
                'referred_by': row[4],
                'credits': row[5],
                'total_referrals': row[6],
                'joined_date': row[7]
            }
        return None
    
    def get_user_by_referral_code(self, referral_code: str) -> Optional[int]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (referral_code,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    
    def get_leaderboard(self, limit: int = 10) -> List[Tuple]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, first_name, total_referrals 
            FROM users 
            WHERE total_referrals > 0
            ORDER BY total_referrals DESC 
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    def get_user_rank(self, user_id: int) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) + 1 
            FROM users 
            WHERE total_referrals > (
                SELECT total_referrals FROM users WHERE user_id = ?
            )
        ''', (user_id,))
        rank = cursor.fetchone()[0]
        conn.close()
        return rank
    
    def redeem_credits(self, user_id: int, credits_required: int = 300) -> Optional[str]:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT credits FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if not row or row[0] < credits_required:
            conn.close()
            return None
        
        redemption_code = f"REWARD-{uuid.uuid4().hex[:8].upper()}"
        date = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO redemptions (user_id, redemption_code, credits_used, date)
            VALUES (?, ?, ?, ?)
        ''', (user_id, redemption_code, credits_required, date))
        
        cursor.execute('''
            UPDATE users SET credits = credits - ?
            WHERE user_id = ?
        ''', (credits_required, user_id))
        
        conn.commit()
        conn.close()
        return redemption_code
    
    def get_all_users(self) -> List[int]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users
    
    def get_stats(self) -> dict:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM referrals')
        total_referrals = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM redemptions')
        total_redemptions = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_users': total_users,
            'total_referrals': total_referrals,
            'total_redemptions': total_redemptions
        }
    
    def add_channel(self, channel_id: str, channel_name: str) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO channels (channel_id, channel_name) VALUES (?, ?)', 
                         (channel_id, channel_name))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def remove_channel(self, channel_id: str) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM channels WHERE channel_id = ?', (channel_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    
    def get_channels(self) -> List[Tuple[str, str]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT channel_id, channel_name FROM channels')
        channels = cursor.fetchall()
        conn.close()
        return channels
    
    def set_start_message(self, message: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', 
                      ('start_message', message))
        conn.commit()
        conn.close()
    
    def get_start_message(self) -> str:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', ('start_message',))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 'Welcome!'
