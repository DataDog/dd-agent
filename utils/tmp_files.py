import os
import tempfile

def setup_temp_dir(agentConfig, proc_name=None):
    # if it has neither of these, then just drop back
    if not agentConfig["use_dd_temp_dir"] and not agentConfig["custom_temp_dir"]:
        return

    if agentConfig["custom_temp_dir"]:
        temp_dir = agentConfig["custom_temp_dir"]

    if agentConfig["use_dd_temp_dir"]:
        temp_dir = os.path.join(__file__, '..', 'tmp')

    if proc_name:
        temp_dir = os.path.join(temp_dir, proc_name)

    temp_dir = os.path.abspath(temp_dir)

    # make sure that it exists
    if not os.path.exists(temp_dir):
        # This is being run by every process,
        # creating a race condition which will throw an OSError
        # when one tries ot make the folder after the other
        # We should just pass on an OSError
        # This should be lessened by adding the proc_name to each tempdir
        # But, the error should be caught regardless
        try:
            # the default is 0777, it should probably be 0666
            os.makedirs(temp_dir, '0755')
        except OSError:
            pass


    # Python will look at this variable first to determine what tempdir to use,
    # it only uses system tempdirs or looks in envvars if it is not set
    tempfile.tempdir = temp_dir

    # We should also export it to ensure that any subprocesses get this as well
    os.environ['TMPDIR'] = temp_dir
