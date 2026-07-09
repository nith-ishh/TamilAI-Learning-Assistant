# TamilAI Learning Assistant 🤖

AI-Powered Learning Assistant for Tamil Medium Students

## 🚀 Quick Start

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Add your GEMINI_API_KEY to .env
python app.py
```

### Frontend
Open any HTML file in your browser or serve with:
```bash
cd frontend
npx serve .   # or use Live Server in VS Code
```

## 📁 Project Structure
```
TamilAI/
├── frontend/
│   ├── index.html       ← Landing page
│   ├── auth.html        ← Login / Register
│   ├── dashboard.html   ← Student dashboard
│   ├── tutor.html       ← AI Tutor chat
│   └── quiz.html        ← Quiz generator
├── backend/
│   ├── app.py           ← Flask entry point
│   ├── requirements.txt
│   ├── database/db.py   ← SQLite setup
│   ├── routes/          ← API endpoints
│   ├── services/        ← AI services (Gemini)
│   └── utils/           ← JWT helpers
└── README.md
```

## 🔑 Get Gemini API Key
1. Go to https://aistudio.google.com
2. Create API key (free tier available)
3. Add to backend/.env as GEMINI_API_KEY=...

## 📦 Modules Built So Far
- ✅ Module 1: Landing Page
- ✅ Module 2: Auth (Login/Register + JWT backend)
- ✅ Module 3: Student Dashboard
- ✅ Module 4: AI Tutor (Gemini powered)
- ✅ Module 5: Quiz Generator
- 🔜 Module 6: Notes AI
- 🔜 Module 7: Textbook Upload + RAG
- 🔜 Module 8: Voice Tutor
- 🔜 Module 9: Progress Analytics
- 🔜 Module 10: Study Planner
