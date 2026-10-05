let taskChartInstance = null;
let financeChartInstance = null;

Chart.defaults.color = 'rgba(255,255,255,0.8)';
Chart.defaults.font.family = 'Inter';

function switchTab(tabId) {
    document.querySelectorAll('.tab-content, .nav-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    document.getElementById(`btn-${tabId}`).classList.add('active');

    if (tabId === 'tasks') loadTasks();
    if (tabId === 'finance') loadFinances();
}

// --- TASKS LOGIC ---
async function loadTasks() {
    try {
        const res = await fetch('/api/tasks');
        const tasks = await res.json();
        
        const list = document.getElementById('task-list');
        if (!list) return;
        list.innerHTML = '';
        
        let done = 0, pending = 0;

        tasks.forEach((task, index) => {
            if(task.completed) done++; else pending++;
            
            list.innerHTML += `
                <div class="task-item pop-in p-3 rounded-xl flex items-center gap-3 border border-white/20 bg-black/30 backdrop-blur-md shadow-lg" style="animation-delay: ${index * 0.05}s">
                    <button onclick="toggleTask(${index}, ${!task.completed})" style="color: ${task.completed ? '#00f0ff' : '#9ca3af'}" class="hover:scale-125 transition-transform duration-300">
                        <span class="material-symbols-rounded text-2xl">${task.completed ? 'check_circle' : 'radio_button_unchecked'}</span>
                    </button>
                    <div class="flex-1 ${task.completed ? 'line-through opacity-50' : ''} transition-all">
                        <p class="font-medium text-white">${task.desc}</p>
                        <p class="text-xs text-[#00a8ff] opacity-90 font-semibold">Due: ${task.due} | Priority: ${task.prio}</p>
                    </div>
                    <button onclick="deleteTask(${index})" class="glass-button p-2 rounded-lg text-[#00a8ff] hover:bg-[#00a8ff]/20 hover:text-white">
                        <span class="material-symbols-rounded text-sm">delete</span>
                    </button>
                </div>
            `;
        });
        updateTaskChart(done, pending);
    } catch (e) { console.error("Error loading tasks:", e); }
}

async function addTask(aiDesc = null, aiPrio = null, aiDue = null) {
    let d = aiDesc || document.getElementById('task-desc').value;
    let p = aiPrio || document.getElementById('task-prio').value;
    let du = aiDue || document.getElementById('task-date').value || new Date().toISOString().split('T')[0];
    
    if(!d) return alert("Task description cannot be empty!");
    
    try {
        await fetch('/api/tasks', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({desc: d, prio: p, due: du})
        });
        document.getElementById('task-desc').value = '';
        loadTasks();
    } catch (e) { console.error("Task Error:", e); }
}

async function deleteTask(index) {
    await fetch(`/api/tasks/${index}`, { method: 'DELETE' });
    loadTasks();
}

