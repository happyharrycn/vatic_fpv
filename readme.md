## vatic_fpv
Video Annotation Tools for Action Labeling

This file is primarily a to-do list for the development. We wil fill in the proper readme later.

We now have
* A simple and clean interface for trimming video events;
* A working demo that query a task from server and return user annotations. 

## Dependencies

* Python: flask werkzeug tornado (pip install them)
* Cross-Origin Resource Sharing enabled (depends on your browser and web server)

## Organization of the repo

* simple_vatic --> all the js/python/html/css files
* simple_vatic/www/ --> frontend web UI (js/html/css)
* simple_vatic/server/ --> backend python code

## How to Get it Running?

* You will need a web server for hosting the web UI (e.g. apache or nginx)
* Copy all files (and folders) in simple_vatic/www/ to your web hosting folder (default: /var/www/html/). Make sure they have the right permission.
* Go to simple_vatic/server folder. Run "python ./web_app.py". You can check the log in the terminal.
* In your browser, type "localhost/index.html". Now you should see the interface (you can use debug mode to check console logs). 

## To-Do-List

* Web interface for action labeling (naming)
* Fill in the code for task management in web_app.py

## Flow chart of our pipeline

![Alt text](http://webshare.ipat.gatech.edu/coc-rim-wall-lab/web/yli440/web_diagram.svg)

* All Communications between the fronend and backend are done through a RESTful API using JSON files
* [TO-DO] We will need a light-weighted DB in the backend to keep track of all videos (something like redis?) 