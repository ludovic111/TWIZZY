import SwiftUI

struct ContentView: View {
    @EnvironmentObject var agentService: AgentService
    @State private var selectedTab: Tab = .chat

    enum Tab {
        case chat
        case permissions
        case improvements
    }

    var body: some View {
        NavigationSplitView {
            // Sidebar
            List(selection: $selectedTab) {
                NavigationLink(value: Tab.chat) {
                    Label("Chat", systemImage: "bubble.left.and.bubble.right")
                }

                NavigationLink(value: Tab.permissions) {
                    Label("Permissions", systemImage: "lock.shield")
                }

                NavigationLink(value: Tab.improvements) {
                    Label("Improvements", systemImage: "sparkles")
                }
            }
            .listStyle(.sidebar)
            .navigationSplitViewColumnWidth(min: 180, ideal: 200)

        } detail: {
            // Main content
            switch selectedTab {
            case .chat:
                ChatView()
            case .permissions:
                PermissionsView()
            case .improvements:
                ImprovementsView()
            }
        }
        .frame(minWidth: 800, minHeight: 600)
        .toolbar {
            ToolbarItem(placement: .status) {
                HStack(spacing: 8) {
                    Circle()
                        .fill(agentService.isConnected ? Color.green : Color.red)
                        .frame(width: 8, height: 8)
                    Text(agentService.isConnected ? "Connected" : "Disconnected")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
    }
}

// Placeholder for improvements view
struct ImprovementsView: View {
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "sparkles")
                .font(.system(size: 60))
                .foregroundColor(.purple)

            Text("Self-Improvement")
                .font(.title)

            Text("When the agent is idle, it analyzes your usage patterns\nand improves itself automatically.")
                .multilineTextAlignment(.center)
                .foregroundColor(.secondary)

            // TODO: Show improvement history
            Text("Improvement history coming soon...")
                .foregroundColor(.secondary)
                .padding()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

#Preview {
    ContentView()
        .environmentObject(AgentService.shared)
}
