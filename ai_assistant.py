import tkinter as tk
from tkinter import ttk, messagebox
import threading
import psutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
import subprocess
import cv2
import numpy as np
from PIL import ImageGrab, Image, ImageTk
import serial
import serial.tools.list_ports

# --- APPLE AESTHETIC PALETTE ---
APPLE_THEME = {
    "bg": "#F5F5F7",           # Apple Light Gray
    "sidebar": "#FFFFFF",      # Pure White
    "accent": "#0071E3",       # San Francisco Blue
    "text": "#1D1D1F",         # Dark Charcoal
    "text_sec": "#86868B",     # Secondary Gray
    "card": "#FFFFFF",         # Card background
    "border": "#D2D2D7",       # Subtle divider
    "terminal": "#1D1D1F"      # Terminal Dark
}

class ModernSwitch(tk.Canvas):
    """An iOS-style toggle switch."""
    def __init__(self, parent, command=None, width=50, height=26, **kwargs):
        super().__init__(parent, width=width, height=height, bg=parent['bg'], highlightthickness=0, **kwargs)
        self.command = command
        self.state = False
        self.bind("<Button-1>", self.toggle)
        self.draw()

    def draw(self):
        self.delete("all")
        color = APPLE_THEME["accent"] if self.state else APPLE_THEME["border"]
        self.create_rounded_rect(2, 2, 48, 24, 11, fill=color, outline="")
        circle_x = 37 if self.state else 13
        self.create_oval(circle_x-9, 13-9, circle_x+9, 13+9, fill="white", outline="")

    def create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2, x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1]
        return self.create_polygon(points, smooth=True, **kwargs)

    def toggle(self, event=None):
        self.state = not self.state
        self.draw()
        if self.command: self.command(self.state)

