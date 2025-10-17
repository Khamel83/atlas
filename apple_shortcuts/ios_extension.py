"""
iOS Share Extension Integration
Templates and configurations for iOS Share Extension with Atlas
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import sys

sys.path.append(str(Path(__file__).parent.parent))
from helpers.config import load_config


@dataclass
class ShareExtensionConfig:
    """Configuration for iOS Share Extension"""

    server_url: str
    api_key: Optional[str] = None
    timeout: int = 30
    offline_storage: bool = True
    auto_categorization: bool = True
    location_capture: bool = True
    background_processing: bool = True
    content_preview: bool = True
    custom_tags: List[str] = None


@dataclass
class IOSTemplate:
    """Template for iOS configuration files"""

    template_type: str  # shortcut, extension, automation
    name: str
    description: str
    content: str
    configuration: Dict[str, Any]
    ios_version: str = "iOS 15.0+"


class IOSShareExtension:
    """iOS Share Extension template generator and configuration manager"""

    def __init__(self, config=None):
        self.config = config or load_config()
        self.templates_dir = Path(__file__).parent / "ios_extension"
        self.templates_dir.mkdir(exist_ok=True)

        # Default server configuration
        self.server_config = {
            "host": self.config.get("server_host", "localhost"),
            "port": self.config.get("server_port", 5000),
            "use_https": self.config.get("use_https", False),
            "api_path": "/api/capture",
        }

    def generate_share_extension_template(self) -> IOSTemplate:
        """Generate iOS Share Extension template configuration"""

        server_url = self._build_server_url()

        # Share Extension Info.plist template
        info_plist = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleDisplayName</key>
    <string>Save to Atlas</string>
    <key>CFBundleExecutable</key>
    <string>$(EXECUTABLE_NAME)</string>
    <key>CFBundleIdentifier</key>
    <string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>$(PRODUCT_NAME)</string>
    <key>CFBundlePackageType</key>
    <string>XPC!</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>NSExtension</key>
    <dict>
        <key>NSExtensionAttributes</key>
        <dict>
            <key>NSExtensionActivationRule</key>
            <dict>
                <key>NSExtensionActivationSupportsText</key>
                <true/>
                <key>NSExtensionActivationSupportsWebURLWithMaxCount</key>
                <integer>1</integer>
                <key>NSExtensionActivationSupportsWebPageWithMaxCount</key>
                <integer>1</integer>
                <key>NSExtensionActivationSupportsImageWithMaxCount</key>
                <integer>5</integer>
                <key>NSExtensionActivationSupportsFileWithMaxCount</key>
                <integer>10</integer>
            </dict>
        </dict>
        <key>NSExtensionMainStoryboard</key>
        <string>MainInterface</string>
        <key>NSExtensionPointIdentifier</key>
        <string>com.apple.share-services</string>
    </dict>
    <key>NSLocationWhenInUseUsageDescription</key>
    <string>Atlas uses location to provide context for your saved content.</string>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
    </dict>
</dict>
</plist>"""

        return IOSTemplate(
            template_type="extension",
            name="Share Extension Info.plist",
            description="iOS Share Extension configuration file",
            content=info_plist,
            configuration={
                "server_url": server_url,
                "bundle_id": "com.atlas.shareextension",
                "display_name": "Save to Atlas",
            },
        )

    def generate_share_extension_code(self) -> IOSTemplate:
        """Generate iOS Share Extension Swift code template"""

        server_url = self._build_server_url()

        swift_code = f"""//
//  ShareViewController.swift
//  Atlas Share Extension
//

import UIKit
import Social
import CoreLocation
import MobileCoreServices

class ShareViewController: SLComposeServiceViewController, CLLocationManagerDelegate {{

    // MARK: - Configuration
    private let serverURL = "{server_url}"
    private let timeout: TimeInterval = 30.0

    // MARK: - Properties
    private var locationManager: CLLocationManager?
    private var currentLocation: CLLocation?
    private var sharedContent: [String: Any] = [:]
    private var isProcessing = false

    // MARK: - Lifecycle
    override func viewDidLoad() {{
        super.viewDidLoad()
        setupLocationManager()
        setupUI()
        extractSharedContent()
    }}

    // MARK: - Setup
    private func setupLocationManager() {{
        locationManager = CLLocationManager()
        locationManager?.delegate = self
        locationManager?.desiredAccuracy = kCLLocationAccuracyBest

        if CLLocationManager.locationServicesEnabled() {{
            switch locationManager?.authorizationStatus {{
            case .notDetermined:
                locationManager?.requestWhenInUseAuthorization()
            case .authorizedWhenInUse, .authorizedAlways:
                locationManager?.requestLocation()
            default:
                break
            }}
        }}
    }}

    private func setupUI() {{
        title = "Save to Atlas"
        placeholder = "Add notes (optional)..."
        charactersRemaining = 280

        // Customize appearance
        navigationController?.navigationBar.tintColor = .systemBlue
    }}

    // MARK: - Content Extraction
    private func extractSharedContent() {{
        guard let extensionItem = extensionContext?.inputItems.first as? NSExtensionItem else {{
            return
        }}

        for attachment in extensionItem.attachments ?? [] {{
            if attachment.hasItemConformingToTypeIdentifier(kUTTypeURL as String) {{
                extractURL(from: attachment)
            }} else if attachment.hasItemConformingToTypeIdentifier(kUTTypeText as String) {{
                extractText(from: attachment)
            }} else if attachment.hasItemConformingToTypeIdentifier(kUTTypeImage as String) {{
                extractImage(from: attachment)
            }} else if attachment.hasItemConformingToTypeIdentifier(kUTTypeFileURL as String) {{
                extractFile(from: attachment)
            }}
        }}
    }}

    private func extractURL(from attachment: NSItemProvider) {{
        attachment.loadItem(forTypeIdentifier: kUTTypeURL as String, options: nil) {{ [weak self] (item, error) in
            guard let url = item as? URL else {{ return }}

            DispatchQueue.main.async {{
                self?.sharedContent["type"] = "url"
                self?.sharedContent["content"] = url.absoluteString
                self?.sharedContent["title"] = url.absoluteString

                // Try to get page title if available
                if let title = self?.extensionContext?.inputItems.first?.attributedTitle?.string,
                   !title.isEmpty {{
                    self?.sharedContent["title"] = title
                }}

                self?.updateUI()
            }}
        }}
    }}

    private func extractText(from attachment: NSItemProvider) {{
        attachment.loadItem(forTypeIdentifier: kUTTypeText as String, options: nil) {{ [weak self] (item, error) in
            guard let text = item as? String else {{ return }}

            DispatchQueue.main.async {{
                self?.sharedContent["type"] = "text"
                self?.sharedContent["content"] = text
                self?.sharedContent["title"] = String(text.prefix(100))
                self?.updateUI()
            }}
        }}
    }}

    private func extractImage(from attachment: NSItemProvider) {{
        attachment.loadItem(forTypeIdentifier: kUTTypeImage as String, options: nil) {{ [weak self] (item, error) in
            DispatchQueue.main.async {{
                self?.sharedContent["type"] = "image"
                self?.sharedContent["content"] = "Image captured from share extension"
                self?.sharedContent["title"] = "Image - \\(Date())"
                // Note: Actual image processing would require additional implementation
                self?.updateUI()
            }}
        }}
    }}

    private func extractFile(from attachment: NSItemProvider) {{
        attachment.loadItem(forTypeIdentifier: kUTTypeFileURL as String, options: nil) {{ [weak self] (item, error) in
            guard let fileURL = item as? URL else {{ return }}

            DispatchQueue.main.async {{
                self?.sharedContent["type"] = "file"
                self?.sharedContent["content"] = fileURL.absoluteString
                self?.sharedContent["title"] = fileURL.lastPathComponent
                self?.updateUI()
            }}
        }}
    }}

    private func updateUI() {{
        // Update the UI with extracted content information
        if let title = sharedContent["title"] as? String {{
            self.textView.text = "Content: \\(title)\\n\\n"
        }}
    }}

    // MARK: - SLComposeServiceViewController Overrides
    override func isContentValid() -> Bool {{
        // Validation logic
        return !sharedContent.isEmpty && !isProcessing
    }}

    override func didSelectPost() {{
        guard !isProcessing else {{ return }}
        isProcessing = true

        // Add user notes
        if let notes = contentText, !notes.isEmpty {{
            sharedContent["notes"] = notes
        }}

        // Add metadata
        addMetadata()

        // Send to Atlas
        sendToAtlas() {{ [weak self] success in
            DispatchQueue.main.async {{
                self?.isProcessing = false
                self?.extensionContext?.completeRequest(returningItems: [], completionHandler: nil)
            }}
        }}
    }}

    override func configurationItems() -> [Any]! {{
        // Custom configuration options
        return []
    }}

    // MARK: - Metadata
    private func addMetadata() {{
        var metadata: [String: Any] = [
            "captured_timestamp": ISO8601DateFormatter().string(from: Date()),
            "source_app": getSourceApp(),
            "device_info": getDeviceInfo(),
            "capture_context": "share_extension"
        ]

        // Add location if available
        if let location = currentLocation {{
            metadata["location"] = [
                "latitude": location.coordinate.latitude,
                "longitude": location.coordinate.longitude,
                "accuracy": location.horizontalAccuracy,
                "timestamp": ISO8601DateFormatter().string(from: location.timestamp)
            ]
        }}

        sharedContent["metadata"] = metadata
    }}

    private func getSourceApp() -> String {{
        // Try to determine source app
        if let hostAppBundleID = extensionContext?.inputItems.first?.userInfo?["NSExtensionItemsUserInfoKey"] as? String {{
            return hostAppBundleID
        }}
        return "unknown"
    }}

    private func getDeviceInfo() -> [String: Any] {{
        let device = UIDevice.current
        return [
            "model": device.model,
            "system_name": device.systemName,
            "system_version": device.systemVersion,
            "battery_level": device.batteryLevel,
            "orientation": getOrientationString()
        ]
    }}

    private func getOrientationString() -> String {{
        switch UIDevice.current.orientation {{
        case .portrait: return "portrait"
        case .portraitUpsideDown: return "portrait_upside_down"
        case .landscapeLeft: return "landscape_left"
        case .landscapeRight: return "landscape_right"
        case .faceUp: return "face_up"
        case .faceDown: return "face_down"
        default: return "unknown"
        }}
    }}

    // MARK: - Network Communication
    private func sendToAtlas(completion: @escaping (Bool) -> Void) {{
        guard let url = URL(string: serverURL) else {{
            completion(false)
            return
        }}

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = timeout

        do {{
            let jsonData = try JSONSerialization.data(withJSONObject: sharedContent)
            request.httpBody = jsonData
        }} catch {{
            completion(false)
            return
        }}

        URLSession.shared.dataTask(with: request) {{ data, response, error in
            if let error = error {{
                print("Atlas capture error: \\(error.localizedDescription)")
                // Store for retry if offline
                self.storeForOfflineRetry()
                completion(false)
                return
            }}

            if let httpResponse = response as? HTTPURLResponse {{
                completion(httpResponse.statusCode == 200)
            }} else {{
                completion(false)
            }}
        }}.resume()
    }}

    private func storeForOfflineRetry() {{
        // Store content for offline retry
        let timestamp = Int(Date().timeIntervalSince1970)
        let fileName = "atlas_offline_\\(timestamp).json"

        if let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first {{
            let fileURL = documentsPath.appendingPathComponent(fileName)

            do {{
                let jsonData = try JSONSerialization.data(withJSONObject: sharedContent, options: .prettyPrinted)
                try jsonData.write(to: fileURL)
            }} catch {{
                print("Failed to store offline content: \\(error)")
            }}
        }}
    }}

    // MARK: - Location Manager Delegate
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {{
        currentLocation = locations.last
    }}

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {{
        print("Location error: \\(error.localizedDescription)")
    }}

    func locationManager(_ manager: CLLocationManager, didChangeAuthorization status: CLAuthorizationStatus) {{
        switch status {{
        case .authorizedWhenInUse, .authorizedAlways:
            locationManager?.requestLocation()
        default:
            break
        }}
    }}
}}"""

        return IOSTemplate(
            template_type="extension",
            name="ShareViewController.swift",
            description="iOS Share Extension main view controller",
            content=swift_code,
            configuration={
                "server_url": server_url,
                "features": [
                    "URL capture",
                    "Text capture",
                    "Image capture",
                    "File capture",
                    "Location capture",
                    "Offline queuing",
                    "Custom notes",
                ],
            },
        )

    def generate_offline_sync_template(self) -> IOSTemplate:
        """Generate offline synchronization helper"""

        swift_code = (
            '''//
//  OfflineSyncManager.swift
//  Atlas Share Extension Support
//

import Foundation

class OfflineSyncManager {

    static let shared = OfflineSyncManager()
    private let serverURL: String
    private let documentsDirectory: URL

    private init() {
        self.serverURL = "'''
            + self._build_server_url()
            + """"
        self.documentsDirectory = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
    }

    // MARK: - Offline Storage
    func storeOfflineContent(_ content: [String: Any]) -> Bool {
        let timestamp = Int(Date().timeIntervalSince1970)
        let fileName = "atlas_offline_\\(timestamp).json"
        let fileURL = documentsDirectory.appendingPathComponent(fileName)

        do {
            let jsonData = try JSONSerialization.data(withJSONObject: content, options: .prettyPrinted)
            try jsonData.write(to: fileURL)
            return true
        } catch {
            print("Failed to store offline content: \\(error)")
            return false
        }
    }

    // MARK: - Sync Operations
    func syncOfflineContent(completion: @escaping (Int, Int) -> Void) {
        let offlineFiles = getOfflineFiles()
        var successCount = 0
        var failureCount = 0
        let dispatchGroup = DispatchGroup()

        for fileURL in offlineFiles {
            dispatchGroup.enter()

            syncFile(fileURL) { success in
                if success {
                    successCount += 1
                    self.deleteOfflineFile(fileURL)
                } else {
                    failureCount += 1
                }
                dispatchGroup.leave()
            }
        }

        dispatchGroup.notify(queue: .main) {
            completion(successCount, failureCount)
        }
    }

    private func getOfflineFiles() -> [URL] {
        do {
            let fileURLs = try FileManager.default.contentsOfDirectory(
                at: documentsDirectory,
                includingPropertiesForKeys: nil
            )

            return fileURLs.filter { $0.lastPathComponent.hasPrefix("atlas_offline_") }
        } catch {
            print("Failed to get offline files: \\(error)")
            return []
        }
    }

    private func syncFile(_ fileURL: URL, completion: @escaping (Bool) -> Void) {
        do {
            let jsonData = try Data(contentsOf: fileURL)
            let content = try JSONSerialization.jsonObject(with: jsonData) as? [String: Any]

            guard let content = content else {
                completion(false)
                return
            }

            sendToAtlas(content, completion: completion)

        } catch {
            print("Failed to read offline file: \\(error)")
            completion(false)
        }
    }

    private func sendToAtlas(_ content: [String: Any], completion: @escaping (Bool) -> Void) {
        guard let url = URL(string: serverURL) else {
            completion(false)
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 30.0

        do {
            let jsonData = try JSONSerialization.data(withJSONObject: content)
            request.httpBody = jsonData
        } catch {
            completion(false)
            return
        }

        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                print("Sync error: \\(error.localizedDescription)")
                completion(false)
                return
            }

            if let httpResponse = response as? HTTPURLResponse {
                completion(httpResponse.statusCode == 200)
            } else {
                completion(false)
            }
        }.resume()
    }

    private func deleteOfflineFile(_ fileURL: URL) {
        do {
            try FileManager.default.removeItem(at: fileURL)
        } catch {
            print("Failed to delete offline file: \\(error)")
        }
    }

    // MARK: - Status
    func getOfflineCount() -> Int {
        return getOfflineFiles().count
    }

    func getTotalOfflineSize() -> Int64 {
        let files = getOfflineFiles()
        var totalSize: Int64 = 0

        for file in files {
            do {
                let attributes = try FileManager.default.attributesOfItem(atPath: file.path)
                if let size = attributes[.size] as? Int64 {
                    totalSize += size
                }
            } catch {
                continue
            }
        }

        return totalSize
    }
}"""
        )

        return IOSTemplate(
            template_type="extension",
            name="OfflineSyncManager.swift",
            description="Offline content synchronization manager",
            content=swift_code,
            configuration={
                "features": [
                    "Offline storage",
                    "Background sync",
                    "Retry logic",
                    "Storage management",
                ]
            },
        )

    def generate_app_transport_security_config(self) -> IOSTemplate:
        """Generate App Transport Security configuration for local development"""

        config = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSExceptionDomains</key>
        <dict>
            <key>{self.server_config['host']}</key>
            <dict>
                <key>NSExceptionAllowsInsecureHTTPLoads</key>
                <true/>
                <key>NSExceptionMinimumTLSVersion</key>
                <string>TLSv1.0</string>
                <key>NSIncludesSubdomains</key>
                <true/>
            </dict>
            <key>localhost</key>
            <dict>
                <key>NSExceptionAllowsInsecureHTTPLoads</key>
                <true/>
            </dict>
        </dict>
        <key>NSAllowsArbitraryLoads</key>
        <false/>
    </dict>
