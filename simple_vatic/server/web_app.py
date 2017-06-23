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
sys.stdout = open('./web_app.log', 'a', 1)
sys.stderr = open('./web_app.err', 'a', 1)


# Obtain the flask app object (and make it cors)
app = flask.Flask(__name__) # pylint: disable=invalid-name
CORS(app)

# max delay for one task
MAX_DELAY = 120

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

        print_log_info("Named {:d}, Trimmed {:d}, flagged {:d}, Locked {:d}".format(
            num_clips_named, num_clips_trimmed, num_clips_flaged, num_clips_locked))

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
    # red_falg integer

    # Instantiate a connection to db
    annotation_tasks = sqlite3.connect(video_db)
    annotation_tasks.row_factory = dict_factory
    # returns the database
    return annotation_tasks

def get_next_available_task(annotation_tasks, annotation_type):
    """
    Wrapper for getting a new task
    """
    # get db cursor
    db_cursor = annotation_tasks.cursor()

    if annotation_type == 'name':
        try:
            db_cursor.execute('''SELECT * FROM video_db WHERE named=0 AND name_locked=0''')
        except sqlite3.Error as e:
            print_log_info(str(e))
    else:
        try:
            db_cursor.execute('''SELECT * FROM video_db WHERE named=1 
                                                          AND trimmed=0
                                                          AND trim_locked=0''')
        except sqlite3.Error as e:
            print_log_info(str(e))

    item = db_cursor.fetchone()

    # No task available
    if item is None:
        return None
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
        else:
            try:
                db_cursor.execute('''UPDATE video_db SET trim_locked=1, trim_lock_time=? 
                                     WHERE id=?''', (cur_time, task['id']))
            except sqlite3.Error as e:
                print_log_info(str(e))

    annotation_tasks.commit()
    return task

def update_task(annotation_tasks, json_res):
    """
    Wrapper for updating a existing task. Quick and Dirty
    """
    # get db cursor
    db_cursor = annotation_tasks.cursor()

    # get annotation_type and video id
    ant_type = json_res['annotation_type']

    # find the task to update
    if ant_type == 'name':
        update_item = (int(json_res['occluded']), 
                       json_res['nouns'], json_res['verb'],
                       json_res['user_name'], int(json_res['red_flag'])*1, 
                       int(json_res['id']))
        try:           
            db_cursor.execute('''UPDATE video_db 
                                 SET named=1, name_locked=0, occluded=?, 
                                 action_noun=?, action_verb=?, named_by_user=?, red_flag=? 
                                 WHERE id=?''', update_item)
            annotation_tasks.commit()
        except sqlite3.Error as e:
            print_log_info(str(e))
            return False
    else:
        update_item = (float(json_res['start_time']), 
                       float(json_res['end_time']),
                       json_res['user_name'], int(json_res['red_flag'])*2, 
                       int(json_res['id']))
        try:
            db_cursor.execute('''UPDATE video_db 
                                 SET trimmed=1, trim_locked=0, 
                                 start_time=?, end_time=?, trimmed_by_user=?, red_flag=?
                                 WHERE id=?''', update_item)
            annotation_tasks.commit()
        except sqlite3.Error as e:
            print_log_info(str(e))
            return False

    # color print the red flag
    if json_res['red_flag']:
        print_log_info('\033[93m' + "Task ID ({:d}) Type ({:s}) has been RED_FLAGED!".format(
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
    A request is a json file with a single field "annotation_type"
    """
    # an empty dict that holds the results
    ret = {}

    # always use try / except for your code blocks
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

    try:
        # decode json from request data into a dict
        json_file = json.JSONDecoder().decode(request_data)
        print_log_info("Task request: {:s}".format(json_file))
        if 'annotation_type' not in json_file:
            raise ValueError('annotation_type missing in request')
        else:
            # more sanity check
            ant_type = json_file['annotation_type']
            if not ((ant_type == 'name') or (ant_type == 'trim')):
                raise ValueError('unknown annotation_type')

            # get next available task
            task = get_next_available_task(app.annotation_tasks, ant_type)

            if not task:
                raise ValueError('can not get a valid task. please re-try.')
            else:
                ret = task

    except ValueError as err:
        ret['code'] = -3
        ret['error_msg'] = str(err)
    except:
        ret['code'] = -4
        ret['error_msg'] = 'SQL query error'

    return json.dumps(ret)

@app.route('/return_task', methods=['POST'])
def return_task():
    """
    Return the annotations to the server
    """

    # an empty dict that holds the results
    ret = {}

    # always use try / except for your code blocks
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

    try:
        # decode json from request data into a dict
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

            # get next available task
            flag = update_task(app.annotation_tasks, json_file)

            if not flag:
                raise ValueError('can not update the task. Please re-try.')
            else:
                ret['code'] = 0
                ret['error_msg'] = 'success'

    except ValueError as err:
        ret['code'] = -3
        ret['error_msg'] = str(err)
    except:
        ret['code'] = -4
        ret['error_msg'] = 'unkown error'

    return json.dumps(ret)

def parse_args():
    """
    Parse input arguments
    """
    parser = argparse.ArgumentParser(description='Setup a web server for video annotation')
    parser.add_argument('--port', dest='port',
                        help='which port to serve content on',
                        default=5050, type=int)
    parser.add_argument('--video_db', dest='video_db',
                        help='json file for database',
                        default='video_db.json', type=str)
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
    # start web server using tornado
    server = tornado.httpserver.HTTPServer(tornado.wsgi.WSGIContainer(app))
    server.bind(args.port)

    # setup exist function
    def save_db():
        app.annotation_tasks.close()
    import atexit
    atexit.register(save_db)

    # set up one server
    server.start(1)
    print_log_info("Tornado server starting on port {}".format(args.port))
    tornado.ioloop.PeriodicCallback(expire_locked_items, 20000).start()
    tornado.ioloop.PeriodicCallback(collect_db_stats, 3600*1000).start()
    tornado.ioloop.IOLoop.current().start()

if __name__ == '__main__':
    start_from_terminal()
    