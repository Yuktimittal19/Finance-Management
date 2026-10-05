const express = require('express');
const fs = require('fs');
const path = require('path');
require('dotenv').config();
const { GoogleGenAI } = require('@google/genai');

const app = express();
const PORT = 3000;

// Initialize Gemini Client
// Make sure you have a .env file with GEMINI_API_KEY=your_key_here
const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

// Middleware
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public'))); // Serves your index.html, style.css, app.js

// Ensure the /data directory exists
const dataDir = path.join(__dirname, 'data');
if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir);
}

// Helper functions for reading/writing JSON files safely
const readJSON = (filename, defaultData) => {
    const filePath = path.join(dataDir, filename);
    if (!fs.existsSync(filePath)) {
        fs.writeFileSync(filePath, JSON.stringify(defaultData, null, 4));
        return defaultData;
    }
    const data = fs.readFileSync(filePath, 'utf-8');
    return data ? JSON.parse(data) : defaultData;
};

const writeJSON = (filename, data) => {
    const filePath = path.join(dataDir, filename);
    fs.writeFileSync(filePath, JSON.stringify(data, null, 4));
};

// ==========================================
// API ENDPOINTS FOR DATA (TASKS, FINANCE)
// ==========================================

// Get all tasks
app.get('/api/tasks', (req, res) => {
    const tasks = readJSON('tasks.json', []);
    res.json(tasks);
});

// Add a new task
app.post('/api/tasks', (req, res) => {
    const tasks = readJSON('tasks.json', []);
    const newTask = {
        desc: req.body.desc,
        prio: req.body.prio || 3,
        due: req.body.due || new Date().toISOString().split('T')[0],
        completed: false
    };
    tasks.push(newTask);
    writeJSON('tasks.json', tasks);
    res.json({ success: true, task: newTask });
});

// Get all finances
app.get('/api/finance', (req, res) => {
    const finances = readJSON('finance.json', []);
    res.json(finances);
});

// Add a new expense
app.post('/api/finance', (req, res) => {
    const finances = readJSON('finance.json', []);
    const newExpense = {
        amt: parseFloat(req.body.amt),
        cat: req.body.cat
    };
    finances.push(newExpense);
    writeJSON('finance.json', finances);
    res.json({ success: true, expense: newExpense });
});


// ==========================================
// AI CHAT ENDPOINT (VEYON)
// ==========================================

app.post('/api/chat', async (req, res) => {
    try {
        const userMsg = req.body.message;
        
        // 1. Gather current context to make Veyon smart
        const tasks = readJSON('tasks.json', []);
        const finances = readJSON('finance.json', []);
        const settings = readJSON('settings.json', { study_fund_goal: 1120000.0 });
        
        const pendingTasks = tasks.filter(t => !t.completed).length;
        const totalSpent = finances.reduce((sum, item) => sum + item.amt, 0);

        // 2. Construct the Prompt (Mirroring your Python logic exactly)
        const prompt = `Act as a casual, honest assistant named Veyon. 
        Context: Total spent = ${totalSpent} INR, Goal = ${settings.study_fund_goal}, Pending tasks = ${pendingTasks}.
        
        If the user explicitly asks to add an expense, reply ONLY with a valid JSON format like: {"action": "add_expense", "amount": 100, "category": "food"}
        If the user explicitly asks to add a task, reply ONLY with a valid JSON format like: {"action": "add_task", "desc": "homework", "priority": 1}
        If it's neither, just reply naturally to: '${userMsg}'. Do not use markdown formatting.`;

        // 3. Call Gemini
        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash', // Using 2.5 flash for super fast hackathon responses
            contents: prompt
        });

        let replyText = response.text.trim();

        // 4. Clean up any markdown JSON blocks the AI might accidentally add
        if (replyText.startsWith('```json')) {
            replyText = replyText.replace(/```json/g, '').replace(/```/g, '').trim();
        } else if (replyText.startsWith('```')) {
            replyText = replyText.replace(/```/g, '').trim();
        }

        // 5. Send it back to the frontend
        res.json({ reply: replyText });

    } catch (error) {
        console.error("AI Error:", error);
        res.status(500).json({ reply: "Sorry, I had a short circuit. Check my API key!" });
    }
});

// Start the server
app.listen(PORT, () => {
    console.log(`🚀 Veyon Dashboard is running live on http://localhost:${PORT}`);
});