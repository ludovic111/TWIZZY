import Foundation

/// JSON-RPC client for communicating with the Python agent daemon
actor AgentBridge {
    private let socketPath: String
    private var socketFd: Int32 = -1
    private var requestId: Int = 0

    init(socketPath: String = "/tmp/twizzy.sock") {
        self.socketPath = socketPath
    }

    /// Connect to the agent daemon
    func connect() async throws {
        // Create Unix socket
        let sock = socket(AF_UNIX, SOCK_STREAM, 0)
        guard sock >= 0 else {
            throw BridgeError.connectionFailed("Failed to create socket")
        }

        var addr = sockaddr_un()
        addr.sun_family = sa_family_t(AF_UNIX)

        // Copy socket path
        let pathBytes = socketPath.utf8CString
        withUnsafeMutablePointer(to: &addr.sun_path) { ptr in
            let boundPtr = UnsafeMutableRawPointer(ptr).assumingMemoryBound(to: CChar.self)
            for (index, byte) in pathBytes.enumerated() {
                boundPtr[index] = byte
            }
        }

        let connectResult = withUnsafePointer(to: &addr) { ptr in
            ptr.withMemoryRebound(to: sockaddr.self, capacity: 1) { sockaddrPtr in
                Darwin.connect(sock, sockaddrPtr, socklen_t(MemoryLayout<sockaddr_un>.size))
            }
        }

        guard connectResult == 0 else {
            close(sock)
            throw BridgeError.connectionFailed("Failed to connect to socket: \(String(cString: strerror(errno)))")
        }

        socketFd = sock
    }

    /// Check if connected
    var isConnected: Bool {
        return socketFd >= 0
    }

    /// Disconnect from the agent daemon
    func disconnect() {
        if socketFd >= 0 {
            close(socketFd)
            socketFd = -1
        }
    }

    /// Send a JSON-RPC request and get the response
    func call<T: Decodable>(method: String, params: [String: Any] = [:]) async throws -> T {
        guard socketFd >= 0 else {
            throw BridgeError.notConnected
        }

        requestId += 1
        let id = requestId

        // Build JSON-RPC request
        let request: [String: Any] = [
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": id
        ]

        let data = try JSONSerialization.data(withJSONObject: request)
        var requestData = data
        requestData.append(contentsOf: "\n".utf8)

        // Send request
        let sendResult = requestData.withUnsafeBytes { buffer in
            send(socketFd, buffer.baseAddress, buffer.count, 0)
        }
        guard sendResult >= 0 else {
            throw BridgeError.connectionFailed("Failed to send: \(String(cString: strerror(errno)))")
        }

        // Read response - use a buffer and read until newline
        var responseBuffer = Data()
        var readBuffer = [UInt8](repeating: 0, count: 4096)

        while true {
            let bytesRead = recv(socketFd, &readBuffer, readBuffer.count, 0)
            if bytesRead <= 0 {
                if bytesRead == 0 {
                    throw BridgeError.noResponse
                }
                throw BridgeError.connectionFailed("Read error: \(String(cString: strerror(errno)))")
            }

            responseBuffer.append(contentsOf: readBuffer[0..<bytesRead])

            // Check for newline (end of JSON-RPC message)
            if responseBuffer.contains(0x0A) { // newline
                break
            }
        }

        // Parse response
        guard let response = try JSONSerialization.jsonObject(with: responseBuffer) as? [String: Any] else {
            throw BridgeError.invalidResponse
        }

        if let error = response["error"] as? [String: Any] {
            let message = error["message"] as? String ?? "Unknown error"
            throw BridgeError.rpcError(message)
        }

        guard let result = response["result"] else {
            throw BridgeError.noResult
        }

        // Convert result to expected type
        let resultData: Data
        if let stringResult = result as? String {
            // Handle plain string results (e.g., chat response)
            // For String type, return directly without JSON encoding
            if T.self == String.self {
                return stringResult as! T
            }
            // For other types, wrap in array to make valid JSON
            resultData = try JSONSerialization.data(withJSONObject: [stringResult])
        } else {
            // Handle dict/array results
            resultData = try JSONSerialization.data(withJSONObject: result)
        }
        return try JSONDecoder().decode(T.self, from: resultData)
    }

    /// Send a chat message and get the response
    func chat(message: String) async throws -> String {
        return try await call(method: "chat", params: ["user_message": message])
    }

    /// Get agent status
    func getStatus() async throws -> AgentStatus {
        return try await call(method: "status")
    }

    /// Clear conversation
    func clearConversation() async throws {
        let _: [String: String] = try await call(method: "clear")
    }

    /// Get permissions
    func getPermissions() async throws -> PermissionsConfig {
        return try await call(method: "get_permissions")
    }

    /// Update permissions
    func setPermissions(_ permissions: PermissionsConfig) async throws {
        let encoder = JSONEncoder()
        let data = try encoder.encode(permissions)
        let dict = try JSONSerialization.jsonObject(with: data) as! [String: Any]
        let _: SetPermissionsResponse = try await call(method: "set_permissions", params: ["permissions": dict])
    }
}

struct SetPermissionsResponse: Decodable {
    let success: Bool
    let error: String?
}

enum BridgeError: LocalizedError {
    case notConnected
    case connectionFailed(String)
    case noResponse
    case invalidResponse
    case noResult
    case rpcError(String)

    var errorDescription: String? {
        switch self {
        case .notConnected:
            return "Not connected to agent"
        case .connectionFailed(let reason):
            return "Connection failed: \(reason)"
        case .noResponse:
            return "No response from agent"
        case .invalidResponse:
            return "Invalid response format"
        case .noResult:
            return "No result in response"
        case .rpcError(let message):
            return "RPC error: \(message)"
        }
    }
}
