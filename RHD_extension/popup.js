document.getElementById('analyzeBtn').addEventListener('click', async () => {
  chrome.storage.local.get(['selectedText'], async (data) => {
    if (!data.selectedText) {
      document.getElementById('result').textContent = "⚠️ No text selected.";
      return;
    }

    try {
      const response = await fetch('https://kinyarwanda-hatespeech-detection.onrender.com/api/analyze', {
        method: 'POST',
        credentials: 'include', // include session cookie for @login_required
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text: data.selectedText })
      });

      const result = await response.json();
      document.getElementById('result').innerHTML = `
        <strong>Prediction:</strong> <span class="${result.prediction === 'normal' ? 'safe' : 'flagged'}">${result.prediction}</span><br>
        <strong>Top Words:</strong> ${result.explanation.join(', ')}
      `;
    } catch (err) {
      document.getElementById('result').textContent = "❌ Error: " + err;
    }
  });
});