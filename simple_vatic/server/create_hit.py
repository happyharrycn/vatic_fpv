import sqlite3
import argparse
import boto.mturk.connection


def create_hit(hits, verifications, labels, reward_amount_usd, task, mturk_db,
               sandbox, title, description, url, aws_access_key_id, aws_secret_access_key):
    for i in xrange(hits):
        sandbox_host = 'mechanicalturk.sandbox.amazonaws.com'
        real_host = 'mechanicalturk.amazonaws.com'

        mturk = boto.mturk.connection.MTurkConnection(
            aws_access_key_id = aws_access_key_id,
            aws_secret_access_key = aws_secret_access_key,
            host = (sandbox_host if sandbox else real_host),
            debug = 1 # debug = 2 prints out all requests.
        )

        print boto.Version # 2.29.1
        print "Account balance:" + str(mturk.get_account_balance()) # [$10,000.00]
        keywords = ["annotation", "machine learning"]
        frame_height = 630 # the height of the iframe holding the external hit

        questionform = boto.mturk.question.ExternalQuestion( url, frame_height )

        # syntax: http://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_CreateHITOperation.html

        create_hit_result = mturk.create_hit(
            title = title,
            description = description,
            keywords = keywords,
            question = questionform,
            reward = boto.mturk.price.Price( amount = reward_amount_usd),
            response_groups = ( 'Minimal', 'HITDetail' ), # I don't know what response groups are
        )

        hit_id = create_hit_result[0].HITId

        conn = sqlite3.connect(mturk_db)
        db_cursor = conn.cursor()
        try:
            db_cursor.execute('''INSERT INTO hits(
                hit_id, task, verifications_completed, labels_completed,
                verifications_total, labels_total, status)
                VALUES (?,?,?,?,?,?,?)''', (hit_id, task, 0, 0, verifications, labels, 'pending_completion'))
            conn.commit()
            print "Created new HIT:" + str(hit_id)
        except sqlite3.Error as e:
            print str(e)


def parse_args():
    parser = argparse.ArgumentParser(description='Create a hit')
    parser.add_argument('--hits', dest='hits',
                        help='Number of HITS',
                        default=1, type=int)
    parser.add_argument('--verifications', dest='verifications',
                        help='Number of verification videos to complete',
                        default=1, type=int)
    parser.add_argument('--labels', dest='labels',
                        help='Number of unlablelled videos to label',
                        default=1, type=int)
    parser.add_argument('--reward_amount_usd', dest='reward_amount_usd',
                        help='Amount of money to pay worker per HIT',
                        default=.05, type=float)
    parser.add_argument('--task', dest='task',
                        help='task (name or trim)',
                        default='name', type=str)
    parser.add_argument('--mturk_db', dest='mturk_db',
                        help='SQLite3 database with logs for mturk',
                        default='mturk_db.db', type=str)
    parser.add_argument('--sandbox', dest='sandbox',
                        help='If this is a sandbox HIT (otherwise is a real one)',
                        default=False, action='store_true')
    parser.add_argument('--title', dest='title',
                        help='Title for the hit',
                        default="Label 2 videos", type=str)
    parser.add_argument('--description', dest='description',
                        help='Description for the hit',
                        default="Categorize first-person oriented videos for the purposes of machine learning"
                        , type=str)
    parser.add_argument('--url', dest='url',
                        help='URL for iFrame in the hit',
                        default="", type=str)
    parser.add_argument('--aws_key_id', dest='aws_access_key_id',
                        help='AWS Access Key ID',
                        default='', type=str)
    parser.add_argument('--aws_key', dest='aws_secret_access_key',
                        help='AWS Secret Access Key',
                        default='', type=str)
    args = parser.parse_args()
    return args


def start_from_terminal():
    args = parse_args()
    create_hit(args.hits, args.verifications, args.labels, args.reward_amount_usd, args.task, args.mturk_db,
               args.sandbox, args.title, args.description, args.url, args.aws_access_key_id, args.aws_secret_access_key)


if __name__ == '__main__':
    start_from_terminal()