import time
import logging

# create logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# add formatter to ch
ch.setFormatter(formatter)
logger.addHandler(ch)

from dogapi import dog_stats_api as dog
import random
import time
import math
from datetime import datetime

send_every = 1

dog.start(api_key='', flush_interval=send_every, api_host='http://localhost:8888', roll_up_interval=send_every)

def loop_forever():
	beginning = time.time()
	i = 0

	while (0 != 1):
		t = datetime.now()
		dog.gauge('millSeconds' + str(i), t.second * 1000000, tags=['seconds', 'big'])	# 1
		dog.gauge('random' + str(i), random.random())
		dog.gauge('sine' + str(i), math.sin(t.second / (math.pi)) + 1)
		dog.gauge('cos', math.cos(t.second / (math.pi)) + 1)
		dog.gauge('bin', float(round(random.random())) + 0.5);
		dog.gauge('one', 1)
		dog.gauge('cos2', math.cos(t.second / (math.pi)) + 1)
		dog.gauge('bin333', float(round(random.random())) + 0.5)
		dog.gauge('randommore', random.random() * random.random() * random.random())
		dog.gauge('zero', 0)
		dog.gauge('seconds.max', t.second * 4+2, tags=['seconds'])
		dog.gauge('seconds.min', t.second +1, tags=['seconds'])
		dog.gauge('seconds.average', t.second * 2+4, tags=['seconds'])
		# if i < 5: i+= 1
		time.sleep(send_every)


loop_forever()
