from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime
from google import genai
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")  # Get API key from environment variables

app = Flask(__name__, static_folder='public', static_url_path='', template_folder='public')
ai_client = genai.Client(api_key=API_KEY) if API_KEY and API_KEY != "PASTE_YOUR_API_KEY_HERE" else None

def load_data(filename, default_data):
    filepath = os.path.join('data', filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            return default_data
    return default_data

def save_data(filename, data):
    os.makedirs('data', exist_ok=True)
    with open(os.path.join('data', filename), 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tasks', methods=['GET', 'POST'])
def handle_tasks():
    tasks = load_data('tasks.json', [])
    if request.method == 'POST':
        data = request.json
        tasks.append({
            "desc": data.get('desc'),
            "prio": int(data.get('prio', 3)),
            "due": data.get('due', datetime.today().strftime('%Y-%m-%d')),
            "assignee": data.get('assignee', 'Any'), # NEW: Delegation feature
            "completed": False
        })
        save_data('tasks.json', tasks)
        return jsonify({"success": True})
    return jsonify(tasks)

@app.route('/api/tasks/<int:index>', methods=['DELETE', 'PUT'])
def modify_task(index):
    tasks = load_data('tasks.json', [])
    if 0 <= index < len(tasks):
        if request.method == 'DELETE':
            tasks.pop(index)
        elif request.method == 'PUT':
            if 'completed' in request.json:
                tasks[index]['completed'] = request.json['completed']
        save_data('tasks.json', tasks)
        return jsonify({"success": True})
    return jsonify({"error": "Invalid index"}), 400

@app.route('/api/finance', methods=['GET', 'POST'])
def handle_finance():
    expenses = load_data('finance.json', [])
    if request.method == 'POST':
        data = request.json
        expenses.append({
            "amt": float(data.get('amt', 0)),
            "cat": data.get('cat', 'Uncategorized')
        })
        save_data('finance.json', expenses)
        return jsonify({"success": True})
    return jsonify(expenses)

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    settings = load_data('settings.json', {"study_fund_goal": 10000.0})
    if request.method == 'POST':
        settings['study_fund_goal'] = float(request.json.get('goal', 10000))
        save_data('settings.json', settings)
        return jsonify({"success": True})
    return jsonify(settings)

@app.route('/api/chat_history', methods=['GET'])
def get_chat_history():
    history = load_data('chat_history.json', [])
    return jsonify(history)

@app.route('/api/chat', methods=['POST'])
def ai_chat():
    user_msg = request.json.get('message', '').strip()
    if not ai_client: 
        return jsonify({"reply": "API Key is missing in .env file! AI cannot respond."})

    expenses = load_data('finance.json', [])
    total_spent = sum(e.get('amt', 0) for e in expenses)

    history = load_data('chat_history.json', [])
    recent_history = history[-10:]
    history_text = "\n".join([f"{msg['role'].capitalize()}: {msg['text']}" for msg in recent_history])

    # Upgraded AI Prompt for Hackathon (Understands Hindi/English, acts smart)
    prompt = f"""Act as Veyon, an advanced AI hackathon assistant.
    Total spent by the user so far = ₹{total_spent}.
    
    Previous Conversation Context:
    {history_text}
    
    Current User Message: {user_msg}
    
    Instructions:
    1. If the user asks to add an expense, return EXACTLY this JSON: {{"action": "add_expense", "amount": 500, "category": "food"}}
    2. If the user asks to add a task, return EXACTLY this JSON: {{"action": "add_task", "desc": "study", "priority": 2}}
    3. Otherwise, reply directly in short, natural plain text. You can understand English, Hinglish, and Hindi. If asked for financial advice, give a smart 1-sentence tip based on the total spent."""

    try:
        response = ai_client.models.generate_content(model='gemini-3.8-flash', contents=prompt)
        reply = response.text.strip()
        
        if reply.startswith("```json"): reply = reply[7:-3].strip()
        elif reply.startswith("```"): reply = reply[3:-3].strip()
        
        history_save_text = reply
        try:
            data = json.loads(reply)
            if data.get("action") == "add_expense":
                history_save_text = f"✅ Added expense of ₹{data.get('amount')} for {data.get('category')}."
            elif data.get("action") == "add_task":
                history_save_text = f"✅ Added task: {data.get('desc')}."
        except:
            pass 
            
        history.append({"role": "user", "text": user_msg})
        history.append({"role": "veyon", "text": history_save_text})
        save_data('chat_history.json', history[-20:])

        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"Backend Error: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)