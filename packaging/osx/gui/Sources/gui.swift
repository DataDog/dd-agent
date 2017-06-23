import Cocoa

class AgentGUI: NSObject {
    var systemTrayItem: NSStatusItem!
    var ddMenu: NSMenu!
    var versionItem: NSMenuItem!
    var startItem: NSMenuItem!
    var stopItem: NSMenuItem!
    var restartItem: NSMenuItem!
    var loginItem: NSMenuItem!
    var exitItem: NSMenuItem!
    var countUpdate: Int
    var agentStatus: Bool!


    override init() {
        // initialising at for update
        countUpdate = 10

        super.init()

        NSApplication.shared()

        ddMenu = NSMenu(title: "Menu")
        ddMenu.autoenablesItems = true

        // Create menu items
        versionItem = NSMenuItem(title: "Datadog Agent", action: nil, keyEquivalent: "")
        versionItem.isEnabled = false
        startItem = NSMenuItem(title: "Start", action: #selector(startAgent), keyEquivalent: "")
        startItem.target = self
        stopItem = NSMenuItem(title: "Stop", action: #selector(stopAgent), keyEquivalent: "")
        stopItem.target = self
        restartItem = NSMenuItem(title: "Restart", action: #selector(restartAgent), keyEquivalent: "")
        restartItem.target = self
        loginItem = NSMenuItem(title: "Enable at login", action: nil, keyEquivalent: "")
        loginItem.target = self
        exitItem = NSMenuItem(title: "Exit", action: #selector(exitGUI), keyEquivalent: "")
        exitItem.target = self

        ddMenu.addItem(versionItem)
        ddMenu.addItem(NSMenuItem.separator())
        ddMenu.addItem(startItem)
        ddMenu.addItem(stopItem)
        ddMenu.addItem(restartItem)
        ddMenu.addItem(loginItem)
        ddMenu.addItem(exitItem)

        // Create tray icon
        systemTrayItem = NSStatusBar.system().statusItem(withLength: NSVariableStatusItemLength)
        systemTrayItem!.button!.title = "DD"

        systemTrayItem!.menu = ddMenu
    }

    override func validateMenuItem(_ menuItem: NSMenuItem) -> Bool {
        // Count to check only once agent status
        if (countUpdate >= 4){
            countUpdate = 0
            agentStatus = AgentManager.status()
        }
        // Update menu items
        if (menuItem == startItem) {
            menuItem.isEnabled = !agentStatus
        }
        if (menuItem == stopItem) {
            menuItem.isEnabled = agentStatus
        }
        if (menuItem == restartItem) {
            menuItem.isEnabled = agentStatus
        }
        countUpdate += 1

        return menuItem.isEnabled
    }

    func run() {
        print("run_start")
        agentStatus = AgentManager.status()
        NSApp.run()
    }

    func updateMenuItems(agentStatus: Bool) {
        startItem.isEnabled = !agentStatus
        stopItem.isEnabled = agentStatus
        restartItem.isEnabled = agentStatus
    }

    func startAgent(_ sender: Any?) {
        AgentManager.exec(command: "start")
        updateMenuItems(agentStatus: true)
    }

    func stopAgent(_ sender: Any?) {
        AgentManager.exec(command: "stop")
        updateMenuItems(agentStatus: false)
    }

    func restartAgent(_ sender: Any?) {
        AgentManager.exec(command: "restart")
        updateMenuItems(agentStatus: true)
    }

    func exitGUI(_ sender: Any?) {
        NSApp.terminate(sender)
    }
}

class AgentManager {
    var countUpdate: Int!
    var agentStatus: Bool!

    static func status() -> Bool {
        return call(command: "status").exitCode == 0
    }

    static func exec(command: String) {
        let processInfo = call(command: command)
        if processInfo.exitCode != 0 {
            NSLog(processInfo.stdOut)
            NSLog(processInfo.stdErr)
        }
    }

    static func call(command: String) -> (exitCode: Int32, stdOut: String, stdErr: String) {
        let stdOutPipe = Pipe()
        let stdErrPipe = Pipe()
        let process = Process()
        process.launchPath = "/usr/local/bin/datadog-agent"
        process.arguments = [command]
        process.standardOutput = stdOutPipe
        process.standardError = stdErrPipe
        process.launch()
        process.waitUntilExit()
        let stdOut = String(data: stdOutPipe.fileHandleForReading.readDataToEndOfFile(), encoding: String.Encoding.utf8)
        let stdErr = String(data: stdErrPipe.fileHandleForReading.readDataToEndOfFile(), encoding: String.Encoding.utf8)

        return (process.terminationStatus, stdOut!, stdErr!)
    }
}
