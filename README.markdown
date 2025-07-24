# Kinyarwanda Hate Speech Detection App

A machine learning app to detect **hate**, **normal**, or **sarcasm** in Kinyarwanda text using a transformer model. Includes a Chrome extension (Developer Mode) for real-time classification.

---

## 🚀 Features

- Detects `hate`, `normal`, or `sarcasm` in Kinyarwanda
- Uses a fine-tuned `afro-xlmr-mini` transformer model
- Highlights key words with attention-based explanations
- Web interface for text analysis
- Chrome extension for live web integration

---

## 📁 Project Structure

```
project/
│
├── app.py                    # Flask app
├── README.md
├── Procfile
├── requirements.txt
├── css/
│    ├── dashboard.css
│    ├── index.css
│    ├── login.css
│    ├── register.css
│    ├── moderator_dashboard.css
│    ├── verify.css
│    ├── forgot_password.css
│    ├── reset_password.css
├── templates/
│    ├── dashboard.html
│    ├── index.html
│    ├── login.html
│    ├── register.html
│    ├── moderator_dashboard.html
│    ├── verify.html
│    ├── forgot_password.html
│    ├── reset_password.html
├── model/
│    ├── kinyamodel2.ipynb     # Model training notebook
│    ├── kinyarwanda_hard_texts.csv
│    ├── realistic_kinyarwanda_hate_sarcasm_normal.csv
│    ├── label_encoder.pkl
│    ├── kinyarwanda-hatespeech-model/  # Transformer model directory
│    │    ├── config.json
│    │    ├── pytorch_model.bin
│    │    ├── tokenizer_config.json
│    │    ├── sentencepiece.bpe.model
│    │    ├── special_tokens_map.json
├── RHD_extension/    # Chrome extension source files
│    ├── manifest.json
│    ├── popup.html
│    ├── popup.js
│    ├── icon.png
│    ├── content.js
│    ├── background.js
```

---

## 🛠️ Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Olamieee/kinyarwanda-hate-speech-app.git
   cd kinyarwanda-hate-speech-app
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # macOS/Linux
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **(Optional) Fine-Tune Model**
   ```bash
   jupyter notebook model/kinyamodel2.ipynb
   ```
   - Loads `kinyarwanda_hard_texts.csv` and `realistic_kinyarwanda_hate_sarcasm_normal.csv`
   - Fine-tunes `afro-xlmr-mini`
   - Saves model to `model/kinyarwanda-hatespeech-model/` and `label_encoder.pkl`
   - Use a GPU (e.g., Colab) for faster training

5. **Run the App**
   ```bash
   python app.py
   ```
   Visit `http://localhost:5000`

---

## 🧩 Chrome Extension (Developer Mode)

1. **Load Extension**
   - Go to `chrome://extensions/`
   - Enable **Developer Mode**
   - Click **Load Unpacked**
   - Select `RHD_extension/`

2. **Use Extension**
   - Highlight Kinyarwanda text on a webpage
   - Click extension icon and **Analyze**
   - View `hate`, `normal`, or `sarcasm` result with key words

   > Ensure the app is running locally (`http://localhost:5000`) or deployed (`https://kinyarwanda-hatespeech-detection.onrender.com`).

---

## 🔍 Model Summary

- **Algorithm**: Fine-tuned `afro-xlmr-mini` transformer
- **Tokenizer**: Sentencepiece (`sentencepiece.bpe.model`)
- **Explainability**: Attention-based word importance
- **Classes**: `hate`, `normal`, `sarcasm`
- **Metrics**: See `kinyamodel2.ipynb` for accuracy and F1 scores

---

## 🧪 Example Usage

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import joblib

# Load model and tokenizer
model_path = "model/kinyarwanda-hatespeech-model"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path)
label_encoder = joblib.load("model/kinyarwanda-hatespeech-model/label_encoder.pkl")

def predict(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
        pred = torch.argmax(outputs.logits, dim=1).item()
    return label_encoder.inverse_transform([pred])[0]

# Example
text = "Urwanko rw'abanyarwanda ruzamara iteka"
print(predict(text))  # e.g., 'normal'
```

---

## 🛡️ License

MIT License