</dict>
</plist>"""

        return IOSTemplate(
            template_type="configuration",
            name="ATS Configuration",
            description="App Transport Security settings for Atlas server",
            content=config,
            configuration={
                "host": self.server_config["host"],
                "port": self.server_config["port"],
                "security_notes": [
                    "Allows HTTP for local development",
                    "Should use HTTPS in production",
                    "Includes localhost exception",
                ],
            },
        )

    def _build_server_url(self) -> str:
        """Build server URL from configuration"""
        protocol = "https" if self.server_config["use_https"] else "http"
        host = self.server_config["host"]
        port = self.server_config["port"]
        path = self.server_config["api_path"]

        if (
            port in [80, 443]
            or (protocol == "http" and port == 80)
            or (protocol == "https" and port == 443)
        ):
            return f"{protocol}://{host}{path}"
        else:
            return f"{protocol}://{host}:{port}{path}"

    def save_all_templates(self) -> Dict[str, str]:
        """Generate and save all iOS templates"""

        templates = [
            self.generate_share_extension_template(),
            self.generate_share_extension_code(),
            self.generate_offline_sync_template(),
            self.generate_app_transport_security_config(),
        ]

        saved_files = {}

        for template in templates:
            # Determine file extension
            if template.name.endswith(".plist") or "plist" in template.name.lower():
                filename = f"{template.name.replace(' ', '_').lower()}"
            elif template.name.endswith(".swift"):
                filename = template.name
            else:
                filename = f"{template.name.replace(' ', '_').lower()}.txt"

            file_path = self.templates_dir / filename

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(template.content)

                saved_files[template.name] = str(file_path)

                # Also save configuration as JSON
                config_path = file_path.with_suffix(".config.json")
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "template_type": template.template_type,
                            "description": template.description,
                            "configuration": template.configuration,
                            "ios_version": template.ios_version,
                            "generated_at": datetime.now().isoformat(),
                        },
                        f,
                        indent=2,
                    )

            except Exception as e:
                print(f"Error saving template {template.name}: {e}")

        return saved_files

    def generate_setup_instructions(self) -> str:
        """Generate setup instructions for iOS Share Extension"""

        server_url = self._build_server_url()

        instructions = f"""# Atlas iOS Share Extension Setup Guide

