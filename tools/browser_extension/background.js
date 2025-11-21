// background.js
chrome.runtime.onInstalled.addListener(function() {
  // Create context menu items
  chrome.contextMenus.create({
    id: "atlasSavePage",
    title: "Save Page to Atlas",
    contexts: ["page"]
  });

  chrome.contextMenus.create({
    id: "atlasSaveSelection",
    title: "Save Selection to Atlas",
    contexts: ["selection"]
  });

  chrome.contextMenus.create({
    id: "atlasSaveLink",
    title: "Save Link to Atlas",
    contexts: ["link"]
  });
});

chrome.contextMenus.onClicked.addListener(function(info, tab) {
  if (info.menuItemId === "atlasSavePage") {
    saveContent(tab.url, tab.title, 'context-menu-page');
  } else if (info.menuItemId === "atlasSaveSelection") {
    // Get the selected text
    chrome.tabs.sendMessage(tab.id, {action: "getSelection"}, function(response) {
      if (response && response.selection) {
        saveContent('', '', 'context-menu-selection', response.selection);
      }
    });
  } else if (info.menuItemId === "atlasSaveLink") {
    saveContent(info.linkUrl, info.linkUrl, 'context-menu-link');
  }
});

function saveContent(url, title, source, content = '') {
  chrome.storage.sync.get(['atlasServerUrl'], function(result) {
    const serverUrl = result.atlasServerUrl || 'https://atlas.khamel.com';
    const apiUrl = `${serverUrl}/api/v1/content/save`;

    const data = {
      url: url,
      title: title,
      content: content,
      content_type: 'article'
    };

    fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
      console.log('Content saved successfully:', data);
    })
    .catch(error => {
      console.error('Error saving content:', error);
    });
  });
}