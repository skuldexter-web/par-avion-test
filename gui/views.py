import customtkinter as ctk
import threading
import time
import sys

class ModuleView(ctk.CTkFrame):
    """A reusable frame template for CLI tool integration"""
    def __init__(self, master, module_name, **kwargs):
        super().__init__(master, **kwargs)
        self.module_name = module_name
        self.is_running = False
        self.thread = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.header = ctk.CTkLabel(self, text=f"{self.module_name} Configuration", font=ctk.CTkFont(size=18, weight="bold"))
        self.header.grid(row=0, column=0, sticky="w", padx=20, pady=10)

        self.options_frame = ctk.CTkScrollableFrame(self)
        self.options_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        self.freq_label = ctk.CTkLabel(self.options_frame, text="Frequency (MHz):")
        self.freq_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.freq_entry = ctk.CTkEntry(self.options_frame, placeholder_text="e.g. 1090.0")
        self.freq_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.gain_switch = ctk.CTkSwitch(self.options_frame, text="Auto Gain")
        self.gain_switch.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        self.gain_switch.select()

        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=20)
        self.control_frame.grid_columnconfigure((0, 1), weight=1)

        self.start_btn = ctk.CTkButton(self.control_frame, text="▶ Start Execution", fg_color="green", hover_color="darkgreen", command=self.start_task)
        self.start_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.stop_btn = ctk.CTkButton(self.control_frame, text="■ Stop / Cancel", fg_color="red", hover_color="darkred", state="disabled", command=self.stop_task)
        self.stop_btn.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

    def start_task(self):
        if self.is_running: return
        
        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        print(f"[{self.module_name}] Starting initialization...")
        print(f"[{self.module_name}] Params: Freq={self.freq_entry.get()}, AutoGain={self.gain_switch.get()}")

        self.thread = threading.Thread(target=self._run_backend_process, daemon=True)
        self.thread.start()

    def stop_task(self):
        self.is_running = False
        print(f"[{self.module_name}] Stop signal sent. Awaiting thread shutdown...")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def _run_backend_process(self):
        try:
            for i in range(1, 6):
                if not self.is_running:
                    break
                print(f"[{self.module_name}] Processing data block {i}...")
                time.sleep(1.0)
                
            if self.is_running:
                print(f"[{self.module_name}] Task completed successfully.")
                
        except Exception as e:
            print(f"[{self.module_name}] ERROR: {str(e)}", file=sys.stderr)
        finally:
            self.is_running = False
            self.master.after(0, lambda: self.start_btn.configure(state="normal"))
            self.master.after(0, lambda: self.stop_btn.configure(state="disabled"))
