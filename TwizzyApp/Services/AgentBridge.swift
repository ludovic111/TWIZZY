import Foundation

/// JSON-RPC client for communicating with the Python agent daemon
actor AgentBridge {
    private let socketPath: String
    private var connection: FileHandle?
    private var inputStream: InputStream?
    private var outputStream: OutputStream?
    private var requestId: Int = 0
    private var pendingRequests: [Int: CheckedContinuation<Data, Error>] = [:]

    init(socketPath: String = "/tmp/twizzy.sock") {
        self.socketPath = socketPath
    }

    /// Connect to the agent daemon
    func connect() async throws {
        // Create Unix socket streams
        var readStream: Unmanaged<CFReadStream>?
        var writeStream: Unmanaged<CFWriteStream>?

        CFStreamCreatePairWithSocketToHost(
            nil,
            "localhost" as CFString, // Placeholder, we'll use Unix socket
            0,
            &readStream,
            &writeStream
        )

        // For Unix socket, we need a different approach
        // Using FileHandle with socket
        let socket = socket(AF_UNIX, SOCK_STREAM, 0)
        guard socket >= 0 else {
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
                Darwin.connect(socket, sockaddrPtr, socklen_t(MemoryLayout<sockaddr_un>.size))
            }
        }

        guard connectResult == 0 else {
            close(socket)
            throw BridgeError.connectionFailed("Failed to connect to socket: \(String(cString: strerror(errno)))")
        }

        connection = FileHandle(fileDescriptor: socket, closeOnDealloc: true)
    }

    /// Disconnect from the agent daemon
    func disconnect() {
        connection = nil
        pendingRequests.removeAll()
    }

    /// Send a JSON-RPC request and get the response
    func call<T: Decodable>(method: String, params: [String: Any] = [:]) async throws -> T {
        guard let connection = connection else {
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
        try connection.write(contentsOf: requestData)

        // Read response (blocking for now, should be async)
        guard let responseData = try connection.availableData.isEmpty ? nil : connection.availableData else {
            throw BridgeError.noResponse
        }

        // Parse response
        guard let response = try JSONSerialization.jsonObject(with: responseData) as? [String: Any] else {
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
        let resultData = try JSONSerialization.data(withJSONObject: result)
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
        let _: [String: Any] = try await call(method: "set_permissions", params: ["permissions": dict])
    }
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
