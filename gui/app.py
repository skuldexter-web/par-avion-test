import customtkinter as ctk
import psutil
import sys
import time
from gui.views import ModuleView

# Configure default theme
ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue")  

class RedirectText:
    """Redirects stdout/stderr to a CustomTkinter Textbox safely"""
    def __init__(self, textbox, tag):
        self.textbox = textbox
        self.tag = tag

    def write(self, string):
        self.textbox.after(0, self._write_thread_safe, string)

    def _write_thread_safe(self, string):
        self.textbox.insert("end", string, self.tag)
        self.textbox.see("end")

    def flush(self):
        pass


class ParAvionApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Par-Avion GUI Suite")
        self.geometry("1100x700")
        self.minsize(800, 600)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()
        
        sys.stdout = RedirectText(self.terminal_box, "stdout")
        sys.stderr = RedirectText(self.terminal_box, "stderr")

        self.update_telemetry()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(9, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="Par-Avion", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.nav_buttons = {}
        modules = ["Airplanes", "ISS", "Maritime", "Morse", "Radio", "SSTV", "Radar", "Waterfall"]
        
        for i, mod_name in enumerate(modules, start=1):
            btn = ctk.CTkButton(self.sidebar, text=mod_name, command=lambda m=mod_name: self.select_module(m))
            btn.grid(row=i, column=0, padx=20, pady=5)
            self.nav_buttons[mod_name] = btn

        self.cpu_label = ctk.CTkLabel(self.sidebar, text="CPU: 0%", font=ctk.CTkFont(size=12))
        self.cpu_label.grid(row=10, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.ram_label = ctk.CTkLabel(self.sidebar, text="RAM: 0%", font=ctk.CTkFont(size=12))
        self.ram_label.grid(row=11, column=0, padx=20, pady=(0, 20), sticky="w")

        self.theme_switch = ctk.CTkSwitch(self.sidebar, text="Dark Mode", command=self.toggle_theme)
        self.theme_switch.grid(row=12, column=0, padx=20, pady=20)
        self.theme_switch.select()

    def _build_main_area(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=3)
        self.main_container.grid_rowconfigure(1, weight=1)

        self.views = {}
        
        self.terminal_frame = ctk.CTkFrame(self.main_container)
        self.terminal_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.terminal_frame.grid_columnconfigure(0, weight=1)
        self.terminal_frame.grid_rowconfigure(1, weight=1)

        self.term_tools = ctk.CTkFrame(self.terminal_frame, fg_color="transparent", height=30)
        self.term_tools.grid(row=0, column=0, sticky="ew", padx=5)
        ctk.CTkLabel(self.term_tools, text="Live Output Log", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(self.term_tools, text="Clear", width=60, height=24, command=self.clear_terminal).pack(side="right", padx=5)

        self.terminal_box = ctk.CTkTextbox(self.terminal_frame, state="normal", font=ctk.CTkFont(family="Courier", size=12))
        self.terminal_box.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        self.terminal_box.tag_config("stderr", foreground="red")
        self.terminal_box.tag_config("stdout", foreground="gray90")

        self.select_module("Airplanes")

    def select_module(self, module_name):
        for view in self.views.values():
            view.grid_forget()

        if module_name not in self.views:
            self.views[module_name] = ModuleView(self.main_container, module_name)
        
        self.views[module_name].grid(row=0, column=0, sticky="nsew")

    def toggle_theme(self):
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Dark")
            self.terminal_box.tag_config("stdout", foreground="gray90")
        else:
            ctk.set_appearance_mode("Light")
            self.terminal_box.tag_config("stdout", foreground="black")

    def clear_terminal(self):
        self.terminal_box.delete("1.0", "end")

    def update_telemetry(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        self.cpu_label.configure(text=f"CPU: {cpu}%")
        self.ram_label.configure(text=f"RAM: {ram}%")
        self.after(2000, self.update_telemetry)
