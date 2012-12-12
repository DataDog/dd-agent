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

logger = logging.getLogger(__name__)

class Daemon:
    """
    A generic daemon class.
    
    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, pidfile, stdin=os.devnull, stdout=os.devnull, stderr=os.devnull):
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
            logger.error(msg)
            sys.stderr.write(msg + "\n")
            sys.exit(1)
       
        logger.debug("Fork 1 ok") 

        # Decouple from parent environment
        os.chdir("/") 
        os.setsid() 
        os.umask(0) 
    
        # Do second fork
        try: 
            pid = os.fork() 
            if pid > 0:
                # Exit from second parent
                sys.exit(0) 
        except OSError, e: 
            msg = "fork #2 failed: %d (%s)" % (e.errno, e.strerror)
            logger.error(msg)
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
        
        logger.info("Started")
    
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
            logger.exception(msg)
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
        
        logger.info("Starting...")
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        except SystemExit:
            pid = None
    
        if pid:
            message = "pidfile %s already exists. Is it already running?\n"
            logger.error(message % self.pidfile)
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        logger.info("Pidfile: %s" % self.pidfile)
        self.daemonize()        
        logger.debug("Calling run method")
        self.run()

    def stop(self):
        """
        Stop the daemon
        """

        from signal import SIGTERM

        logger.info("Stopping...") 
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        except ValueError:
            pid = None

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
                    logger.exception("Cannot kill agent daemon at pid %s" % pid)
                    sys.stderr.write(str(err) + "\n")
        else:
            message = "Pidfile %s does not exist. Not running?\n" % self.pidfile
            logger.info(message)
            sys.stderr.write(message)
            
            # Just to be sure. A ValueError might occur if the PID file is empty but does actually exist
            if os.path.exists(self.pidfile):
                os.remove(self.pidfile)
            
            return # Not an error in a restart

        
        logger.info("Stopped")

    def restart(self):
        "Restart the daemon"
        self.stop()     
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """

