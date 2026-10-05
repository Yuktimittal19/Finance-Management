import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, filedialog
import tkinter as tk
import json
import os
import csv
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from google import genai
import threading
import random
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

class StudentDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Dashboard")
        self.root.geometry("1100x700")
        self.root.attributes('-alpha', 0.95)
        
        self.tasks_file = "tasks.json"
        self.finance_file = "finance.json"
        self.settings_file = "settings.json"
        self.notes_file = "notes.json"
        
        self.tasks = []
        self.expenses = []
        self.notes_list = ["", "", ""]
        self.study_fund_goal = 0.0
        self.current_saved = 0.0

        self.load_data()

        if API_KEY != "PASTE_YOUR_API_KEY_HERE":
            self.ai_client = genai.Client(api_key=API_KEY)
        else:
            self.ai_client = None

        self.notebook = ttk.Notebook(root, bootstyle="info")
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.tab_tasks = ttk.Frame(self.notebook)
        self.tab_finances = ttk.Frame(self.notebook)
        self.tab_notes = ttk.Frame(self.notebook)
        self.tab_ai = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_tasks, text="📝 Task Manager")
        self.notebook.add(self.tab_finances, text="💰 Finance Tracker")
        self.notebook.add(self.tab_notes, text="🗒️ Quick Notes")
        self.notebook.add(self.tab_ai, text="🤖 Veyon Chat")

        self.setup_tasks_tab()
        self.setup_finances_tab()
        self.setup_notes_tab()
        self.setup_ai_tab()

    def load_data(self):
        if os.path.exists(self.tasks_file):
            with open(self.tasks_file, 'r') as f:
                self.tasks = json.load(f)
        if os.path.exists(self.finance_file):
            with open(self.finance_file, 'r') as f:
                self.expenses = json.load(f)
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
                self.study_fund_goal = settings.get("study_fund_goal", 1120000.0)
        if os.path.exists(self.notes_file):
            with open(self.notes_file, 'r') as f:
                self.notes_list = json.load(f)

    def save_data(self):
        with open(self.tasks_file, 'w') as f:
            json.dump(self.tasks, f, indent=4)
        with open(self.finance_file, 'w') as f:
            json.dump(self.expenses, f, indent=4)
        with open(self.settings_file, 'w') as f:
            json.dump({"study_fund_goal": self.study_fund_goal}, f, indent=4)

    def setup_tasks_tab(self):
        self.task_graph_panel = ttk.Frame(self.tab_tasks, width=350)
        self.task_graph_panel.pack(side='right', fill='y', padx=10, pady=15)
        self.task_graph_panel.pack_propagate(False) 

        left_panel = ttk.Frame(self.tab_tasks)
        left_panel.pack(side='left', fill='both', expand=True, padx=10)

        input_frame = ttk.LabelFrame(left_panel, text=" Add a New Task ", padding=15, bootstyle="info")
        input_frame.pack(fill='x', pady=15)

        ttk.Label(input_frame, text="Desc:").grid(row=0, column=0, padx=2)
        self.task_desc = ttk.Entry(input_frame, width=25)
        self.task_desc.grid(row=0, column=1, padx=2)

        ttk.Label(input_frame, text="Priority:").grid(row=0, column=2, padx=2)
        self.task_prio = ttk.Combobox(input_frame, values=["1(High)", "2(Med)", "3(Low)"], width=7, state="readonly")
        self.task_prio.current(2)
        self.task_prio.grid(row=0, column=3, padx=2)
        
        ttk.Label(input_frame, text="Due (YYYY-MM-DD):").grid(row=0, column=4, padx=2)
        self.task_due = ttk.Entry(input_frame, width=12)
        self.task_due.insert(0, datetime.today().strftime('%Y-%m-%d'))
        self.task_due.grid(row=0, column=5, padx=2)

        ttk.Button(input_frame, text="Add", bootstyle="success", command=self.add_task).grid(row=0, column=6, padx=5)

        self.task_tree = ttk.Treeview(left_panel, columns=("Status", "Priority", "Due", "Description"), show="headings", height=10, bootstyle="info")
        self.task_tree.heading("Status", text="Status")
        self.task_tree.heading("Priority", text="Priority")
        self.task_tree.heading("Due", text="Due Date")
        self.task_tree.heading("Description", text="Description")
        self.task_tree.column("Status", width=80, anchor="center")
        self.task_tree.column("Priority", width=80, anchor="center")
        self.task_tree.column("Due", width=100, anchor="center")
        self.task_tree.column("Description", width=250)
        self.task_tree.pack(fill='both', expand=True, pady=5)
        self.task_tree.tag_configure('overdue', foreground='red')

        btn_frame = ttk.Frame(left_panel)
        btn_frame.pack(fill='x', pady=10)
        
        ttk.Button(btn_frame, text="Mark Complete", bootstyle="primary", command=self.complete_task).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete", bootstyle="danger", command=self.delete_task).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Export CSV", bootstyle="outline-info", command=self.export_tasks).pack(side='right', padx=5)

        self.fig_tasks, self.ax_tasks = plt.subplots(figsize=(3, 3))
        self.canvas_tasks = FigureCanvasTkAgg(self.fig_tasks, master=self.task_graph_panel)
        self.canvas_tasks.get_tk_widget().pack(fill='both', expand=True)

        self.refresh_task_list()

    def add_task(self):
        desc = self.task_desc.get().strip()
        prio_str = self.task_prio.get()
        due = self.task_due.get().strip()
        if not desc:
            messagebox.showwarning("Empty Field", "Task cannot be empty!")
            return
        
        try:
            datetime.strptime(due, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("Error", "Date format YYYY-MM-DD!")
            return

        priority = int(prio_str[0])
        self.tasks.append({"desc": desc, "prio": priority, "due": due, "completed": False})
        self.save_data()
        self.task_desc.delete(0, "end")
        self.refresh_task_list()

    def refresh_task_list(self):
        self.tasks.sort(key=lambda x: (x['completed'], x['prio'], x.get('due', '9999-99-99')))
        for row in self.task_tree.get_children():
            self.task_tree.delete(row)
            
        today = datetime.today().strftime('%Y-%m-%d')
        
        for index, task in enumerate(self.tasks):
            status = "✅ Done" if task['completed'] else "❌ Pending"
            prio_label = {1: "High", 2: "Med", 3: "Low"}[task['prio']]
            due = task.get('due', 'N/A')
            
            tag = ""
            if not task['completed'] and due < today and due != 'N/A':
                tag = "overdue"
                
            self.task_tree.insert("", "end", iid=index, values=(status, prio_label, due, task['desc']), tags=(tag,))
        self.update_task_graph()

    def complete_task(self):
        selected = self.task_tree.selection()
        if not selected: return
        index = int(selected[0])
        self.tasks[index]['completed'] = True
        self.save_data()
        self.refresh_task_list()

    def delete_task(self):
        selected = self.task_tree.selection()
        if not selected: return
        index = int(selected[0])
        del self.tasks[index]
        self.save_data()
        self.refresh_task_list()

    def export_tasks(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filepath:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Status", "Priority", "Due Date", "Description"])
                for t in self.tasks:
                    writer.writerow(["Done" if t['completed'] else "Pending", t['prio'], t.get('due', ''), t['desc']])

    def update_task_graph(self):
        self.ax_tasks.clear()
        done = sum(1 for t in self.tasks if t['completed'])
        pending = len(self.tasks) - done
        
        if len(self.tasks) == 0:
            self.ax_tasks.pie([1], labels=["No Tasks"], colors=["#444444"])
        else:
            self.ax_tasks.pie([done, pending], labels=["Done", "Pending"], colors=["#28a745", "#dc3545"], autopct='%1.1f%%')
        self.ax_tasks.set_title("Task Progress", color='white')
        self.fig_tasks.patch.set_facecolor('#222222') 
        self.canvas_tasks.draw()

    def setup_finances_tab(self):
        self.fin_graph_panel = ttk.Frame(self.tab_finances, width=350)
        self.fin_graph_panel.pack(side='right', fill='y', padx=10, pady=15)
        self.fin_graph_panel.pack_propagate(False)

        left_panel = ttk.Frame(self.tab_finances)
        left_panel.pack(side='left', fill='both', expand=True, padx=10)

        input_frame = ttk.LabelFrame(left_panel, text=" Log Expense ", padding=15, bootstyle="info")
        input_frame.pack(fill='x', pady=15)

        ttk.Label(input_frame, text="Amt (INR):").grid(row=0, column=0, padx=2)
        self.exp_amt = ttk.Entry(input_frame, width=12)
        self.exp_amt.grid(row=0, column=1, padx=2)

        ttk.Label(input_frame, text="Category:").grid(row=0, column=2, padx=2)
        self.exp_cat = ttk.Entry(input_frame, width=20)
        self.exp_cat.grid(row=0, column=3, padx=2)

        ttk.Button(input_frame, text="Add", bootstyle="success", command=self.add_expense).grid(row=0, column=4, padx=5)
        
        goal_frame = ttk.LabelFrame(left_panel, text=" Target Fund Goal ", padding=10, bootstyle="warning")
        goal_frame.pack(fill='x', pady=5)
        ttk.Label(goal_frame, text="New Goal (INR):").grid(row=0, column=0, padx=2)
        self.goal_entry = ttk.Entry(goal_frame, width=15)
        self.goal_entry.grid(row=0, column=1, padx=2)
        ttk.Button(goal_frame, text="Update", bootstyle="primary", command=self.update_goal).grid(row=0, column=2, padx=10)

        stats_frame = ttk.Frame(left_panel)
        stats_frame.pack(fill='x', pady=10)
        
        self.lbl_total = ttk.Label(stats_frame, text="Total Spent: INR 0.00", font=("Helvetica", 14, "bold"), bootstyle="warning")
        self.lbl_total.pack(anchor='w')
        self.lbl_fund = ttk.Label(stats_frame, text=f"Savings Progress: INR {self.current_saved} / {self.study_fund_goal}", font=("Helvetica", 11), bootstyle="secondary")
        self.lbl_fund.pack(anchor='w', pady=5)

        self.exp_tree = ttk.Treeview(left_panel, columns=("Amount", "Category"), show="headings", height=8, bootstyle="info")
        self.exp_tree.heading("Amount", text="Amount (INR)")
        self.exp_tree.heading("Category", text="Category")
        self.exp_tree.column("Amount", width=120, anchor="center")
        self.exp_tree.column("Category", width=350)
        self.exp_tree.pack(fill='both', expand=True, pady=5)
        
        ttk.Button(left_panel, text="Export CSV", bootstyle="outline-info", command=self.export_finances).pack(anchor='e', pady=5)

        self.fig_fin, self.ax_fin = plt.subplots(figsize=(3, 3))
        self.canvas_fin = FigureCanvasTkAgg(self.fig_fin, master=self.fin_graph_panel)
        self.canvas_fin.get_tk_widget().pack(fill='both', expand=True)

        self.refresh_finance_list()

    def add_expense(self):
        try:
            amt = float(self.exp_amt.get())
            cat = self.exp_cat.get().strip()
            if not cat: raise ValueError
            self.expenses.append({"amt": amt, "cat": cat})
            self.save_data()
            self.exp_amt.delete(0, "end")
            self.exp_cat.delete(0, "end")
            self.refresh_finance_list()
        except ValueError:
            messagebox.showerror("Error", "Invalid data!")

    def update_goal(self):
        try:
            new_goal = float(self.goal_entry.get().strip())
            if new_goal <= 0: raise ValueError
            self.study_fund_goal = new_goal
            self.save_data()
            self.lbl_fund.config(text=f"Savings Progress: INR {self.current_saved} / {self.study_fund_goal}")
            self.goal_entry.delete(0, "end")
        except ValueError:
            messagebox.showerror("Error", "Numbers only!")

    def export_finances(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filepath:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Amount (INR)", "Category"])
                for e in self.expenses:
                    writer.writerow([e['amt'], e['cat']])

    def update_finance_graph(self):
        self.ax_fin.clear()
        if not self.expenses:
            self.ax_fin.pie([1], labels=["No Expenses"], colors=["#444444"])
        else:
            cat_totals = {}
            for e in self.expenses:
                cat_totals[e['cat']] = cat_totals.get(e['cat'], 0) + e['amt']
            self.ax_fin.pie(cat_totals.values(), labels=cat_totals.keys(), autopct='%1.1f%%', textprops={'color':"w"})
        
        self.ax_fin.set_title("Expense Breakdown", color='white')
        self.fig_fin.patch.set_facecolor('#222222')
        self.canvas_fin.draw()

    def refresh_finance_list(self):
        total_spent = 0.0
        for row in self.exp_tree.get_children():
            self.exp_tree.delete(row)
        for exp in self.expenses:
            total_spent += exp['amt']
            self.exp_tree.insert("", "end", values=(f"{exp['amt']:.2f}", exp['cat']))
        self.lbl_total.config(text=f"Total Spent: INR {total_spent:.2f}")
        self.update_finance_graph()

    def setup_notes_tab(self):
        grid_frame = ttk.Frame(self.tab_notes)
        grid_frame.pack(fill='both', expand=True, padx=15, pady=20)

        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.columnconfigure(2, weight=1)

        self.note_widgets = []

        for i in range(3):
            frame = ttk.LabelFrame(grid_frame, text=f" Sticky Note {i+1} ", bootstyle="warning")
            frame.grid(row=0, column=i, padx=10, sticky="nsew")

            txt = ttk.Text(frame, width=10, height=20, wrap="word", font=("Helvetica", 11))
            txt.pack(fill='both', expand=True, padx=5, pady=5)
            self.note_widgets.append(txt)

            if i < len(self.notes_list):
                txt.insert("1.0", self.notes_list[i])

        btn_frame = ttk.Frame(self.tab_notes)
        btn_frame.pack(fill='x', pady=10)
        ttk.Button(btn_frame, text="💾 Save All Notes", bootstyle="success", command=self.save_notes).pack(anchor='center')

    def save_notes(self):
        self.notes_list = [txt.get("1.0", "end-1c") for txt in self.note_widgets]
        with open(self.notes_file, 'w', encoding='utf-8') as f:
            json.dump(self.notes_list, f, indent=4)
        messagebox.showinfo("Saved", "Notes saved!")

    def setup_ai_tab(self):
        self.chat_history = ttk.Text(self.tab_ai, wrap="word", font=("Helvetica", 11), state="disabled")
        self.chat_history.pack(fill='both', expand=True, padx=15, pady=(15, 5))

        self.anim_canvas = tk.Canvas(self.tab_ai, height=40, bg="#222222", highlightthickness=0)
        self.anim_canvas.pack(fill='x', padx=15, pady=5)
        self.bars = []
        for i in range(5):
            x = 510 + (i * 15)
            bar = self.anim_canvas.create_rectangle(x, 18, x+10, 22, fill="#00d8ff", width=0)
            self.bars.append(bar)
        self.is_thinking = False

        bottom_frame = ttk.Frame(self.tab_ai)
        bottom_frame.pack(side='bottom', fill='x', padx=15, pady=15)
        
        self.chat_input = ttk.Entry(bottom_frame, font=("Helvetica", 11))
        self.chat_input.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.chat_input.bind("<Return>", lambda e: self.send_message())
        
        self.btn_send = ttk.Button(bottom_frame, text="Send", bootstyle="primary", command=self.send_message)
        self.btn_send.pack(side='right')

        self.append_chat("🤖 Veyon", "Hello! I am Veyon, your assistant. You can tell me to add expenses or tasks, or just chat!")

    def append_chat(self, sender, text):
        self.chat_history.config(state="normal")
        self.chat_history.insert("end", f"{sender}:\n{text}\n\n")
        self.chat_history.see("end")
        self.chat_history.config(state="disabled")

    def animate_waves(self):
        if not self.is_thinking:
            for i, bar in enumerate(self.bars):
                x = 510 + (i * 15)
                self.anim_canvas.coords(bar, x, 18, x+10, 22)
            return
            
        for i, bar in enumerate(self.bars):
            x = 510 + (i * 15)
            h = random.randint(5, 30)
            self.anim_canvas.coords(bar, x, 20 - h/2, x+10, 20 + h/2)
            
        self.root.after(100, self.animate_waves)

    def send_message(self):
        user_msg = self.chat_input.get().strip()
        if not user_msg: return
        
        self.chat_input.delete(0, 'end')
        self.append_chat("🧑 You", user_msg)
        
        if not self.ai_client:
            self.append_chat("🤖 Veyon", "Error: API Key missing!")
            return
            
        self.is_thinking = True
        self.animate_waves()
        self.btn_send.config(state="disabled")
        
        threading.Thread(target=self.get_ai_reply, args=(user_msg,), daemon=True).start()

    def get_ai_reply(self, user_msg):
        try:
            total_spent = sum(e['amt'] for e in self.expenses)
            pending_tasks = sum(1 for t in self.tasks if not t['completed'])
            
            prompt = f"""Act as a casual, honest assistant named Veyon. Context: Total spent = {total_spent} INR, Goal = {self.study_fund_goal}, Pending tasks = {pending_tasks}.
If the user explicitly asks to add an expense, reply ONLY with a valid JSON format like: {{"action": "add_expense", "amount": 100, "category": "food"}}
If the user explicitly asks to add a task, reply ONLY with a valid JSON format like: {{"action": "add_task", "desc": "homework", "priority": 1}}
If it's neither, just reply naturally to: '{user_msg}'. Do not use markdown formatting."""
            
            response = self.ai_client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt
            )
            
            self.root.after(0, self.finalize_ai_reply, response.text)
        except Exception as e:
            self.root.after(0, self.finalize_ai_reply, f"Error: {str(e)}")

    def finalize_ai_reply(self, text):
        self.is_thinking = False
        
        try:
            clean_text = text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:-3].strip()
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:-3].strip()
                
            data = json.loads(clean_text)
            if data.get("action") == "add_expense":
                self.expenses.append({"amt": float(data["amount"]), "cat": data["category"]})
                self.save_data()
                self.refresh_finance_list()
                self.append_chat("🤖 Veyon", f"Done! Added expense: {data['amount']} INR for {data['category']}.")
            elif data.get("action") == "add_task":
                due = datetime.today().strftime('%Y-%m-%d')
                self.tasks.append({"desc": data["desc"], "prio": int(data["priority"]), "due": due, "completed": False})
                self.save_data()
                self.refresh_task_list()
                self.append_chat("🤖 Veyon", f"Done! Added task: '{data['desc']}'.")
            else:
                self.append_chat("🤖 Veyon", text)
        except:
            self.append_chat("🤖 Veyon", text)
            
        self.btn_send.config(state="normal")

if __name__ == "__main__":
    root = ttk.Window(themename="darkly") 
    app = StudentDashboard(root)
    root.mainloop()