## Prerequisites
- Xcode 13.0 or later
- iOS 15.0 or later target
- Atlas server running at {server_url}

## Setup Steps

### 1. Create Share Extension Target
1. In Xcode, select File → New → Target
2. Choose "Share Extension" from iOS Application Extension
3. Name it "Atlas Share Extension"
4. Set Bundle Identifier: `com.yourapp.atlas.shareextension`

### 2. Configure Info.plist
1. Replace the generated Info.plist with the template provided
2. Update bundle identifiers and display names as needed
3. Ensure App Transport Security settings allow your Atlas server

### 3. Implement Share Extension
1. Replace ShareViewController.swift with the provided template
2. Add OfflineSyncManager.swift to your project
3. Update server URL in both files to match your Atlas installation

### 4. Configure Capabilities
1. Enable App Groups capability
2. Add Location Services capability (if using location context)
3. Configure Background App Refresh for offline sync

### 5. Test the Extension
1. Build and run the app
2. Try sharing a URL from Safari
3. Check that content appears in Atlas dashboard

## Configuration Options

### Server Settings
- Server URL: {server_url}
- Timeout: 30 seconds
- Offline storage: Enabled
- Location capture: Optional

### Supported Content Types
- URLs (web pages, articles)
- Text (notes, quotes)
- Images (photos, screenshots)
- Files (documents, PDFs)

