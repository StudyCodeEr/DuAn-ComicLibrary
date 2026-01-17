import sqlite3
import os

DB_FILE = "manga_library.db"

class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        # Tạo bảng Manga
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS manga (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                path TEXT,
                cover_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # [QUAN TRỌNG] Tạo bảng Tags với ràng buộc UNIQUE và không phân biệt hoa thường (NOCASE)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE COLLATE NOCASE
            )
        ''')
        
        # Bảng liên kết
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS manga_tags (
                manga_id INTEGER,
                tag_id INTEGER,
                FOREIGN KEY(manga_id) REFERENCES manga(id),
                FOREIGN KEY(tag_id) REFERENCES tags(id),
                PRIMARY KEY (manga_id, tag_id)
            )
        ''')
        self.conn.commit()

    def save_manga(self, url, title, path, cover_path=None, tags=None):
        try:
            # 1. Lưu hoặc Cập nhật Manga
            self.cursor.execute("SELECT id FROM manga WHERE url = ?", (url,))
            row = self.cursor.fetchone()
            
            if row:
                manga_id = row[0]
                self.cursor.execute("UPDATE manga SET title=?, path=?, cover_path=? WHERE id=?", (title, path, cover_path, manga_id))
            else:
                self.cursor.execute("INSERT INTO manga (url, title, path, cover_path) VALUES (?, ?, ?, ?)", (url, title, path, cover_path))
                manga_id = self.cursor.lastrowid

            # 2. Xử lý Tags (Logic chống trùng lặp)
            if tags:
                for tag in tags:
                    tag_clean = tag.strip() 
                    if not tag_clean: continue
                    
                    # Bước A: Kiểm tra xem Tag này đã có trong kho chưa?
                    self.cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_clean,))
                    tag_row = self.cursor.fetchone()
                    
                    if tag_row:
                        # Nếu có rồi -> Lấy ID cũ
                        tag_id = tag_row[0]
                    else:
                        # Nếu chưa có -> Tạo mới
                        try:
                            self.cursor.execute("INSERT INTO tags (name) VALUES (?)", (tag_clean,))
                            tag_id = self.cursor.lastrowid
                        except sqlite3.IntegrityError:
                            # Phòng trường hợp hiếm hoi bị trùng do race condition
                            self.cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_clean,))
                            tag_id = self.cursor.fetchone()[0]

                    # Bước B: Liên kết Manga với Tag (Nếu chưa liên kết)
                    self.cursor.execute("INSERT OR IGNORE INTO manga_tags (manga_id, tag_id) VALUES (?, ?)", (manga_id, tag_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"SQL Error: {e}")
            return False

    def get_all_tags(self):
        """Lấy danh sách tất cả tag đã được sắp xếp"""
        self.cursor.execute("SELECT name FROM tags ORDER BY name ASC")
        return [r[0] for r in self.cursor.fetchall()]

    def search_advanced(self, keyword="", include_tags=[], exclude_tags=[]):
        """Tìm kiếm nâng cao (AND / NOT IN)"""
        sql = "SELECT DISTINCT m.id, m.title, m.path, m.cover_path FROM manga m WHERE 1=1"
        params = []

        # Lọc theo tên
        if keyword:
            sql += " AND m.title LIKE ?"
            params.append(f"%{keyword}%")

        # Lọc loại trừ (EXCLUDE)
        if exclude_tags:
            placeholders = ','.join('?' * len(exclude_tags))
            subquery = f"SELECT mt.manga_id FROM manga_tags mt JOIN tags t ON mt.tag_id = t.id WHERE t.name IN ({placeholders})"
            sql += f" AND m.id NOT IN ({subquery})"
            params.extend(exclude_tags)

        # Lọc bắt buộc (INCLUDE - Logic AND)
        for tag in include_tags:
            # Tìm những manga CÓ chứa tag này
            subquery = "SELECT mt.manga_id FROM manga_tags mt JOIN tags t ON mt.tag_id = t.id WHERE t.name = ?"
            sql += f" AND m.id IN ({subquery})"
            params.append(tag)

        sql += " ORDER BY m.created_at DESC"
        
        self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()