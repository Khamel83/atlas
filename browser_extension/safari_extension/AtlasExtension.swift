//
//  AtlasExtension.swift
//  Atlas Safari Extension
//
//  Created by Atlas AI System on 2025-08-30.
//

import SafariServices
import Foundation

class SafariExtensionHandler: SFSafariExtensionHandler {
    
    override func messageReceived(withName messageName: String, from page: SFSafariPage, userInfo: [String : Any]?) {
        // This is where we'll handle messages from our injected script
        if messageName == "saveContent" {
            if let contentData = userInfo {
                saveToAtlas(contentData: contentData)
            }
        }
    }
    
    override func toolbarItemClicked(in window: SFSafariWindow) {
        // Handle toolbar item click
        window.getActiveTab { tab in
            tab?.getActivePage { page in
                page?.dispatchMessageToScript(withName: "showPopup", userInfo: nil)
            }
        }
    }
    
    override func contextMenuItemSelected(withCommand command: String, in page: SFSafariPage, userInfo: [String : Any]? = nil) {
        switch command {
        case "savePage":
            page.dispatchMessageToScript(withName: "savePage", userInfo: nil)
        case "saveSelection":
            page.dispatchMessageToScript(withName: "saveSelection", userInfo: nil)
        case "saveArticle":
            page.dispatchMessageToScript(withName: "saveArticle", userInfo: nil)
        default:
            break
        }
    }
    
    private func saveToAtlas(contentData: [String: Any]) {
        let serverUrl = UserDefaults.standard.string(forKey: "atlasServerUrl") ?? "http://localhost:8000"
        let apiUrl = "\(serverUrl)/api/v1/content/save"
        
        guard let url = URL(string: apiUrl) else {
            print("Invalid Atlas server URL: \(apiUrl)")
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        do {
            let jsonData = try JSONSerialization.data(withJSONObject: contentData, options: [])
            request.httpBody = jsonData
            
            let task = URLSession.shared.dataTask(with: request) { data, response, error in
                if let error = error {
                    print("Error sending content to Atlas: \(error.localizedDescription)")
                    return
                }
                
                if let httpResponse = response as? HTTPURLResponse {
                    if httpResponse.statusCode == 200 {
                        print("Content successfully saved to Atlas")
                    } else {
                        print("Atlas server returned status code: \(httpResponse.statusCode)")
                    }
                }
            }
            
            task.resume()
        } catch {
            print("Error serializing content data: \(error.localizedDescription)")
        }
    }
}