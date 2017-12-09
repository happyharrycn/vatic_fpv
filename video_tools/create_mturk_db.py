import sqlite3
import argparse


def main(output_db):
    """
    The main function for creating a mini database of videos
    """
    # connect to db and get the cursor
    conn = sqlite3.connect(output_db)
    db_cursor = conn.cursor()

    # create the table if not exist
    db_cursor.execute('''CREATE TABLE `hits` (
        `hit_id`	TEXT,
        `assignment_id`	TEXT,
        `worker_id`	TEXT,
        `task`	TEXT,
        `verifications_completed`	INTEGER,
        `labels_completed`	INTEGER,
        `verifications_total`	INTEGER,
        `labels_total`	INTEGER,
        `status`	TEXT,
        PRIMARY KEY(`hit_id`)
    );''')
    db_cursor.execute('''CREATE TABLE `name_verification_attempts` (
        `hit_id`	TEXT,
        `assignment_id`	TEXT,
        `worker_id`	TEXT,
        `id`	INTEGER,
        `action_noun`	TEXT,
        `action_verb`	TEXT
    );''')
    db_cursor.execute('''CREATE TABLE `trim_verification_attempts` (
        `hit_id`	TEXT,
        `assignment_id`	TEXT,
        `worker_id`	TEXT,
        `id`	INTEGER,
        `start_time`	REAL,
        `end_time`	REAL
    );''')
    conn.commit()


if __name__ == '__main__':
    description = 'Helper script creates an empty database for storing mturk info.'
    p = argparse.ArgumentParser(description=description)
    p.add_argument('output_db', type=str, default='mturk_db.db',
                   help='Output file where the db will be saved.')
    main(**vars(p.parse_args()))
