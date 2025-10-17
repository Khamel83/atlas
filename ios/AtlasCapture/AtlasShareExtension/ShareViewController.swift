import UIKit
import Social
import UniformTypeIdentifiers

class ShareViewController: UIViewController {
    
    @IBOutlet weak var textView: UITextView!
    @IBOutlet weak var notesTextField: UITextField!
    @IBOutlet weak var sendButton: UIButton!
    @IBOutlet weak var cancelButton: UIButton!
    @IBOutlet weak var statusLabel: UILabel!
    
    private var capturedContent: String = ""
    private var contentType: String = "text"
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        setupUI()
        extractSharedContent()
    }
    
    private func setupUI() {
        view.backgroundColor = UIColor.systemBackground
        
        // Setup text view
        textView.isEditable = false
        textView.layer.borderColor = UIColor.systemGray4.cgColor
        textView.layer.borderWidth = 1
        textView.layer.cornerRadius = 8
        textView.font = UIFont.systemFont(ofSize: 16)
        
        // Setup notes field
        notesTextField.placeholder = "Add optional notes..."
        notesTextField.borderStyle = .roundedRect
        
        // Setup buttons
        sendButton.backgroundColor = UIColor.systemBlue
        sendButton.setTitleColor(.white, for: .normal)
        sendButton.layer.cornerRadius = 8
        sendButton.addTarget(self, action: #selector(sendToAtlas), for: .touchUpInside)
        
        cancelButton.backgroundColor = UIColor.systemGray4
        cancelButton.setTitleColor(.label, for: .normal)
        cancelButton.layer.cornerRadius = 8
        cancelButton.addTarget(self, action: #selector(cancel), for: .touchUpInside)
        
        // Setup status label
        statusLabel.textColor = UIColor.systemBlue
        statusLabel.font = UIFont.systemFont(ofSize: 14)
        statusLabel.text = "Ready to capture content"
    }
    
    private func extractSharedContent() {
        guard let extensionItem = extensionContext?.inputItems.first as? NSExtensionItem,
              let attachments = extensionItem.attachments else {
            showError("No content to capture")
            return
        }
        
        for attachment in attachments {
            // Handle URLs
            if attachment.hasItemConformingToTypeIdentifier(UTType.url.identifier) {
                attachment.loadItem(forTypeIdentifier: UTType.url.identifier, options: nil) { [weak self] (item, error) in
                    if let url = item as? URL {
                        DispatchQueue.main.async {
                            self?.contentType = "url"
                            self?.capturedContent = url.absoluteString
                            self?.textView.text = self?.capturedContent
                            self?.statusLabel.text = "URL captured: \(url.host ?? "unknown site")"
                        }
                    }
                }
                return
            }
            
            // Handle plain text
            if attachment.hasItemConformingToTypeIdentifier(UTType.plainText.identifier) {
                attachment.loadItem(forTypeIdentifier: UTType.plainText.identifier, options: nil) { [weak self] (item, error) in
                    if let text = item as? String {
                        DispatchQueue.main.async {
                            self?.contentType = "text"
                            self?.capturedContent = text
                            self?.textView.text = self?.capturedContent
                            self?.statusLabel.text = "Text captured (\(text.count) characters)"
                        }
                    }
                }
                return
            }
            
            // Handle web pages
            if attachment.hasItemConformingToTypeIdentifier("public.url") {
                attachment.loadItem(forTypeIdentifier: "public.url", options: nil) { [weak self] (item, error) in
                    if let url = item as? URL {
                        DispatchQueue.main.async {
                            self?.contentType = "url"
                            self?.capturedContent = url.absoluteString
                            self?.textView.text = self?.capturedContent
                            self?.statusLabel.text = "Web page captured"
                        }
                    }
                }
                return
            }
        }
        
        // Fallback: try to get any string content
        if let attachment = attachments.first {
            attachment.loadItem(forTypeIdentifier: kUTTypeText as String, options: nil) { [weak self] (item, error) in
                if let text = item as? String {
                    DispatchQueue.main.async {
                        self?.contentType = "text"
                        self?.capturedContent = text
                        self?.textView.text = self?.capturedContent
                        self?.statusLabel.text = "Content captured"
                    }
                } else {
                    DispatchQueue.main.async {
                        self?.showError("Unable to extract content from this item")
                    }
                }
            }
        }
    }
    
    @objc private func sendToAtlas() {
        guard !capturedContent.isEmpty else {
            showError("No content to send")
            return
        }
        
        updateUI(sending: true)
        
        Task {
            let success = await sendContentToAtlas()
            
            DispatchQueue.main.async {
                if success {
                    self.statusLabel.text = "✅ Sent to Atlas successfully!"
                    self.statusLabel.textColor = UIColor.systemGreen
                    
                    // Close after brief delay
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                        self.extensionContext?.completeRequest(returningItems: nil, completionHandler: nil)
                    }
                } else {
                    self.statusLabel.text = "❌ Failed to send - saved offline"
                    self.statusLabel.textColor = UIColor.systemRed
                    self.updateUI(sending: false)
                }
            }
        }
    }
    
    private func sendContentToAtlas() async -> Bool {
        // Get server URL from shared app group or UserDefaults
        let serverURL = UserDefaults.standard.string(forKey: "AtlasServerURL") ?? ""
        
        guard !serverURL.isEmpty,
              let url = URL(string: "\(serverURL)/api/capture") else {
            // Save to offline queue
            saveToOfflineQueue()
            return false
        }
        
        let notes = notesTextField.text?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        
        let payload: [String: Any] = [
            "type": contentType,
            "content": capturedContent,
            "metadata": [
                "notes": notes,
                "source": "ios_share_extension",
                "app": "Share Extension"
            ],
            "source_device": "iOS Device"
        ]
        
        do {
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.timeoutInterval = 30
            request.httpBody = try JSONSerialization.data(withJSONObject: payload)
            
            let (data, response) = try await URLSession.shared.data(for: request)
            
            if let httpResponse = response as? HTTPURLResponse,
               httpResponse.statusCode == 200 {
                
                if let jsonResponse = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let success = jsonResponse["success"] as? Bool {
                    return success
                }
            }
            
            // If we get here, the request failed
            saveToOfflineQueue()
            return false
            
        } catch {
            print("Network error: \(error)")
            saveToOfflineQueue()
            return false
        }
    }
    
    private func saveToOfflineQueue() {
        // Save to UserDefaults for later processing when the main app is opened
        let offlineItem = [
            "content": capturedContent,
            "type": contentType,
            "notes": notesTextField.text ?? "",
            "timestamp": Date().timeIntervalSince1970,
            "status": "offline"
        ]
        
        var offlineQueue = UserDefaults.standard.array(forKey: "OfflineQueue") as? [[String: Any]] ?? []
        offlineQueue.append(offlineItem)
        
        // Keep only last 100 items
        if offlineQueue.count > 100 {
            offlineQueue.removeFirst()
        }
        
        UserDefaults.standard.set(offlineQueue, forKey: "OfflineQueue")
    }
    
    @objc private func cancel() {
        extensionContext?.completeRequest(returningItems: nil, completionHandler: nil)
    }
    
    private func updateUI(sending: Bool) {
        sendButton.isEnabled = !sending
        cancelButton.isEnabled = !sending
        notesTextField.isEnabled = !sending
        
        if sending {
            statusLabel.text = "Sending to Atlas..."
            statusLabel.textColor = UIColor.systemBlue
        }
    }
    
    private func showError(_ message: String) {
        statusLabel.text = "❌ \(message)"
        statusLabel.textColor = UIColor.systemRed
    }
}

