import SwiftUI

struct SettingsView: View {
    @ObservedObject var captureService: CaptureService
    @Environment(\.dismiss) private var dismiss
    
    @State private var serverURL: String = ""
    @State private var showingConnectionTest = false
    @State private var connectionTestResult = ""
    
    var body: some View {
        NavigationView {
            Form {
                Section("Atlas Server") {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Server URL")
                            .font(.headline)
                        
                        TextField("http://192.168.1.100:5000", text: $serverURL)
                            .textFieldStyle(RoundedBorderTextFieldStyle())
                            .autocapitalization(.none)
                            .disableAutocorrection(true)
                            .keyboardType(.URL)
                        
                        Text("Enter the IP address or URL where Atlas is running")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                
                Section("Connection") {
                    Button(action: testConnection) {
                        HStack {
                            Image(systemName: "network")
                            Text("Test Connection")
                        }
                    }
                    .disabled(serverURL.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    
                    if showingConnectionTest {
                        Text(connectionTestResult)
                            .font(.caption)
                            .foregroundColor(connectionTestResult.contains("Success") ? .green : .red)
                    }
                }
                
                Section("Current Status") {
                    HStack {
                        Text("Status")
                        Spacer()
                        HStack {
                            Circle()
                                .fill(captureService.isConnected ? Color.green : Color.red)
                                .frame(width: 8, height: 8)
                            Text(captureService.isConnected ? "Connected" : "Offline")
                                .font(.caption)
                        }
                    }
                    
                    if !captureService.serverURL.isEmpty {
                        HStack {
                            Text("Server")
                            Spacer()
                            Text(captureService.serverURL)
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                }
                
                Section("Usage Instructions") {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("How to capture content:")
                            .font(.headline)
                        
                        VStack(alignment: .leading, spacing: 8) {
                            Text("1. Configure your Atlas server URL above")
                            Text("2. From any app (Safari, Notes, etc.), tap the Share button")
                            Text("3. Select 'Atlas Capture' from the share sheet")
                            Text("4. Add optional notes and tap 'Send to Atlas'")
                            Text("5. Content will be processed automatically")
                        }
                        .font(.body)
                        .foregroundColor(.secondary)
                    }
                }
                
                Section("Shortcuts Integration") {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Voice Capture")
                            .font(.headline)
                        
                        Text("Use Siri Shortcuts to capture voice memos:")
                            .font(.body)
                        
                        Text("\"Hey Siri, add to Atlas\"")
                            .font(.caption)
                            .fontFamily(.monospaced)
                            .padding(8)
                            .background(Color.gray.opacity(0.1))
                            .cornerRadius(4)
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Save") {
                        saveSettings()
                        dismiss()
                    }
                }
            }
        }
        .onAppear {
            serverURL = captureService.serverURL
        }
    }
    
    private func testConnection() {
        showingConnectionTest = true
        connectionTestResult = "Testing..."
        
        Task {
            let success = await captureService.testConnection(url: serverURL)
            await MainActor.run {
                connectionTestResult = success ? "✅ Connection successful!" : "❌ Connection failed"
            }
        }
    }
    
    private func saveSettings() {
        captureService.updateServerURL(serverURL)
        captureService.saveSettings()
    }
}

#Preview {
    SettingsView(captureService: CaptureService())
}