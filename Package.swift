// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "TwizzyApp",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "TwizzyApp", targets: ["TwizzyApp"])
    ],
    targets: [
        .executableTarget(
            name: "TwizzyApp",
            path: "TwizzyApp"
        )
    ]
)
