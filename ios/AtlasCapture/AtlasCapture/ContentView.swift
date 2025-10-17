import SwiftUI

struct ContentView: View {
    @StateObject private var captureService = CaptureService()
    @State private var showingSettings = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                // Header
                VStack {
                    Image(systemName: "brain.head.profile")
                        .font(.system(size: 60))
                        .foregroundColor(.blue)
                    
                    Text("Atlas Capture")
                        .font(.title)
                        .fontWeight(.bold)
                    
                    Text("Personal Knowledge System")
                        .font(.subtitle)
                        .foregroundColor(.secondary)
                }
                .padding()
                
                // Connection Status
                HStack {
                    Circle()
                        .fill(captureService.isConnected ? Color.green : Color.red)
                        .frame(width: 10, height: 10)
                    
                    Text(captureService.isConnected ? "Connected to Atlas" : "Atlas Offline")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                // Server Info
                if !captureService.serverURL.isEmpty {
                    Text("Server: \(captureService.serverURL)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                }
                
                Spacer()
                
                // Capture History
                VStack(alignment: .leading, spacing: 12) {
                    Text("Recent Captures")
                        .font(.headline)
                        .padding(.horizontal)
                    
                    if captureService.captureHistory.isEmpty {
                        Text("No captures yet. Use the share extension from any app to capture content to Atlas.")
                            .font(.body)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                            .padding()
                    } else {
                        List(captureService.captureHistory) { capture in
                            CaptureRowView(capture: capture)
                        }
                        .listStyle(PlainListStyle())
                    }
                }
                
                Spacer()
                
                // Test Connection Button
                Button(action: {
                    Task {
                        await captureService.testConnection()
                    }
                }) {
                    HStack {
                        Image(systemName: "network")
                        Text("Test Connection")
                    }
                    .foregroundColor(.white)
                    .padding()
                    .background(Color.blue)
                    .cornerRadius(8)
                }
                .disabled(captureService.serverURL.isEmpty)
            }
            .navigationTitle("Atlas")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Settings") {
                        showingSettings = true
                    }
                }
            }
            .sheet(isPresented: $showingSettings) {
                SettingsView(captureService: captureService)
            }
        }
        .onAppear {
            captureService.loadSettings()
        }
    }
}

struct CaptureRowView: View {
    let capture: CaptureItem
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Image(systemName: iconForContentType(capture.contentType))
                    .foregroundColor(.blue)
                
                Text(capture.contentType.capitalized)
                    .font(.caption)
                    .fontWeight(.medium)
                
                Spacer()
                
                Text(capture.timestamp, style: .relative)
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
            
            Text(capture.content)
                .font(.body)
                .lineLimit(2)
            
            if let notes = capture.notes, !notes.isEmpty {
                Text("Note: \(notes)")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .italic()
            }
            
            // Status indicator
            HStack {
                Circle()
                    .fill(colorForStatus(capture.status))
                    .frame(width: 6, height: 6)
                
                Text(capture.status.capitalized)
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
        .padding(.vertical, 4)
    }
    
    private func iconForContentType(_ type: String) -> String {
        switch type.lowercased() {
        case "url":
            return "link"
        case "text":
            return "text.quote"
        case "voice":
            return "mic"
        default:
            return "doc"
        }
    }
    
    private func colorForStatus(_ status: String) -> Color {
        switch status.lowercased() {
        case "completed":
            return .green
        case "processing":
            return .orange
        case "failed":
            return .red
        default:
            return .gray
        }
    }
}

#Preview {
    ContentView()
}