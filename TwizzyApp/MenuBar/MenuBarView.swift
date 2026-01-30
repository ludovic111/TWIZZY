import SwiftUI

struct MenuBarView: View {
    @EnvironmentObject var agentService: AgentService
    @State private var quickInput = ""
    @Environment(\.openWindow) private var openWindow

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Status header
            HStack {
                Image(systemName: "brain.head.profile")
                    .foregroundColor(.purple)
                Text("TWIZZY")
                    .fontWeight(.semibold)
                Spacer()
                Circle()
                    .fill(agentService.isConnected ? Color.green : Color.red)
                    .frame(width: 8, height: 8)
            }
            .padding(.horizontal)

            Divider()

            // Quick input
            HStack {
                TextField("Quick command...", text: $quickInput)
                    .textFieldStyle(.plain)
                    .onSubmit {
                        sendQuickCommand()
                    }

                Button(action: sendQuickCommand) {
                    Image(systemName: "arrow.up.circle.fill")
                        .foregroundColor(quickInput.isEmpty ? .gray : .accentColor)
                }
                .buttonStyle(.plain)
                .disabled(quickInput.isEmpty)
            }
            .padding(.horizontal)

            // Recent messages preview
            if let lastMessage = agentService.messages.last(where: { $0.role == .assistant }) {
                Divider()

                VStack(alignment: .leading, spacing: 4) {
                    Text("Last response:")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(lastMessage.content)
                        .font(.caption)
                        .lineLimit(3)
                        .foregroundColor(.primary)
                }
                .padding(.horizontal)
            }

            Divider()

            // Actions
            VStack(spacing: 2) {
                MenuBarButton(
                    title: "Open TWIZZY",
                    icon: "rectangle.expand.vertical",
                    action: {
                        NSApp.activate(ignoringOtherApps: true)
                        // Open main window
                        if let window = NSApp.windows.first(where: { $0.title.contains("TWIZZY") || $0.isKeyWindow }) {
                            window.makeKeyAndOrderFront(nil)
                        }
                    }
                )

                MenuBarButton(
                    title: "Clear Conversation",
                    icon: "trash",
                    action: {
                        Task {
                            await agentService.clearConversation()
                        }
                    }
                )

                MenuBarButton(
                    title: "Reconnect",
                    icon: "arrow.triangle.2.circlepath",
                    action: {
                        Task {
                            agentService.disconnect()
                            await agentService.connect()
                        }
                    }
                )

                Divider()
                    .padding(.vertical, 4)

                MenuBarButton(
                    title: "Settings...",
                    icon: "gearshape",
                    shortcut: ",",
                    action: {
                        NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
                    }
                )

                MenuBarButton(
                    title: "Quit TWIZZY",
                    icon: "power",
                    shortcut: "q",
                    action: {
                        NSApp.terminate(nil)
                    }
                )
            }
        }
        .padding(.vertical, 8)
        .frame(width: 280)
    }

    private func sendQuickCommand() {
        guard !quickInput.isEmpty else { return }
        let command = quickInput
        quickInput = ""

        Task {
            await agentService.sendMessage(command)
        }
    }
}

struct MenuBarButton: View {
    let title: String
    let icon: String
    var shortcut: String? = nil
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Image(systemName: icon)
                    .frame(width: 20)
                Text(title)
                Spacer()
                if let shortcut = shortcut {
                    Text("⌘\(shortcut)")
                        .foregroundColor(.secondary)
                        .font(.caption)
                }
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(Color.clear)
        .contentShape(Rectangle())
    }
}

#Preview {
    MenuBarView()
        .environmentObject(AgentService.shared)
}
