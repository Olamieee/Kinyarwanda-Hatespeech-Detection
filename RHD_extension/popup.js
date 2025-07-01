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

    // Smart server detection
    const servers = [
      'http://127.0.0.1:5000',  // Local development
      'http://localhost:5000',   // Alternative local
      'https://kinyarwanda-hatespeech-detection.onrender.com'  // Production
    ];

    let result = null;
    let lastError = null;

    for (const serverUrl of servers) {
      try {
        console.log(`Trying server: ${serverUrl}`);
        
        const response = await fetch(`${serverUrl}/api/analyze/public`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ text: selectedText }),
          // Add timeout for faster fallback
          signal: AbortSignal.timeout(5000) // 5 second timeout
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        result = await response.json();
        console.log(`Successfully connected to: ${serverUrl}`);
        break; // Success! Exit the loop

      } catch (err) {
        console.log(`Failed to connect to ${serverUrl}:`, err.message);
        lastError = err;
        continue; // Try next server
      }
    }

    if (!result) {
      throw new Error(`All servers failed. Last error: ${lastError?.message || 'Unknown error'}`);
    }
    
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