import SwiftUI

struct ChatView: View {
    @EnvironmentObject var agentService: AgentService
    @State private var inputText = ""
    @FocusState private var isInputFocused: Bool

    var body: some View {
        VStack(spacing: 0) {
            // Messages list
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 16) {
                        ForEach(agentService.messages) { message in
                            MessageBubble(message: message)
                                .id(message.id)
                        }
                    }
                    .padding()
                }
                .onChange(of: agentService.messages.count) { _, _ in
                    // Scroll to bottom when new message arrives
                    if let lastMessage = agentService.messages.last {
                        withAnimation {
                            proxy.scrollTo(lastMessage.id, anchor: .bottom)
                        }
                    }
                }
            }

            Divider()

            // Input area
            HStack(spacing: 12) {
                TextField("Ask TWIZZY anything...", text: $inputText, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .padding(4)
                    .focused($isInputFocused)
                    .onSubmit {
                        sendMessage()
                    }
                    .disabled(agentService.isLoading)
                    .onAppear {
                        isInputFocused = true
                    }

                Button(action: sendMessage) {
                    if agentService.isLoading {
                        ProgressView()
                            .scaleEffect(0.8)
                            .frame(width: 32, height: 32)
                    } else {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.system(size: 32))
                            .foregroundColor(inputText.isEmpty ? .gray : .accentColor)
                    }
                }
                .buttonStyle(.plain)
                .disabled(inputText.isEmpty || agentService.isLoading)
            }
            .padding()
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button(action: {
                    Task {
                        await agentService.clearConversation()
                    }
                }) {
                    Label("Clear", systemImage: "trash")
                }
            }
        }
    }

    private func sendMessage() {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        inputText = ""
        Task {
            await agentService.sendMessage(text)
        }
    }
}

struct MessageBubble: View {
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            if message.role == .user {
                Spacer(minLength: 60)
            }

            // Avatar
            if message.role == .assistant {
                Image(systemName: "brain.head.profile")
                    .font(.title2)
                    .foregroundColor(.purple)
                    .frame(width: 32, height: 32)
            }

            // Message content
            VStack(alignment: message.role == .user ? .trailing : .leading, spacing: 4) {
                Text(message.content)
                    .textSelection(.enabled)
                    .padding(12)
                    .background(message.role == .user ? Color.accentColor : Color(.controlBackgroundColor))
                    .foregroundColor(message.role == .user ? .white : .primary)
                    .cornerRadius(16)

                if message.isStreaming {
                    HStack(spacing: 4) {
                        ProgressView()
                            .scaleEffect(0.5)
                        Text("Thinking...")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }

            // User avatar
            if message.role == .user {
                Image(systemName: "person.circle.fill")
                    .font(.title2)
                    .foregroundColor(.accentColor)
                    .frame(width: 32, height: 32)
            }

            if message.role == .assistant {
                Spacer(minLength: 60)
            }
        }
    }
}

#Preview {
    ChatView()
        .environmentObject(AgentService.shared)
}
