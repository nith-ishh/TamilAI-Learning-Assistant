"""
TamilAI - Google Gemini AI Service
Handles all AI calls: tutor, quiz generation, notes generation
"""

import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
genai.configure(api_key=GEMINI_API_KEY)

# Model config
_model = None

def _get_model():
    global _model
    if _model is None:
        _model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            generation_config={
                'temperature': 0.7,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 4096,
            }
        )
    return _model


# ─── System Prompt ────────────────────────────────────────────
TUTOR_SYSTEM = """You are TamilAI Tutor, an expert AI teacher for Tamil-medium school students (Class 6-12, Samacheer Kalvi syllabus).

Your role:
- Explain concepts in SIMPLE Tamil that any school student can understand
- Use clear, friendly, encouraging language
- Break down complex topics into easy steps
- Use emojis to make explanations fun and visual
- Provide real-life examples Tamil students can relate to
- Format answers with clear headings, bullet points, and equations where needed
- Always end with encouragement and offer to explain further

Language rules:
- Primary language: Tamil (தமிழ்)
- Use Tamil script for explanations
- Technical terms: write in Tamil first, then English in brackets
- Math equations: write clearly with proper formatting
- If student asks in English, respond in Tamil with English terms where needed

Format guidelines:
- Use **bold** for important terms
- Use numbered lists for steps
- Use bullet points for features/points
- Use `code blocks` for formulas and equations
- Keep paragraphs short and readable
- Always start with a warm acknowledgment

After your main explanation, suggest 3 related topics as a JSON array in this exact format:
[RELATED:["topic1","topic2","topic3"]]"""


# ─── Tamil Tutor Response ─────────────────────────────────────
def get_tamil_tutor_response(message: str, subject: str = 'General', history: list = None):
    """
    Get AI tutor response for a student question.
    Returns: (response_text, related_topics)
    """
    model = _get_model()

    # Build conversation history
    chat_history = []
    if history:
        for msg in history[-8:]:   # last 8 messages for context window efficiency
            role = 'user' if msg.get('role') == 'user' else 'model'
            chat_history.append({
                'role': role,
                'parts': [msg.get('content', '')]
            })

    # Compose prompt
    subject_context = f"\n\n[Subject context: {subject}]" if subject != 'General' else ''
    full_prompt = f"{TUTOR_SYSTEM}{subject_context}\n\nStudent question: {message}"

    if chat_history:
        chat = model.start_chat(history=chat_history)
        response = chat.send_message(full_prompt)
    else:
        response = model.generate_content(full_prompt)

    raw_text = response.text or ''

    # Extract related topics
    related_topics = []
    if '[RELATED:' in raw_text:
        try:
            start = raw_text.index('[RELATED:') + 9
            end   = raw_text.index(']', start) + 1
            topics_json = raw_text[start:end]
            related_topics = json.loads(topics_json)
            raw_text = raw_text[:raw_text.index('[RELATED:')].strip()
        except (ValueError, json.JSONDecodeError):
            pass

    return raw_text, related_topics


# ─── Quiz Generation ──────────────────────────────────────────
def generate_quiz(topic, subject, num_questions=5,
                  difficulty="medium",
                  quiz_type="mcq",
                  context=""):

    model = _get_model()

    prompt = f"""
You are an expert Tamil school teacher.

Generate {num_questions} Multiple Choice Questions.

Topic: {topic}
Subject: {subject}
Difficulty: {difficulty}

Return ONLY JSON.

Example:

[
 {{
   "id":1,
   "question":"Question",
   "type":"mcq",
   "options":[
      "Option A",
      "Option B",
      "Option C",
      "Option D"
   ],
   "correct":"Option B",
   "correct_index":1,
   "explanation":"Explain why option B is correct.",
   "difficulty":"{difficulty}"
 }}
]

Do not write markdown.
Do not write ```json.
Do not explain anything.
Return only JSON.
"""

    response = model.generate_content(prompt)

    text = response.text.strip()

    text = text.replace("```json", "")
    text = text.replace("```", "")
    text = text.strip()

    print("\n========== GEMINI RESPONSE ==========")
    print(text)
    print("=====================================\n")

    return json.loads(text)


