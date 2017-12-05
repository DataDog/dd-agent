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
    var loginStatus: Bool!
    var updatingAgent: Bool!
    var loginStatusEnableTitle = "Enable at login"
    var loginStatusDisableTitle = "Disable at login"

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
        loginItem = NSMenuItem(title: loginStatusEnableTitle, action: #selector(loginAction), keyEquivalent: "")
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

        // Find and load tray image
        var imagePath = "./agent.png"
        if !FileManager.default.isReadableFile(atPath: imagePath) {
            // fall back to image in applications dir
            imagePath = "/Applications/Datadog Agent.app/Contents/Resources/agent.png"
        }
        let ddImage = NSImage(byReferencingFile: imagePath)

        // Create tray icon and set it up
        systemTrayItem = NSStatusBar.system().statusItem(withLength: NSVariableStatusItemLength)
        systemTrayItem!.menu = ddMenu
        if ddImage!.isValid {
            ddImage!.size = NSMakeSize(15, 15)
            systemTrayItem!.button!.image = ddImage
        } else {
            systemTrayItem!.button!.title = "DD"
        }
    }

    override func validateMenuItem(_ menuItem: NSMenuItem) -> Bool {
        // Count to check only once agent status
        if (self.countUpdate >= 5){
            if (self.updatingAgent){
                disableActionItems()
            }
            else {
                self.countUpdate = 0
                DispatchQueue.global().async {
                    self.agentStatus = AgentManager.status()
                    DispatchQueue.main.async(execute: {
                        self.updateMenuItems(agentStatus: self.agentStatus)
                        })
                    }
                }
            }

        self.countUpdate += 1

        return menuItem.isEnabled
    }

    func run() {
        // Initialising
        agentStatus = AgentManager.status()
        loginStatus = AgentManager.getLoginStatus()
        updateLoginItem()
        updatingAgent = false
        NSApp.run()
    }

    func disableActionItems(){
        startItem.isEnabled = false
        stopItem.isEnabled = false
        restartItem.isEnabled = false
    }

    func updateMenuItems(agentStatus: Bool) {
        versionItem!.title = "Datadog Agent"
        startItem.isEnabled = !agentStatus
        stopItem.isEnabled = agentStatus
        restartItem.isEnabled = agentStatus
    }

    func updateLoginItem() {
        loginItem.title = loginStatus! ? loginStatusDisableTitle : loginStatusEnableTitle
    }

    func loginAction(_ sender: Any?) {
        self.loginStatus = AgentManager.switchLoginStatus()
        updateLoginItem()
    }

    func startAgent(_ sender: Any?) {
        self.commandAgent(command: "start", display: "starting")
    }

    func stopAgent(_ sender: Any?) {
        self.commandAgent(command: "stop", display: "stopping")
    }

    func restartAgent(_ sender: Any?) {
        self.commandAgent(command: "restart", display: "restarting")
    }

    func commandAgent(command: String, display: String) {
        self.updatingAgent = true
        versionItem!.title = String(format: "Datadog Agent (%@...)", display)
        DispatchQueue.global().async {
            self.disableActionItems()

            // Sending agent command
            AgentManager.exec(command: command)
            self.agentStatus = AgentManager.status()

            DispatchQueue.main.async(execute: {
                // Updating the menu items after completion
                self.updatingAgent = false
                self.updateMenuItems(agentStatus: self.agentStatus)
            })
        }
    }

    func exitGUI(_ sender: Any?) {
        NSApp.terminate(sender)
    }
}

class AgentManager {
    static let systemEventsCommandFormat = "tell application \"System Events\" to %@"

    static func status() -> Bool {
        return agentCall(command: "status").exitCode == 0
    }

    static func exec(command: String) {
        let processInfo = agentCall(command: command)
        if processInfo.exitCode != 0 {
            NSLog(processInfo.stdOut)
            NSLog(processInfo.stdErr)
        }
    }

    static func agentCall(command: String) -> (exitCode: Int32, stdOut: String, stdErr: String) {
        return call(launchPath: "/usr/local/bin/datadog-agent", arguments: [command])
    }

    static func getLoginStatus() -> Bool {
        let processInfo = systemEventsCall(command: "get the path of every login item whose name is \"Datadog Agent\"")
        return processInfo.stdOut.contains("Datadog")
    }

    static func switchLoginStatus() -> Bool {
        let currentLoginStatus = getLoginStatus()
        var command: String
        if currentLoginStatus { // enabled -> disable
            command = "delete every login item whose name is \"Datadog Agent\""
        } else { // disabled -> enable
            command = "make login item at end with properties {path:\"/Applications/Datadog Agent.app\", name:\"Datadog Agent\", hidden:false}"
        }
        let processInfo = systemEventsCall(command: command)
        if processInfo.exitCode != 0 {
            NSLog(processInfo.stdOut)
            NSLog(processInfo.stdErr)
            return currentLoginStatus
        }

        return !currentLoginStatus
    }

    static func systemEventsCall(command: String) -> (exitCode: Int32, stdOut: String, stdErr: String) {
        return call(launchPath: "/usr/bin/osascript", arguments: ["-e", String(format: systemEventsCommandFormat, command)])
    }

    static func call(launchPath: String, arguments: [String]) -> (exitCode: Int32, stdOut: String, stdErr: String) {
        let stdOutPipe = Pipe()
        let stdErrPipe = Pipe()
        let process = Process()
        process.launchPath = launchPath
        process.arguments = arguments
        process.standardOutput = stdOutPipe
        process.standardError = stdErrPipe
        process.launch()
        process.waitUntilExit()
        let stdOut = String(data: stdOutPipe.fileHandleForReading.readDataToEndOfFile(), encoding: String.Encoding.utf8)
        let stdErr = String(data: stdErrPipe.fileHandleForReading.readDataToEndOfFile(), encoding: String.Encoding.utf8)

        return (process.terminationStatus, stdOut!, stdErr!)
    }
}
