# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import logging

# project
from utils.platform import Platform
from utils.subprocess_output import get_subprocess_output

log = logging.getLogger(__name__)

def run_gohai_metadata():
    return _run_gohai(['--exclude', 'processes'])

def run_gohai_processes():
    return _run_gohai(['--only', 'processes'])

def _run_gohai(options):
    output = None
    try:
        if not Platform.is_windows():
            command = "gohai"
        else:
            command = "gohai\gohai.exe"
        output, err, _ = get_subprocess_output([command] + options, log)
        if err:
            log.debug("GOHAI LOG | %s", err)
    except OSError as e:
        if e.errno == 2:  # file not found, expected when install from source
            log.info("gohai file not found")
        else:
            log.warning("Unexpected OSError when running gohai %s", e)
    except Exception as e:
        log.warning("gohai command failed with error %s", e)

    return output