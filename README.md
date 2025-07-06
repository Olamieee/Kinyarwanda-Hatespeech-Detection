# 🇷🇼 Kinyarwanda Hate Speech Detection App

A machine learning-powered app that detects **hate**, **offensive**, or **normal** speech in **Kinyarwanda** social media text using logistic regression. Also includes a **Chrome extension** (Developer Mode) for real-time classification.

---

## 🚀 Features

- ✅ Detects `hate`, `offensive`, or `normal` content in Kinyarwanda
- 🧠 Trained with Logistic Regression + TF-IDF
- 📊 Balanced dataset for fair classification
- 🌐 Web interface for testing input text
- 🧩 Chrome extension for live web integration

---

## 📁 Project Structure

```
project/
│
├── app 2.py                       # Main app script (e.g., Streamlit or Flask)
├── hate_speech_model.ipynb.txt   # Notebook (text version of training pipeline)
├── kinyarwanda_hatespeech_noisy.csv  # Initial dataset
├── final_dataset.tsv             # Additional scraped dataset
├── model.pkl                     # Trained logistic regression model
├── tfidf_vectorizer.pkl          # TF-IDF vectorizer used during training
├── extension/                    # Chrome extension source files
│   ├── manifest.json
│   ├── popup.html
│   ├── popup.js
│   └── style.css
```

---

## 🛠️ Installation (Web App)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/kinyarwanda-hate-speech-app.git
cd kinyarwanda-hate-speech-app
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` is missing, use:

```txt
pandas
numpy
scikit-learn
joblib
streamlit  # or flask if applicable
```

### Step 4 (Optional): Train the Model

Open the notebook:

```bash
jupyter notebook hate_speech_model.ipynb
```

This will:
- Merge + clean datasets
- Vectorize text
- Train logistic regression
- Export `model.pkl` & `tfidf_vectorizer.pkl`

### Step 5: Run the App

#### Run with Flask

```bash
python app\ 2.py
```

Visit the app at `http://localhost:5000` (default Flask port).

---

## 🧩 Chrome Extension (Developer Mode Only)

### Step 1: Load Unpacked Extension

1. Go to `chrome://extensions/`
2. Enable **Developer Mode** (top right)
3. Click **Load Unpacked**
4. Select the `extension/` folder

### Step 2: Use the Extension

- Click the extension icon in Chrome toolbar
- Paste or highlight Kinyarwanda text
- Click **Analyze**
- Classification result will display below

> Note: Extension communicates with local server (e.g., Streamlit app) via `localhost`. Ensure the web app is running before using the extension.

---

## 🔍 Model Summary

- **Algorithm**: Logistic Regression (sklearn)
- **Feature Extraction**: TF-IDF (1–3 grams)
- **Accuracy**: ~95% on test data
- **Classes**: `hate`, `offensive`, `normal`

---

## 🧪 Example Usage (Manual)

```python
import joblib

model = joblib.load("model.pkl")
vectorizer = joblib.load("tfidf_vectorizer.pkl")

def predict(text):
    X = vectorizer.transform([text])
    return model.predict(X)[0]
```

---

## 🛡️ License

This project is licensed under the **MIT License**.

---

## 🙌 Credits

Built by [Your Name] — Contributions welcome!
