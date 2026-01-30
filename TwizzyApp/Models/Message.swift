import Foundation

/// A chat message in the conversation
struct ChatMessage: Identifiable, Equatable {
    let id: UUID
    let role: Role
    let content: String
    let timestamp: Date
    var isStreaming: Bool

    enum Role: String, Codable {
        case user
        case assistant
        case system
    }

    init(
        id: UUID = UUID(),
        role: Role,
        content: String,
        timestamp: Date = Date(),
        isStreaming: Bool = false
    ) {
        self.id = id
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.isStreaming = isStreaming
    }
}

/// Status response from the agent
struct AgentStatus: Codable {
    let running: Bool
    let enabledCapabilities: [String]
    let registeredPlugins: [String]
    let conversationLength: Int

    enum CodingKeys: String, CodingKey {
        case running
        case enabledCapabilities = "enabled_capabilities"
        case registeredPlugins = "registered_plugins"
        case conversationLength = "conversation_length"
    }
}

/// Permissions configuration
struct PermissionsConfig: Codable {
    var capabilities: [String: CapabilityConfig]

    struct CapabilityConfig: Codable {
        var enabled: Bool
        var restrictions: Restrictions

        struct Restrictions: Codable {
            var allowSudo: Bool?
            var blockedCommands: [String]?
            var allowedPaths: [String]?
            var blockedPaths: [String]?
            var allowedApps: [String]?
            var blockedApps: [String]?

            enum CodingKeys: String, CodingKey {
                case allowSudo = "allow_sudo"
                case blockedCommands = "blocked_commands"
                case allowedPaths = "allowed_paths"
                case blockedPaths = "blocked_paths"
                case allowedApps = "allowed_apps"
                case blockedApps = "blocked_apps"
            }
        }
    }

    static var `default`: PermissionsConfig {
        PermissionsConfig(capabilities: [
            "terminal": CapabilityConfig(
                enabled: true,
                restrictions: .init(
                    allowSudo: false,
                    blockedCommands: ["rm -rf", "shutdown"],
                    allowedPaths: nil,
                    blockedPaths: nil,
                    allowedApps: nil,
                    blockedApps: nil
                )
            ),
            "filesystem": CapabilityConfig(
                enabled: true,
                restrictions: .init(
                    allowSudo: nil,
                    blockedCommands: nil,
                    allowedPaths: ["~/Documents", "~/Desktop", "~/Downloads"],
                    blockedPaths: ["~/.ssh", "~/.aws"],
                    allowedApps: nil,
                    blockedApps: nil
                )
            ),
            "applications": CapabilityConfig(
                enabled: true,
                restrictions: .init(
                    allowSudo: nil,
                    blockedCommands: nil,
                    allowedPaths: nil,
                    blockedPaths: nil,
                    allowedApps: ["*"],
                    blockedApps: ["System Preferences"]
                )
            )
        ])
    }
}
