// settings.js
document.addEventListener('DOMContentLoaded', function() {
  const serverUrlInput = document.getElementById('serverUrl');
  const saveSettingsButton = document.getElementById('saveSettings');
  const statusDiv = document.getElementById('status');

  // Load saved settings
  chrome.storage.sync.get(['atlasServerUrl'], function(result) {
    if (result.atlasServerUrl) {
      serverUrlInput.value = result.atlasServerUrl;
    } else {
      // Default to localhost
      serverUrlInput.value = 'http://localhost:8000';
    }
  });

  saveSettingsButton.addEventListener('click', function() {
    const serverUrl = serverUrlInput.value.trim();

    if (!serverUrl) {
      showStatus('Please enter a server URL', 'error');
      return;
    }

    // Validate URL format
    try {
      new URL(serverUrl);
    } catch (e) {
      showStatus('Please enter a valid URL', 'error');
      return;
    }

    chrome.storage.sync.set({atlasServerUrl: serverUrl}, function() {
      showStatus('Settings saved successfully!', 'success');
    });
  });

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