### Features
- ✅ Offline queuing when server unavailable
- ✅ Location context capture
- ✅ Custom notes and annotations
- ✅ Automatic content detection
- ✅ Background synchronization

## Troubleshooting

### Common Issues
1. **Extension not appearing**: Check target iOS version and activation rules
2. **Network errors**: Verify server URL and ATS configuration
3. **Location not working**: Check location permissions in Settings
4. **Offline sync failing**: Ensure background app refresh is enabled

### Debug Tips
- Check Xcode console for error messages
- Test with simulator and real device
- Verify Atlas server is accessible from iOS device
- Check network connectivity and firewall settings

## Security Notes
- The template includes basic ATS exceptions for local development
- For production, use HTTPS and proper SSL certificates
- Consider adding API key authentication for enhanced security
- Offline files are stored securely in app sandbox

## Next Steps
1. Customize UI to match your app's design
2. Add custom content categorization rules
3. Implement push notifications for sync status
4. Add support for additional content types
5. Integrate with iOS Shortcuts app

Generated on: {datetime.now().isoformat()}
Atlas Version: 1.0.0
"""

        # Save instructions
        instructions_path = self.templates_dir / "SETUP_INSTRUCTIONS.md"
        try:
            with open(instructions_path, "w", encoding="utf-8") as f:
                f.write(instructions)
        except Exception as e:
            print(f"Error saving setup instructions: {e}")

        return instructions

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get summary of current iOS extension configuration"""

        return {
            "server_configuration": self.server_config,
            "templates_directory": str(self.templates_dir),
            "server_url": self._build_server_url(),
            "features": [
                "Share Extension for iOS",
                "Offline content queuing",
                "Location context capture",
                "Multiple content type support",
                "Background synchronization",
                "Custom note annotations",
            ],
            "supported_content_types": [
                "URLs (web pages)",
                "Text (notes, quotes)",
                "Images (photos, screenshots)",
                "Files (documents, PDFs)",
            ],
            "requirements": {
                "ios_version": "iOS 15.0+",
                "xcode_version": "Xcode 13.0+",
                "atlas_server": "Running and accessible",
            },
        }
