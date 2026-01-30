import SwiftUI

struct PermissionsView: View {
    @EnvironmentObject var agentService: AgentService
    @State private var showingRestrictions: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                // Header
                VStack(alignment: .leading, spacing: 8) {
                    Text("Permissions")
                        .font(.largeTitle)
                        .fontWeight(.bold)

                    Text("Control what TWIZZY can access on your Mac")
                        .foregroundColor(.secondary)
                }
                .padding(.bottom)

                // Capability toggles
                ForEach(Array(agentService.permissions.capabilities.keys.sorted()), id: \.self) { key in
                    if let capability = agentService.permissions.capabilities[key] {
                        CapabilityCard(
                            name: key,
                            capability: capability,
                            isExpanded: showingRestrictions == key,
                            onToggle: {
                                Task {
                                    await agentService.toggleCapability(key)
                                }
                            },
                            onExpandToggle: {
                                withAnimation {
                                    showingRestrictions = showingRestrictions == key ? nil : key
                                }
                            }
                        )
                    }
                }

                Spacer()
            }
            .padding(24)
        }
    }
}

struct CapabilityCard: View {
    let name: String
    let capability: PermissionsConfig.CapabilityConfig
    let isExpanded: Bool
    let onToggle: () -> Void
    let onExpandToggle: () -> Void

    var icon: String {
        switch name {
        case "terminal": return "terminal"
        case "filesystem": return "folder"
        case "applications": return "app.badge"
        case "browser": return "globe"
        case "system": return "gearshape"
        case "ui_control": return "hand.tap"
        default: return "questionmark.circle"
        }
    }

    var description: String {
        switch name {
        case "terminal": return "Execute shell commands in Terminal"
        case "filesystem": return "Read, write, and manage files"
        case "applications": return "Launch, quit, and control apps"
        case "browser": return "Automate web browser"
        case "system": return "Change system settings"
        case "ui_control": return "Control mouse and keyboard"
        default: return ""
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Main toggle row
            HStack(spacing: 16) {
                Image(systemName: icon)
                    .font(.title2)
                    .foregroundColor(capability.enabled ? .accentColor : .gray)
                    .frame(width: 40, height: 40)
                    .background(capability.enabled ? Color.accentColor.opacity(0.1) : Color.gray.opacity(0.1))
                    .cornerRadius(8)

                VStack(alignment: .leading, spacing: 4) {
                    Text(name.capitalized.replacingOccurrences(of: "_", with: " "))
                        .font(.headline)

                    Text(description)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                Spacer()

                Toggle("", isOn: Binding(
                    get: { capability.enabled },
                    set: { _ in onToggle() }
                ))
                .labelsHidden()

                Button(action: onExpandToggle) {
                    Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding(16)

            // Restrictions detail (expanded)
            if isExpanded {
                Divider()

                VStack(alignment: .leading, spacing: 12) {
                    Text("Restrictions")
                        .font(.subheadline)
                        .fontWeight(.medium)

                    RestrictionsDetail(name: name, restrictions: capability.restrictions)
                }
                .padding(16)
                .background(Color(.controlBackgroundColor))
            }
        }
        .background(Color(.textBackgroundColor))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.1), radius: 2, y: 1)
    }
}

struct RestrictionsDetail: View {
    let name: String
    let restrictions: PermissionsConfig.CapabilityConfig.Restrictions

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            switch name {
            case "terminal":
                if let allowSudo = restrictions.allowSudo {
                    RestrictionRow(icon: "lock.shield", text: "sudo commands", allowed: allowSudo)
                }
                if let blocked = restrictions.blockedCommands, !blocked.isEmpty {
                    RestrictionRow(icon: "xmark.circle", text: "Blocked: \(blocked.joined(separator: ", "))", allowed: false)
                }

            case "filesystem":
                if let allowed = restrictions.allowedPaths, !allowed.isEmpty {
                    RestrictionRow(icon: "checkmark.circle", text: "Allowed paths: \(allowed.joined(separator: ", "))", allowed: true)
                }
                if let blocked = restrictions.blockedPaths, !blocked.isEmpty {
                    RestrictionRow(icon: "xmark.circle", text: "Blocked paths: \(blocked.joined(separator: ", "))", allowed: false)
                }

            case "applications":
                if let allowed = restrictions.allowedApps, !allowed.isEmpty {
                    if allowed == ["*"] {
                        RestrictionRow(icon: "checkmark.circle", text: "All applications allowed", allowed: true)
                    } else {
                        RestrictionRow(icon: "checkmark.circle", text: "Allowed apps: \(allowed.joined(separator: ", "))", allowed: true)
                    }
                }
                if let blocked = restrictions.blockedApps, !blocked.isEmpty {
                    RestrictionRow(icon: "xmark.circle", text: "Blocked apps: \(blocked.joined(separator: ", "))", allowed: false)
                }

            default:
                Text("No restrictions configured")
                    .foregroundColor(.secondary)
            }
        }
    }
}

struct RestrictionRow: View {
    let icon: String
    let text: String
    let allowed: Bool

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .foregroundColor(allowed ? .green : .red)
            Text(text)
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }
}

#Preview {
    PermissionsView()
        .environmentObject(AgentService.shared)
}
