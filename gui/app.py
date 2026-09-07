from __future__ import annotations
import os, sys, time, threading, queue, platform, subprocess
from concurrent.futures import ThreadPoolExecutor
import customtkinter as ctk
import psutil

from core.modules import hardware, airplanes, maritime, iss, radio, waterfall, sstv, morse

APP_NAME = "PAR AVION"
BG = ("#f4f6f8", "#0d1117")
PANEL = ("#ffffff", "#151b23")
TEXT = ("#17202a", "#e6edf3")
MUTED = ("#667085", "#8b949e")
ACCENT = ("#2563eb", "#3b82f6")
GOOD = ("#15803d", "#3fb950")
WARN = ("#b45309", "#d29922")
BAD = ("#b91c1c", "#f85149")

class Page(ctk.CTkFrame):
    def __init__(self, master, app, title, subtitle=""):
        super().__init__(master, fg_color="transparent")
        self.app=app
        top=ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(16,8))
        ctk.CTkLabel(top,text=title,font=ctk.CTkFont(size=24,weight="bold"),text_color=TEXT).pack(anchor="w")
        if subtitle: ctk.CTkLabel(top,text=subtitle,text_color=MUTED).pack(anchor="w",pady=(2,0))
    def button(self, master, text, command, **kw): return ctk.CTkButton(master,text=text,command=command,**kw)

class HomePage(Page):
    def __init__(self, master, app):
        super().__init__(master,app,"Dashboard","Receive-only RF & telemetry workstation")
        self.grid_columnconfigure((0,1,2),weight=1)
        cards=[("System", "CPU / RAM / platform"),("Hardware","SDR / GPS / dump1090"),("Safety","All bundled modes are receive-only")]
        for i,(a,b) in enumerate(cards):
            f=ctk.CTkFrame(self,fg_color=PANEL,corner_radius=12); f.grid(row=0,column=i,padx=8,pady=8,sticky="nsew")
            ctk.CTkLabel(f,text=a,font=ctk.CTkFont(size=16,weight="bold"),text_color=TEXT).pack(anchor="w",padx=14,pady=(14,4))
            ctk.CTkLabel(f,text=b,text_color=MUTED).pack(anchor="w",padx=14,pady=(0,14))
        self.summary=ctk.CTkTextbox(self,fg_color=PANEL,text_color=TEXT,corner_radius=12,height=300)
        self.summary.grid(row=1,column=0,columnspan=3,padx=8,pady=12,sticky="nsew")
        self.refresh()
    def refresh(self):
        self.summary.delete("1.0","end")
        self.summary.insert("end", "PAR AVION is ready.\n\nSelect a mode from the navigation rail. Backend work is dispatched to background threads so the GUI remains responsive.\n\nDetected capabilities will appear in the sidebar telemetry and the live log console.")

class TablePage(Page):
    def __init__(self, master, app, title, subtitle=""):
        super().__init__(master,app,title,subtitle)
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(1,weight=1)
        bar=ctk.CTkFrame(self,fg_color="transparent"); bar.grid(row=0,column=0,sticky="ew",padx=18,pady=6)
        self.controls=bar
        self.output=ctk.CTkTextbox(self,fg_color=PANEL,text_color=TEXT,corner_radius=10,font=ctk.CTkFont(family="DejaVu Sans Mono",size=12))
        self.output.grid(row=1,column=0,sticky="nsew",padx=18,pady=(6,18))
    def write(self,s): self.output.delete("1.0","end"); self.output.insert("end",s)

