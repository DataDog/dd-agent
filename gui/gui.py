# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""
GUI-based test launcher
"""

import sys
import os
import os.path as osp
import webbrowser

#import win32serviceutil
from spyderlib.widgets.sourcecode.codeeditor import CodeEditor

# Local imports
from guidata.qt.QtGui import (QWidget, QVBoxLayout, QSplitter, QFont,
                              QListWidget, QPushButton, QLabel, QGroupBox,
                              QHBoxLayout, QMessageBox,
                              QSystemTrayIcon, QIcon, QMenu)
from guidata.qt.QtCore import SIGNAL, Qt, QSize

from guidata.configtools import get_icon, get_family, MONOSPACE
from guidata.qthelpers import get_std_icon

import yaml
from yaml import Loader as yLoader

CHECK_DIRECTORY = "C:\ProgramData\Datadog\conf.d"
DATADOG_CONF = "C:\ProgramData\Datadog\datadog.conf"
CHECK_DIRECTORY = "/Users/remi/Documents/dd-agent/conf.d-win/"
DATADOG_CONF = "/Users/remi/Documents/dd-agent/datadog.conf"

def get_checks():
    checks = []

    for fname in sorted(os.listdir(CHECK_DIRECTORY)):
        module_name, ext = osp.splitext(fname)
        if ext not in ('.yaml', '.example'):
            continue

        agent_check = AgentCheck(fname, ext)
        checks.append(agent_check)
    return checks

class AgentCheck(object):
    def __init__(self, fname, ext, parse_yaml=True):
        self.filename = fname
        self.module_name = fname.split('.')[0]
        self.enabled = ext == '.yaml'
        self.path = osp.join(CHECK_DIRECTORY, fname)
        self.enabled_name = osp.join(CHECK_DIRECTORY, "{0}.yaml".format(self.module_name))
        self.disabled_name = "{0}.example".format(self.enabled_name)
        self.current_file_name = self.path
        self.parse_yaml = parse_yaml

    def get_description(self):
        return self.module_name

    def enable(self):
        self.enabled = True
        os.rename(self.disabled_name, self.enabled_name)
        self.current_file_name = self.enabled_name

    def disable(self):
        self.enabled = False
        os.rename(self.enabled_name, self.disabled_name)
        self.current_file_name = self.disabled_name

    def save(self, content):
        f = open(self.current_file_name,'w')
        f.write(content)


class PropertiesWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        font = QFont(get_family(MONOSPACE), 10, QFont.Normal)
        
        info_icon = QLabel()
        icon = get_std_icon('MessageBoxInformation').pixmap(24, 24)
        info_icon.setPixmap(icon)
        info_icon.setFixedWidth(32)
        info_icon.setAlignment(Qt.AlignTop)
        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        self.desc_label.setAlignment(Qt.AlignTop)
        self.desc_label.setFont(font)
        group_desc = QGroupBox("Description", self)
        layout = QHBoxLayout()
        layout.addWidget(info_icon)
        layout.addWidget(self.desc_label)
        group_desc.setLayout(layout)
        
        self.editor = CodeEditor(self)
        self.editor.setup_editor(linenumbers=True, font=font)
        self.editor.setReadOnly(False)
        group_code = QGroupBox("Source code", self)
        layout = QVBoxLayout()
        layout.addWidget(self.editor)
        group_code.setLayout(layout)
        
        self.enable_button = QPushButton(get_icon("apply.png"),
                                      "Enable", self)

        self.save_button = QPushButton(get_icon("filesave.png"),
                                      "Save", self)

        self.edit_datadog_conf_button = QPushButton(get_icon("edit.png"),
                                      "Edit agent settings", self)

        self.disable_button = QPushButton(get_icon("delete.png"),
                                      "Disable", self)


        hlayout = QHBoxLayout()
        hlayout.addWidget(self.save_button)
        hlayout.addStretch()
        hlayout.addWidget(self.enable_button)
        hlayout.addStretch()
        hlayout.addWidget(self.disable_button)
        hlayout.addStretch()
        hlayout.addWidget(self.edit_datadog_conf_button)
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(group_desc)
        vlayout.addWidget(group_code)
        vlayout.addLayout(hlayout)
        self.setLayout(vlayout)

        self.current_check = None
        
    def set_item(self, check):
        self.current_check = check
        self.desc_label.setText(check.get_description())
        self.editor.set_text_from_file(check.path)
        check.content = self.editor.toPlainText().__str__()
        if check.enabled:
            self.disable_button.setEnabled(True)
            self.enable_button.setEnabled(False)
        else:
            self.disable_button.setEnabled(False)
            self.enable_button.setEnabled(True)

    def set_datadog_conf(self, datadog_conf):
        self.current_check = datadog_conf
        self.desc_label.setText(datadog_conf.get_description())
        self.editor.set_text_from_file(datadog_conf.path)
        datadog_conf.content = self.editor.toPlainText().__str__()
        self.disable_button.setEnabled(False)
        self.enable_button.setEnabled(False)

class EditChecksFrame(QSplitter):
    def __init__(self, parent=None):
        QSplitter.__init__(self, parent)

        checks = get_checks()
        datadog_conf = AgentCheck(DATADOG_CONF, '.conf', parse_yaml=False)

        listwidget = QListWidget(self)
        listwidget.addItems([osp.basename(check.module_name) for check in checks])
        
        self.properties = PropertiesWidget(self)
        
        self.addWidget(listwidget)
        self.addWidget(self.properties)
        
        self.connect(self.properties.enable_button, SIGNAL("clicked()"),
                     lambda: enable_check(self.properties, self))

        self.connect(self.properties.disable_button, SIGNAL("clicked()"),
                     lambda: disable_check(self.properties, self))

        self.connect(self.properties.save_button, SIGNAL("clicked()"),
                     lambda: save_check(self.properties, self))

        self.connect(listwidget, SIGNAL('currentRowChanged(int)'),
                     lambda row: self.properties.set_item(checks[row]))

        self.connect(self.properties.edit_datadog_conf_button, SIGNAL('clicked()'),
                     lambda: self.properties.set_datadog_conf(datadog_conf))

        self.connect(listwidget, SIGNAL('itemActivated(QListWidgetItem*)'),
                     lambda: checks[listwidget.currentRow()].run())


        listwidget.setCurrentRow(0)
        
        self.properties.set_item(checks[0])

        self.setSizes([150, 1])
        self.setStretchFactor(1, 1)
        self.resize(QSize(950, 600))

class AgentManagerFrame(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)

        self.stop_button = QPushButton(get_icon("apply.png"),
                                      "Stop agent", self)
        self.start_button = QPushButton(get_icon("apply.png"),
                                      "Start agent", self)

        self.restart_button = QPushButton(get_icon("apply.png"),
                                      "Restart agent", self)

        layout = QHBoxLayout()
        layout.addWidget(self.stop_button)
        layout.addWidget(self.start_button)
        layout.addWidget(self.restart_button)

        self.connect(self.stop_button, SIGNAL("clicked()"),
                     lambda: service_manager("stop"))

        self.connect(self.start_button, SIGNAL("clicked()"),
                     lambda: service_manager("start"))

        self.connect(self.restart_button, SIGNAL("clicked()"),
                     lambda: service_manager("restart"))

        self.setLayout(layout)

class MainWindow(QSplitter):

    def __init__(self, parent=None):
        QSplitter.__init__(self, parent)
        self.setWindowTitle("Datadog Agent Manager")
        self.setWindowIcon(get_icon("agent.svg"))
        self.setOrientation(Qt.Vertical)
        self.setSizes([150, 1])
        self.setStretchFactor(1, 1)
        self.resize(QSize(950, 600))

        self.addWidget(EditChecksFrame(self))
        self.addWidget(AgentManagerFrame(self))

        self.create_sys_tray()

        traySignal = "activated(QSystemTrayIcon::ActivationReason)"
        self.connect(self.sysTray, SIGNAL(traySignal), self.__icon_activated)

    def create_sys_tray(self):
        self.sysTray = QSystemTrayIcon(self)
        self.sysTray.setIcon( get_icon("agent.png") )
        self.sysTray.setVisible(True)
        self.connect(self.sysTray, SIGNAL("activated(QSystemTrayIcon::ActivationReason)"), self.on_sys_tray_activated)

        self.sysTrayMenu = QMenu(self)
        
        start_action = self.sysTrayMenu.addAction("Start Agent")
        stop_action = self.sysTrayMenu.addAction("Stop Agent")
        restart_action = self.sysTrayMenu.addAction("RestartService Agent")
        status_page_action = self.sysTrayMenu.addAction("Status page")
        exit_manager_action = self.sysTrayMenu.addAction("Exit Agent Manager")
        
        self.sysTray.setContextMenu(self.sysTrayMenu)

        self.sysTrayMenu.connect(start_action, SIGNAL('triggered()'), lambda: service_manager("start"))
        self.sysTrayMenu.connect(stop_action, SIGNAL('triggered()'), lambda: service_manager("stop"))
        self.sysTrayMenu.connect(restart_action, SIGNAL('triggered()'), lambda: service_manager("restart"))
        self.sysTrayMenu.connect(status_page_action, SIGNAL('triggered()'), lambda: webbrowser.open("http://localhost:17125/status"))
        self.sysTrayMenu.connect(exit_manager_action, SIGNAL('triggered()'), lambda: sys.exit(0))

    def on_sys_tray_activated(self, reason):
        print "reason-=" , reason

    def closeEvent(self, event):
        #"minimize"
        self.hide()
        self.sysTray.show() #thanks @mojo
        event.ignore()

    def __icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()

def disable_check(properties, parent):
    check = properties.current_check
    new_content = properties.editor.toPlainText().__str__()

    if check.content != new_content:
        QMessageBox.warning(None, 'Message',
            "You must first save the file", QMessageBox.Ok)
        return

    properties.enable_button.setEnabled(True)
    properties.disable_button.setEnabled(False)
    check.disable()
    
def enable_check(properties, check, parent):
    check = properties.current_check

    new_content = properties.editor.toPlainText().__str__()
    if check.content != new_content:
        QMessageBox.warning(None, 'Message',
            "You must first save the file", QMessageBox.Ok)
        return

    properties.enable_button.setEnabled(False)
    properties.disable_button.setEnabled(True)
    check.enable()
    

def save_check(properties, parent):
    check = properties.current_check

    new_content = properties.editor.toPlainText().__str__()
    if check.parse_yaml:
        check_yaml_syntax(new_content)
    try:
        check.save(new_content)
        QMessageBox.information(None, 'Message',
            "File saved", QMessageBox.Ok)
    except Exception, e:
        QMessageBox.warning(None, 'Message',
            "Unable to save file: \n %s" % str(e), QMessageBox.Ok)
        raise
    
def check_yaml_syntax(content):
    try:
        yaml.load(content, Loader=yLoader)
    except Exception, e:
        QMessageBox.warning(None, 'Message',
            "Unable to parse yaml: \n %s" % str(e), QMessageBox.Ok)
        raise
    
def service_manager(action):
    service = "DatadogAgent"
    machine = "localhost"
    if action == 'stop':
        win32serviceutil.StopService(service, machine)
    elif action == 'start':
        win32serviceutil.StartService(service, machine)
    elif action == 'restart':
        win32serviceutil.RestartService(service, machine)
   

if __name__ == '__main__':
    from guidata.qt.QtGui import QApplication
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec_()