// background_firefox.js - Firefox-compatible version
browser.runtime.onInstalled.addListener(function() {
  // Create context menu items
  browser.contextMenus.create({
    id: "atlasSavePage",
    title: "Save Page to Atlas",
    contexts: ["page"]
  });

  browser.contextMenus.create({
    id: "atlasSaveSelection",
    title: "Save Selection to Atlas",
    contexts: ["selection"]
  });

  browser.contextMenus.create({
    id: "atlasSaveLink",
    title: "Save Link to Atlas",
    contexts: ["link"]
  });
});

browser.contextMenus.onClicked.addListener(function(info, tab) {
  if (info.menuItemId === "atlasSavePage") {
    saveContent(tab.url, tab.title, 'context-menu-page');
  } else if (info.menuItemId === "atlasSaveSelection") {
    // Get the selected text
    browser.tabs.sendMessage(tab.id, {action: "getSelection"}).then(function(response) {
      if (response && response.selection) {
        saveContent('', '', 'context-menu-selection', response.selection);
      }
    });
  } else if (info.menuItemId === "atlasSaveLink") {
    saveContent(info.linkUrl, info.linkUrl, 'context-menu-link');
  }
});

function saveContent(url, title, source, content = '') {
  browser.storage.sync.get(['atlasServerUrl']).then(function(result) {
    const serverUrl = result.atlasServerUrl || 'http://localhost:8000';
    const apiUrl = `${serverUrl}/api/v1/content/save`;

    const data = {
      url: url,
      title: title,
      content: content,
      source: source
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