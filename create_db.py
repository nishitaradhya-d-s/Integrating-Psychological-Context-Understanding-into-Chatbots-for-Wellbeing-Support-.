# create_db.py - initialize SQLite DB and optionally load CSVs from /data
import sqlite3, os, csv
from textblob import download_corpora
from werkzeug.security import generate_password_hash

DB = os.path.join(os.path.dirname(__file__), 'app.db')

def create_tables(conn):
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'user',
        gender TEXT,
        age INTEGER,
        avatar TEXT,
        last_login TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        sentiment TEXT,
        polarity REAL,
        timestamp TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        specialization TEXT,
        city TEXT,
        contact TEXT,
        map_link TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS remedies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        condition TEXT,
        remedy_name TEXT,
        description TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote TEXT,
        author TEXT,
        date TEXT
    )
    ''')
    conn.commit()

def load_csv(conn, csv_path, table, cols):
    if not os.path.exists(csv_path):
        return
    with open(csv_path, encoding='utf-8') as f:
        dr = csv.DictReader(f)
        rows = []
        for r in dr:
            rows.append([r[c] for c in cols])
        placeholders = ','.join(['?']*len(cols))
        conn.executemany(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})", rows)
        conn.commit()

if __name__ == '__main__':
    print("Downloading TextBlob corpora (if needed)...")
    try:
        download_corpora.download_all()
    except Exception as e:
        print("Note: automatic corpora download failed or not needed.", e)
    conn = sqlite3.connect(DB)
    create_tables(conn)
    # seed admin
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email=?", ('nraja@gmail.com',))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                    ("Admin","nraja@gmail.com",generate_password_hash('admin123'),"admin"))
        conn.commit()
        print("Admin created: nraja@gmail.com (password: admin123)")
    # load CSVs if exist under data/
    load_csv(conn, os.path.join('data','doctors.csv'), 'doctors', ['name','specialization','city','contact','map_link'])
    load_csv(conn, os.path.join('data','remedies.csv'), 'remedies', ['condition','remedy_name','description'])
    load_csv(conn, os.path.join('data','quotes.csv'), 'quotes', ['quote','author','date'])
    conn.close()
    print("Database initialized at", DB)

// enhanced_chat.js - Add this to your dashboard HTML

class EnhancedChatInterface {
    constructor() {
        this.userId = localStorage.getItem('chat_user_id') || `user_${Date.now()}`;
        this.speechEnabled = false;
        this.conversationHistory = [];
        this.isTyping = false;
        
        // Initialize speech synthesis if available
        if ('speechSynthesis' in window) {
            this.speechEnabled = true;
        }
        
        this.initEventListeners();
        this.sendGreeting();
    }
    
    initEventListeners() {
        const chatInput = document.getElementById('chatInput');
        const sendButton = document.querySelector('.chat-input button');
        
        if (chatInput) {
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
        
        if (sendButton) {
            sendButton.addEventListener('click', () => this.sendMessage());
        }
    }
    
    async sendMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        
        if (!message || this.isTyping) return;
        
        // Clear input
        input.value = '';
        
        // Add user message
        this.addMessage('user', message);
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            const response = await this.getChatResponse(message);
            
            // Remove typing indicator
            this.hideTypingIndicator();
            
            // Add bot response
            this.addMessage('bot', response.reply);
            
            // Handle suggestions
            if (response.suggestions && response.suggestions.length > 0) {
                this.showQuickActions(response.suggestions);
            }
            
            // Handle resources if present
            if (response.resources) {
                this.showResources(response.resources);
            }
            
            // Speak response if enabled
            if (this.speechEnabled && response.reply) {
                this.speak(response.reply);
            }
            
            // Store in history
            this.conversationHistory.push({
                user: message,
                bot: response.reply,
                timestamp: new Date().toISOString(),
                metadata: response.metadata
            });
            
            // Update mood chart if sentiment data available
            if (response.sentiment_analysis) {
                this.updateMoodChart(response.sentiment_analysis);
            }
            
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage('bot', "I'm having trouble connecting. Please check your internet connection or try again.");
            console.error('Chat error:', error);
        }
    }
    
    async getChatResponse(message) {
        // Use your enhanced chatbot endpoint
        const response = await fetch('/api/enhanced_chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        });
        
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        
        return await response.json();
    }
    
    addMessage(sender, text) {
        const chatArea = document.getElementById('chatArea');
        if (!chatArea) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `bubble ${sender}`;
        
        if (sender === 'bot') {
            messageDiv.innerHTML = `
                <div class="bot-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">${this.formatMessage(text)}</div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="message-content">${this.formatMessage(text)}</div>
            `;
        }
        
        chatArea.appendChild(messageDiv);
        chatArea.scrollTop = chatArea.scrollHeight;
    }
    
    formatMessage(text) {
        // Convert markdown-like formatting to HTML
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>')
            .replace(/•/g, '•')
            .replace(/\. /g, '.<br>')
            .replace(/(🚨|😄|💭|🎵|💪|👋|🌈|💙|🤔|🧠|🌟|😊|🎶)/g, 
                    '<span class="emoji">$1</span>');
        
        // Add paragraph breaks for long texts
        const parts = formatted.split('<br><br>');
        if (parts.length > 1) {
            formatted = parts.map(part => `<p>${part}</p>`).join('');
        }
        
        return formatted;
    }
    
    showTypingIndicator() {
        const chatArea = document.getElementById('chatArea');
        if (!chatArea) return;
        
        this.isTyping = true;
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'bubble bot typing-indicator';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="bot-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        
        chatArea.appendChild(typingDiv);
        chatArea.scrollTop = chatArea.scrollHeight;
    }
    
    hideTypingIndicator() {
        this.isTyping = false;
        const typingEl = document.getElementById('typing-indicator');
        if (typingEl) {
            typingEl.remove();
        }
    }
    
    showQuickActions(suggestions) {
        const chatArea = document.getElementById('chatArea');
        if (!chatArea || !suggestions) return;
        
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'quick-actions';
        
        let html = '<div class="quick-actions-title">Quick Actions:</div>';
        html += '<div class="actions-container">';
        
        suggestions.forEach(action => {
            html += `
                <button class="quick-action-btn" 
                        onclick="chatInterface.handleQuickAction('${action.action}')"
                        title="${action.text}">
                    ${action.text}
                </button>
            `;
        });
        
        html += '</div>';
        actionsDiv.innerHTML = html;
        chatArea.appendChild(actionsDiv);
        chatArea.scrollTop = chatArea.scrollHeight;
    }
    
    handleQuickAction(action) {
        const actionMessages = {
            'breathing_exercise': "Guide me through a breathing exercise",
            'grounding_technique': "Help me with grounding techniques",
            'emergency_contacts': "Show me emergency contacts",
            'coping_strategy': "Suggest a coping strategy",
            'gratitude_exercise': "Help me practice gratitude",
            'mood_checkin': "How am I feeling right now?",
            'another_joke': "Tell me another joke",
            'different_genre': "Suggest different music genre"
        };
        
        const message = actionMessages[action] || "I need help with mental health support";
        document.getElementById('chatInput').value = message;
        this.sendMessage();
    }
    
    showResources(resources) {
        // Optional: Display resources in a structured way
        console.log('Available resources:', resources);
        // You can implement a modal or expandable section for resources
    }
    
    speak(text) {
        if (!this.speechEnabled) return;
        
        // Clean text for speech
        const cleanText = text
            .replace(/[🚨😄💭🎵💪👋🌈💙🤔🧠🌟😊🎶]/g, '')
            .replace(/\*\*/g, '')
            .replace(/<br>/g, '. ')
            .replace(/<[^>]*>/g, '');
        
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = 'en-US';
        utterance.rate = 0.9;
        utterance.pitch = 1;
        utterance.volume = 1;
        
        // Cancel any ongoing speech
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
    }
    
    sendGreeting() {
        setTimeout(() => {
            const greetings = [
                "👋 Hello! I'm your mental health companion. How are you feeling today?",
                "🌟 Welcome! I'm here to listen and support you. What's on your mind?",
                "💭 Hi there! Ready to talk about anything that's on your mind?"
            ];
            
            const randomGreeting = greetings[Math.floor(Math.random() * greetings.length)];
            this.addMessage('bot', randomGreeting);
        }, 1000);
    }
    
    updateMoodChart(sentimentData) {
        // Update your existing mood chart with new data
        if (window.moodChart && sentimentData.polarity !== undefined) {
            const now = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            
            // Add new data point
            window.moodChart.data.labels.push(now);
            window.moodChart.data.datasets[0].data.push(sentimentData.polarity);
            
            // Keep only last 10 points
            if (window.moodChart.data.labels.length > 10) {
                window.moodChart.data.labels.shift();
                window.moodChart.data.datasets[0].data.shift();
            }
            
            window.moodChart.update();
        }
    }
    
    toggleSpeech() {
        this.speechEnabled = !this.speechEnabled;
        return this.speechEnabled;
    }
    
    clearConversation() {
        const chatArea = document.getElementById('chatArea');
        if (chatArea) {
            chatArea.innerHTML = '';
        }
        this.conversationHistory = [];
        this.sendGreeting();
    }
}

// Initialize chat interface when page loads
document.addEventListener('DOMContentLoaded', function() {
    window.chatInterface = new EnhancedChatInterface();
    
    // Add CSS for enhanced chat
    const style = document.createElement('style');
    style.textContent = `
        .typing-indicator .typing-dots {
            display: flex;
            gap: 4px;
            align-items: center;
        }
        
        .typing-dots span {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: rgba(139, 198, 236, 0.7);
            animation: typing 1.4s infinite ease-in-out both;
        }
        
        .typing-dots span:nth-child(1) { animation-delay: -0.32s; }
        .typing-dots span:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes typing {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
        
        .quick-actions {
            margin: 15px 0;
            padding: 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .quick-actions-title {
            font-size: 0.9rem;
            color: rgba(232, 244, 248, 0.7);
            margin-bottom: 10px;
        }
        
        .actions-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .quick-action-btn {
            padding: 8px 12px;
            background: rgba(139, 198, 236, 0.15);
            border: 1px solid rgba(139, 198, 236, 0.3);
            color: var(--text-color);
            border-radius: 20px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.3s ease;
            white-space: nowrap;
            border: none;
        }
        
        .quick-action-btn:hover {
            background: rgba(139, 198, 236, 0.25);
            transform: translateY(-1px);
        }
        
        .emoji {
            font-size: 1.2em;
            margin-right: 4px;
        }
        
        .bubble.bot .message-content p {
            margin-bottom: 10px;
        }
        
        .bubble.bot .message-content strong {
            color: rgba(139, 198, 236, 0.9);
        }
    `;
    document.head.appendChild(style);
});