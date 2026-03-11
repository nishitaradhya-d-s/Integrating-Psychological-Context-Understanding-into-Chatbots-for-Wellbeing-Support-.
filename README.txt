Personalized Mental Health Chatbot - Flask + SQLite
--------------------------------------------------
Location: /mnt/data/mental_health_chatbot

Quick start:
1. Create a virtual environment and activate it:
   python -m venv venv
   source venv/bin/activate  (Linux/Mac) or venv\Scripts\activate (Windows)

2. Install requirements:
   pip install -r requirements.txt

3. Initialize database (creates app.db and admin user nraja@gmail.com with password admin123):
   python create_db.py

4. Run the app:
   python app.py 
   Visit http://127.0.0.1:5000/

Admin credentials (change after first login):
  email: nraja@gmail.com
  password: admin123

Notes:
- TextBlob/NLTK corpora may be downloaded automatically by create_db.py; if not, run Python and use nltk.download('punkt') etc.
- Avatar uploads save to static/uploads/
- Chatbot uses TextBlob sentiment and simple rule-based responses.