// MARK: - UI Layout

extension ShareViewController {
    
    override func loadView() {
        view = UIView()
        view.backgroundColor = UIColor.systemBackground
        
        // Create UI elements
        let stackView = UIStackView()
        stackView.axis = .vertical
        stackView.spacing = 16
        stackView.distribution = .fill
        stackView.translatesAutoresizingMaskIntoConstraints = false
        
        // Title label
        let titleLabel = UILabel()
        titleLabel.text = "Add to Atlas"
        titleLabel.font = UIFont.boldSystemFont(ofSize: 18)
        titleLabel.textAlignment = .center
        
        // Content preview
        textView = UITextView()
        textView.translatesAutoresizingMaskIntoConstraints = false
        
        // Notes field
        notesTextField = UITextField()
        notesTextField.translatesAutoresizingMaskIntoConstraints = false
        
        // Button stack
        let buttonStack = UIStackView()
        buttonStack.axis = .horizontal
        buttonStack.spacing = 12
        buttonStack.distribution = .fillEqually
        
        cancelButton = UIButton(type: .system)
        cancelButton.setTitle("Cancel", for: .normal)
        cancelButton.titleLabel?.font = UIFont.systemFont(ofSize: 16, weight: .medium)
        
        sendButton = UIButton(type: .system)
        sendButton.setTitle("Send to Atlas", for: .normal)
        sendButton.titleLabel?.font = UIFont.systemFont(ofSize: 16, weight: .medium)
        
        buttonStack.addArrangedSubview(cancelButton)
        buttonStack.addArrangedSubview(sendButton)
        
        // Status label
        statusLabel = UILabel()
        statusLabel.font = UIFont.systemFont(ofSize: 14)
        statusLabel.textAlignment = .center
        statusLabel.numberOfLines = 2
        
        // Add to stack
        stackView.addArrangedSubview(titleLabel)
        stackView.addArrangedSubview(textView)
        stackView.addArrangedSubview(notesTextField)
        stackView.addArrangedSubview(buttonStack)
        stackView.addArrangedSubview(statusLabel)
        
        view.addSubview(stackView)
        
        // Constraints
        NSLayoutConstraint.activate([
            stackView.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 16),
            stackView.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -16),
            stackView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 16),
            stackView.bottomAnchor.constraint(lessThanOrEqualTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -16),
            
            textView.heightAnchor.constraint(greaterThanOrEqualToConstant: 120),
            notesTextField.heightAnchor.constraint(equalToConstant: 44),
            buttonStack.heightAnchor.constraint(equalToConstant: 44)
        ])
    }
}