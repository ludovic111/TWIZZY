import Foundation
import Combine

/// Main service for managing agent communication
@MainActor
class AgentService: ObservableObject {
    static let shared = AgentService()

    @Published var isConnected = false
    @Published var messages: [ChatMessage] = []
    @Published var status: AgentStatus?
    @Published var permissions: PermissionsConfig = .default
    @Published var isLoading = false
    @Published var error: String?

    private let bridge = AgentBridge()
    private var statusTimer: Timer?

    private init() {
        // Add welcome message
        messages.append(ChatMessage(
            role: .assistant,
            content: "Hello! I'm TWIZZY, your autonomous Mac assistant. I can help you with terminal commands, file management, and controlling applications. What would you like me to do?"
        ))
    }

    /// Connect to the agent daemon
    func connect() async {
        do {
            try await bridge.connect()
            isConnected = true
            error = nil

            // Fetch initial status
            await refreshStatus()
            await loadPermissions()

            // Start status polling
            startStatusPolling()
        } catch {
            isConnected = false
            self.error = error.localizedDescription
        }
    }

    /// Disconnect from the agent daemon
    func disconnect() {
        Task {
            await bridge.disconnect()
        }
        isConnected = false
        stopStatusPolling()
    }

    /// Send a message to the agent
    func sendMessage(_ text: String) async {
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return
        }

        // Add user message
        let userMessage = ChatMessage(role: .user, content: text)
        messages.append(userMessage)

        // Add placeholder for assistant response
        let placeholderId = UUID()
        let placeholder = ChatMessage(
            id: placeholderId,
            role: .assistant,
            content: "",
            isStreaming: true
        )
        messages.append(placeholder)

        isLoading = true

        do {
            let response = try await bridge.chat(message: text)

            // Update placeholder with actual response
            if let index = messages.firstIndex(where: { $0.id == placeholderId }) {
                messages[index] = ChatMessage(
                    id: placeholderId,
                    role: .assistant,
                    content: response,
                    isStreaming: false
                )
            }
        } catch {
            // Update placeholder with error
            if let index = messages.firstIndex(where: { $0.id == placeholderId }) {
                messages[index] = ChatMessage(
                    id: placeholderId,
                    role: .assistant,
                    content: "Sorry, I encountered an error: \(error.localizedDescription)",
                    isStreaming: false
                )
            }
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    /// Clear conversation history
    func clearConversation() async {
        do {
            try await bridge.clearConversation()
            messages.removeAll()
            messages.append(ChatMessage(
                role: .assistant,
                content: "Conversation cleared. How can I help you?"
            ))
        } catch {
            self.error = error.localizedDescription
        }
    }

    /// Refresh agent status
    func refreshStatus() async {
        do {
            status = try await bridge.getStatus()
        } catch {
            // Silently fail status updates
        }
    }

    /// Load permissions from agent
    func loadPermissions() async {
        do {
            permissions = try await bridge.getPermissions()
        } catch {
            // Use defaults if loading fails
        }
    }

    /// Save permissions to agent
    func savePermissions() async {
        do {
            try await bridge.setPermissions(permissions)
        } catch {
            self.error = error.localizedDescription
        }
    }

    /// Toggle a capability on/off
    func toggleCapability(_ name: String) async {
        if var cap = permissions.capabilities[name] {
            cap.enabled.toggle()
            permissions.capabilities[name] = cap
            await savePermissions()
        }
    }

    // MARK: - Private

    private func startStatusPolling() {
        statusTimer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                await self?.refreshStatus()
            }
        }
    }

    private func stopStatusPolling() {
        statusTimer?.invalidate()
        statusTimer = nil
    }
}
