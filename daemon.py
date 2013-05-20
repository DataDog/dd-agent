'''
    ***
    Modified generic daemon class
    ***
    
    Author:     http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
                www.boxedice.com
    
    License:    http://creativecommons.org/licenses/by-sa/3.0/
    
    Changes:    23rd Jan 2009 (David Mytton <david@boxedice.com>)
                - Replaced hard coded '/dev/null in __init__ with os.devnull
                - Added OS check to conditionally remove code that doesn't work on OS X
                - Added output to console on completion
                - Tidied up formatting 
                11th Mar 2009 (David Mytton <david@boxedice.com>)
                - Fixed problem with daemon exiting on Python 2.4 (before SystemExit was part of the Exception base)
                13th Aug 2010 (David Mytton <david@boxedice.com>
                - Fixed unhandled exception if PID file is empty
'''

# Core modules
import atexit
import os
import sys
import time
import logging
import errno

from util import AgentSupervisor

log = logging.getLogger(__name__)

class Daemon:
    """
    A generic daemon class.
    
    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, pidfile, stdin=os.devnull, stdout=os.devnull, stderr=os.devnull):
        self.autorestart = False
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
    
    def daemonize(self):
        """
        Do the UNIX double-fork magic, see Stevens' "Advanced 
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try: 
            pid = os.fork() 
            if pid > 0:
                # Exit first parent
                sys.exit(0) 
        except OSError, e: 
            msg = "fork #1 failed: %d (%s)" % (e.errno, e.strerror)
            log.error(msg)
            sys.stderr.write(msg + "\n")
            sys.exit(1)
       
        log.debug("Fork 1 ok") 

        # Decouple from parent environment
        os.chdir("/") 
        os.setsid() 

        if self.autorestart:
            # Set-up the supervisor callbacks and put a fork in it.
            logging.info('Running Agent with auto-restart ON')
            def parent_func():
                self.start_event = False
            AgentSupervisor.start(parent_func)
        else:
            # Do second fork
            try:
                pid = os.fork()
                if pid > 0:
                    # Exit from second parent
                    sys.exit(0)
            except OSError, e:
                msg = "fork #2 failed: %d (%s)" % (e.errno, e.strerror)
                logging.error(msg)
                sys.stderr.write(msg + "\n")
                sys.exit(1)


        if sys.platform != 'darwin': # This block breaks on OS X
            # Redirect standard file descriptors
            sys.stdout.flush()
            sys.stderr.flush()
            si = file(self.stdin, 'r')
            so = file(self.stdout, 'a+')
            se = file(self.stderr, 'a+', 0)
            os.dup2(si.fileno(), sys.stdin.fileno())
            os.dup2(so.fileno(), sys.stdout.fileno())
            os.dup2(se.fileno(), sys.stderr.fileno())
        
        log.info("Started")
    
        # Write pidfile
        atexit.register(self.delpid) # Make sure pid file is removed if we quit
        pid = str(os.getpid())
        try:
            fp = os.fdopen(os.open(self.pidfile, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0644), 'w+')
            fp.write("%s\n" % pid)
            fp.close()
            os.chmod(self.pidfile, 0644)
        except Exception, e:
            msg = "Unable to write pidfile: %s" % self.pidfile
            log.exception(msg)
            sys.stderr.write(msg + "\n")
            sys.exit(1)

    def delpid(self):
        try:
            os.remove(self.pidfile)
        except OSError:
            pass

    def start(self):
        """
        Start the daemon
        """
        
        log.info("Starting...")
        pid = self.pid
    
        if pid:
            message = "pidfile %s already exists. Is it already running?\n"
            log.error(message % self.pidfile)
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        log.info("Pidfile: %s" % self.pidfile)
        self.daemonize()        
        log.debug("Calling run method")
        self.run()

    def stop(self):
        """
        Stop the daemon
        """

        from signal import SIGTERM

        log.info("Stopping...") 
        pid = self.pid

        # Clear the pid file
        if os.path.exists(self.pidfile):
            os.remove(self.pidfile)

        if pid > 1:
            # Try killing the daemon process    
            try:
                while 1:
                    os.kill(pid, SIGTERM)
                    time.sleep(0.1)
            except OSError, err:
                if str(err).find("No such process") <= 0:
                    log.exception("Cannot kill agent daemon at pid %s" % pid)
                    sys.stderr.write(str(err) + "\n")
        else:
            message = "Pidfile %s does not exist. Not running?\n" % self.pidfile
            log.info(message)
            sys.stderr.write(message)
            
            # Just to be sure. A ValueError might occur if the PID file is empty but does actually exist
            if os.path.exists(self.pidfile):
                os.remove(self.pidfile)
            
            return # Not an error in a restart

        
        log.info("Stopped")

    def restart(self):
        "Restart the daemon"
        self.stop()     
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """

    def info(self):
        """
        You should override this method when you subclass Daemon. It will be
        called to provide information about the status of the process
        """

    def status(self):
        """
        Get the status of the daemon. Exits with 0 if running, 1 if not.
        """
        pid = self.pid

        if pid < 0:
            message = '%s is not running' % self.__class__.__name__
            exit_code = 1
        else:
            # Check for the existence of a process with the pid
            try:
                # os.kill(pid, 0) will raise an OSError exception if the process
                # does not exist, or if access to the process is denied (access denied will be an EPERM error).
                # If we get an OSError that isn't an EPERM error, the process
                # does not exist.
                # (from http://stackoverflow.com/questions/568271/check-if-pid-is-not-in-use-in-python,
                #  Giampaolo's answer)
                os.kill(pid, 0)
            except OSError, e:
                if e.errno != errno.EPERM:
                    message = '%s pidfile contains pid %s, but no running process could be found' % (self.__class__.__name__, pid)
                    exit_code = 1
            else:
                message = '%s is running with pid %s' % (self.__class__.__name__, pid)
                exit_code = 0

        log.info(message)
        sys.stdout.write(message + "\n")
        sys.exit(exit_code)

    @property
    def pid(self):
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
            return pid
        except IOError:
            return None
        except ValueError:
            return None

