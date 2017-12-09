"""A simple web server for video annotation"""

# parsing args
import argparse

# encoding / decoding
import json

# time / logging
import time
#import logging
#import traceback

# flask
import flask
from flask_cors import CORS, cross_origin
import tornado.wsgi
import tornado.httpserver

# database
import sqlite3

# redirect stdout and stderr for logging
import sys
# sys.stdout = open('./web_app.log', 'a', 1)
# sys.stderr = open('./web_app.err', 'a', 1)
import random
import boto.mturk.connection

# Obtain the flask app object (and make it cors)
app = flask.Flask(__name__) # pylint: disable=invalid-name
CORS(app)

# Maximum time allowed for one task
MAX_DELAY = 120
# maximum difference between correct start_time/end_time and verification attempt's start_time/end_time in seconds
TRIM_DIFFERENCE_MAX = 1.0


def dict_factory(cursor, row):
    """Helper function to convert sql item into a dict"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def print_log_info(str_info):
    """Helper function for logging info"""
    prefix = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    print "{:s}  {:s}".format(prefix, str_info)


def collect_db_stats():
    """
    Collect DB stats
    """
    ant_tasks = app.annotation_tasks
    db_cursor = ant_tasks.cursor()

    # show us some stats
    try:
        db_cursor.execute('''SELECT count(*) FROM video_db WHERE named=1''')
        num_clips_named = db_cursor.fetchone()['count(*)']

        db_cursor.execute('''SELECT count(*) FROM video_db WHERE trimmed=1''')
        num_clips_trimmed = db_cursor.fetchone()['count(*)']

        db_cursor.execute('''SELECT count(*) FROM video_db 
                             WHERE trim_locked=1 OR name_locked=1''')
        num_clips_locked = db_cursor.fetchone()['count(*)']

        db_cursor.execute('''SELECT count(*) FROM video_db 
                             WHERE red_flag>=1''')
        num_clips_flaged = db_cursor.fetchone()['count(*)']

        print_log_info("All Stats: Named {:d}, Trimmed {:d}, flagged {:d}, Locked {:d}".format(
            num_clips_named, num_clips_trimmed, num_clips_flaged, num_clips_locked))

    except sqlite3.Error as e:
        print_log_info(str(e))    

    return


def approve_assignments():
    """
    Periodic callback decides whether assignments pending approval
    can be automatically approved and then marks them accordingly
    """
    # TODO verify correct verification labels here
    # TODO make Mturk login details command line arguments
    sandbox_host = 'mechanicalturk.sandbox.amazonaws.com'
    real_host = 'mechanicalturk.amazonaws.com'
    host = (sandbox_host if app.sandbox else real_host)
    mturk = boto.mturk.connection.MTurkConnection(
        aws_access_key_id=app.aws_access_key_id,
        aws_secret_access_key=app.aws_secret_access_key,
        host=host,
        debug=1  # debug = 2 prints out all requests.
    )
    mturk_cur = app.mturk_db_connection.cursor()
    db_cursor = app.annotation_tasks.cursor()
    try:
        # TODO make pending approval a separate table if we think that would be time-efficient
        mturk_cur.execute("SELECT assignment_id, hit_id, task FROM hits WHERE status='pending_approval'")
    except sqlite3.Error as e:
        print_log_info(str(e))
        return
    query_result = mturk_cur.fetchall()
    # We need to loop through every assignment/hit set pending approval
    for result in query_result:
        assignment_id = str(result["assignment_id"])
        hit_id = str(result["hit_id"])
        task = str(result["task"])
        all_verifications_correct = True
        try:
            if task == "name":
                mturk_cur.execute("SELECT id, action_noun, action_verb FROM name_verification_attempts WHERE hit_id=?", (hit_id,))
                action_query_result = mturk_cur.fetchall()
                for attempt_action_set in action_query_result:
                    db_cursor.execute("SELECT action_noun, action_verb FROM video_db WHERE id=?",
                                      (attempt_action_set['id'],))
                    verified_action_set = db_cursor.fetchone()
                    if attempt_action_set['action_verb'] != verified_action_set['action_verb']:
                        print_log_info("Verification Attempt failed! Attempt had verb "
                                       + str(attempt_action_set['action_verb'])
                                       + " but the verified had verb "
                                       + str(verified_action_set['action_verb']))
                        all_verifications_correct = False
                        break
                    if attempt_action_set['action_noun'] != verified_action_set['action_noun']:
                        print_log_info("Verification Attempt failed! Attempt had noun "
                                       + str(attempt_action_set['action_noun'])
                                       + " but the verified had noun "
                                       + str(verified_action_set['action_noun']))
                        all_verifications_correct = False
                        break
            else: # ie. elif task == "trim":
                mturk_cur.execute("SELECT id, start_time, end_time FROM trim_verification_attempts WHERE hit_id=?", (hit_id,))
                times_query_result = mturk_cur.fetchall()
                for attempt_times_set in times_query_result:
                    db_cursor.execute("SELECT start_time, end_time FROM video_db WHERE id=?",
                                      (attempt_times_set['id'],))
                    verified_times_set = db_cursor.fetchone()
                    if abs(attempt_times_set['start_time'] - verified_times_set['start_time']) > TRIM_DIFFERENCE_MAX:
                        print_log_info("Verification Attempt failed! Attempt had start time "
                                       + str(attempt_times_set['start_time'])
                                       + " but the verified had start time "
                                       + str(verified_times_set['start_time']))
                        all_verifications_correct = False
                        break
                    if abs(attempt_times_set['end_time'] - verified_times_set['end_time']) > TRIM_DIFFERENCE_MAX:
                        print_log_info("Verification Attempt failed! Attempt had end time "
                                       + str(attempt_times_set['end_time'])
                                       + " but the verified had end time "
                                       + str(verified_times_set['end_time']))
                        all_verifications_correct = False
                        break

        except sqlite3.Error as e:
            print_log_info(str(e))
            continue
        if all_verifications_correct:
            # TODO Find out if this needs to be a transaction
            print_log_info("Approving assignment " + assignment_id)
            try:
                response = mturk.approve_assignment(assignment_id)
            except boto.mturk.connection.MTurkRequestError as e:
                print_log_info("MTurk verification rejected. Typically, this means the client's completion "
                               + "has not been completed on Amazon's end.")
                print_log_info(str(e))
                query_result = mturk_cur.fetchone()
                continue
            print_log_info(assignment_id + " approved. Amazon response: " + str(response))
            try:
                mturk_cur.execute('''UPDATE hits SET status='approved' WHERE hit_id=?''', (hit_id,))
                app.mturk_db_connection.commit()
            except sqlite3.Error as e:
                print_log_info(str(e))
        else:
            try:
                mturk_cur.execute('''UPDATE hits SET status='pending_manual_approval' WHERE hit_id=?''', (hit_id,))
                app.mturk_db_connection.commit()
            except sqlite3.Error as e:
                print_log_info(str(e))
    return


def expire_locked_items():
    """
    Expires a locked item based on its time stamp
    """
    ant_tasks = app.annotation_tasks
    db_cursor = ant_tasks.cursor()

    # Task: name
    db_cursor.execute('''SELECT * FROM video_db WHERE name_locked=1 AND named=0''')
    locked_items = db_cursor.fetchall()

    for item in locked_items:
        delay = time.time() - item['name_lock_time']
        if delay > MAX_DELAY:
            print_log_info("Expiring task {:d} (Name)".format(item['id']))
            try:
                db_cursor.execute('''UPDATE video_db SET name_locked=0, name_lock_time=? 
                                     WHERE id=?''', (0.0, item['id']))
                ant_tasks.commit()
            except sqlite3.Error as e:
                print_log_info(str(e))

    # Task: trim
    db_cursor.execute('''SELECT * FROM video_db WHERE trim_locked=1 AND trimmed=0''')
    locked_items = db_cursor.fetchall()

    for item in locked_items:
        delay = time.time() - item['trim_lock_time']
        if delay > MAX_DELAY: 
            print_log_info("Expiring task {:d} (Trim)".format(item['id']))
            try:
                db_cursor.execute('''UPDATE video_db SET trim_locked=0, trim_lock_time=? 
                                     WHERE id=?''', (0.0, item['id']))
                ant_tasks.commit()
            except sqlite3.Error as e:
                print_log_info(str(e))

    return


def load_annotation_tasks(video_db):
    """
    Wrapper for loading annotations
    """

    # id integer primary key, 
    # url text, 
    # named integer, 
    # name_locked integer, 
    # name_lock_time real,
    # named_by_user text, 
    # occluded integer, 
    # trimmed integer, 
    # trim_locked integer,
    # trim_lock_time real,
    # trimmed_by_user text,
    # video_src text
    # src_start_time integer,
    # src_end_time integer,
    # pad_start_frame integer,
    # pad_end_frame integer,
    # start_time real,
    # end_time real,
    # action_verb text,
    # action_noun text,
    # red_flag integer

    # Instantiate a connection to db
    annotation_tasks = sqlite3.connect(video_db)
    annotation_tasks.row_factory = dict_factory
    # returns the database
    return annotation_tasks


def decide_if_needs_verification(json_res, mturk_db_connection):
    """
    Makes the decision as to whether this request is going to be a verification video or not.
    Let
        a = the verification videos left
        b = total number of videos left
    The chance of getting a verification videos is a/b
    This gives a uniform distribution of chance of getting a verification video across all requests.

    Called by get_task().

    :param json_res: JSON given by frontend's submit button; must have hitId key
    :type json_res: dict
    :param mturk_db_connection: connection to database containing mturk-related data
    :type mturk_db_connection: sqlite3.Connection
    :return boolean representing whether verification video will be returned
    """
    print json_res
    mturk_cur = mturk_db_connection.cursor()
    try:
        mturk_cur.execute('''SELECT verifications_total, labels_total,
                        verifications_completed, labels_completed FROM hits
                        WHERE hit_id=?''', (json_res['hitId'],))
    except sqlite3.Error as e:
        print_log_info(str(e))
    query_result = mturk_cur.fetchone()
    verifications_total, labels_total, verifications_completed, labels_completed = \
        query_result["verifications_total"], query_result["labels_total"], \
        query_result["verifications_completed"], query_result["labels_completed"]
    chance_of_verification_video = (float(max(verifications_total - verifications_completed, 0))
                                    / max(verifications_total + labels_total
                                          - verifications_completed - labels_completed, 1))
    return chance_of_verification_video > random.random()


def get_verification_task(annotation_tasks, annotation_type):
    """
    Wrapper for querying database for a verification task.

    :param annotation_tasks: connection to database containing mturk-related data
    :type annotation_tasks: sqlite3.Connection
    :param annotation_type: client-defined string for the type of the annotations we're doing
    :type annotation_type: string
    :return dict from querying database
    """
    db_cursor = annotation_tasks.cursor()
    if annotation_type == 'name' or annotation_type == 'name_preview':
        try:
            # from https://stackoverflow.com/questions/4114940/select-random-rows-in-sqlite
            db_cursor.execute('''SELECT * FROM video_db WHERE id IN 
                    (SELECT id FROM named_verification_videos
                    ORDER BY RANDOM() LIMIT 1)''')
        except sqlite3.Error as e:
            print_log_info(str(e))
    else:
        db_cursor.execute('''SELECT * FROM video_db WHERE id IN 
                    (SELECT id FROM trimmed_verification_videos
                    ORDER BY RANDOM() LIMIT 1)''')
    return db_cursor.fetchone()


def task_completed(json_res, mturk_db_connection):
    """
    Tells whether an mturk task has been completed

    :param json_res: JSON given by frontend's submit button; must have hitId key
    :type json_res: dict
    :param mturk_db_connection: connection to database containing mturk-related data
    :type mturk_db_connection: sqlite3.Connection
    :return: boolean representing if task referred to in json_res' hitId has been completed
    """
    mturk_cur = mturk_db_connection.cursor()
    try:
        mturk_cur.execute('''SELECT verifications_total, labels_total,
                        verifications_completed, labels_completed FROM hits
                        WHERE hit_id=?''', (json_res['hitId'],))
    except sqlite3.Error as e:
        print_log_info(str(e))
    query_result = mturk_cur.fetchone()
    verifications_total, labels_total, verifications_completed, labels_completed = \
        query_result["verifications_total"], query_result["labels_total"], \
        query_result["verifications_completed"], query_result["labels_completed"]
    return verifications_total - verifications_completed <= 0 and labels_total - labels_completed <= 0


def get_next_available_task(annotation_tasks, annotation_type):
    """
    Wrapper for querying database for a new labelling task.

    Called by get_task().

    :param annotation_tasks: connection to database containing mturk-related data
    :type annotation_tasks: sqlite3.Connection
    :param annotation_type: client-defined string for the type of the annotations we're doing
    :type annotation_type: string
    :return dict from querying database
    """
    # get db cursor
    db_cursor = annotation_tasks.cursor()

    # Get the next task
    if annotation_type == 'name':
        try:
            db_cursor.execute('''SELECT * FROM video_db WHERE named=0
                                    AND name_locked=0
                                    AND id not in 
                                        (SELECT id from named_verification_videos)
                            ''')  # LIMIT 1 maybe?
        except sqlite3.Error as e:
            print_log_info(str(e))
    else:  # So annotation_type == 'trim'
        try:
            db_cursor.execute('''SELECT * FROM video_db WHERE named=1 
                                    AND red_flag=0
                                    AND trimmed=0
                                    AND trim_locked=0
                                    AND id not in 
                                        (SELECT id from trimmed_verification_videos)
                            ''')  # LIMIT 1 maybe?
        except sqlite3.Error as e:
            print_log_info(str(e))

    item = db_cursor.fetchone()

    # No task available
    if item is None:
        return None
    # Otherwise return a task.
    else:
        task = item
        cur_time = time.time()
        # update the lock
        if annotation_type == 'name':
            try:
                db_cursor.execute('''UPDATE video_db SET name_locked=1, name_lock_time=? 
                                     WHERE id=?''', (cur_time, task['id']))
            except sqlite3.Error as e:
                print_log_info(str(e))
        else:  # So annotation_type == 'trim'
            try:
                db_cursor.execute('''UPDATE video_db SET trim_locked=1, trim_lock_time=? 
                                     WHERE id=?''', (cur_time, task['id']))
            except sqlite3.Error as e:
                print_log_info(str(e))

    annotation_tasks.commit()
    return task


def update_task(mturk_db_connection, annotation_tasks, json_res, is_mturk):
    """
    Updates the data for a labelling task plus relevant mturk variables if it's an mturk task.

    :param mturk_db_connection: connection to database containing mturk-related data
    :type mturk_db_connection: sqlite3.Connection
    :param annotation_tasks: connection to database containing mturk-related data
    :type annotation_tasks: sqlite3.Connection
    :param json_res: JSON given by frontend's submit button; must have hitId key
    :type json_res: dict
    :param is_mturk: indicates if
    :return dict from querying database
    """

    # get db cursor
    db_cursor = annotation_tasks.cursor()
    mturk_cur = mturk_db_connection.cursor()

    # get annotation_type and video id
    ant_type = json_res['annotation_type']

    # Update naming task
    if ant_type == 'name':
        try:
            # Decide if video we are updating is a verification video
            db_cursor.execute('''SELECT * FROM named_verification_videos where id=?''',
                              (json_res['id'],))  # todo find out if is good query
            is_verification = not (db_cursor.fetchone() is None)

            # Apply new label if it isn't a verification video
            if not is_verification:
                update_item = (int(json_res['occluded']),
                               json_res['nouns'], json_res['verb'],
                               json_res['user_name'], int(json_res['red_flag'])*1,
                               int(json_res['id']))
                db_cursor.execute('''UPDATE video_db 
                                SET named=1, name_locked=0, occluded=?, 
                                action_noun=?, action_verb=?, named_by_user=?, red_flag=? 
                                WHERE id=?''', update_item)

            # Update MTurk database to reflect this change
            if is_mturk and is_verification:
                mturk_cur.execute('''UPDATE hits SET assignment_id=?, worker_id=?,
                                verifications_completed = verifications_completed + 1
                                WHERE hit_id=?''', (json_res['assignmentId'],
                                    json_res['workerId'], json_res['hitId']))
                mturk_cur.execute('''INSERT INTO name_verification_attempts(
                                hit_id, assignment_id, worker_id,
                                id, action_noun, action_verb)
                                VALUES (?,?,?,?,?,?)''', (json_res['hitId'],
                                    json_res['assignmentId'], json_res['workerId'],
                                    json_res['id'], json_res['nouns'], json_res['verb']))

                mturk_db_connection.commit()
            elif is_mturk and not is_verification:
                print(json_res['assignmentId'],
                                    json_res['workerId'], json_res['hitId'])
                mturk_cur.execute('''UPDATE hits SET assignment_id=?, worker_id=?,
                                labels_completed = labels_completed + 1
                                WHERE hit_id=?''', (json_res['assignmentId'],
                                    json_res['workerId'], json_res['hitId']))
                mturk_db_connection.commit()
            annotation_tasks.commit()
        except sqlite3.Error as e:
            print_log_info(str(e))
            return False
    else:  # ie. it's a trimming task
        try:
            # Decide if video we are updating is a verification video
            db_cursor.execute('''SELECT * FROM trimmed_verification_videos where id=?''',
                              (json_res['id'],))  # todo find out if is good query
            is_verification = not (db_cursor.fetchone() is None)

            # Apply new label if it isn't a verification video
            if not is_verification:
                update_item = (float(json_res['start_time']),
                               float(json_res['end_time']),
                               json_res['user_name'], int(json_res['red_flag'])*2,
                               int(json_res['id']))
                db_cursor.execute('''UPDATE video_db 
                                 SET trimmed=1, trim_locked=0, 
                                 start_time=?, end_time=?, trimmed_by_user=?, red_flag=?
                                 WHERE id=?''', update_item)

            # Update MTurk database to reflect this change
            if is_mturk and is_verification:
                mturk_cur.execute('''UPDATE hits SET assignment_id=?, worker_id=?,
                                verifications_completed = verifications_completed + 1
                                WHERE hit_id=?''', (json_res['assignmentId'],
                                    json_res['workerId'], json_res['hitId']))
                mturk_cur.execute('''INSERT INTO trim_verification_attempts(
                                hit_id, assignment_id, worker_id,
                                id, start_time, end_time)
                                VALUES (?,?,?,?,?,?)''', (json_res['hitId'],
                                        json_res['assignmentId'], json_res['workerId'],
                                        json_res['id'], float(json_res['start_time']),
                                        float(json_res['end_time'])))

                mturk_db_connection.commit()
            elif is_mturk and not is_verification:
                print(json_res['assignmentId'],
                                    json_res['workerId'], json_res['hitId'])
                mturk_cur.execute('''UPDATE hits SET assignment_id=?, worker_id=?,
                                labels_completed = labels_completed + 1
                                WHERE hit_id=?''', (json_res['assignmentId'],
                                    json_res['workerId'], json_res['hitId']))
                mturk_db_connection.commit()
            # TODO update mturk stuff
            annotation_tasks.commit()
        except sqlite3.Error as e:
            print_log_info(str(e))
            return False

    # color print the red flag
    if json_res['red_flag']:
        print_log_info('\033[93m' + "Task ID ({:d}) Type ({:s}) has been RED_FLAGGED!".format(
            json_res['id'], ant_type) + '\033[0m')

    # return
    return True


@app.errorhandler(404)
def not_found(error):
    """
    Default error handler for 404
    """
    return flask.make_response(json.dumps({'error': str(error)}), 404)


@app.route('/get_task', methods=['POST'])
def get_task():
    """
    Get a task from the server
    A request is a json file with the following fields:
    - "annotation_type" which can have the values...
        - name
        - name_preview
        - trim
        - trim_preview
    - "user_name"
    If it is a request from an MTurk iFrame, it also has the following:
    - "workerId"
    - "hitId"
    """
    # Dict holds the results to return to client
    ret = {}

    # Make sure the content type is json
    try:
        request_type = flask.request.headers.get('Content-Type')
        if request_type != 'application/json':
            raise ValueError('request type must be JSON')

        request_data = flask.request.get_data()

    except ValueError as err:
        ret['code'] = -1
        ret['error_msg'] = str(err)
        return json.dumps(ret)
    except:
        ret['code'] = -2
        ret['error_msg'] = 'unknown parameter error'
        return json.dumps(ret)

    # Decode json from request data into a dict, and make sure all required data is present
    try:
        json_file = json.JSONDecoder().decode(request_data)
        print_log_info("Task request: {:s}".format(json_file))
        is_mturk = "assignmentId" in json_file and "workerId" in json_file and \
                "hitId" in json_file
        if 'annotation_type' not in json_file:
            raise ValueError('annotation_type missing in request')
        else:
            # more sanity check
            ant_type = json_file['annotation_type']
            if not ((ant_type == 'name') or (ant_type == 'trim')
                    or (ant_type == 'name_preview') or (ant_type == 'trim_preview')):
                raise ValueError('unknown annotation_type')
    except ValueError as err:
        ret['code'] = -3
        ret['error_msg'] = str(err)
        return json.dumps(ret)
    # Decide if we need a verification task
    if ant_type == 'name_preview' or ant_type == 'trim_preview':
        needs_verification_task = True
    elif ((ant_type == 'name'
            or ant_type == 'trim')
            and is_mturk):
        needs_verification_task = \
            decide_if_needs_verification(json_file, app.mturk_db_connection)
    else:
        needs_verification_task = False
    # Get a verification task or next available task, and return to user
    try:
        if needs_verification_task:
            task = get_verification_task(app.annotation_tasks, ant_type)
        else:
            task = get_next_available_task(app.annotation_tasks, ant_type)

        if not task:
            raise ValueError('can not get a valid task. please re-try.')
        else:
            ret = task
    except ValueError as err:
        ret['code'] = -1
        ret['error_msg'] = str(err)
        return json.dumps(ret)
    return json.dumps(ret)


@app.route('/return_task', methods=['POST'])
def return_task():
    """
    Processes the JSON sent from the client to submit a label

    JSON has the following fields:
    - id, which is the video ID
    - annotation_type, which can be "name" or "trim"
    - user_name
    If the request is coming from an mturk iFrame, it should have:
    - assignmentId
    - workerId
    - hitId
    If annotation_type is "name", it should have the following:
    - verb, a string representing the word selected from the dropdown menu
    - occluded, a boolean from the checkbox in the page
    - nouns, a string filled out by the user for the objects being handled
    TODO figure out the trim stuff
    """

    # Dict holds the results to return to client
    ret = {}

    try:
        # make sure the content type is json
        request_type = flask.request.headers.get('Content-Type')
        if request_type != 'application/json':
            raise ValueError('request type must be JSON')

        request_data = flask.request.get_data()

    except ValueError as err:
        ret['code'] = -1
        ret['error_msg'] = str(err)
        return json.dumps(ret)
    except:
        ret['code'] = -2
        ret['error_msg'] = 'unknown parameter error'
        return json.dumps(ret)

    # decode json from request data into a dict
    try:
        json_file = json.JSONDecoder().decode(request_data)
        print_log_info("Task returned: {:s}".format(json_file))
        if 'annotation_type' not in json_file:
            raise ValueError('annotation_type missing in request')
        if 'id' not in json_file:
            raise ValueError('id missing in request')
        else:
            # more sanity check
            ant_type = json_file['annotation_type']
            if not ((ant_type == 'name') or (ant_type == 'trim')):
                raise ValueError('unknown annotation_type')
    except ValueError as err:
        ret['code'] = -3
        ret['error_msg'] = str(err)
        return json.dumps(ret)

    is_mturk = "assignmentId" in json_file and "workerId" in json_file and \
               "hitId" in json_file

    # Get next available task
    try:
        flag = update_task(app.mturk_db_connection, app.annotation_tasks, json_file, is_mturk)

        if not flag:
            raise ValueError('can not update the task. Please re-try.')
        else:
            ret['code'] = 0
            ret['error_msg'] = 'success'

    except ValueError as err:
        ret['code'] = -3
        ret['error_msg'] = str(err)
        return json.dumps(ret)

    more_to_complete = not is_mturk or \
        not task_completed(json_file, app.mturk_db_connection)

    if not more_to_complete:
        try:
            mturk_db_connection = app.mturk_db_connection
            mturk_cur = mturk_db_connection.cursor()
            mturk_cur.execute('''UPDATE hits SET status='pending_approval' WHERE assignment_id=?''',
                              (json_file["assignmentId"],))
            mturk_db_connection.commit()
        except sqlite3.Error as err:
            ret['code'] = -3
            ret['error_msg'] = str(err)
            return json.dumps(ret)
    ret['more_to_complete'] = more_to_complete
    return json.dumps(ret)

@app.route('/hello')
def hello():
    return 'hello world'


def parse_args():
    """
    Parse input arguments
    """
    parser = argparse.ArgumentParser(description='Setup a web server for video annotation')
    parser.add_argument('--port', dest='port',
                        help='which port to serve content on',
                        default=5050, type=int)
    parser.add_argument('--video_db', dest='video_db',
                        help='SQLite3 database with normal videos',
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
    parser.add_argument('--certfile', dest='certfile',
                        help='SSL certfile location',
                        default='', type=str)
    parser.add_argument('--keyfile', dest='keyfile',
                        help='SSL keyfile location',
                        default='', type=str)
    args = parser.parse_args()
    return args


def start_from_terminal():
    """
    entry of the main function
    """
    # parse params
    args = parse_args()
    # load annotation tasks
    app.annotation_tasks = load_annotation_tasks(args.video_db)
    app.mturk_db_connection = load_annotation_tasks(args.mturk_db)
    # Set global variables
    app.aws_access_key_id = args.aws_access_key_id
    app.aws_secret_access_key = args.aws_secret_access_key
    app.sandbox = args.sandbox
    # start server without cert if none provided
    if args.certfile == '' and args.keyfile == '':
        server = tornado.httpserver.HTTPServer(tornado.wsgi.WSGIContainer(app))
    else:
        server = tornado.httpserver.HTTPServer(tornado.wsgi.WSGIContainer(app), ssl_options={
            "certfile": args.certfile,
            "keyfile": args.keyfile,
        })
    server.bind(args.port)

    # setup exist function
    def save_db():
        app.annotation_tasks.close()
        app.mturk_db_connection.close()
    import atexit
    atexit.register(save_db)

    # set up one server
    server.start(1)
    print_log_info("Tornado server starting on port {}".format(args.port))
    # show stats every time we launch the service
    collect_db_stats()
    approve_assignments()
    tornado.ioloop.PeriodicCallback(expire_locked_items, 20*1000).start()
    tornado.ioloop.PeriodicCallback(collect_db_stats, 3600*1000).start()
    tornado.ioloop.PeriodicCallback(approve_assignments, 20*1000).start()
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    start_from_terminal()