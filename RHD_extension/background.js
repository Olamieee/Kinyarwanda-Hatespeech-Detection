chrome.action.onClicked.addListener((tab) => {
  chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: getSelectedText
  });
});

function getSelectedText() {
  const selectedText = window.getSelection().toString().trim();
  if (selectedText) {
    chrome.storage.local.set({ selectedText });
    alert("✅ Text captured! Click the extension icon again to analyze.");
  } else {
    alert("⚠️ Please highlight some text first.");
  }
}