class AirplanesPage(TablePage):
    def __init__(self,master,app):
        super().__init__(master,app,"Airplanes","ADS-B 1090 MHz decoder and tactical contact table")
        self.ref_lat=None; self.ref_lon=None; self.tracker=None; self.controller=None; self.running=False
        ctk.CTkButton(self.controls,text="Start",command=self.start).pack(side="left",padx=4)
        ctk.CTkButton(self.controls,text="Stop / Cancel",command=self.stop,fg_color=BAD).pack(side="left",padx=4)
        ctk.CTkButton(self.controls,text="Refresh",command=self.refresh).pack(side="left",padx=4)
    def start(self): self.app.run_bg(self._start,"Starting ADS-B tracker…")
    def _start(self):
        rep=hardware.full_report(); self.ref_lat=self.ref_lon=None
        if rep.gps and rep.gps.fix: self.ref_lat,self.ref_lon=rep.gps.lat,rep.gps.lon
        self.controller=airplanes.Dump1090Controller()
        ok=self.controller.ensure_running()
        if not ok: return False, self.controller.last_error or "Could not start/connect to dump1090."
        self.tracker=airplanes.AircraftTracker(); self.tracker.start(); self.running=True
        return True,"ADS-B tracker running."
    def stop(self):
        def work():
            self.running=False
            if self.tracker: self.tracker.stop(); self.tracker=None
            if self.controller: self.controller.shutdown(); self.controller=None
            return True,"ADS-B tracker stopped."
        self.app.run_bg(work,"Stopping ADS-B tracker…")
    def refresh(self):
        if not self.running: return
        def work():
            return True,self.format_contacts(self.tracker.snapshot())
        self.app.run_bg(work,None,display=False,callback=self._render)
        self.after(1500,self.refresh)
    def _render(self,msg): self.write(msg)
    def format_contacts(self,rows):
        out=["ICAO    CALLSIGN       ALT(ft)   SPEED(kt)  HDG     LAT       LON       RANGE/BRG"]
        out.append("-"*100)
        for a in rows:
            dist=bear=(None)
            if self.ref_lat is not None: dist,bear=a.distance_bearing_from(self.ref_lat,self.ref_lon)
            out.append(f"{a.icao:<7} {a.callsign or '-':<14} {str(a.altitude_ft or '-'):>8} {str(round(a.speed_kt) if a.speed_kt else '-'):>10} {str(round(a.heading_deg) if a.heading_deg else '-'):>5} {a.lat if a.lat is not None else '-':>9} {a.lon if a.lon is not None else '-':>9} {f'{dist:.1f}nm/{bear:.0f}°' if dist is not None else '-'}")
        return "\n".join(out)+f"\n\nContacts: {len(rows)}"

class MaritimePage(TablePage):
    def __init__(self,master,app):
        super().__init__(master,app,"Maritime","AIS vessel tracking and tactical marine contacts")
        self.ref_lat=self.ref_lon=None; self.tracker=None; self.controller=None; self.running=False
        ctk.CTkButton(self.controls,text="Start",command=self.start).pack(side="left",padx=4)
        ctk.CTkButton(self.controls,text="Stop / Cancel",command=self.stop,fg_color=BAD).pack(side="left",padx=4)
    def start(self): self.app.run_bg(self._start,"Starting AIS tracker…")
    def _start(self):
        rep=hardware.full_report()
        if rep.gps and rep.gps.fix:self.ref_lat,self.ref_lon=rep.gps.lat,rep.gps.lon
        self.controller=maritime.RtlAisController(); ok=self.controller.ensure_running()
        if not ok:return False,self.controller.last_error or "Could not start/connect to rtl_ais."
        self.tracker=maritime.AISTracker(); self.tracker.start(); self.running=True
        self.after(500,self.refresh); return True,"AIS tracker running."
    def stop(self):
        def work():
            self.running=False
            if self.tracker:self.tracker.stop();self.tracker=None
            if self.controller:self.controller.shutdown();self.controller=None
            return True,"AIS tracker stopped."
        self.app.run_bg(work,"Stopping AIS tracker…")
    def refresh(self):
        if not self.running:return
        rows=self.tracker.snapshot(); out=["MMSI         NAME                 LAT       LON       SOG     COG      RANGE/BRG","-"*95]
        for v in rows:
            dist=bear=(None)
            if self.ref_lat is not None:dist,bear=v.distance_bearing_from(self.ref_lat,self.ref_lon)
            out.append(f"{v.mmsi:<12} {(v.name or '-')[:20]:<20} {v.lat if v.lat is not None else '-':>8} {v.lon if v.lon is not None else '-':>9} {v.sog if v.sog is not None else '-':>6} {v.cog if v.cog is not None else '-':>7} {f'{dist:.1f}nm/{bear:.0f}°' if dist is not None else '-'}")
        self.write("\n".join(out)+f"\n\nVessels: {len(rows)}"); self.after(1500,self.refresh)

