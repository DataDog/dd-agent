# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# Modified for Datadog

import sys
import os
import os.path as osp
import webbrowser


import win32serviceutil
import win32service

# GUI Imports
from guidata.qt.QtGui import (QWidget, QVBoxLayout, QSplitter, QFont,
                              QListWidget, QPushButton, QLabel, QGroupBox,
                              QHBoxLayout, QMessageBox, QInputDialog,
                              QSystemTrayIcon, QIcon, QMenu)
from guidata.qt.QtCore import SIGNAL, Qt, QSize, QPoint

from guidata.configtools import get_icon, get_family, MONOSPACE
from guidata.qthelpers import get_std_icon
from spyderlib.widgets.sourcecode.codeeditor import CodeEditor


# Datadog
from util import yaml, yLoader
from util import get_os
from config import get_confd_path, get_config_path, get_config

MAIN_WINDOW_TITLE = "Datadog Agent Manager"

DATADOG_SERVICE = "DatadogAgent"

STATUS_PAGE_URL = "http://localhost:17125/status"
AGENT_LOG_FILE = osp.join(os.environ['ALLUSERSPROFILE'], 'Datadog\\logs\\ddagent.log')

HUMAN_SERVICE_STATUS = {
    win32service.SERVICE_RUNNING : 'Service is running',
    win32service.SERVICE_START_PENDING : 'Service is starting',
    win32service.SERVICE_STOP_PENDING : 'Service is stopping',
    win32service.SERVICE_STOPPED : 'Service is stopped',
}


START_AGENT = "Start Agent"
STOP_AGENT = "Stop Agent"
RESTART_AGENT = "Restart Agent"
STATUS_PAGE = "Status page"
EXIT_MANAGER = "Exit Agent Manager"
OPEN_LOG = "Open log file"

SYSTEM_TRAY_MENU = [
    (START_AGENT, lambda: service_manager("start")),
    (STOP_AGENT, lambda: service_manager("stop")),
    (RESTART_AGENT, lambda: service_manager("restart")),
    (STATUS_PAGE, lambda: webbrowser.open(STATUS_PAGE_URL)),
    (OPEN_LOG, lambda: os.startfile(AGENT_LOG_FILE)),
    (EXIT_MANAGER, lambda: sys.exit(0)),
]

def get_checks():
    checks = []
    conf_d_directory = get_confd_path(get_os())

    for filename in sorted(os.listdir(conf_d_directory)):
        module_name, ext = osp.splitext(filename)
        if ext not in ('.yaml', '.example'):
            continue

        agent_check = AgentCheck(filename, ext, conf_d_directory)
        checks.append(agent_check)
    return checks

class ConfigFile(object):
    def __init__(self, file_path, description):
        self.file_path = file_path
        self.description = description

    def get_description(self):
        return self.description

    def save(self, content):
        try:
            f = open(self.file_path,'w')
            f.write(content)
            self.content = content
            QMessageBox.information(None, 'Message',
            "File saved.", QMessageBox.Ok)
        except Exception, e:
            QMessageBox.warning(None, 'Message',
            "Unable to save file: \n %s" % str(e), QMessageBox.Ok)
            raise

class DatadogConf(ConfigFile):

    @property
    def api_key(self):
        config = get_config(parse_args=False, cfg_path=self.file_path)
        api_key = config.get('api_key', None)
        if not api_key or api_key == 'APIKEYHERE':
            return None
        return api_key

    def check_api_key(self, editor):
        if self.api_key is None:
            api_key, ok = QInputDialog.getText(None, "Add your API KEY",
            "You must first set your api key in this file. You can find it here: https://app.datadoghq.com/account/settings#api")
            if ok and api_key:
                new_content = ""
                for line in self.content.split('\n'):
                    if "api_key:" in line:
                        new_content += "api_key: %s \n" % str(api_key)
                    else:
                        new_content += "%s \n" % line
                self.save(new_content)
                editor.set_text(new_content)
            else:
                self.check_api_key()