async function toggleTask(index, status) {
    await fetch(`/api/tasks/${index}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({completed: status})
    });
    loadTasks();
}

function updateTaskChart(done, pending) {
    const ctx = document.getElementById('taskChart');
    if(!ctx) return;
    if(taskChartInstance) taskChartInstance.destroy();
    
    taskChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Done', 'Pending'],
            datasets: [{
                data: [done, pending],
                backgroundColor: ['#00f0ff', 'rgba(0,0,0,0.4)'],
                borderWidth: 0, 
                hoverBackgroundColor: ['#00f0ff', 'rgba(0,0,0,0.4)'],
                hoverBorderWidth: 0,
                hoverOffset: 0
            }]
        },
        options: { 
            cutout: '75%', 
            events: [], 
            plugins: { 
                legend: { position: 'bottom' },
                tooltip: { enabled: false }
            },
            animation: { animateScale: true, animateRotate: true, duration: 2000, easing: 'easeOutElastic' }
        }
    });
}

// --- FINANCE LOGIC ---
async function loadFinances() {
    try {
        try {
            const setRes = await fetch('/api/settings');
            if (setRes.ok) {
                const settings = await setRes.json();
                document.getElementById('fund-goal').value = settings.study_fund_goal || 10000;
            }
        } catch(e) { console.log("Settings missing, using default."); }

        const res = await fetch('/api/finance');
        if(!res.ok) throw new Error("Finance fetch failed");
        const exps = await res.json();
        
        let total = 0;
        let categories = {};
        const list = document.getElementById('expense-list');
        if (list) list.innerHTML = '';

        exps.forEach((e, index) => {
            const amt = parseFloat(e.amt) || 0;
            const cat = e.cat || 'Misc';
            total += amt;
            categories[cat] = (categories[cat] || 0) + amt;

            if (list) {
                // Changed pink to electric blue text
                list.innerHTML += `
                    <div class="pop-in flex justify-between items-center p-3 bg-black/30 backdrop-blur-md rounded-lg border border-white/20 hover:bg-white/10 transition-colors shadow-lg" style="animation-delay: ${index * 0.05}s">
                        <span class="text-sm font-medium text-gray-200">${cat}</span>
                        <span class="font-bold text-[#00a8ff] text-sm tracking-wide">₹${amt.toLocaleString()}</span>
                    </div>
                `;
            }
        });

        const totalDisplay = document.getElementById('total-spent-display');
        totalDisplay.innerText = `₹${total.toLocaleString()}`;
        totalDisplay.style.transform = "scale(1.2)";
        setTimeout(() => totalDisplay.style.transform = "scale(1)", 200);
        
        if (Object.keys(categories).length === 0) {
            updateFinanceChart(['No Data'], [0]);
        } else {
            updateFinanceChart(Object.keys(categories), Object.values(categories));
        }
    } catch (e) { console.error("Finance Load Error:", e); }
}

async function updateGoal() {
    const goal = document.getElementById('fund-goal').value;
    await fetch('/api/settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({goal: parseFloat(goal)})
    });
}

async function addExpense(aiAmt = null, aiCat = null) {
    let a = aiAmt || document.getElementById('exp-amt').value;
    let c = aiCat || document.getElementById('exp-cat').value;
    
    if(!a || !c || isNaN(a)) return alert("Please fill both amount and category properly!");
    
    try {
        await fetch('/api/finance', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({amt: parseFloat(a), cat: c})
        });
        document.getElementById('exp-amt').value = '';
        document.getElementById('exp-cat').value = '';
        loadFinances();
    } catch (e) { console.error("Expense Error:", e); }
}

function updateFinanceChart(labels, data) {
    const ctx = document.getElementById('financeChart');
    if(!ctx) return;
    if(financeChartInstance) financeChartInstance.destroy();
    
    financeChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Spent (₹)',
                data: data,
                // CHANGED TO ELECTRIC BLUE
                backgroundColor: 'rgba(0, 168, 255, 0.8)',
                borderWidth: 0, 
                borderRadius: 8,
                hoverBackgroundColor: 'rgba(0, 168, 255, 0.8)', 
                hoverBorderWidth: 0 
            }]
        },
        options: {
            maintainAspectRatio: false,
            responsive: true,
            events: [], 
            scales: { 
                y: { display: false, beginAtZero: true }, 
                x: { grid: { display: false }, ticks: { color: 'rgba(255,255,255,0.8)', font: { weight: 'bold' } } } 
            },
            plugins: { 
                legend: { display: false },
                tooltip: { enabled: false }
            },
            animation: { duration: 2500, easing: 'easeOutElastic', y: { from: 1000 } }
        }
    });
}

// --- AI CHAT MEMORY LOGIC ---
async function loadChatHistory() {
    try {
        const res = await fetch('/api/chat_history');
        const history = await res.json();
        const chat = document.getElementById('chat-history');
        
        chat.innerHTML = `<div class="self-start pop-in bg-black/60 border border-white/20 backdrop-blur-md rounded-2xl rounded-tl-none p-4 max-w-lg shadow-[0_10px_20px_rgba(0,0,0,0.5)]">Hello! I am Veyon. Let me know if you need to add an expense, log a task, or check your totals.</div>`;
        
        history.forEach(msg => {
            if(msg.role === 'user') {
                chat.innerHTML += `<div class="self-end bg-[#0044ff]/40 text-white border border-[#00f0ff]/50 rounded-2xl rounded-tr-none p-4 max-w-lg shadow-[0_10px_20px_rgba(0,0,0,0.5)] backdrop-blur-md">${msg.text}</div>`;
            } else {
                chat.innerHTML += `<div class="self-start bg-black/60 border border-white/20 text-white rounded-2xl rounded-tl-none p-4 max-w-lg shadow-[0_10px_20px_rgba(0,0,0,0.5)] backdrop-blur-md">${msg.text}</div>`;
            }
        });
        chat.scrollTop = chat.scrollHeight;
    } catch(e) { console.error("Error loading chat memory", e); }
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if(!msg) return;

    const chat = document.getElementById('chat-history');
    const loader = document.getElementById('ai-loading');
    const sendBtn = document.getElementById('send-btn');
    
    input.disabled = true;
    sendBtn.disabled = true;

    chat.innerHTML += `<div class="pop-in self-end bg-[#0044ff]/40 text-white border border-[#00f0ff]/50 rounded-2xl rounded-tr-none p-4 max-w-lg shadow-[0_10px_20px_rgba(0,0,0,0.5)] backdrop-blur-md">${msg}</div>`;
    input.value = '';
    chat.scrollTop = chat.scrollHeight;
    
    loader.classList.remove('hidden');
    chat.parentNode.scrollTop = chat.parentNode.scrollHeight;

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: msg})
        });
        
        if (!res.ok) throw new Error("Server error");
        const data = await res.json();
        
        loader.classList.add('hidden');

        try {
            const actionData = JSON.parse(data.reply);
            if(actionData.action === 'add_expense') {
                await addExpense(actionData.amount, actionData.category);
                chat.innerHTML += `<div class="pop-in self-start bg-green-500/30 text-white border border-green-400/50 rounded-2xl rounded-tl-none p-4 backdrop-blur-md shadow-[0_10px_20px_rgba(0,0,0,0.5)]">✅ Done! Added ₹${actionData.amount} for ${actionData.category}. Check your Finance tab.</div>`;
            } else if (actionData.action === 'add_task') {
                await addTask(actionData.desc, actionData.priority, null);
                chat.innerHTML += `<div class="pop-in self-start bg-green-500/30 text-white border border-green-400/50 rounded-2xl rounded-tl-none p-4 backdrop-blur-md shadow-[0_10px_20px_rgba(0,0,0,0.5)]">✅ Done! Added task: "${actionData.desc}". Check your Tasks tab.</div>`;
            }
        } catch (parseError) {
            chat.innerHTML += `<div class="pop-in self-start bg-black/60 border border-white/20 text-white rounded-2xl rounded-tl-none p-4 max-w-lg shadow-[0_10px_20px_rgba(0,0,0,0.5)] backdrop-blur-md">${data.reply}</div>`;
        }
    } catch (e) {
        loader.classList.add('hidden');
        chat.innerHTML += `<div class="pop-in self-start bg-red-600/40 text-white border border-red-500/50 rounded-2xl rounded-tl-none p-4 backdrop-blur-md shadow-[0_10px_20px_rgba(0,0,0,0.5)]">Oops, something went wrong checking the backend.</div>`;
    }
    
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
    chat.scrollTop = chat.scrollHeight;
}

document.addEventListener("DOMContentLoaded", () => {
    loadTasks();
    loadChatHistory();
    
    const dateInput = document.getElementById('task-date');
    if (dateInput) dateInput.value = new Date().toISOString().split('T')[0];
    
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', e => {
            if(e.key === 'Enter') sendChatMessage();
        });
    }
});