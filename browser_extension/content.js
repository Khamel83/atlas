// content.js
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  if (request.action === "getSelection") {
    const selection = window.getSelection().toString();
    sendResponse({selection: selection});
  } else if (request.action === "getArticleContent") {
    // Simple article content extraction
    // In a real implementation, you might want to use a more sophisticated approach
    const articleContent = extractArticleContent();
    sendResponse({content: articleContent});
  }
});

function extractArticleContent() {
  // Try to find the main content area
  const contentSelectors = [
    'article',
    '.content',
    '.post',
    '.entry-content',
    '.article-content',
    '.story-content',
    'main',
    '#content',
    '.main-content'
  ];

  for (const selector of contentSelectors) {
    const element = document.querySelector(selector);
    if (element) {
      return element.innerText || element.textContent;
    }
  }

  // Fallback to body content
  return document.body.innerText || document.body.textContent;
}