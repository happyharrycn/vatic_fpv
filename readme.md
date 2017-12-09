## vatic_fpv
Video Annotation Tools for Action Labeling

This file is primarily a to-do list for the development. We wil fill in the proper readme later.

We now have
* A simple and clean interface for labeling & trimming video events;
* A working demo that query a task from server and return user annotations. 

## Dependencies

* Python (2): flask flask_cors werkzeug tornado boto (pip install them)
* Cross-Origin Resource Sharing is supported via flask_cors
* Internet Access.

## Organization of the repo

* simple_vatic --> all the js/python/html/css files
* simple_vatic/www/ --> frontend web UI (js/html/css)
* simple_vatic/server/ --> backend python code

## How to Get it Running

* Use ELAN to create annotations. Mark chuncks of the video in the timeline by clicking and dragging, Alt+N to create an annotation, and Enter to create the empty label.
* Use crop_videos.py to create a directory of cropped videos
* Use create_db.py to create video database
* Use create_mturk_db.py to create an empty database to store Amazon Mechanical Turk data
* You will need a web server for hosting the web UI (e.g. apache or nginx)
* Copy all files (and folders) in simple_vatic/www/ to your web hosting folder (default: /var/www/html/), or point the server to simple_vatic/www/
* Copy folder of cropped videos to same place
* In simple_vatic/server modify .sh files to add your AWS secret keys and file directories, adding the command line arguments you want
* Make .sh files executable with chmod +x filename
* Run create_hit sh files to create hits if you're using Mechanical Turk
* ./serve.sh to start the server
* In your browser, type "websitename/trim.html" or "websitename/name.html". Now you should see the interface (you can use debug mode to check console logs). 
* If you want to run it using NGINX/Apache as a reverse proxy, [as is reccomended in tutorials,](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uwsgi-and-nginx-on-ubuntu-16-04) you'll need to change the port number in name.html and trim.html from 5050 to 80.

## To-Do-List

* Improve front-end to be more usable.

## Flow chart of our pipeline

![Alt text](http://webshare.ipat.gatech.edu/coc-rim-wall-lab/web/yli440/web_diagram.svg)

* All Communications between the fronend and backend are done through a RESTful API using JSON files