# ─── Notes Generation ─────────────────────────────────────────
def generate_notes(topic: str, subject: str, note_type: str = 'summary',
                   context: str = '') -> dict:
    """
    Generate AI notes for a topic.
    note_type: summary | keypoints | flashcards | mindmap | revision
    Returns dict with note content.
    """
    model = _get_model()

    type_prompts = {
        'summary': 'a comprehensive summary with headings and subheadings',
        'keypoints': 'key points as a numbered list with brief explanations',
        'flashcards': '10 flashcard pairs in Q&A format for quick revision',
        'mindmap': 'a mind map structure with main topic and sub-branches',
        'revision': 'a quick revision sheet with important formulas, definitions, and facts',
    }

    prompt = f"""You are an expert Tamil school teacher creating study notes.

Topic: {topic}
Subject: {subject}
Note Type: {type_prompts.get(note_type, 'summary')}
{"Textbook content: " + context[:3000] if context else ""}

Create {note_type} notes in Tamil for Samacheer Kalvi Class 10-12 students.

Return a JSON object with this structure:
{{
  "title": "Topic title in Tamil",
  "type": "{note_type}",
  "subject": "{subject}",
  "content": "Main content in Tamil with markdown formatting",
  "key_terms": ["term1", "term2", "term3"],
  "important_formulas": ["formula1", "formula2"],
  "exam_tips": "Important exam tips in Tamil",
  "difficulty_level": "easy/medium/hard"
}}

Make content rich, clear, and exam-focused. Use Tamil language throughout.
Return ONLY the JSON object, no other text."""

    response = model.generate_content(prompt)
    text = response.text.strip()

    if text.startswith('```'):
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]
    text = text.strip().rstrip('`').strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            'title': topic,
            'type': note_type,
            'subject': subject,
            'content': f'## {topic}\n\nNote generation in progress. Please try again.',
            'key_terms': [],
            'important_formulas': [],
            'exam_tips': '',
            'difficulty_level': 'medium',
        }


# ─── Study Plan Generation ────────────────────────────────────
def generate_study_plan(user_data: dict) -> dict:
    """
    Generate a personalized study plan based on user performance.
    """
    model = _get_model()

    prompt = f"""You are a Tamil school education expert creating a personalized study plan.

Student data:
- Class: {user_data.get('class_grade', 'Class 10')}
- Weak subjects: {user_data.get('weak_subjects', [])}
- Strong subjects: {user_data.get('strong_subjects', [])}
- Study hours available: {user_data.get('daily_hours', 3)} hours/day
- Upcoming exam: {user_data.get('exam_date', 'Next month')}
- Learning streak: {user_data.get('streak', 0)} days

Create a 7-day personalized study plan in Tamil.
Return ONLY a JSON object:
{{
  "plan_title": "Plan title",
  "weekly_goal": "Goal description in Tamil",
  "days": [
    {{
      "day": "Monday / திங்கள்",
      "date": "Day 1",
      "sessions": [
        {{
          "time": "4:00 PM - 5:00 PM",
          "subject": "Subject",
          "topic": "Topic in Tamil",
          "activity": "study/quiz/revision/practice",
          "duration_mins": 60,
          "priority": "high/medium/low"
        }}
      ],
      "daily_goal": "Daily goal in Tamil"
    }}
  ],
  "tips": ["tip1 in Tamil", "tip2", "tip3"]
}}"""

    response = model.generate_content(prompt)
    text = response.text.strip()
    if text.startswith('```'):
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]
    text = text.strip().rstrip('`').strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {'error': 'Study plan generation failed. Please try again.'}
    

