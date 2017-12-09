# Modify a database created by the old database creator
import sqlite3 as lite
conn = lite.connect('video_db.db')
cur = conn.cursor()
cur.execute('ALTER TABLE video_db ADD COLUMN named_by_assignment_id TEXT;')
cur.execute('ALTER TABLE video_db ADD COLUMN named_by_worker_id TEXT;')
cur.execute('ALTER TABLE video_db ADD COLUMN named_by_hit_id TEXT;')
cur.execute('ALTER TABLE video_db ADD COLUMN trimmed_by_assignment_id TEXT;')
cur.execute('ALTER TABLE video_db ADD COLUMN trimmed_by_worker_id TEXT;')
cur.execute('ALTER TABLE video_db ADD COLUMN trimmed_by_hit_id TEXT;')
cur.execute('''CREATE TABLE named_verification_videos (
				id INTEGER,
				PRIMARY KEY(id)
			);''')
cur.execute('''CREATE TABLE trimmed_verification_videos (
				id INTEGER,
				PRIMARY KEY(id)
			);''')
conn.commit()