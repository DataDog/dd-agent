# stdlib
import subprocess
import tempfile


# FIXME: python 2.7 has a far better way to do this
def get_subprocess_output(command, log):
    """
    Run the given subprocess command and return it's output. Raise an Exception
    if an error occurs.
    """
    with tempfile.TemporaryFile('rw') as stdout_f:
        proc = subprocess.Popen(command, close_fds=True,
                                stdout=stdout_f, stderr=subprocess.PIPE)
        proc.wait()
        err = proc.stderr.read()
        if err:
            log.debug("Error while running {0} : {1}".format(" ".join(command),
                                                             err))

        stdout_f.seek(0)
        output = stdout_f.read()
    return output
