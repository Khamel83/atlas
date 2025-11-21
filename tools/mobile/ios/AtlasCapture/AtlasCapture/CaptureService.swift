import Foundation
import SwiftUI

struct CaptureItem: Identifiable, Codable {
    let id = UUID()
    let contentType: String
    let content: String
    let notes: String?
    let timestamp: Date
    let captureId: String?
    var status: String = "queued"
    
    enum CodingKeys: String, CodingKey {
        case contentType, content, notes, timestamp, captureId, status
    }
}

@MainActor
class CaptureService: ObservableObject {
    @Published var serverURL: String = ""
    @Published var isConnected: Bool = false
    @Published var captureHistory: [CaptureItem] = []
    
    private let userDefaults = UserDefaults.standard
    private let historyKey = "CaptureHistory"
    private let serverURLKey = "AtlasServerURL"
    
    init() {
        loadSettings()
        loadCaptureHistory()
    }
    
    func loadSettings() {
        serverURL = userDefaults.string(forKey: serverURLKey) ?? ""
        
        // Test connection on load if we have a server URL
        if !serverURL.isEmpty {
            Task {
                await testConnection()
            }
        }
    }
    
    func saveSettings() {
        userDefaults.set(serverURL, forKey: serverURLKey)
    }
    
    func updateServerURL(_ url: String) {
        serverURL = url.trimmingCharacters(in: .whitespacesAndNewlines)
    }
    
    func testConnection(url: String? = nil) async -> Bool {
        let testURL = url ?? serverURL
        
        guard !testURL.isEmpty,
              let healthURL = URL(string: "\(testURL)/api/capture/health") else {
            isConnected = false
            return false
        }
        
        do {
            let (_, response) = try await URLSession.shared.data(from: healthURL)
            
            if let httpResponse = response as? HTTPURLResponse {
                isConnected = httpResponse.statusCode == 200
                return isConnected
            }
        } catch {
            print("Connection test failed: \(error)")
        }
        
        isConnected = false
        return false
    }
    
    func captureContent(type: String, content: String, notes: String? = nil) async -> Bool {
        guard !serverURL.isEmpty,
              let url = URL(string: "\(serverURL)/api/capture") else {
            return false
        }
        
        let captureId = UUID().uuidString
        
        let payload: [String: Any] = [
            "type": type,
            "content": content,
            "metadata": [
                "notes": notes ?? "",
                "source": "ios_share_extension",
                "app": "AtlasCapture"
            ],
            "source_device": "iOS Device"
        ]
        
        do {
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONSerialization.data(withJSONObject: payload)
            
            let (data, response) = try await URLSession.shared.data(for: request)
            
            if let httpResponse = response as? HTTPURLResponse,
               httpResponse.statusCode == 200 {
                
                // Parse response to get capture ID
                if let jsonResponse = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let success = jsonResponse["success"] as? Bool,
                   success,
                   let returnedCaptureId = jsonResponse["capture_id"] as? String {
                    
                    // Add to history
                    let captureItem = CaptureItem(
                        contentType: type,
                        content: content,
                        notes: notes,
                        timestamp: Date(),
                        captureId: returnedCaptureId,
                        status: "queued"
                    )
                    
                    addToCaptureHistory(captureItem)
                    return true
                }
            }
        } catch {
            print("Capture failed: \(error)")
        }
        
        // Add to offline queue if capture failed
        let captureItem = CaptureItem(
            contentType: type,
            content: content,
            notes: notes,
            timestamp: Date(),
            captureId: captureId,
            status: "offline"
        )
        
        addToCaptureHistory(captureItem)
        return false
    }
    
    private func addToCaptureHistory(_ item: CaptureItem) {
        captureHistory.insert(item, at: 0)
        
        // Keep only last 50 items
        if captureHistory.count > 50 {
            captureHistory.removeLast()
        }
        
        saveCaptureHistory()
    }
    
    private func loadCaptureHistory() {
        if let data = userDefaults.data(forKey: historyKey),
           let history = try? JSONDecoder().decode([CaptureItem].self, from: data) {
            captureHistory = history
        }
    }
    
    private func saveCaptureHistory() {
        if let data = try? JSONEncoder().encode(captureHistory) {
            userDefaults.set(data, forKey: historyKey)
        }
    }
    
    func clearHistory() {
        captureHistory.removeAll()
        saveCaptureHistory()
    }
    
    func checkCaptureStatus(_ captureId: String) async -> String? {
        guard !serverURL.isEmpty,
              let url = URL(string: "\(serverURL)/api/capture/status/\(captureId)") else {
            return nil
        }
        
        do {
            let (data, response) = try await URLSession.shared.data(from: url)
            
            if let httpResponse = response as? HTTPURLResponse,
               httpResponse.statusCode == 200,
               let jsonResponse = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let status = jsonResponse["status"] as? String {
                return status
            }
        } catch {
            print("Status check failed: \(error)")
        }
        
        return nil
    }
    
    func refreshCaptureStatuses() async {
        var updatedHistory = captureHistory
        
        for (index, item) in captureHistory.enumerated() {
            if let captureId = item.captureId,
               item.status == "queued" || item.status == "processing" {
                
                if let newStatus = await checkCaptureStatus(captureId) {
                    updatedHistory[index].status = newStatus
                }
            }
        }
        
        captureHistory = updatedHistory
        saveCaptureHistory()
    }
}