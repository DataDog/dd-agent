# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# Modified for Datadog

# stdlib
import logging
import os
import os.path as osp
import platform
import sys
import thread  # To manage the windows process asynchronously

# 3p
# GUI Imports
from guidata.configtools import get_family, get_icon, MONOSPACE
from guidata.qt.QtCore import QPoint, QSize, Qt, QTimer, SIGNAL
from guidata.qt.QtGui import (QFont, QGroupBox, QHBoxLayout, QInputDialog,
                              QLabel, QListWidget, QMenu, QMessageBox,
                              QPushButton, QSplitter, QSystemTrayIcon,
                              QTextEdit, QVBoxLayout, QWidget)
from guidata.qthelpers import get_std_icon

# small hack to avoid having to patch the spyderlib library
# Needed because of py2exe bundling not being able to access
# the spyderlib image sources
import spyderlib.baseconfig
spyderlib.baseconfig.IMG_PATH = [""]
from spyderlib.widgets.sourcecode.codeeditor import CodeEditor

# Windows management & others
import tornado.template as template
import win32service
import win32serviceutil
import yaml

# Datadog
from checks.check_status import CollectorStatus, DogstatsdStatus, ForwarderStatus, logger_info
from config import (
    _windows_commondata_path,
    get_confd_path,
    get_config,
    get_config_path,
    get_version,
)
from util import get_os, yLoader

log = logging.getLogger(__name__)

EXCLUDED_WINDOWS_CHECKS = [
    'btrfs',
    'cacti',
    'directory',
    'docker',
    'gearmand',
    'gunicorn',
    'hdfs',
    'kafka_consumer',
    'marathon',
    'mcache',
    'mesos',
    'network',
    'postfix',
    'process',
    'ssh_check',
    'zk',
]

MAIN_WINDOW_TITLE = "Datadog Agent Manager"

DATADOG_SERVICE = "DatadogAgent"

COLLECTOR_LOG_FILE = os.path.join(_windows_commondata_path(), 'Datadog', 'logs', 'collector.log')
FORWARDER_LOG_FILE = os.path.join(_windows_commondata_path(), 'Datadog', 'logs', 'forwarder.log')
DOGSTATSD_LOG_FILE = os.path.join(_windows_commondata_path(), 'Datadog', 'logs', 'dogstatsd.log')
JMXFETCH_LOG_FILE = os.path.join(_windows_commondata_path(), 'Datadog', 'logs', 'jmxfetch.log')

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

class ForwarderLogFile(EditorFile):
    def __init__(self):
        EditorFile.__init__(self, FORWARDER_LOG_FILE, "Forwarder log file")

class CollectorLogFile(EditorFile):
    def __init__(self):
        EditorFile.__init__(self, COLLECTOR_LOG_FILE, "Collector log file")

class DogstatsdLogFile(EditorFile):
    def __init__(self):
        EditorFile.__init__(self, DOGSTATSD_LOG_FILE, "Dogstatsd log file")

