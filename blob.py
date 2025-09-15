#!/usr/bin/env python3
"""
Client IRC-like avec interface Tkinter
Dépendances: requests
pip install requests
"""

import tkinter as tk
from tkinter import simpledialog, messagebox
import threading
import requests
import time
from datetime import datetime

POLL_INTERVAL = 2.0  # secondes


class Server:
    def __init__(self, base_url, name=None):
        self.base_url = base_url.rstrip('/') + '/'
        self.name = name or self.base_url
        self.last_id = None

    def post_message(self, pseudo, message):
        url = self.base_url + 'post_message.php'
        data = {'pseudo': pseudo, 'message': message, 'server': self.name}
        try:
            r = requests.post(url, data=data, timeout=5)
            return r.ok and r.json().get('success', False)
        except Exception:
            return False

    def fetch_messages(self):
        url = self.base_url + 'get_messages.php'
        params = {}
        if self.last_id:
            params['since_id'] = self.last_id
        try:
            r = requests.get(url, params=params, timeout=5)
            if not r.ok:
                return []
            data = r.json()
            msgs = data.get('messages', [])
            msgs.sort(key=lambda m: m.get('ts', ''))
            if msgs:
                self.last_id = msgs[-1].get('id', self.last_id)
            return msgs
        except Exception:
            return []


class ChatClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Blob")
        self.servers = []
        self.current_server = None
        self.pseudo = "Guest"
        self.running = True

        # Zone affichage messages
        self.text_area = tk.Text(root, state='disabled', wrap='word', bg="#1e1e1e", fg="white")
        self.text_area.pack(expand=True, fill='both', padx=5, pady=5)

        # Zone entrée message
        frame_entry = tk.Frame(root)
        frame_entry.pack(fill='x', padx=5, pady=5)

        self.entry = tk.Entry(frame_entry)
        self.entry.pack(side='left', expand=True, fill='x')
        self.entry.bind("<Return>", self.send_message)

        self.btn_send = tk.Button(frame_entry, text="Send", command=self.send_message)
        self.btn_send.pack(side='left', padx=5)

        # Menu
        menubar = tk.Menu(root)
        root.config(menu=menubar)

        menu_srv = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Servers", menu=menu_srv)
        menu_srv.add_command(label="Add server", command=self.add_server_dialog)
        menu_srv.add_command(label="Change server", command=self.choose_server_dialog)

        menu_user = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="User", menu=menu_user)
        menu_user.add_command(label="Change username", command=self.change_pseudo)

        menu_app = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="App", menu=menu_app)
        menu_app.add_command(label="Quit", command=self.quit_app)

        # Thread polling
        self.poll_thread = threading.Thread(target=self.poll_loop, daemon=True)
        self.poll_thread.start()

    def log(self, text):
        self.text_area.configure(state='normal')
        self.text_area.insert('end', text + "\n")
        self.text_area.configure(state='disabled')
        self.text_area.see('end')

    def add_server_dialog(self):
        url = simpledialog.askstring("New server", "URL (ex: https://mysite.com/chat/)")
        if url:
            name = simpledialog.askstring("Name", "Server name (optional)")
            self.add_server(url, name)

    def add_server(self, url, name=None):
        s = Server(url, name)
        self.servers.append(s)
        if not self.current_server:
            self.current_server = s
            self.log(f"[System] Current server: {s.name}")
        self.log(f"[System] Server added: {s.name} ({s.base_url})")

    def choose_server_dialog(self):
        if not self.servers:
            messagebox.showerror("Error", "No servers disponibles.")
            return
        choices = "\n".join(f"{i}) {s.name}" for i, s in enumerate(self.servers))
        idx = simpledialog.askinteger("Choose server", f"Servers:\n{choices}\nIndex ?")
        if idx is not None and 0 <= idx < len(self.servers):
            self.current_server = self.servers[idx]
            self.log(f"[System] Current server: {self.current_server.name}")

    def change_pseudo(self):
        pseudo = simpledialog.askstring("Change username", "New username:")
        if pseudo:
            self.pseudo = pseudo
            self.log(f"[System] Username changed to {self.pseudo}")

    def send_message(self, event=None):
        text = self.entry.get().strip()
        if not text:
            return
        if not self.current_server:
            self.log("[Error] No servers has been selected.")
            return
        ok = self.current_server.post_message(self.pseudo, text)
        if not ok:
            self.log("[Error] Can't send.")
        self.entry.delete(0, 'end')

    def poll_loop(self):
        while self.running:
            for s in list(self.servers):
                msgs = s.fetch_messages()
                for m in msgs:
                    ts = m.get('ts', '')
                    try:
                        pretty_ts = datetime.fromisoformat(ts).strftime('%H:%M:%S')
                    except Exception:
                        pretty_ts = ts
                    line = f"[{s.name}] {pretty_ts} <{m.get('pseudo')}> {m.get('message')}"
                    self.root.after(0, self.log, line)
            time.sleep(POLL_INTERVAL)

    def quit_app(self):
        self.running = False
        self.root.quit()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.quit_app)
    root.mainloop()
