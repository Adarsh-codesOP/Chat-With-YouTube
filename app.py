from flask import Flask, render_template, request, jsonify
import re
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import os
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables
load_dotenv()

# Configure Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')  # Make sure to set this in your .env file
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Initialize chat history
chat = model.start_chat(history=[])

# Store chat history and transcript
chat_messages = []
current_transcript = ""

def extract_video_id(url):
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        formatted_transcript = ""
        for entry in transcript_list:
            time = entry['start']
            text = entry['text']
            formatted_transcript += f"[{int(time)}s] {text}\n"
        return formatted_transcript
    except Exception as e:
        print(f"Error getting transcript: {str(e)}")
        return None

def get_gemini_response(message, timestamp, transcript):
    try:
        if not hasattr(get_gemini_response, 'chat'):
            initial_context = f"""You are a friendly, knowledgeable, and engaging AI assistant having a natural conversation about a YouTube video. 

Role and Personality:
- Maintain a conversational and approachable tone, akin to a knowledgeable guide
- Provide clear, concise, and accurate explanations
- Use natural language, avoiding formal markers or rigid structures
- Reference specific parts of the video when relevant, ensuring responses are grounded in the transcript
- Encourage deeper discussion through thoughtful follow-up questions
- Acknowledge any uncertainties transparently
- Ensure responses are focused, relevant, and strictly supported by the transcript
- If the user does not ask a question, refrain from providing unsolicited information; instead, maintain a human-like conversational flow with brevity

Here's the video transcript:
{transcript}

Guidelines:
- Maintain a natural conversation flow, providing informative and engaging responses
- Ensure all information is directly supported by the transcript
- Use concise language, providing context without unnecessary elaboration
- Avoid using asterisks or formal markers in the conversation"""

            get_gemini_response.chat = model.start_chat(history=[])
            get_gemini_response.chat.send_message(initial_context)

        # Create a natural prompt for the user's message
        time_context = f"The user is at {int(timestamp)} seconds in the video and asks: {message}"
        
        # Guide the AI to give natural responses
        prompt = f"""{time_context}
dont repeat the users qustion again just answer as follows
Please respond naturally as a professional assistant would in a conversation. Focus on:
1. Directly addressing the question or responding to the comment
2. Referencing relevant parts of the video but don't mention that part in the answer
3. Being conversational and engaging
4. Providing accurate information strictly from the transcript
5. Avoiding formal structures or markers and asterisks
6. don't answer anything outside of the transcript and videos context if user asks out of context just reply it is not in the video """

        response = get_gemini_response.chat.send_message(prompt)
        
        # Clean up the response
        clean_response = (response.text
            .replace('**', '')
            .replace('Assistant:', '')
            .replace('Discussion Points:', '')
            .replace('Additional Questions:', '')
            .strip())
        
        # Ensure the response starts naturally
        conversation_starters = [
            "Well, ", "Actually, ", "You know, ", "I see that ", 
            "Based on the video, ", "Let me explain that. ", 
            "That's interesting! ", "Great question! "
        ]
        
        if not any(clean_response.startswith(starter) for starter in conversation_starters):
            clean_response = "Well, " + clean_response

        return clean_response

    except Exception as e:
        print(f"Gemini API Error: {str(e)}")
        return "I'd be happy to help you understand the video better. Could you please try asking your question again?"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process-video', methods=['POST'])
def process_video():
    try:
        global current_transcript
        data = request.json
        video_url = data.get('video_url')
        
        if not video_url:
            return jsonify({'error': 'No video URL provided'}), 400

        video_id = extract_video_id(video_url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400

        # Get and store transcript
        current_transcript = get_transcript(video_id) or ""
        
        # Reset chat for new video
        if hasattr(get_gemini_response, 'chat'):
            delattr(get_gemini_response, 'chat')
        
        chat_messages.clear()

        return jsonify({
            'success': True,
            'video_id': video_id,
            'has_transcript': bool(current_transcript)
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/send-message', methods=['POST'])
def send_message():
    try:
        data = request.json
        message = data.get('message')
        timestamp = data.get('timestamp', 0)

        if not message:
            return jsonify({'error': 'No message provided'}), 400

        # Add user message
        chat_messages.append({
            'user': True,
            'message': message,
            'timestamp': timestamp
        })

        # Get Gemini response
        bot_response = get_gemini_response(message, timestamp, current_transcript)
        
        # Add bot response
        chat_messages.append({
            'user': False,
            'message': bot_response,
            'timestamp': timestamp
        })

        return jsonify({
            'success': True,
            'response': bot_response
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)