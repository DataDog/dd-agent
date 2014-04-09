from statsd import statsd
from multiprocessing import Process
import os
N = 5000

def start():
    i = 0
    while True:
            statsd.gauge("ridiculouslongname{0}".format(i % N) * 20, i % N, tags=["tags:42"] * 200)
            i += 1
            if i % N == 0:
                print "Parent: {0} Process: {1} Iteration {2}".format(os.getppid(), os.getpid(), i)


if __name__ == '__main__':
    for j in range(20):
        p = Process(target=start)
        p.start()    