class ISSPage(TablePage):
    def __init__(self,master,app):
        super().__init__(master,app,"ISS","Current orbital position and next pass prediction")
        self.tracker=None
        ctk.CTkButton(self.controls,text="Refresh TLE / Position",command=self.refresh_data).pack(side="left",padx=4)
        self.after(1000,self.refresh_data)
    def refresh_data(self):
        def work():
            rep=hardware.full_report(); lat=rep.gps.lat if rep.gps and rep.gps.fix else 0.0; lon=rep.gps.lon if rep.gps and rep.gps.fix else 0.0
            t=iss.ISSTracker(lat,lon); sub=t.current_subpoint(); pred=t.next_pass() if rep.gps and rep.gps.fix else iss.PassPrediction()
            return True,(t,rep.gps,sub,pred)
        self.app.run_bg(work,"Updating ISS telemetry…",display=False,callback=self.render)
    def render(self,data):
        t,gps,sub,p=data; lat,lon,alt=sub
        lines=["ISS (ZARYA)","","Sub-satellite point: " + (f"{lat:+.3f}, {lon:+.3f}" if lat is not None else "unavailable"),f"Altitude: {alt:.1f} km" if alt is not None else "Altitude: unavailable",""]
        if gps and gps.fix:
            lines += ["Observer GPS: %.5f, %.5f"%(gps.lat,gps.lon),"Next rise: "+str(p.rise_time or "unknown"),"Culmination: "+str(p.culminate_time or "unknown"),"Set: "+str(p.set_time or "unknown"),"Max elevation: "+(f"{p.max_elevation_deg:.1f}°" if p.max_elevation_deg is not None else "unknown")]
        else: lines += ["Observer GPS: no fix","Pass prediction disabled until a GPS fix is available."]
        self.write("\n".join(lines))

class RadioPage(Page):
    def __init__(self,master,app):
        super().__init__(master,app,"Radio","Broadcast AM/FM receiver via rtl_fm → sox")
        self.tuner=radio.TunerState(); self.ctrl=radio.AudioTunerController()
        box=ctk.CTkFrame(self,fg_color=PANEL,corner_radius=12);box.pack(fill="x",padx=18,pady=12)
        self.mode=ctk.StringVar(value=self.tuner.mode.upper()); ctk.CTkOptionMenu(box,values=["FM","AM"],variable=self.mode,command=self.setmode).pack(side="left",padx=10,pady=14)
        self.freq=ctk.CTkEntry(box,width=180);self.freq.insert(0,str(self.tuner.freq_hz));self.freq.pack(side="left",padx=10)
        ctk.CTkLabel(box,text="Frequency Hz",text_color=MUTED).pack(side="left")
        ctk.CTkButton(box,text="Tune",command=self.tune).pack(side="left",padx=8)
        ctk.CTkButton(box,text="Start",command=self.start).pack(side="left",padx=4)
        ctk.CTkButton(box,text="Stop / Cancel",command=self.stop,fg_color=BAD).pack(side="left",padx=4)
        vol=ctk.CTkSlider(box,from_=0,to=100,command=lambda v:setattr(self.tuner,"volume_pct",int(v)));vol.set(70);vol.pack(side="left",padx=14,fill="x",expand=True)
        self.status=ctk.CTkLabel(self,text="Stopped",text_color=MUTED);self.status.pack(anchor="w",padx=22)
    def setmode(self,m): self.tuner.mode=m.lower(); self.tuner.freq_hz=next(p[1] for p in radio.PRESETS if p[2]==self.tuner.mode);self.freq.delete(0,"end");self.freq.insert(0,str(self.tuner.freq_hz))
    def tune(self):
        try:self.tuner.freq_hz=int(float(self.freq.get()))
        except ValueError:self.app.log("ERROR: Frequency must be numeric.","error")
    def start(self):
        def work():
            self.tune(); ok=self.ctrl.start(self.tuner); return ok,("Radio playing." if ok else self.ctrl.last_error)
        self.app.run_bg(work,"Starting radio…")
    def stop(self):self.app.run_bg(lambda:(self.ctrl.stop() or True,"Radio stopped."),"Stopping radio…")

