// popup.js
document.addEventListener('DOMContentLoaded', function() {
  const savePageButton = document.getElementById('savePage');
  const saveSelectionButton = document.getElementById('saveSelection');
  const saveArticleButton = document.getElementById('saveArticle');
  const statusDiv = document.getElementById('status');

  // Load saved server URL
  chrome.storage.sync.get(['atlasServerUrl'], function(result) {
    if (!result.atlasServerUrl) {
      // Default to localhost
      chrome.storage.sync.set({atlasServerUrl: 'https://atlas.khamel.com'});
    }
  });

  savePageButton.addEventListener('click', function() {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      const activeTab = tabs[0];
      saveContent(activeTab.url, activeTab.title, 'page');
    });
  });

  saveSelectionButton.addEventListener('click', function() {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      chrome.tabs.sendMessage(tabs[0].id, {action: "getSelection"}, function(response) {
        if (response && response.selection) {
          saveContent('', '', 'selection', response.selection);
        } else {
          showStatus('No text selected', 'error');
        }
      });
    });
  });

  saveArticleButton.addEventListener('click', function() {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      chrome.tabs.sendMessage(tabs[0].id, {action: "getArticleContent"}, function(response) {
        if (response && response.content) {
          saveContent(tabs[0].url, tabs[0].title, 'article', response.content);
        } else {
          showStatus('Could not extract article content', 'error');
        }
      });
    });
  });

  function saveContent(url, title, type, content = '') {
    showStatus('Saving to Atlas...', 'info');

    chrome.storage.sync.get(['atlasServerUrl'], function(result) {
      const serverUrl = result.atlasServerUrl || 'http://localhost:8000';
      const apiUrl = `${serverUrl}/api/v1/content/save`;

      const data = {
        url: url,
        title: title,
        content: content,
        source: `browser-extension-${type}`
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
        showStatus('Content saved successfully!', 'success');
        setTimeout(() => {
          window.close();
        }, 1500);
      })
      .catch(error => {
        console.error('Error:', error);
        showStatus('Failed to save content', 'error');
      });
    });
  }

  function showStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = 'status ' + type;
    statusDiv.style.display = 'block';

    if (type === 'success') {
      setTimeout(() => {
        statusDiv.style.display = 'none';
      }, 2000);
    }
  }
});