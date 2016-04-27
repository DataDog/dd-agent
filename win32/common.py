# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import ctypes

def handle_exe_click(name):
    ''' When the executables are clicked directly in the UI, we must let the
    user know that they have to install the program as a service instead of
    running it directly. '''
    message = """To use %(name)s, you must install it as a service.

To install %(name)s as a service, you must run the following in the console:

    %(name)s.exe install

For all available options, including how to install the service for a particular user, run the following in a console:

    %(name)s.exe help
""" % ({'name': name})
    MessageBox = ctypes.windll.user32.MessageBoxA
    MessageBox(None, message, 'Install as a Service', 0)