class JMXFetchLogFile(EditorFile):
    def __init__(self):
        EditorFile.__init__(self, JMXFETCH_LOG_FILE, "JMX Fetch log file")

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

        self.group_desc = QGroupBox("Description", self)
        layout = QHBoxLayout()
        layout.addWidget(info_icon)
        layout.addWidget(self.desc_label)
        layout.addStretch()
        layout.addWidget(self.service_status_label)

        self.group_desc.setLayout(layout)

        self.editor = CodeEditor(self)
        self.editor.setup_editor(linenumbers=True, font=font)
        self.editor.setReadOnly(False)
        self.group_code = QGroupBox("Source code", self)
        layout = QVBoxLayout()
        layout.addWidget(self.editor)
        self.group_code.setLayout(layout)

        self.enable_button = QPushButton(get_icon("apply.png"),
                                      "Enable", self)

        self.save_button = QPushButton(get_icon("filesave.png"),
                                      "Save", self)

        self.disable_button = QPushButton(get_icon("delete.png"),
                                      "Disable", self)

        self.refresh_button = QPushButton(get_icon("restart.png"),
                                      "Refresh", self)
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.save_button)
        hlayout.addWidget(self.enable_button)
        hlayout.addWidget(self.disable_button)
        hlayout.addWidget(self.refresh_button)


        vlayout = QVBoxLayout()
        vlayout.addWidget(self.group_desc)
        vlayout.addWidget(self.group_code)
        self.html_window = HTMLWindow()
        vlayout.addWidget(self.html_window)

        vlayout.addLayout(hlayout)
        self.setLayout(vlayout)

        self.current_file = None

    def set_status(self):
        self.refresh_button.setEnabled(True)
        self.disable_button.setEnabled(False)
        self.enable_button.setEnabled(False)
        self.save_button.setEnabled(False)

    def set_item(self, check):
        self.refresh_button.setEnabled(False)
        self.save_button.setEnabled(True)
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
        self.save_button.setEnabled(True)
        self.refresh_button.setEnabled(False)
        self.current_file = datadog_conf
        self.desc_label.setText(datadog_conf.get_description())
        self.editor.set_text_from_file(datadog_conf.file_path)
        datadog_conf.content = self.editor.toPlainText().__str__()
        self.disable_button.setEnabled(False)
        self.enable_button.setEnabled(False)
        datadog_conf.check_api_key(self.editor)

    def set_log_file(self, log_file):
        self.save_button.setEnabled(False)
        self.refresh_button.setEnabled(True)
        self.disable_button.setEnabled(False)
        self.enable_button.setEnabled(False)
        try:
            self.current_file = log_file
            self.desc_label.setText(log_file.get_description())
            self.editor.set_text_from_file(log_file.file_path)
            log_file.content = self.editor.toPlainText().__str__()
            self.editor.go_to_line(len(log_file.content.splitlines()))
        except Exception:
            self.editor.set_text("Log file not found")

class HTMLWindow(QTextEdit):
    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)
        self.setReadOnly(True)
        self.setHtml(self.latest_status())

    def latest_status(self):
        try:
            loaded_template = template.Loader(".")
            dogstatsd_status = DogstatsdStatus.load_latest_status()
            forwarder_status = ForwarderStatus.load_latest_status()
            collector_status = CollectorStatus.load_latest_status()
            generated_template = loaded_template.load("status.html").generate(
                port=22,
                platform=platform.platform(),
                agent_version=get_version(),
                python_version=platform.python_version(),
                logger_info=logger_info(),
                dogstatsd=dogstatsd_status.to_dict(),
                forwarder=forwarder_status.to_dict(),
                collector=collector_status.to_dict(),
            )
            return generated_template
        except Exception:
            return ("Unable to fetch latest status")


