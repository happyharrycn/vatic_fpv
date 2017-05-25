#signature   = "" # AWS secret access key
#accesskey   = "" # AWS access key ID
sandbox     = False # if true, put on workersandbox.mturk.com
localhost   = "http://vision.csres.utexas.edu/" # your local host
database    = "mysql://root:Utaust!1@localhost/vatic" # server://user:pass@localhost/dbname
geolocation = "" # api key for ipinfodb.com

# probably no need to mess below this line

import multiprocessing
processes = multiprocessing.cpu_count()

import os.path
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
