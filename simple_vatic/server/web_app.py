"""A simple web server for video annotation"""

# parsing args
import argparse

# encoding / decoding
import json

# time / logging
#import time
#import logging
#import traceback

# flask
import flask
import tornado.wsgi
import tornado.httpserver

# database
from tinydb import TinyDB, Query

# Obtain the flask app object
app = flask.Flask(__name__) # pylint: disable=invalid-name

def load_annotation_tasks(video_db):
    """
    Wrapper for loading annotations
    """

    # Example item in the db
    # {
    #         'id'         : 1,
    #         'url'            : 'http://vjs.zencdn.net/v/oceans.mp4',
    #         # tags for annotation
    #         'named'          : False,
    #         'occluded'       : False,
    #         'trimmed'        : False,
    #         # link to untrimmed full video
    #         'video_src'      : 'oceans',
    #         'src_start_time' : 0,
    #         'src_end_time'   : 0,
    #         # annotations : action boundary
    #         'start_time'     : -1.0,
    #         'end_time'       : -1.0,
    #         # annotations : action names
    #         'action_verb'    : '',
    #         'action_noun'    : []
    # }

    # Instantiate a json database
    annotation_tasks = TinyDB(video_db)
    # returns the database
    return annotation_tasks

def get_next_available_task(annotation_tasks, annotation_type):
    """
    Wrapper for getting a new task
    """
    if annotation_type == 'name':
        item = annotation_tasks.get(Query()['named'] == False)
    else:
        item = annotation_tasks.get((Query()['named'] == True)
                                    & (Query()['trimmed'] == False))

    # No task available
    if item == None:
        return None
    else:
        task = dict(item)
        task['id'] = item.eid

    return task

def update_task(annotation_tasks, json_res):
    """
    Wrapper for updating a existing task. Quick and Dirty
    """
    # get annotation_type and video id
    ant_type = json_res['annotation_type']
    eid = json_res['id']

    # find the task to update
    if ant_type == 'name':
        # explicite update of the fields
        idx = annotation_tasks.update({'occluded' : json_res['occluded']},
                                eids=[eid])
        idx = annotation_tasks.update({'action_noun' : json_res['nouns'].split(',')},
                                eids=[eid])
        idx = annotation_tasks.update({'action_verb' : json_res['verb']},
                                      eids=[eid])
        if idx[0] == eid:
            annotation_tasks.update({'named' : True}, 
                                    eids=[eid])
    else:
        annotation_tasks.update({'trimmed' : True}, 
                                eids=[eid])
        annotation_tasks.update({'start_time' : json_res['start_time']},
                                eids=[eid])
        idx = annotation_tasks.update({'end_time' : json_res['end_time']},
                                      eids=[eid])
        if idx[0] == eid:
            annotation_tasks.update({'trimmed' : True}, 
                                    eids=[eid])

    # return true if task is updated, false if not
    return idx[0] == eid

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
        print json_file
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
        ret['error_msg'] = 'unkown error'

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
        print json_file
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
    # set up one server
    server.start(1)
    print "Tornado server starting on port {}".format(args.port)
    tornado.ioloop.IOLoop.current().start()

if __name__ == '__main__':
    start_from_terminal()