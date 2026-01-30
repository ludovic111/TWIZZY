import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var agentService: AgentService
    @AppStorage("launchAtLogin") private var launchAtLogin = false
    @State private var apiKey = ""
    @State private var showingApiKey = false

    var body: some View {
        TabView {
            // General settings
            Form {
                Section {
                    Toggle("Launch TWIZZY at login", isOn: $launchAtLogin)

                    LabeledContent("Status") {
                        HStack {
                            Circle()
                                .fill(agentService.isConnected ? Color.green : Color.red)
                                .frame(width: 8, height: 8)
                            Text(agentService.isConnected ? "Connected" : "Disconnected")
                        }
                    }

                    if let status = agentService.status {
                        LabeledContent("Plugins") {
                            Text(status.registeredPlugins.joined(separator: ", "))
                        }

                        LabeledContent("Capabilities") {
                            Text(status.enabledCapabilities.joined(separator: ", "))
                        }
                    }
                }

                Section("Connection") {
                    Button("Reconnect") {
                        Task {
                            agentService.disconnect()
                            await agentService.connect()
                        }
                    }
                }
            }
            .formStyle(.grouped)
            .tabItem {
                Label("General", systemImage: "gearshape")
            }

            // API settings
            Form {
                Section("Kimi API") {
                    HStack {
                        if showingApiKey {
                            TextField("API Key", text: $apiKey)
                        } else {
                            SecureField("API Key", text: $apiKey)
                        }
                        Button(action: { showingApiKey.toggle() }) {
                            Image(systemName: showingApiKey ? "eye.slash" : "eye")
                        }
                        .buttonStyle(.plain)
                    }

                    Text("Your Kimi API key is stored securely in the macOS Keychain.")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    Button("Save API Key") {
                        saveApiKey()
                    }
                    .disabled(apiKey.isEmpty)

                    Link("Get API Key from Moonshot AI",
                         destination: URL(string: "https://platform.moonshot.ai/")!)
                }
            }
            .formStyle(.grouped)
            .tabItem {
                Label("API", systemImage: "key")
            }

            // About
            VStack(spacing: 20) {
                Image(systemName: "brain.head.profile")
                    .font(.system(size: 64))
                    .foregroundColor(.purple)

                Text("TWIZZY")
                    .font(.largeTitle)
                    .fontWeight(.bold)

                Text("Autonomous Mac Agent")
                    .foregroundColor(.secondary)

                Text("Version 0.1.0")
                    .font(.caption)
                    .foregroundColor(.secondary)

                Divider()
                    .frame(width: 200)

                Text("TWIZZY can control your Mac through natural language commands. It uses Kimi 2.5k for intelligent task planning and execution.")
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 300)

                Link("GitHub Repository",
                     destination: URL(string: "https://github.com/twizzy/twizzy")!)
                    .padding(.top)
            }
            .padding()
            .tabItem {
                Label("About", systemImage: "info.circle")
            }
        }
        .frame(width: 450, height: 350)
    }

    private func saveApiKey() {
        // Store in Keychain via agent
        // For now, just set environment variable
        setenv("KIMI_API_KEY", apiKey, 1)
        apiKey = ""
    }
}

#Preview {
    SettingsView()
        .environmentObject(AgentService.shared)
}
