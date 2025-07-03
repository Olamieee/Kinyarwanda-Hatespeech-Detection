// Add this at the top to prevent multiple initializations
if (window.popupInitialized) {
  console.log('Popup already initialized, skipping...');
} else {
  window.popupInitialized = true;
  
  // Your existing code with request deduplication
  let isAnalyzing = false; // Prevent concurrent requests
  
  document.getElementById('analyzeBtn').addEventListener('click', async (e) => {
    // Prevent multiple rapid clicks
    if (isAnalyzing) {
      console.log('Analysis already in progress, ignoring click');
      return;
    }
    
    // Disable button during analysis
    const button = e.target;
    button.disabled = true;
    isAnalyzing = true;
    
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => {
          const selectedText = window.getSelection().toString().trim();
          return selectedText;
        }
      });
      
      const selectedText = results[0].result;
      
      if (!selectedText) {
        document.getElementById('result').innerHTML = '<div class="warning">No text selected. Please highlight some text first.</div>';
        return;
      }

      document.getElementById('result').innerHTML = '<div class="loading">Analyzing text...</div>';

      // Smart server detection with request deduplication
      const servers = [
        'http://127.0.0.1:5000',
        'http://localhost:5000',
        'https://kinyarwanda-hatespeech-detection.onrender.com'
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
            signal: AbortSignal.timeout(5000)
          });

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          result = await response.json();
          console.log(`Successfully connected to: ${serverUrl}`);
          break;

        } catch (err) {
          console.log(`Failed to connect to ${serverUrl}:`, err.message);
          lastError = err;
          continue;
        }
      }

      if (!result) {
        throw new Error(`All servers failed. Last error: ${lastError?.message || 'Unknown error'}`);
      }
      
      if (result.error) {
        throw new Error(result.error);
      }
      
      document.getElementById('result').innerHTML = `
        <div class="result-content">
          <strong>Prediction:</strong> 
          <span class="${result.prediction === 'normal' ? 'safe' : 'flagged'}">${result.prediction}</span>
          <div class="top-words">
            <strong>Key Words:</strong> ${result.explanation.join(', ')}
          </div>
        </div>
      `;
      
    } catch (err) {
      console.error('Analysis error:', err);
      document.getElementById('result').innerHTML = `<div class="error">Error: ${err.message}</div>`;
    } finally {
      // Re-enable button and reset flag
      button.disabled = false;
      isAnalyzing = false;
    }
  });

  // Add ripple effect to button (only once)
  document.getElementById('analyzeBtn').addEventListener('click', function(e) {
    // Only add ripple if not disabled
    if (this.disabled) return;
    
    const ripple = document.createElement('span');
    const rect = this.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = e.clientX - rect.left - size / 2;
    const y = e.clientY - rect.top - size / 2;
    
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    ripple.style.position = 'absolute';
    ripple.style.borderRadius = '50%';
    ripple.style.background = 'rgba(255, 255, 255, 0.3)';
    ripple.style.transform = 'scale(0)';
    ripple.style.animation = 'ripple 0.6s linear';
    ripple.style.pointerEvents = 'none';
    
    this.appendChild(ripple);
    
    setTimeout(() => {
      ripple.remove();
    }, 600);
  });
}