class AetherisHub:
    def __init__(self, root):
        self.root = root
        self.root.title("Aetheris Hub")
        self.root.geometry("1280x850")
        self.root.configure(bg=APPLE_THEME["bg"])
        
        # State
        self.arduino = None
        self.vision_active = False
        self.arduino_data = [0] * 50
        
        self.setup_hardware()
        self.create_layout()
        self.show_home()

    def setup_hardware(self):
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if "Arduino" in p.description or "USB Serial" in p.description:
                try:
                    self.arduino = serial.Serial(p.device, 115200, timeout=0.01)
                    break
                except: pass

    def create_layout(self):
        # Sidebar
        self.sidebar = tk.Frame(self.root, bg=APPLE_THEME["sidebar"], width=240, bd=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        # Apple-style Logo
        tk.Label(self.sidebar, text="Aetheris", font=("SF Pro Display", 22, "bold"), 
                 bg=APPLE_THEME["sidebar"], fg=APPLE_THEME["text"]).pack(pady=(40, 30))

        nav_items = [
            ("Home", self.show_home),
            ("Models", self.show_terminal),
            ("Vision Sync", self.show_vision),
            ("Analytics", self.show_stats)
        ]

        for text, cmd in nav_items:
            btn = tk.Button(self.sidebar, text=text, font=("SF Pro Text", 13), 
                            bg=APPLE_THEME["sidebar"], fg=APPLE_THEME["text_sec"],
                            relief="flat", anchor="w", padx=40, command=cmd,
                            activebackground=APPLE_THEME["bg"])
            btn.pack(fill="x", pady=2)

        # Main Viewport
        self.main_view = tk.Frame(self.root, bg=APPLE_THEME["bg"])
        self.main_view.pack(side="right", fill="both", expand=True, padx=40, pady=40)

    def show_home(self):
        self.clear_view()
        tk.Label(self.main_view, text="Welcome, Brighton", font=("SF Pro Display", 32, "bold"), 
                 bg=APPLE_THEME["bg"], fg=APPLE_THEME["text"]).pack(anchor="w")
        
        card = tk.Frame(self.main_view, bg=APPLE_THEME["card"], padx=30, pady=30)
        card.pack(fill="x", pady=30)
        tk.Label(card, text="System Status: Optimal", font=("SF Pro Text", 16), bg="white").pack(anchor="w")
        tk.Label(card, text="M1 Offload Active • Arduino Ready", fg=APPLE_THEME["text_sec"], bg="white").pack(anchor="w")

    def show_terminal(self):
        self.clear_view()
        tk.Label(self.main_view, text="OpenClaw Terminal", font=("SF Pro Display", 24, "bold"), 
                 bg=APPLE_THEME["bg"], fg=APPLE_THEME["text"]).pack(anchor="w", pady=(0, 20))
        
        term_container = tk.Frame(self.main_view, bg=APPLE_THEME["terminal"], padx=15, pady=15)
        term_container.pack(fill="both", expand=True)
        
        self.cli_out = tk.Text(term_container, bg=APPLE_THEME["terminal"], fg="#A6E22E", 
                               font=("Menlo", 12), relief="flat", insertbackground="white")
        self.cli_out.pack(fill="both", expand=True)
        
        cmd_frame = tk.Frame(term_container, bg=APPLE_THEME["terminal"])
        cmd_frame.pack(fill="x")
        tk.Label(cmd_frame, text="", fg="#66D9EF", bg=APPLE_THEME["terminal"]).pack(side="left")
        self.cli_in = tk.Entry(cmd_frame, bg=APPLE_THEME["terminal"], fg="white", 
                               font=("Menlo", 12), relief="flat", insertbackground="white")
        self.cli_in.pack(side="left", fill="x", expand=True, padx=10)
        self.cli_in.bind("<Return>", self.handle_cli)

    def show_vision(self):
        self.clear_view()
        header = tk.Frame(self.main_view, bg=APPLE_THEME["bg"])
        header.pack(fill="x")
        tk.Label(header, text="Vision Sync", font=("SF Pro Display", 24, "bold"), 
                 bg=APPLE_THEME["bg"]).pack(side="left")
        
        self.v_switch = ModernSwitch(header, command=self.toggle_vision)
        self.v_switch.pack(side="right")

        # Visual Feedback Card
        self.vis_card = tk.Frame(self.main_view, bg="black", height=300)
        self.vis_card.pack(fill="x", pady=20)
        self.vis_label = tk.Label(self.vis_card, bg="black")
        self.vis_label.pack(expand=True)

    def show_stats(self):
        self.clear_view()
        tk.Label(self.main_view, text="Arduino Usage Analytics", font=("SF Pro Display", 24, "bold"), 
                 bg=APPLE_THEME["bg"]).pack(anchor="w")
        
        self.fig, self.ax = plt.subplots(figsize=(8, 4), facecolor=APPLE_THEME["bg"])
        self.ax.set_facecolor(APPLE_THEME["bg"])
        self.canvas = FigureCanvasTkAgg(self.fig, self.main_view)
        self.canvas.get_tk_widget().pack(fill="both", pady=20)
        self.update_stats_loop()

    def toggle_vision(self, state):
        self.vision_active = state
        if state: threading.Thread(target=self.run_vision, daemon=True).start()

    def run_vision(self):
        while self.vision_active:
            # Capturing specific ROI (Region of Interest) to save 8GB RAM overhead
            screen = np.array(ImageGrab.grab(bbox=(0, 0, 800, 600)))
            gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
            activity = int(np.mean(gray))
            
            # Send to Arduino and update graph data
            if self.arduino:
                self.arduino.write(f"V{activity}\n".encode())
                self.arduino_data.append(activity)
                self.arduino_data.pop(0)
            
            # Update Preview (Thumbnail)
            small = cv2.resize(screen, (320, 180))
            img = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB)))
            self.vis_label.config(image=img)
            self.vis_label.image = img
            time.sleep(0.1)

    def update_stats_loop(self):
        if not hasattr(self, 'ax'): return
        self.ax.clear()
        self.ax.plot(self.arduino_data, color=APPLE_THEME["accent"], linewidth=2)
        self.ax.set_ylim(0, 255)
        self.ax.axis('off')
        self.canvas.draw()
        self.root.after(1000, self.update_stats_loop)

    def handle_cli(self, event):
        cmd = self.cli_in.get()
        self.cli_out.insert("end", f"\n{cmd}\n")
        if "ollama launch openclaw" in cmd:
            self.cli_out.insert("end", "[Process] Bridging Ollama to Aetheris Core...\n", "proc")
        self.cli_in.delete(0, "end")

    def clear_view(self):
        for widget in self.main_view.winfo_children(): widget.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AetherisHub(root)
    root.mainloop()
