import SwiftUI

@main
struct TwizzyApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var agentService = AgentService.shared

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(agentService)
        }
        .windowStyle(.hiddenTitleBar)
        .windowResizability(.contentMinSize)

        // Menu bar widget
        MenuBarExtra("TWIZZY", systemImage: agentService.isConnected ? "brain.head.profile" : "brain.head.profile.slash") {
            MenuBarView()
                .environmentObject(agentService)
        }
        .menuBarExtraStyle(.window)

        // Settings window
        Settings {
            SettingsView()
                .environmentObject(agentService)
        }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Start the agent service connection
        Task {
            await AgentService.shared.connect()
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        // Cleanup
        AgentService.shared.disconnect()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return false // Keep running in menu bar
    }
}
