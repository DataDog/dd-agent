from distutils.core import setup
import py2exe # Patching distutils setup
from guidata.disthelpers import Distribution

dist = Distribution()
dist.setup(name=u"Datadog Agent Manger", version='0.9.0',
           description=u"Manage your datadog agent",
           script="gui.py", target_name="agent-manager.exe"
           )
dist.add_modules('PyQt4', 'guidata')
dist.build('py2exe')