class WaterfallPage(Page):
    def __init__(self,master,app):
        super().__init__(master,app,"Waterfalls","FFT spectrum and scrolling waterfall; simulated when no RTL-SDR is available")
        bar=ctk.CTkFrame(self,fg_color=PANEL,corner_radius=10);bar.pack(fill="x",padx=18,pady=8)
        self.preset=ctk.StringVar(value=waterfall.BAND_PRESETS[0][0]); ctk.CTkOptionMenu(bar,values=[x[0] for x in waterfall.BAND_PRESETS],variable=self.preset,command=self.change).pack(side="left",padx=10,pady=10)
        ctk.CTkButton(bar,text="Start",command=self.start).pack(side="left",padx=4);ctk.CTkButton(bar,text="Stop / Cancel",command=self.stop,fg_color=BAD).pack(side="left",padx=4)
        self.canvas=ctk.CTkCanvas(self,background="#05070a",highlightthickness=0);self.canvas.pack(fill="both",expand=True,padx=18,pady=10)
        self.tuner=waterfall.TunerState();self.reader=None;self.running=False
    def change(self,name):self.tuner.apply_preset([x[0] for x in waterfall.BAND_PRESETS].index(name));
    def start(self):
        def work():
            if self.reader:self.reader.close()
            self.reader=waterfall.SDRReader(self.tuner);self.running=True;return True,"Waterfall started (%s)."%("SIMULATED" if self.reader.simulated else "LIVE")
        self.app.run_bg(work,"Starting spectrum…",callback=lambda _:self.tick())
    def stop(self):
        def work():
            self.running=False
            if self.reader:self.reader.close();self.reader=None
            return True,"Waterfall stopped."
        self.app.run_bg(work,"Stopping spectrum…")
    def tick(self):
        if not self.running:return
        def work():return True,self.reader.read_power_spectrum(max(20,self.canvas.winfo_width()-10))
        self.app.run_bg(work,None,display=False,callback=self.draw)
    def draw(self,arr):
        w=max(20,self.canvas.winfo_width());h=max(80,self.canvas.winfo_height());self.canvas.delete("all")
        n=len(arr); step=max(1,w/n); hist=getattr(self,"hist",[]);hist.insert(0,arr);self.hist=hist[:max(20,h//3)]
        for x,v in enumerate(arr):
            xx=x*step; y=h-int(float(v)*(h*0.65)); self.canvas.create_line(xx,h,xx,y,fill="#4ade80",width=max(1,int(step)))
        for r,row in enumerate(hist):
            yy=int(h*0.68)+r*2
            if yy>=h:break
            for x,v in enumerate(row[::max(1,int(n/160))]):
                intensity=float(v); shade=int(40+intensity*200); shade=max(0,min(255,shade)); c=f"#{shade:02x}{shade:02x}{shade:02x}"
                self.canvas.create_rectangle(x*3,yy,x*3+3,yy+2,outline=c,fill=c)
        self.after(120,self.tick)

class AudioDecoderPage(Page):
    def __init__(self,master,app,kind):
        title="SSTV" if kind=="sstv" else "Morse"; sub="Slow Scan TV decoder (Martin / Scottie / Robot)" if kind=="sstv" else "CW / Morse decoder and visualizer"
        super().__init__(master,app,title,sub);self.kind=kind
        box=ctk.CTkFrame(self,fg_color=PANEL,corner_radius=12);box.pack(fill="x",padx=18,pady=10)
        self.freq=ctk.CTkEntry(box,width=180);self.freq.insert(0,"433100000" if kind=="sstv" else "145500000");self.freq.pack(side="left",padx=10,pady=12)
        self.source=ctk.CTkOptionMenu(box,values=["Microphone","RTL-SDR"],variable=ctk.StringVar(value="Microphone"));self.source.pack(side="left",padx=6)
        ctk.CTkButton(box,text="Start",command=self.start).pack(side="left",padx=4);ctk.CTkButton(box,text="Stop / Cancel",command=self.stop,fg_color=BAD).pack(side="left",padx=4);ctk.CTkButton(box,text="Clear",command=lambda:self.output.delete("1.0","end")).pack(side="left",padx=4)
        self.output=ctk.CTkTextbox(self,fg_color=PANEL,text_color=TEXT,font=ctk.CTkFont(family="DejaVu Sans Mono",size=12));self.output.pack(fill="both",expand=True,padx=18,pady=10)
        self.decoder=None;self.capture=None;self.running=False
    def start(self):self.app.run_bg(self._start,"Starting decoder…",callback=lambda _:self.poll())
    def _start(self):
        if self.kind=="sstv": self.decoder=sstv.SstvDecoder(); self.capture=sstv.AudioCaptureController()
        else:self.decoder=morse.MorseDecoder();self.capture=morse.AudioCaptureController()
        src=self.source.get()
        if src=="RTL-SDR":
            f=int(float(self.freq.get())); ok=self.capture.start_rtl_fm(f,self.decoder)
        else: ok=self.capture.start_mic(self.decoder)
        self.running=ok
        return ok,("Decoder running." if ok else self.capture.last_error)
    def stop(self):
        def work():
            self.running=False
            if self.capture:self.capture.stop()
            return True,"Decoder stopped."
        self.app.run_bg(work,"Stopping decoder…")
    def poll(self):
        if not self.running:return
        def work():
            self.decoder.process();return True,self.decoder.snapshot() if self.kind=="sstv" else self.decoder.text()
        self.app.run_bg(work,None,display=False,callback=self.render);self.after(500,self.poll)
    def render(self,data):
        if self.kind=="sstv":
            self.output.delete("1.0","end"); self.output.insert("end",f"Rows decoded: {data[1] if isinstance(data,tuple) else 'unknown'}\n")
        else:
            self.output.delete("1.0","end");self.output.insert("end",str(data))

class HardwarePage(TablePage):
    def __init__(self,master,app):
        super().__init__(master,app,"Hardware","SDR, GPS, DVB driver and dump1090 diagnostics")
        ctk.CTkButton(self.controls,text="Run Hardware Scan",command=self.scan).pack(side="left",padx=4);self.scan()
    def scan(self):
        def work():
            r=hardware.full_report();return True,r
        self.app.run_bg(work,"Scanning hardware…",display=False,callback=self.render)
    def render(self,r):
        lines=["SDR DEVICES:"]+[f"  - {x}" for x in r.sdrs] or ["  NONE DETECTED"]
        lines += ["",f"GPS: {r.gps or 'NONE'}",f"dump1090 raw port: {'OPEN' if r.dump1090_running else 'CLOSED'}","","WARNINGS:"]+[f"  ! {e}" for e in r.errors]
        self.write("\n".join(lines))

class App(ctk.CTk):
    def __init__(self):
        super().__init__();self.title(APP_NAME+" — Tactical RF & Telemetry Suite");self.geometry("1280x820");self.minsize(900,620);self.configure(fg_color=BG)
        self.executor=ThreadPoolExecutor(max_workers=6);self.events=queue.Queue();self.page=None;self.pages={};self.dark=True
        self.protocol("WM_DELETE_WINDOW",self.close)
        self.build();self.show("Dashboard");self.telemetry()
    def build(self):
        self.grid_columnconfigure(1,weight=1);self.grid_rowconfigure(0,weight=1);self.grid_rowconfigure(1,weight=0)
        self.side=ctk.CTkFrame(self,width=235,fg_color=PANEL,corner_radius=0);self.side.grid(row=0,column=0,rowspan=2,sticky="nsew");self.side.grid_propagate(False)
        ctk.CTkLabel(self.side,text=APP_NAME,font=ctk.CTkFont(size=22,weight="bold"),text_color=TEXT).pack(anchor="w",padx=18,pady=(22,2));ctk.CTkLabel(self.side,text="Tactical RF & Telemetry Suite",text_color=MUTED).pack(anchor="w",padx=18,pady=(0,16))
        nav=[("Dashboard",HomePage),("Airplanes",AirplanesPage),("Waterfalls",WaterfallPage),("Radio",RadioPage),("Maritime",MaritimePage),("ISS",ISSPage),("SSTV",lambda m,a:AudioDecoderPage(m,a,"sstv")),("Morse",lambda m,a:AudioDecoderPage(m,a,"morse")),("Hardware",HardwarePage)]
        for name,cls in nav:
            ctk.CTkButton(self.side,text=name,command=lambda n=name:self.show(n),fg_color="transparent",text_color=TEXT,hover_color=ACCENT,anchor="w",height=36).pack(fill="x",padx=10,pady=2)
        ctk.CTkLabel(self.side,text="SYSTEM TELEMETRY",text_color=MUTED,font=ctk.CTkFont(size=11,weight="bold")).pack(anchor="w",padx=18,pady=(22,5))
        self.tele=ctk.CTkLabel(self.side,text="CPU --\nRAM --\nSDR --\nGPS --",justify="left",text_color=TEXT);self.tele.pack(anchor="w",padx=18)
        self.theme=ctk.CTkSwitch(self.side,text="Dark mode",command=self.toggle_theme);self.theme.select();self.theme.pack(anchor="w",padx=18,pady=18)
        self.main=ctk.CTkFrame(self,fg_color=BG,corner_radius=0);self.main.grid(row=0,column=1,sticky="nsew");self.main.grid_rowconfigure(0,weight=1);self.main.grid_columnconfigure(0,weight=1)
        self.console=ctk.CTkTextbox(self,fg_color=("#111827","#090c10"),text_color="#d1d5db",height=145,font=ctk.CTkFont(family="DejaVu Sans Mono",size=11));self.console.grid(row=1,column=1,sticky="ew",padx=10,pady=(0,10))
        self.console.bind("<Control-c>",lambda e:self.copy_output())
        for tag in ("info","success","warning","error"): self.console.tag_config(tag,foreground={"info":"#d1d5db","success":"#4ade80","warning":"#fbbf24","error":"#f87171"}[tag])
        ctk.CTkButton(self.side,text="Clear Logs",command=lambda:self.console.delete("1.0","end")).pack(side="bottom",fill="x",padx=12,pady=(0,6));ctk.CTkButton(self.side,text="Copy Output",command=self.copy_output).pack(side="bottom",fill="x",padx=12,pady=(0,6))
        self.nav_classes=dict(nav)
    def show(self,name):
        if self.page:self.page.destroy()
        cls=self.nav_classes[name];self.page=cls(self.main,self);self.page.grid(row=0,column=0,sticky="nsew");self.log("VIEW: "+name)
    def log(self,msg,level="info"):
        self.console.insert("end",f"[{time.strftime('%H:%M:%S')}] {msg}\n",level);self.console.see("end")
    def run_bg(self,fn,status=None,display=True,callback=None):
        if status:self.log(status)
        fut=self.executor.submit(fn)
        def done(f):
            try: ok,data=f.result()
            except Exception as e: ok,data=False,f"{type(e).__name__}: {e}"
            self.after(0,lambda:self._complete(ok,data,display,callback))
        fut.add_done_callback(done)
    def _complete(self,ok,data,display,callback):
        if ok:self.log(str(data) if display else "Background operation completed.","success")
        else:self.log(str(data),"error")
        if callback and ok: callback(data)
    def telemetry(self):
        try:
            cpu=psutil.cpu_percent();ram=psutil.virtual_memory().percent
            self.tele.configure(text=f"CPU {cpu:5.1f}%\nRAM {ram:5.1f}%\nOS {platform.system()} {platform.machine()}")
        except Exception:pass
        self.after(1500,self.telemetry)
    def toggle_theme(self):
        self.dark=bool(self.theme.get());ctk.set_appearance_mode("Dark" if self.dark else "Light")
    def copy_output(self):
        self.clipboard_clear();self.clipboard_append(self.console.get("1.0","end"));self.log("Console output copied.")
    def close(self):
        for p in self.pages.values():
            try:p.destroy()
            except:pass
        self.executor.shutdown(wait=False,cancel_futures=True);self.destroy()

def main():
    ctk.set_appearance_mode("Dark");ctk.set_default_color_theme("blue");app=App();app.mainloop()
if __name__=="__main__":main()
