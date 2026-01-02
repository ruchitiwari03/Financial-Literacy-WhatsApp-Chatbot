# 💰 Financial Literacy WhatsApp Chatbot

A **multilingual WhatsApp chatbot** that explains financial terms, provides saving tips, and sends scam alerts in **English and Hindi** using AI-powered retrieval and intelligent fallback.

This project aims to improve **financial awareness**, encourage **smart money habits**, and protect users from **financial fraud** through real-time WhatsApp conversations.

---

## 🚀 Features

- 📚 Explains financial terms (Budget, SIP, Credit Score, Inflation, etc.)
- 💡 Provides practical saving and budgeting tips
- 🚨 Sends alerts about common financial scams
- 🌐 Supports **English & Hindi**
- 🤖 Uses **RAG (Retrieval-Augmented Generation)**
- ⚡ Real-time WhatsApp message handling
- 🔐 Secure configuration using environment variables

---

## 🛠️ Tech Stack

- **Python 3.10+**
- **Flask**
- **Google Gemini API**
- **WhatsApp Cloud API**
- **aiohttp**
- **python-dotenv**

---

## 📂 Project Structure

financial-literacy-whatsapp-bot/
│
├── chatbot.py # Core RAG logic + Gemini fallback
├── whatsapp_quickstart.py # WhatsApp webhook server
├── financial_data.json # Financial knowledge base
├── requirements.txt
├── .env.example # Environment variable template
├── .gitignore
└── README.md

yaml
Copy code

---

## 🔑 Environment Setup

### 1️⃣ Clone the repository
```bash
git clone https://github.com/your-username/financial-literacy-whatsapp-bot.git
cd financial-literacy-whatsapp-bot
2️⃣ Create a virtual environment (recommended)
bash
Copy code
python -m venv venv
source venv/bin/activate        # Linux / Mac
venv\Scripts\activate           # Windows
3️⃣ Install dependencies
bash
Copy code
pip install -r requirements.txt
4️⃣ Configure environment variables
Create a .env file using .env.example:

env
Copy code
GEMINI_API_KEY=your_gemini_api_key
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
PHONE_NUMBER_ID=your_phone_number_id
VERIFY_TOKEN=your_verify_token
VERSION=v18.0
⚠️ Important:

Never commit .env to GitHub

Always keep API keys private

▶️ Running the Application
bash
Copy code
python whatsapp_quickstart.py
The Flask server will start at:

bash
Copy code
http://localhost:5000/webhook
🔗 WhatsApp Webhook Configuration
Open Meta Developer Console

Add webhook URL:

arduino
Copy code
https://<your-ngrok-url>/webhook
Set the Verify Token (same as .env)

Subscribe to messages events

💬 Example User Queries
What is SIP?

Give me 3 saving tips

बचत क्या है

Explain credit score

Latest financial scams

🧠 How It Works (High-Level Flow)
User sends a WhatsApp message

Language is auto-detected (English / Hindi)

Local financial knowledge base is searched (RAG)

If no match is found → Gemini AI fallback

Response is sent back via WhatsApp Cloud API

🔐 Security Best Practices
❌ Never commit .env

❌ Never expose API keys in code

✅ Use .env.example

✅ Rotate keys immediately if leaked

⭐ Future Enhancements
User session memory

More Indian financial terms (SIP, GST, ITR, etc.)

Additional language support

Analytics dashboard

Cloud deployment (Render / Railway / AWS)

👤 Author
Ruchi Tiwari
🎓 Computer Science | Data Analytics Enthusiast
📌 Aspiring Data Analyst / Business Intelligence Analyst

📧 Email: ruchitiwari0307@gmail.com
🔗 LinkedIn: linkedin.com/in/ruchitiwari03
💻 GitHub: github.com/ruchitiwari03