class AgentCheck(ConfigFile):
    def __init__(self, filename, ext, conf_d_directory):
        file_path = osp.join(conf_d_directory, filename)
        self.module_name = filename.split('.')[0]

        ConfigFile.__init__(self, file_path, description=self.module_name)
        
        self.enabled = ext == '.yaml'
        self.enabled_name = osp.join(conf_d_directory, "%s.yaml" % self.module_name)
        self.disabled_name = "%s.example" % self.enabled_name

    def enable(self):
        self.enabled = True
        os.rename(self.disabled_name, self.enabled_name)
        self.file_path = self.enabled_name

    def disable(self):
        self.enabled = False
        os.rename(self.enabled_name, self.disabled_name)
        self.file_path = self.disabled_name

    def save(self, content):
        check_yaml_syntax(content)
        ConfigFile.save(self, content)

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

        self.menu_button = QPushButton(get_icon("settings.png"),
                                      "Manager", self)


        hlayout = QHBoxLayout()
        hlayout.addWidget(self.save_button)
        hlayout.addStretch()
        hlayout.addWidget(self.enable_button)
        hlayout.addStretch()
        hlayout.addWidget(self.disable_button)
        hlayout.addStretch()
        hlayout.addWidget(self.edit_datadog_conf_button)
        hlayout.addStretch()
        hlayout.addWidget(self.menu_button)
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(group_desc)
        vlayout.addWidget(group_code)
        vlayout.addLayout(hlayout)
        self.setLayout(vlayout)

        self.current_file = None
        
    def set_item(self, check):
        self.current_file = check
        self.desc_label.setText(check.get_description())
        self.editor.set_text_from_file(check.file_path)
        check.content = self.editor.toPlainText().__str__()
        if check.enabled:
            self.disable_button.setEnabled(True)
            self.enable_button.setEnabled(False)
        else:
            self.disable_button.setEnabled(False)
            self.enable_button.setEnabled(True)

    def set_datadog_conf(self, datadog_conf):
        self.current_file = datadog_conf
        self.desc_label.setText(datadog_conf.get_description())
        self.editor.set_text_from_file(datadog_conf.file_path)
        datadog_conf.content = self.editor.toPlainText().__str__()
        self.disable_button.setEnabled(False)
        self.enable_button.setEnabled(False)

        datadog_conf.check_api_key(self.editor)


class MainWindow(QSplitter):
    def __init__(self, parent=None):
        QSplitter.__init__(self, parent)
        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.setWindowIcon(get_icon("agent.svg"))
        
        self.sysTray = SystemTray(self)

        self.connect(self.sysTray, SIGNAL("activated(QSystemTrayIcon::ActivationReason)"), self.__icon_activated)

        checks = get_checks()
        datadog_conf = DatadogConf(get_config_path(), description="Agent settings file: datadog.conf")

        listwidget = QListWidget(self)
        listwidget.addItems([osp.basename(check.module_name) for check in checks])
        
        self.properties = PropertiesWidget(self)
        
        self.addWidget(listwidget)
        self.addWidget(self.properties)
        
        self.connect(self.properties.enable_button, SIGNAL("clicked()"),
                     lambda: enable_check(self.properties))

        self.connect(self.properties.disable_button, SIGNAL("clicked()"),
                     lambda: disable_check(self.properties))

        self.connect(self.properties.save_button, SIGNAL("clicked()"),
                     lambda: save_file(self.properties))

        self.connect(listwidget, SIGNAL('currentRowChanged(int)'),
                     lambda row: self.properties.set_item(checks[row]))

        self.connect(self.properties.edit_datadog_conf_button, SIGNAL('clicked()'),
                     lambda: self.properties.set_datadog_conf(datadog_conf))

        self.connect(listwidget, SIGNAL('itemActivated(QListWidgetItem*)'),
                     lambda: checks[listwidget.currentRow()].run())


        self.manager_menu = Menu(self)
        self.connect(self.properties.menu_button, SIGNAL("clicked()"),
            lambda: self.manager_menu.popup(self.properties.menu_button.mapToGlobal(QPoint(0,0))))


        listwidget.setCurrentRow(0)
        
        self.setSizes([150, 1])
        self.setStretchFactor(1, 1)
        self.resize(QSize(950, 600))
        self.properties.set_datadog_conf(datadog_conf)


    def closeEvent(self, event):
        self.hide()
        self.sysTray.show() 
        event.ignore()

    def __icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()

