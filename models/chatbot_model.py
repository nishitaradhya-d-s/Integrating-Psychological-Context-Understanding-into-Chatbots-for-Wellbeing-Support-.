# models/chatbot_model.py
from textblob import TextBlob
from datetime import datetime
import random
import re
import json
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartFriendlyChatbot:
    """Intelligent, friendly chatbot that acts like ChatGPT but with mental health awareness"""
    
    def __init__(self):
        # Knowledge bases
        self._init_patterns()
        self._init_responses()
        
        # User memory
        self.user_context = {}
        self.conversation_history = {}
        
        # Settings
        self.similarity_threshold = 0.3
        self.max_history = 20
        
        logger.info("Smart Friendly Chatbot initialized")
    
    def _init_patterns(self):
        """Initialize pattern recognition for various topics"""
        self.topic_patterns = {
            'greeting': {
                'patterns': ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening', 'whats up', 'sup'],
                'responses': self._get_greeting_responses()
            },
            'farewell': {
                'patterns': ['bye', 'goodbye', 'see you', 'talk later', 'catch you later', 'take care'],
                'responses': [
                    "Take care! Remember I'm always here if you need to talk. 🌟",
                    "Goodbye! Hope to chat with you again soon. 💫",
                    "See you later! Don't hesitate to reach out anytime. ✨"
                ]
            },
            'gratitude': {
                'patterns': ['thanks', 'thank you', 'appreciate', 'grateful', 'thankful'],
                'responses': [
                    "You're very welcome! 😊",
                    "Happy to help! Let me know if you need anything else. 🌈",
                    "Anytime! That's what I'm here for. 💝"
                ]
            },
            'achievement': {
                'patterns': ['won', 'win', 'achieved', 'success', 'passed', 'got promoted', 'got the job', 'accomplished', 
                           'finished', 'completed', 'did it', 'made it', 'first place', 'award', 'prize'],
                'responses': self._get_achievement_responses()
            },
            'feeling_good': {
                'patterns': ['good', 'great', 'awesome', 'fantastic', 'amazing', 'wonderful', 'excellent', 'happy', 'joyful'],
                'responses': self._get_feeling_good_responses()
            },
            'feeling_bad': {
                'patterns': ['bad', 'terrible', 'awful', 'horrible', 'sad', 'upset', 'depressed', 'anxious', 'stressed', 'worried'],
                'responses': self._get_feeling_bad_responses()
            },
            'weather': {
                'patterns': ['weather', 'sunny', 'rain', 'raining', 'cold', 'hot', 'temperature', 'climate'],
                'responses': [
                    "Weather can really affect our mood! ☀️🌧️",
                    "Hope the weather is treating you well today! 🌈",
                    "Whether it's sunny or rainy, I hope you're finding ways to enjoy your day! ☔🌞"
                ]
            },
            'hobbies': {
                'patterns': ['read', 'reading', 'book', 'movie', 'music', 'game', 'gaming', 'sport', 'exercise', 'gym', 
                           'draw', 'paint', 'art', 'cook', 'bake', 'travel', 'hike'],
                'responses': self._get_hobby_responses()
            },
            'food': {
                'patterns': ['food', 'eat', 'eating', 'meal', 'dinner', 'lunch', 'breakfast', 'snack', 'restaurant', 'cook', 'recipe'],
                'responses': [
                    "Food is such a wonderful part of life! 🍕🍔",
                    "Hope you're enjoying something delicious! 🍰",
                    "Good food can really brighten up a day! What are you having? 😋"
                ]
            },
            'work_study': {
                'patterns': ['work', 'job', 'office', 'study', 'exam', 'test', 'project', 'assignment', 'homework', 'deadline'],
                'responses': self._get_work_study_responses()
            },
            'family_friends': {
                'patterns': ['family', 'friend', 'friends', 'mom', 'dad', 'parent', 'sibling', 'brother', 'sister', 'cousin'],
                'responses': [
                    "Relationships are so important for our wellbeing! 👨‍👩‍👧‍👦",
                    "Hope you're surrounded by supportive people in your life! 💖",
                    "Connecting with loved ones can make all the difference. 😊"
                ]
            },
            'future_plans': {
                'patterns': ['tomorrow', 'next week', 'next month', 'future', 'plan', 'plans', 'goal', 'dream'],
                'responses': [
                    "Planning for the future shows you're proactive! 🎯",
                    "Having goals gives us direction and purpose. 🌟",
                    "Future plans can be exciting! What are you looking forward to? 🚀"
                ]
            },
            'joke_request': {
                'patterns': ['joke', 'funny', 'laugh', 'humor', 'make me laugh'],
                'responses': self._get_joke_responses()
            },
            'advice_request': {
                'patterns': ['advice', 'suggestion', 'recommend', 'what should i', 'how can i', 'help me'],
                'responses': [
                    "I'd be happy to offer some thoughts! Could you tell me more about what you're looking for? 💭",
                    "I can try to help! What specific situation are you dealing with? 🤔",
                    "Let me think about that... Could you give me a bit more context? 🧠"
                ]
            },
            'meaningless': {
                'patterns': [],  # Special case for gibberish
                'responses': [
                    "Hmm, I didn't quite understand that. Could you rephrase or tell me more about what's on your mind? 🤔",
                    "I want to make sure I understand you correctly. Could you explain that differently? 💭",
                    "I'm here to have a meaningful conversation. Could you tell me more about what you'd like to discuss? 🎯"
                ]
            }
        }
    
    def _get_greeting_responses(self):
        """Get varied greeting responses"""
        return [
            "Hey there! 👋 How's your day going?",
            "Hello! 😊 Great to chat with you! What's new?",
            "Hi! 🌟 What would you like to talk about today?",
            "Hey! 🎉 How are you feeling today?",
            "Hi there! 💫 It's nice to hear from you!"
        ]
    
    def _get_achievement_responses(self):
        """Get congratulatory responses for achievements"""
        return [
            "🎉 That's amazing! Congratulations on your achievement! You should be proud!",
            "🌟 Wow, that's fantastic news! Well done!",
            "🏆 Congratulations! That's a big accomplishment!",
            "✨ That's wonderful! You worked hard for this, enjoy the success!",
            "🥳 Awesome news! Celebrate this achievement!",
            "👏 Incredible! You deserve all the recognition!",
            "🎊 Congratulations! This is just the beginning of more great things!",
            "💫 That's superb! Your hard work paid off!"
        ]
    
    def _get_feeling_good_responses(self):
        """Get responses for good feelings"""
        return [
            "That's wonderful to hear! 😊 What's making you feel so good?",
            "I'm so glad you're feeling great! 🌟 Keep riding that positive wave!",
            "Awesome! Positive energy is contagious! 🌈",
            "That's fantastic! Enjoy this good mood! 🎉",
            "Great to hear! What's bringing you joy today? 💖"
        ]
    
    def _get_feeling_bad_responses(self):
        """Get empathetic responses for bad feelings"""
        return [
            "I'm sorry to hear you're feeling that way. 💙 Would you like to talk about it?",
            "That sounds difficult. Remember it's okay to not be okay. 🌧️",
            "I'm here for you. Would it help to share what's going on? 🤗",
            "It's completely valid to feel that way. You're not alone. 💝",
            "Thank you for sharing that with me. How can I support you right now? 🌻"
        ]
    
    def _get_hobby_responses(self):
        """Get responses about hobbies"""
        return [
            "That's a great way to spend your time! Hobbies can be so fulfilling. 🎨",
            "Nice! Having hobbies you enjoy is important for wellbeing. 🎮",
            "That sounds fun! Hobbies help us relax and express ourselves. 🎵",
            "Wonderful! What do you enjoy most about it? 🏃‍♂️",
            "Great hobby! It's nice to have activities that bring you joy. 📚"
        ]
    
    def _get_work_study_responses(self):
        """Get responses about work/study"""
        return [
            "Work/study can be challenging but also rewarding! 💼",
            "Hope you're finding balance with your responsibilities. ⚖️",
            "Remember to take breaks and care for yourself during busy times. ☕",
            "You're doing important work! How's it going? 📈",
            "Finding meaning in what we do makes all the difference. 🌟"
        ]
    
    def _get_joke_responses(self):
        """Get joke responses"""
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything! 😄",
            "What do you call a fake noodle? An impasta! 🍝",
            "Why did the scarecrow win an award? Because he was outstanding in his field! 🌾",
            "What do you call cheese that isn't yours? Nacho cheese! 🧀",
            "Why couldn't the bicycle stand up by itself? It was two tired! 🚲",
            "What do you call a bear with no teeth? A gummy bear! 🐻",
            "Why did the math book look so sad? Because it had too many problems! 📚",
            "What did one ocean say to the other ocean? Nothing, they just waved! 🌊",
            "Why don't eggs tell jokes? They'd crack each other up! 🥚",
            "What do you call a sleeping bull? A bulldozer! 🐂"
        ]
        return jokes
    
    def _init_responses(self):
        """Initialize intelligent response templates"""
        self.response_templates = {
            'follow_up_question': [
                "What do you think about that? 💭",
                "How does that make you feel? 🤔",
                "Tell me more about that. 🎤",
                "What happened next? ⏭️",
                "That's interesting! What else? 🌟"
            ],
            'encouragement': [
                "You're doing great! 👍",
                "Thanks for sharing that with me. 💖",
                "I appreciate our conversation. 😊",
                "You have interesting perspectives! 🧠",
                "I'm enjoying our chat! 🎉"
            ],
            'clarification': [
                "Could you tell me more about that? 🤔",
                "I want to make sure I understand correctly... 💭",
                "What exactly do you mean by that? 🎯",
                "Could you elaborate a bit more? 📝",
                "Help me understand your perspective better. 👂"
            ],
            'transition': [
                "Changing topics a bit... what have you been up to lately? 🔄",
                "By the way, how has your week been? 📅",
                "On a different note, what's something good that happened today? ✨",
                "Speaking of which, what are you looking forward to? 🎯",
                "Random question: what's your favorite way to relax? 🛋️"
            ]
        }
    
    def is_gibberish(self, text: str) -> bool:
        """Check if text is gibberish/meaningless"""
        # Remove common words and check if what remains looks like random characters
        common_words = ['the', 'and', 'you', 'that', 'this', 'with', 'for', 'have', 'are', 'was',
                       'what', 'when', 'where', 'why', 'how', 'can', 'will', 'not', 'but', 'like',
                       'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
                       'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must']
        
        words = text.lower().split()
        meaningful_words = [word for word in words if word not in common_words and len(word) > 2]
        
        # If most words are short or don't look like real words
        if len(meaningful_words) == 0 and len(text.split()) > 2:
            return True
        
        # Check character patterns (too many repeated characters)
        if re.search(r'(.)\1{3,}', text):  # 4+ same characters in a row
            return True
        
        # Check for random keyboard mashing (limited character set)
        if len(text) > 10:
            unique_chars = len(set(text.lower()))
            if unique_chars < 5:  # Very limited character set
                return True
            
            # Check if it's mostly non-alphabetic
            alpha_chars = sum(1 for c in text if c.isalpha())
            if alpha_chars / len(text) < 0.3:  # Less than 30% alphabetic
                return True
        
        # Check for nonsensical word-like patterns
        if len(text) > 15:
            # Look for patterns like "asdfasdf" or "qwertyqwerty"
            if re.search(r'([a-z]{3,})\1', text.lower()):  # Repeated substring
                return True
        
        return False
    
    def get_topic(self, text: str) -> str:
        """Identify the main topic of the message"""
        text_lower = text.lower()
        
        # Check each topic pattern
        for topic, data in self.topic_patterns.items():
            for pattern in data['patterns']:
                if pattern in text_lower:
                    return topic
        
        # Check for specific phrase patterns
        if self.is_gibberish(text):
            return 'meaningless'
        
        # Check for achievement statements
        achievement_phrases = [
            r'i (?:won|got|achieved|passed|completed|finished)',
            r'i (?:am|was) (?:promoted|accepted|selected|chosen)',
            r'i (?:got|received) (?:the|a) (?:job|award|prize)',
            r'i (?:came|got) (?:first|second|third)',
            r'i (?:beat|defeated)'
        ]
        
        for phrase in achievement_phrases:
            if re.search(phrase, text_lower):
                return 'achievement'
        
        return 'general'
    
    def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of text"""
        try:
            tb = TextBlob(text)
            polarity = round(tb.sentiment.polarity, 3)
            subjectivity = round(tb.sentiment.subjectivity, 3)
            
            if polarity > 0.3:
                label = 'positive'
                emoji = '😊'
            elif polarity > 0.1:
                label = 'slightly_positive'
                emoji = '🙂'
            elif polarity < -0.3:
                label = 'negative'
                emoji = '😔'
            elif polarity < -0.1:
                label = 'slightly_negative'
                emoji = '😕'
            else:
                label = 'neutral'
                emoji = '😐'
        except:
            # Default sentiment if analysis fails
            polarity = 0.0
            subjectivity = 0.0
            label = 'neutral'
            emoji = '😐'
        
        return {
            'polarity': polarity,
            'subjectivity': subjectivity,
            'label': label,
            'emoji': emoji,
            'text_length': len(text)
        }
    
    def get_response_for_topic(self, topic: str, text: str = None) -> str:
        """Get appropriate response for a topic"""
        if topic in self.topic_patterns:
            responses = self.topic_patterns[topic]['responses']
            
            # For achievements, check for specific details
            if topic == 'achievement' and text:
                achievement_type = self._identify_achievement_type(text)
                if achievement_type:
                    responses = self._get_specific_achievement_responses(achievement_type)
            
            return random.choice(responses)
        
        # Default general response
        general_responses = [
            "Thanks for sharing that! 😊 What's on your mind?",
            "Interesting! Tell me more about that. 💭",
            "I appreciate you sharing that with me. 🌟",
            "That's good to know! How are you feeling about it? 🤔",
            "Thanks for telling me! What else would you like to chat about? 🎤",
            "Got it! What would you like to talk about next? 🎯",
            "I see! Is there anything specific you'd like to discuss? 🧠",
            "Alright! Feel free to share whatever you're comfortable with. 💖"
        ]
        return random.choice(general_responses)
    
    def _identify_achievement_type(self, text: str) -> Optional[str]:
        """Identify specific type of achievement"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['won', 'win', 'first place', 'tournament', 'competition', 'contest', 'champion', 'victory']):
            return 'competition'
        elif any(word in text_lower for word in ['promoted', 'promotion', 'job', 'position', 'career', 'raise', 'salary']):
            return 'career'
        elif any(word in text_lower for word in ['passed', 'exam', 'test', 'graduated', 'degree', 'school', 'college', 'university', 'marks', 'grades']):
            return 'academic'
        elif any(word in text_lower for word in ['finished', 'completed', 'project', 'task', 'goal', 'milestone']):
            return 'completion'
        elif any(word in text_lower for word in ['award', 'prize', 'recognition', 'honor', 'medal', 'trophy']):
            return 'recognition'
        
        return None
    
    def _get_specific_achievement_responses(self, achievement_type: str) -> List[str]:
        """Get specific responses for different achievement types"""
        responses = {
            'competition': [
                "🏆 Incredible! Winning takes skill and determination! You should be so proud!",
                "🎊 Champion! That's amazing! All your hard work paid off!",
                "🥇 First place! That's outstanding! You truly earned this victory!",
                "🌟 Tournament winner! What an achievement! Celebrate this moment!",
                "👑 Victory! You're a true champion! Enjoy this well-deserved success!"
            ],
            'career': [
                "💼 Congratulations on the promotion/new job! That's a huge step forward in your career!",
                "📈 Amazing career news! Your talents are being recognized!",
                "🎯 Well done on achieving this career milestone! More success ahead!",
                "🚀 Career advancement! That's fantastic! Your hard work is paying off!",
                "💼 Excellent career progress! You're definitely going places!"
            ],
            'academic': [
                "🎓 Congratulations on passing/graduating! All that studying paid off!",
                "📚 Academic success! That's wonderful! You should be very proud!",
                "🏅 Well done on your academic achievement! Knowledge is power!",
                "🌟 Excellent academic news! Your dedication to learning shows!",
                "📝 Test success! That's a testament to your hard work and intelligence!"
            ],
            'completion': [
                "✅ Mission accomplished! Completing something feels so satisfying!",
                "🎯 Goal achieved! That's fantastic! What's next on your list?",
                "✨ Project completed! Great work seeing it through to the end!",
                "🏁 Finished! Crossing the finish line is always an amazing feeling!",
                "✓ Task done! You should feel proud of your accomplishment!"
            ],
            'recognition': [
                "🏅 Award winner! That's incredible recognition for your efforts!",
                "⭐ Prize recipient! Well deserved! Your talents are shining!",
                "🎖️ Recognition achieved! That's a testament to your hard work!",
                "💫 Honor received! What a wonderful acknowledgment of your abilities!",
                "👏 Awarded! Your dedication has been properly recognized!"
            ]
        }
        
        return responses.get(achievement_type, self._get_achievement_responses())
    
    def generate_response(self, user_id: str, message: str) -> Dict:
        """Generate intelligent, friendly response"""
        
        # Initialize user context if needed
        if user_id not in self.user_context:
            self.user_context[user_id] = {
                'conversation_count': 0,
                'last_topic': None,
                'preferred_topics': [],
                'sentiment_trend': []
            }
        
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        # Clean message
        message = message.strip()
        
        # Check for empty message
        if not message:
            response_text = "I'd love to chat with you! What would you like to talk about? 😊"
            sentiment = {'label': 'neutral', 'emoji': '😊'}
            topic = 'greeting'
        
        # Check for gibberish/meaningless input
        elif self.is_gibberish(message):
            response_text = random.choice(self.topic_patterns['meaningless']['responses'])
            sentiment = {'label': 'neutral', 'emoji': '🤔'}
            topic = 'meaningless'
        
        else:
            # Analyze sentiment
            sentiment = self.analyze_sentiment(message)
            
            # Get topic
            topic = self.get_topic(message)
            
            # Get base response for topic
            response_text = self.get_response_for_topic(topic, message)
            
            # Add follow-up or transition based on conversation flow
            response_text = self._enhance_response(response_text, user_id, topic)
        
        # Update user context
        self._update_user_context(user_id, message, topic, sentiment)
        
        # Store conversation
        self.conversation_history[user_id].append({
            'user': message,
            'bot': response_text,
            'topic': topic,
            'timestamp': datetime.utcnow().isoformat(),
            'sentiment': sentiment
        })
        
        # Keep history manageable
        if len(self.conversation_history[user_id]) > self.max_history:
            self.conversation_history[user_id] = self.conversation_history[user_id][-self.max_history:]
        
        # Prepare response
        response = {
            'reply': response_text,
            'sentiment_analysis': sentiment,
            'topic': topic,
            'timestamp': datetime.utcnow().isoformat(),
            'conversation_depth': len(self.conversation_history[user_id])
        }
        
        # Add suggestions if appropriate
        if topic != 'meaningless' and random.random() > 0.5:  # 50% chance
            response['suggestions'] = self._generate_suggestions(topic, sentiment)
        
        return response
    
    def _enhance_response(self, base_response: str, user_id: str, current_topic: str) -> str:
        """Enhance response with follow-ups or transitions"""
        context = self.user_context[user_id]
        
        # If same topic as last time, add a follow-up question
        if context['last_topic'] == current_topic and current_topic not in ['greeting', 'farewell', 'meaningless']:
            follow_up = random.choice(self.response_templates['follow_up_question'])
            return f"{base_response}\n\n{follow_up}"
        
        # If many conversations, occasionally add a transition
        if context['conversation_count'] > 3 and random.random() > 0.7:  # 30% chance
            transition = random.choice(self.response_templates['transition'])
            return f"{base_response}\n\n{transition}"
        
        # Add encouragement sometimes
        if random.random() > 0.6:  # 40% chance
            encouragement = random.choice(self.response_templates['encouragement'])
            return f"{base_response}\n\n{encouragement}"
        
        return base_response
    
    def _update_user_context(self, user_id: str, message: str, topic: str, sentiment: Dict):
        """Update user context information"""
        context = self.user_context[user_id]
        
        context['conversation_count'] += 1
        context['last_topic'] = topic
        context['last_interaction'] = datetime.utcnow().isoformat()
        
        # Track sentiment trend
        context['sentiment_trend'].append(sentiment['label'])
        if len(context['sentiment_trend']) > 10:
            context['sentiment_trend'] = context['sentiment_trend'][-10:]
        
        # Track preferred topics (if not meaningless)
        if topic != 'meaningless' and topic not in context['preferred_topics']:
            context['preferred_topics'].append(topic)
            if len(context['preferred_topics']) > 5:
                context['preferred_topics'] = context['preferred_topics'][-5:]
    
    def _generate_suggestions(self, topic: str, sentiment: Dict) -> List[Dict]:
        """Generate conversation suggestions"""
        suggestions = []
        
        if sentiment['label'] in ['positive', 'slightly_positive']:
            suggestions.append({'action': 'share_more', 'text': 'Share more good news'})
            suggestions.append({'action': 'celebrate', 'text': 'How to celebrate?'})
        elif sentiment['label'] in ['negative', 'slightly_negative']:
            suggestions.append({'action': 'coping', 'text': 'Need coping strategies?'})
            suggestions.append({'action': 'vent', 'text': 'Want to talk about it?'})
        else:
            suggestions.append({'action': 'continue', 'text': 'Continue conversation'})
            suggestions.append({'action': 'new_topic', 'text': 'Change topic'})
        
        # Topic-specific suggestions
        if topic == 'achievement':
            suggestions.append({'action': 'share_details', 'text': 'Share details'})
            suggestions.append({'action': 'future_goals', 'text': 'Next goals?'})
        elif topic == 'hobbies':
            suggestions.append({'action': 'share_hobby', 'text': 'Tell me about your hobby'})
            suggestions.append({'action': 'recommendations', 'text': 'Need recommendations?'})
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def get_conversation_summary(self, user_id: str) -> Dict:
        """Get summary of user's conversation history"""
        if user_id not in self.conversation_history:
            return {'error': 'No conversation history found'}
        
        history = self.conversation_history[user_id]
        if not history:
            return {'error': 'No conversation history found'}
        
        # Analyze topics
        topics = [msg.get('topic', 'unknown') for msg in history]
        topic_counts = {}
        for topic in topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # Analyze sentiment trends
        sentiments = [msg.get('sentiment', {}).get('label', 'neutral') for msg in history]
        sentiment_counts = {}
        for sentiment in sentiments:
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        
        return {
            'total_messages': len(history),
            'favorite_topics': sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:3],
            'sentiment_distribution': sentiment_counts,
            'last_topic': topics[-1] if topics else 'unknown',
            'conversation_depth': len(history)
        }        

# Create global instance
chatbot = SmartFriendlyChatbot()

# Export functions
def analyze_sentiment(text: str) -> Dict:
    """Analyze sentiment of text"""
    return chatbot.analyze_sentiment(text)

def generate_response(user_id: str, message: str) -> Dict:
    """Generate response for user message"""
    return chatbot.generate_response(user_id, message)

# Also export helper functions
def is_meaningless_text(text: str) -> bool:
    """Check if text is meaningless/gibberish"""
    return chatbot.is_gibberish(text)

def get_conversation_summary(user_id: str) -> Dict:
    """Get conversation summary"""
    return chatbot.get_conversation_summary(user_id)