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
import thread # To manage the windows process asynchronously

import win32serviceutil
import win32service

# GUI Imports
from guidata.qt.QtGui import (QWidget, QVBoxLayout, QSplitter, QFont,
                              QListWidget, QPushButton, QLabel, QGroupBox,
                              QHBoxLayout, QMessageBox, QInputDialog,
                              QSystemTrayIcon, QIcon, QMenu)
from guidata.qt.QtCore import SIGNAL, Qt, QSize, QPoint, QTimer

from guidata.configtools import get_icon, get_family, MONOSPACE
from guidata.qthelpers import get_std_icon
from spyderlib.widgets.sourcecode.codeeditor import CodeEditor

# small hack to avoid having to patch the spyderlib library
# Needed because of py2exe bundling not being able to access
# the spyderlib image sources
import spyderlib.baseconfig
spyderlib.baseconfig.IMG_PATH = [""]

# Datadog
from util import get_os, yLoader
from config import (get_confd_path, get_config_path, get_config,
    _windows_commondata_path)

# 3rd Party
import yaml

EXCLUDED_WINDOWS_CHECKS = [
    'cacti', 'directory', 'docker', 'gearmand',
    'hdfs', 'kafka_consumer', 'marathon', 'mcache',
    'mesos', 'network', 'postfix', 'process',
    'gunicorn', 'zk',
    ]

MAIN_WINDOW_TITLE = "Datadog Agent Manager"

DATADOG_SERVICE = "DatadogAgent"

AGENT_LOG_FILE = osp.join(_windows_commondata_path(), 'Datadog', 'logs', 'ddagent.log')

HUMAN_SERVICE_STATUS = {
    win32service.SERVICE_RUNNING : 'Service is running',
    win32service.SERVICE_START_PENDING : 'Service is starting',
    win32service.SERVICE_STOP_PENDING : 'Service is stopping',
    win32service.SERVICE_STOPPED : 'Service is stopped',
    "Unknown" : "Cannot get service status",
}

REFRESH_PERIOD = 5000

START_AGENT = "Start Agent"
STOP_AGENT = "Stop Agent"
RESTART_AGENT = "Restart Agent"
EXIT_MANAGER = "Exit Agent Manager"
OPEN_LOG = "Open log file"

SYSTEM_TRAY_MENU = [
    (START_AGENT, lambda: service_manager("start")),
    (STOP_AGENT, lambda: service_manager("stop")),
    (RESTART_AGENT, lambda: service_manager("restart")),
    (EXIT_MANAGER, lambda: sys.exit(0)),
]

def get_checks():
    checks = {}
    conf_d_directory = get_confd_path(get_os())

    for filename in sorted(os.listdir(conf_d_directory)):
        module_name, ext = osp.splitext(filename)
        if filename.split('.')[0] in EXCLUDED_WINDOWS_CHECKS:
            continue
        if ext not in ('.yaml', '.example', '.disabled'):
            continue

        agent_check = AgentCheck(filename, ext, conf_d_directory)
        if (agent_check.enabled or agent_check.module_name not in checks or
            (not agent_check.is_example and not checks[agent_check.module_name].enabled)):
            checks[agent_check.module_name] = agent_check

    checks_list = checks.values()
    checks_list.sort(key=lambda c: c.module_name)

    return checks_list

class EditorFile(object):
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
            info_popup("File saved.")
        except Exception, e:
            warning_popup("Unable to save file: \n %s" % str(e))
            raise

class LogFile(EditorFile):
    def __init__(self):
        EditorFile.__init__(self, AGENT_LOG_FILE, "Agent log file")


class DatadogConf(EditorFile):

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
                new_content = []
                for line in self.content.splitlines():
                    if "api_key:" in line:
                        new_content.append("api_key: %s" % str(api_key))
                    else:
                        new_content.append("%s" % line)
                new_content = "\n".join(new_content)
                self.save(new_content)
                editor.set_text(new_content)

                if not is_service_stopped():
                    service_manager("restart")
                else:
                    service_manager("start")
            else:
                self.check_api_key(editor)

class AgentCheck(EditorFile):
    def __init__(self, filename, ext, conf_d_directory):
        file_path = osp.join(conf_d_directory, filename)
        self.module_name = filename.split('.')[0]

        EditorFile.__init__(self, file_path, description=self.module_name.replace("_", " ").title())

        self.enabled = ext == '.yaml'
        self.is_example = ext == '.example'
        self.enabled_name = osp.join(conf_d_directory, "%s.yaml" % self.module_name)
        self.disabled_name = "%s.disabled" % self.enabled_name

    def enable(self):
        self.enabled = True
        os.rename(self.file_path, self.enabled_name)
        self.file_path = self.enabled_name

    def disable(self):
        self.enabled = False
        os.rename(self.file_path, self.disabled_name)
        self.file_path = self.disabled_name

    def save(self, content):
        check_yaml_syntax(content)
        EditorFile.save(self, content)

class PropertiesWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        font = QFont(get_family(MONOSPACE), 10, QFont.Normal)

        info_icon = QLabel()
        icon = get_std_icon('MessageBoxInformation').pixmap(24, 24)
        info_icon.setPixmap(icon)
        info_icon.setFixedWidth(32)
        info_icon.setAlignment(Qt.AlignTop)

        self.service_status_label = QLabel()
        self.service_status_label.setWordWrap(True)
        self.service_status_label.setAlignment(Qt.AlignTop)
        self.service_status_label.setFont(font)

        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        self.desc_label.setAlignment(Qt.AlignTop)
        self.desc_label.setFont(font)

        group_desc = QGroupBox("Description", self)
        layout = QHBoxLayout()
        layout.addWidget(info_icon)
        layout.addWidget(self.desc_label)
        layout.addStretch()
        layout.addWidget(self.service_status_label  )

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

        self.view_log_button = QPushButton(get_icon("txt.png"),
                                      "View log", self)

        self.status_button = QPushButton(get_icon("settings.png"),
                                      "Status", self)

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
        hlayout.addWidget(self.view_log_button)
        hlayout.addStretch()
        hlayout.addWidget(self.status_button)
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

    def set_log_file(self, log_file):
        self.current_file = log_file
        self.desc_label.setText(log_file.get_description())
        self.editor.set_text_from_file(log_file.file_path)
        log_file.content = self.editor.toPlainText().__str__()
        self.disable_button.setEnabled(False)
        self.enable_button.setEnabled(False)
        self.editor.go_to_line(len(log_file.content.splitlines()))


class MainWindow(QSplitter):
    def __init__(self, parent=None):

        QSplitter.__init__(self, parent)
        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.setWindowIcon(get_icon("agent.svg"))

        self.sysTray = SystemTray(self)

        self.connect(self.sysTray, SIGNAL("activated(QSystemTrayIcon::ActivationReason)"), self.__icon_activated)

        checks = get_checks()
        datadog_conf = DatadogConf(get_config_path(), description="Agent settings file: datadog.conf")
        self.log_file = LogFile()

        listwidget = QListWidget(self)
        listwidget.addItems([osp.basename(check.module_name).replace("_", " ").title() for check in checks])

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

        self.connect(self.properties.view_log_button, SIGNAL('clicked()'),
                     lambda: self.properties.set_log_file(self.log_file))

        self.manager_menu = Menu(self)
        self.connect(self.properties.menu_button, SIGNAL("clicked()"),
            lambda: self.manager_menu.popup(self.properties.menu_button.mapToGlobal(QPoint(0,0))))


        listwidget.setCurrentRow(0)

        self.setSizes([150, 1])
        self.setStretchFactor(1, 1)
        self.resize(QSize(950, 600))
        self.properties.set_datadog_conf(datadog_conf)

        self.do_refresh()

    def do_refresh(self):
        try:
            if self.isVisible():
                service_status = get_service_status()
                self.properties.service_status_label.setText(HUMAN_SERVICE_STATUS[service_status])

                if not is_service_stopped(service_status) and self.properties.current_file == self.log_file:
                    self.properties.set_log_file(self.log_file)
        finally:
            QTimer.singleShot(REFRESH_PERIOD, self.do_refresh)

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
        status = get_service_status()
        if is_service_running(status):
            self.options[START_AGENT].setEnabled(False)
            self.options[RESTART_AGENT].setEnabled(True)
            self.options[STOP_AGENT].setEnabled(True)
        elif is_service_stopped(status):
            self.options[START_AGENT].setEnabled(True)
            self.options[RESTART_AGENT].setEnabled(False)
            self.options[STOP_AGENT].setEnabled(False)
        elif is_service_pending(status):
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
        warning_popup("You must first save the file.")
        return

    properties.enable_button.setEnabled(True)
    properties.disable_button.setEnabled(False)
    check.disable()

def enable_check(properties):
    check = properties.current_file

    new_content = properties.editor.toPlainText().__str__()
    if check.content != new_content:
        warning_popup("You must first save the file")
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
        warning_popup("Unable to parse yaml: \n %s" % str(e))
        raise

def _service_manager(action):
    try:
        if action == 'stop':
            win32serviceutil.StopService(DATADOG_SERVICE)
        elif action == 'start':
            win32serviceutil.StartService(DATADOG_SERVICE)
        elif action == 'restart':
            win32serviceutil.RestartService(DATADOG_SERVICE)
    except Exception, e:
        warning_popup("Couldn't %s service: \n %s" % (action, str(e)))

def service_manager(action, async=True):
    if not async:
        _service_manager(action)
    else:
        thread.start_new_thread(_service_manager, (action,))

def get_service_status():
    try:
        return win32serviceutil.QueryServiceStatus(DATADOG_SERVICE)[1]
    except Exception:
        return "Unknown"

def is_service_running(status = None):
    if status == None:
        status = get_service_status()
    return status == win32service.SERVICE_RUNNING

def is_service_pending(status = None):
    if status == None:
        status = get_service_status()
    return status in [win32service.SERVICE_STOP_PENDING, win32service.SERVICE_START_PENDING]

def is_service_stopped(status = None):
    if status == None:
        status = get_service_status()
    return status == win32service.SERVICE_STOPPED

def warning_popup(message, parent=None):
    QMessageBox.warning(parent, 'Message', message, QMessageBox.Ok)

def info_popup(message, parent=None):
    QMessageBox.information(parent, 'Message', message, QMessageBox.Ok)


if __name__ == '__main__':
    from guidata.qt.QtGui import QApplication
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec_()
