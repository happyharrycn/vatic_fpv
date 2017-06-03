# encoding / decoding
import json

# time / logging
import time

#import logging
#import traceback

# flask
import flask
import werkzeug
import tornado.wsgi
import tornado.httpserver

# database
from tinydb import TinyDB, Query

# misc
import argparse
import os

# Obtain the flask app object
app = flask.Flask(__name__)

# Instantiate a json database
db = TinyDB('db.json')

def load_annotation_tasks():
    """
    Wrapper for loading annotations
    """
    # dummy data for testing
    db.insert({
            'id'         : 1,
            'url'            : 'http://vjs.zencdn.net/v/oceans.mp4',
            # tags for annotation
            'named'          : False, 
            'occluded'       : False,
            'trimmed'        : False,
            # link to untrimmed full video
            'video_src'      : 'oceans',
            'src_start_time' : 0,
            'src_end_time'   : 0,
            # annotations : action boundary
            'start_time'     : -1.0,
            'end_time'       : -1.0,
            # annotations : action names
            'action_verb'    : '',
            'action_noun'    : []
    })
    
    # returns a list of all dicts in the database
    return db.all()

def get_next_available_task(annotation_tasks, annotation_type):
    """
    Wrapper for getting a new task
    """ 
    # dummy code for getting a toy task
    ant_task = annotation_tasks[0]
    task = {
        'id' : ant_task['id'],
        'url' : ant_task['url'],
        'annotation_type' : annotation_type
    }

    return task

def update_task(annotation_tasks, video_id, annotation_type, json_res):
    """
    Wrapper for updating a existing task 
    """     
    # find the task to update
    task = filter(lambda x: x['id'] == video_id, annotation_tasks)
    
    # update all keys in the task
    for key, val in json_res.items():
        task[key] = val
    task[annotation_type] = True
    
    # return true if task is updated, false if not
    return task != None

@app.errorhandler(404)
def not_found(error):
    """
    Default error handler for 404
    """
    return flask.make_response(json.dumps({'error': 'Not found'}), 404)

@app.route('/get_task', methods=['POST'])
def get_task():
    """
    Get a task from the server
    A request is a json file with one field "annotation_type"
    """
    # an empty dict that holds the results
    ret = {}

    # always use try / except for your code blocks
    try:
        # make sure the content type is json
        request_type = flask.request.headers.get('Content-Type')
        if not (request_type=='application/json'):
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
        if not (request_type=='application/json'):
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
            video_id = json_file['id']

            if not ((ant_type == 'name') or (ant_type == 'trim')):
                raise ValueError('unknown annotation_type')

            # get next available task    
            flag = update_task(app.annotation_tasks, video_id, ant_type, json_file)

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
    
    args = parser.parse_args()
    return args


def start_from_terminal(app):
    """
    entry of the main function
    """
    # parse params
    args = parse_args()

    # load annotation tasks
    app.annotation_tasks = load_annotation_tasks()
    
    # start web server using tornado       
    server = tornado.httpserver.HTTPServer(tornado.wsgi.WSGIContainer(app))
    server.bind(args.port)
    # set up one server
    server.start(1)
    print("Tornado server starting on port {}".format(args.port))
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    start_from_terminal(app)