class MainWindow(QSplitter):
    def __init__(self, parent=None):

        QSplitter.__init__(self, parent)
        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.setWindowIcon(get_icon("agent.svg"))

        self.sysTray = SystemTray(self)

        self.connect(self.sysTray, SIGNAL("activated(QSystemTrayIcon::ActivationReason)"), self.__icon_activated)

        checks = get_checks()
        datadog_conf = DatadogConf(get_config_path(), description="Agent settings file: datadog.conf")

        self.forwarder_log_file = ForwarderLogFile()
        self.collector_log_file = CollectorLogFile()
        self.dogstatsd_log_file = DogstatsdLogFile()
        self.jmxfetch_log_file = JMXFetchLogFile()

        listwidget = QListWidget(self)
        listwidget.addItems([osp.basename(check.module_name).replace("_", " ").title() for check in checks])

        self.properties = PropertiesWidget(self)

        self.setting_button = QPushButton(get_icon("info.png"),
                                      "Logs and Status", self)
        self.menu_button = QPushButton(get_icon("settings.png"),
                                      "Actions", self)
        self.settings = [
            ("Forwarder Logs", lambda: [self.properties.set_log_file(self.forwarder_log_file),
                self.show_html(self.properties.group_code, self.properties.html_window, False)]),
            ("Collector Logs", lambda: [self.properties.set_log_file(self.collector_log_file),
                self.show_html(self.properties.group_code, self.properties.html_window, False)]),
            ("Dogstatsd Logs", lambda: [self.properties.set_log_file(self.dogstatsd_log_file),
                self.show_html(self.properties.group_code, self.properties.html_window, False)]),
            ("JMX Fetch Logs", lambda: [self.properties.set_log_file(self.jmxfetch_log_file),
                self.show_html(self.properties.group_code, self.properties.html_window, False)]),
            ("Agent Status", lambda: [self.properties.html_window.setHtml(self.properties.html_window.latest_status()),
                self.show_html(self.properties.group_code, self.properties.html_window, True),
                self.properties.set_status()]),
        ]

        self.agent_settings = QPushButton(get_icon("edit.png"),
                                      "Settings", self)
        self.connect(self.agent_settings, SIGNAL("clicked()"),
            lambda: [self.properties.set_datadog_conf(datadog_conf),
                self.show_html(self.properties.group_code, self.properties.html_window, False)])

        self.setting_menu = SettingMenu(self.settings)
        self.connect(self.setting_button, SIGNAL("clicked()"),
            lambda: self.setting_menu.popup(self.setting_button.mapToGlobal(QPoint(0,0))))

        self.manager_menu = Menu(self)
        self.connect(self.menu_button, SIGNAL("clicked()"),
            lambda: self.manager_menu.popup(self.menu_button.mapToGlobal(QPoint(0,0))))

        holdingBox = QGroupBox("", self)
        Box = QVBoxLayout(self)
        Box.addWidget(self.agent_settings)
        Box.addWidget(self.setting_button)
        Box.addWidget(self.menu_button)
        Box.addWidget(listwidget)
        holdingBox.setLayout(Box)

        self.addWidget(holdingBox)
        self.addWidget(self.properties)

        self.connect(self.properties.enable_button, SIGNAL("clicked()"),
                     lambda: enable_check(self.properties))

        self.connect(self.properties.disable_button, SIGNAL("clicked()"),
                     lambda: disable_check(self.properties))

        self.connect(self.properties.save_button, SIGNAL("clicked()"),
                     lambda: save_file(self.properties))

        self.connect(self.properties.refresh_button, SIGNAL("clicked()"),
                     lambda: [self.properties.set_log_file(self.properties.current_file),
                     self.properties.html_window.setHtml(self.properties.html_window.latest_status())])

        self.connect(listwidget, SIGNAL('currentRowChanged(int)'),
                     lambda row: [self.properties.set_item(checks[row]),
                     self.show_html(self.properties.group_code, self.properties.html_window, False)])

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
        finally:
            QTimer.singleShot(REFRESH_PERIOD, self.do_refresh)

    def closeEvent(self, event):
        self.hide()
        self.sysTray.show()
        event.ignore()

    def __icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()

    def show_html(self, editor, html, state):
        if state is True:
            editor.setVisible(False)
            html.setVisible(True)
        else:
            editor.setVisible(True)
            html.setVisible(False)

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

class SettingMenu(QMenu):

    def __init__(self, settings, parent=None,):
        QMenu.__init__(self, parent)
        self.options = {}

        for name, action in settings:
            menu_action = self.addAction(name)
            self.connect(menu_action, SIGNAL('triggered()'), action)
            self.options[name] = menu_action


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
    if status is None:
        status = get_service_status()
    return status == win32service.SERVICE_RUNNING

def is_service_pending(status = None):
    if status is None:
        status = get_service_status()
    return status in [win32service.SERVICE_STOP_PENDING, win32service.SERVICE_START_PENDING]

def is_service_stopped(status = None):
    if status is None:
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
