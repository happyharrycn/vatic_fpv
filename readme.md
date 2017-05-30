## vatic_fpv
Video Annotation Tools for Action Localization

This file is primarily a to-do list for the development. We wil fill in the proper readme later.

* We now have a simple and clean interface for video events!
* We now have a working demo for the interface!

#To-Do-List

* Web interface for action labeling (naming)
* Fill in the code for task management

#Flow chart of our pipeline

![Alt text](http://webshare.ipat.gatech.edu/coc-rim-wall-lab/web/yli440/web_diagram.svg)

* All Communications between the fronend and backend will be done through a RESTful API using JSON files
* We will need a light-weighted DB in the backend to keep track of all videos (something like redis?) 