class Menu(QMenu):

    def __init__(self, parent=None, ):
        QMenu.__init__(self, parent)
        self.options = {}

        for name, action in SYSTEM_TRAY_MENU:
            menu_action = self.addAction(name)
            self.connect(menu_action, SIGNAL('triggered()'), action)
            self.options[name] = menu_action

        self.connect(self, SIGNAL("aboutToShow()"), lambda: self.update_options())



    def update_options(self):
        if is_service_running():
            self.options[START_AGENT].setEnabled(False)
            self.options[RESTART_AGENT].setEnabled(True)
            self.options[STOP_AGENT].setEnabled(True)
        elif is_service_stopped():
            self.options[START_AGENT].setEnabled(True)
            self.options[RESTART_AGENT].setEnabled(False)
            self.options[STOP_AGENT].setEnabled(False)
        elif is_service_pending():
            self.options[START_AGENT].setEnabled(False)
            self.options[RESTART_AGENT].setEnabled(False)
            self.options[STOP_AGENT].setEnabled(False)


class SystemTray(QSystemTrayIcon):

    def __init__(self, parent=None):
        QSystemTrayIcon.__init__(self, parent)
        self.setIcon(get_icon("agent.png"))
        self.setVisible(True)
        self.options = {}

        menu = Menu(self.parent())
        self.setContextMenu(menu)

    
def disable_check(properties):
    check = properties.current_file
    new_content = properties.editor.toPlainText().__str__()

    if check.content != new_content:
        QMessageBox.warning(None, 'Message',
            "You must first save the file", QMessageBox.Ok)
        return

    properties.enable_button.setEnabled(True)
    properties.disable_button.setEnabled(False)
    check.disable()
    
def enable_check(properties):
    check = properties.current_file

    new_content = properties.editor.toPlainText().__str__()
    if check.content != new_content:
        QMessageBox.warning(None, 'Message',
            "You must first save the file", QMessageBox.Ok)
        return

    properties.enable_button.setEnabled(False)
    properties.disable_button.setEnabled(True)
    check.enable()
    

def save_file(properties):
    current_file = properties.current_file
    new_content = properties.editor.toPlainText().__str__()
    current_file.save(new_content)
    
def check_yaml_syntax(content):
    try:
        yaml.load(content, Loader=yLoader)
    except Exception, e:
        QMessageBox.warning(None, 'Message',
            "Unable to parse yaml: \n %s" % str(e), QMessageBox.Ok)
        raise
    
def service_manager(action):
    if action == 'stop':
        win32serviceutil.StopService(DATADOG_SERVICE)
    elif action == 'start':
        win32serviceutil.StartService(DATADOG_SERVICE)
    elif action == 'restart':
        win32serviceutil.RestartService(DATADOG_SERVICE)

def get_service_status():
    return win32serviceutil.QueryServiceStatus(DATADOG_SERVICE)[1]

def is_service_running():
    return get_service_status() == win32service.SERVICE_RUNNING

def is_service_pending():
    return get_service_status() in [win32service.SERVICE_STOP_PENDING, win32service.SERVICE_START_PENDING]

def is_service_stopped():
    return get_service_status() == win32service.SERVICE_STOPPED

if __name__ == '__main__':
    from guidata.qt.QtGui import QApplication
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec_()