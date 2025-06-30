// Updated popup.js - Replace your current popup.js with this
document.getElementById('analyzeBtn').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const selectedText = window.getSelection().toString().trim();
        return selectedText;
      }
    });
    
    const selectedText = results[0].result;
    
    if (!selectedText) {
      document.getElementById('result').textContent = "⚠️ No text selected. Please highlight some text first.";
      return;
    }

    document.getElementById('result').textContent = "🔄 Analyzing...";

    // Use the public endpoint that doesn't require authentication
    const response = await fetch('https://kinyarwanda-hatespeech-detection.onrender.com/api/analyze/public', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ text: selectedText })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    
    // Handle potential error response
    if (result.error) {
      throw new Error(result.error);
    }
    
    document.getElementById('result').innerHTML = `
      <strong>Prediction:</strong> <span class="${result.prediction === 'normal' ? 'safe' : 'flagged'}">${result.prediction}</span><br>
      <strong>Top Words:</strong> ${result.explanation.join(', ')}
    `;
  } catch (err) {
    console.error('Analysis error:', err);
    document.getElementById('result').textContent = "❌ Error: " + err.message;
  }
});