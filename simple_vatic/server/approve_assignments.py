import sqlite3
import argparse
import boto.mturk.connection

TRIM_DIFFERENCE_MAX = 1.0

def main(video_db, mturk_db, sandbox, aws_access_key_id, aws_secret_access_key):
    """
    Command line tool to decide whether assignments are rejected
    """
    # TODO verify correct verification labels here
    # TODO make Mturk login details command line arguments
    sandbox_host = 'mechanicalturk.sandbox.amazonaws.com'
    real_host = 'mechanicalturk.amazonaws.com'
    host = (sandbox_host if sandbox else real_host)
    mturk = boto.mturk.connection.MTurkConnection(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        host=host,
        debug=1  # debug = 2 prints out all requests.
    )
    mturk_db = sqlite3.connect(mturk_db)
    video_db = sqlite3.connect(video_db)

    mturk_cur = mturk_db.cursor()
    db_cursor = video_db.cursor()
    try:
        # TODO make pending approval a separate table if we think that would be time-efficient
        mturk_cur.execute("SELECT assignment_id, hit_id, task FROM hits WHERE status='pending_manual_approval'")
    except sqlite3.Error as e:
        print (str(e))
        return
    query_result = mturk_cur.fetchall()
    # We need to loop through every assignment/hit set pending approval
    print "Hello!"
    for result in query_result:
        assignment_id = str(result[0])
        hit_id = str(result[1])
        task = str(result[2])
        try:
            if task == "name":
                print "naming task!"
                mturk_cur.execute("SELECT id, action_noun, action_verb FROM name_verification_attempts WHERE hit_id=?", (hit_id,))
                action_query_result = mturk_cur.fetchall()
                for attempt_action_set in action_query_result:
                    db_cursor.execute("SELECT action_noun, action_verb FROM video_db WHERE id=?",
                                      (attempt_action_set[0],))
                    verified_action_set = db_cursor.fetchone()
                    if attempt_action_set[2] != verified_action_set[1]:
                        print ("Video " + str(attempt_action_set[0]) + " label has verb "
                                       + str(attempt_action_set[2])
                                       + " but the verified had verb "
                                       + str(verified_action_set[1]))
                        break
                    if attempt_action_set[1] != verified_action_set[0]:
                        print ("Video " + str(attempt_action_set[0]) + " label has noun "
                                       + str(attempt_action_set[1])
                                       + " but the verified had noun "
                                       + str(verified_action_set[0]))
            else: # ie. elif task == "trim":
                print str(task) + "ming task!"
                mturk_cur.execute("SELECT id, start_time, end_time FROM trim_verification_attempts WHERE hit_id=?", (hit_id,))
                times_query_result = mturk_cur.fetchall()
                for attempt_times_set in times_query_result:
                    db_cursor.execute("SELECT start_time, end_time FROM video_db WHERE id=?",
                                      (attempt_times_set[0],))
                    verified_times_set = db_cursor.fetchone()
                    if abs(attempt_times_set[1] - verified_times_set[0]) > TRIM_DIFFERENCE_MAX:
                        print ("Video " + str(attempt_times_set[0]) + " label has start time "
                                       + str(attempt_times_set[1])
                                       + " but the verified had start time "
                                       + str(verified_times_set[0]))
                    if abs(attempt_times_set[2] - verified_times_set[1]) > TRIM_DIFFERENCE_MAX:
                        print ("Video " + str(attempt_times_set[0]) + " label has end start time "
                                       + str(attempt_times_set[2])
                                       + " but the verified had end time "
                                       + str(verified_times_set[1]))
                        all_verifications_correct = False
                        break

        except sqlite3.Error as e:
            print (str(e))
            continue
        approval = str(raw_input("Approve? [Y/n]"))
        approved = 'n' in approval or 'N' in approval
        if approved:
            try:
                response = mturk.approve_assignment(assignment_id)
            except boto.mturk.connection.MTurkRequestError as e:
                print ("MTurk verification rejected. Typically, this means the client's completion "
                               + "has not been completed on Amazon's end.")
                print (str(e))
                query_result = mturk_cur.fetchone()
                continue
            print (assignment_id + " approved. Amazon response: " + str(response))
            try:
                mturk_cur.execute('''UPDATE hits SET status='approved' WHERE hit_id=?''', (hit_id,))
                mturk_db.commit()
            except sqlite3.Error as e:
                print (str(e))
        else:
            try:
                response = mturk.reject_assignment(assignment_id)
            except boto.mturk.connection.MTurkRequestError as e:
                print ("MTurk verification rejected. Typically, this means the client's completion "
                               + "has not been completed on Amazon's end.")
                print (str(e))
                query_result = mturk_cur.fetchone()
                continue
            print (assignment_id + " rejected. Amazon response: " + str(response))
            try:
                mturk_cur.execute('''UPDATE hits SET status='rejected' WHERE hit_id=?''', (hit_id,))
                mturk_db.commit()
            except sqlite3.Error as e:
                print (str(e))


def parse_args():
    parser = argparse.ArgumentParser(description='Accept or reject hits')
    parser.add_argument('--video_db', dest='video_db',
                        help='SQLite3 database with videos',
                        default='video_db.db', type=str)
    parser.add_argument('--mturk_db', dest='mturk_db',
                        help='SQLite3 database with logs for mturk',
                        default='mturk_db.db', type=str)
    parser.add_argument('--sandbox', dest='sandbox',
                        help='If this is a sandbox HIT (otherwise is a real one)',
                        default=False, action='store_true')
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
    main(args.video_db, args.mturk_db, args.sandbox, args.aws_access_key_id, args.aws_secret_access_key)


if __name__ == '__main__':
    start_from_terminal()
