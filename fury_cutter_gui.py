"""
Fury Cutter GUI - User-friendly interface for Pokemon video battle detection.
"""
import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from pathlib import Path

# Game versions with display names
GAME_VERSIONS = {
    "black": "Pokemon Black",
    "platinum": "Pokemon Platinum",
    "heartgold": "Pokemon HeartGold",
    "emerald": "Pokemon Emerald",
    "ruby": "Pokemon Ruby",
    "sapphire": "Pokemon Sapphire",
    "firered": "Pokemon FireRed",
    "leafgreen": "Pokemon LeafGreen",
    "crystal": "Pokemon Crystal",
    "yellow": "Pokemon Yellow",
    "red": "Pokemon Red",
}

SCRIPT_DIR = Path(__file__).parent
FURY_CUTTER_SCRIPT = SCRIPT_DIR / "fury_cutter.py"


class FuryCutterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Fury Cutter")
        self.root.geometry("720x660")
        self.root.minsize(600, 550)
        self.process = None

        # --- Style ---
        style = ttk.Style()
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Sub.TLabel", font=("Segoe UI", 9), foreground="#666")

        main = ttk.Frame(root, padding=16)
        main.pack(fill="both", expand=True)

        # --- Header ---
        ttk.Label(main, text="Fury Cutter", style="Header.TLabel").pack(anchor="w")
        ttk.Label(main, text="Pokemon video battle detection tool", style="Sub.TLabel").pack(anchor="w")
        ttk.Separator(main, orient="horizontal").pack(fill="x", pady=(8, 12))

        # --- Input section ---
        input_frame = ttk.LabelFrame(main, text="Input", padding=8)
        input_frame.pack(fill="x", pady=(0, 8))

        # Video path
        path_row = ttk.Frame(input_frame)
        path_row.pack(fill="x", pady=2)
        ttk.Label(path_row, text="Video file or folder:").pack(side="left")

        self.video_path = tk.StringVar()
        path_entry = ttk.Entry(path_row, textvariable=self.video_path)
        path_entry.pack(side="left", fill="x", expand=True, padx=(8, 4))

        ttk.Button(path_row, text="File...", width=6, command=self.browse_file).pack(side="left", padx=2)
        ttk.Button(path_row, text="Folder...", width=7, command=self.browse_folder).pack(side="left")

        # Game version
        ver_row = ttk.Frame(input_frame)
        ver_row.pack(fill="x", pady=4)
        ttk.Label(ver_row, text="Game version:").pack(side="left")

        self.version = tk.StringVar(value="black")
        version_combo = ttk.Combobox(
            ver_row, textvariable=self.version, state="readonly", width=30,
            values=[f"{key}  -  {name}" for key, name in GAME_VERSIONS.items()],
        )
        version_combo.pack(side="left", padx=(8, 0))
        version_combo.current(0)
        version_combo.bind("<<ComboboxSelected>>", self._on_version_select)

        # --- Options section ---
        options_frame = ttk.LabelFrame(main, text="Options", padding=8)
        options_frame.pack(fill="x", pady=(0, 8))

        # Row 1: detection mode + downscale
        row1 = ttk.Frame(options_frame)
        row1.pack(fill="x", pady=2)

        ttk.Label(row1, text="Detection mode:").pack(side="left")
        self.detection_mode = tk.StringVar(value="auto")
        ttk.Combobox(
            row1, textvariable=self.detection_mode, state="readonly", width=10,
            values=["auto", "template", "ocr"],
        ).pack(side="left", padx=(4, 16))

        ttk.Label(row1, text="Downscale:").pack(side="left")
        self.downscale = tk.StringVar(value="0.25")
        ttk.Entry(row1, textvariable=self.downscale, width=6).pack(side="left", padx=(4, 16))

        ttk.Label(row1, text="Workers:").pack(side="left")
        self.workers = tk.StringVar(value="")
        ttk.Entry(row1, textvariable=self.workers, width=5).pack(side="left", padx=(4, 0))

        # Row 2: tuning params
        row2 = ttk.Frame(options_frame)
        row2.pack(fill="x", pady=4)

        ttk.Label(row2, text="Transition jump:").pack(side="left")
        self.transition_jump = tk.StringVar(value="720")
        ttk.Entry(row2, textvariable=self.transition_jump, width=6).pack(side="left", padx=(4, 16))

        ttk.Label(row2, text="Early interval:").pack(side="left")
        self.early_interval = tk.StringVar(value="480")
        ttk.Entry(row2, textvariable=self.early_interval, width=6).pack(side="left", padx=(4, 16))

        ttk.Label(row2, text="Normal interval:").pack(side="left")
        self.normal_interval = tk.StringVar(value="1440")
        ttk.Entry(row2, textvariable=self.normal_interval, width=6).pack(side="left", padx=(4, 0))

        # Row 3: trainers override + debug
        row3 = ttk.Frame(options_frame)
        row3.pack(fill="x", pady=2)

        ttk.Label(row3, text="Trainers (override, space-separated):").pack(side="left")
        self.trainers = tk.StringVar(value="")
        ttk.Entry(row3, textvariable=self.trainers).pack(side="left", fill="x", expand=True, padx=(4, 16))

        self.debug_ocr = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text="Debug OCR", variable=self.debug_ocr).pack(side="left")

        # Row 4: output path
        row4 = ttk.Frame(options_frame)
        row4.pack(fill="x", pady=2)

        ttk.Label(row4, text="Output JSON:").pack(side="left")
        self.output_path = tk.StringVar(value="")
        ttk.Entry(row4, textvariable=self.output_path).pack(side="left", fill="x", expand=True, padx=(4, 4))
        ttk.Button(row4, text="Browse...", width=8, command=self.browse_output).pack(side="left")

        # --- Buttons ---
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x", pady=(0, 8))

        self.run_btn = ttk.Button(btn_frame, text="Run Analysis", command=self.run_analysis)
        self.run_btn.pack(side="left")

        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_analysis, state="disabled")
        self.stop_btn.pack(side="left", padx=8)

        self.open_output_btn = ttk.Button(btn_frame, text="Open Output", command=self.open_output, state="disabled")
        self.open_output_btn.pack(side="right")

        # --- Log output ---
        log_frame = ttk.LabelFrame(main, text="Output", padding=4)
        log_frame.pack(fill="both", expand=True)

        self.log = scrolledtext.ScrolledText(log_frame, wrap="word", height=12, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)
        self.log.config(state="disabled")

        # --- Status bar ---
        self.status = tk.StringVar(value="Ready")
        ttk.Label(main, textvariable=self.status, style="Sub.TLabel").pack(anchor="w", pady=(4, 0))

    def _on_version_select(self, event):
        """Extract the version key from the combo display string."""
        selected = event.widget.get()
        key = selected.split("  -  ")[0].strip()
        self.version.set(key)

    def browse_file(self):
        path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")],
        )
        if path:
            self.video_path.set(path)

    def browse_folder(self):
        path = filedialog.askdirectory(title="Select Folder with MP4 Files")
        if path:
            self.video_path.set(path)

    def browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Save Output JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if path:
            self.output_path.set(path)

    def log_append(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.config(state="disabled")

    def build_command(self):
        video = self.video_path.get().strip()
        version = self.version.get().strip()

        if not video:
            raise ValueError("Please select a video file or folder.")
        if not version:
            raise ValueError("Please select a game version.")

        cmd = [sys.executable, str(FURY_CUTTER_SCRIPT), video, "--version", version]

        # Detection mode
        mode = self.detection_mode.get()
        if mode != "auto":
            cmd += ["--detection-mode", mode]

        # Downscale
        ds = self.downscale.get().strip()
        if ds and ds != "0.25":
            cmd += ["--downscale", ds]

        # Workers
        w = self.workers.get().strip()
        if w:
            cmd += ["--workers", w]

        # Tuning
        tj = self.transition_jump.get().strip()
        if tj and tj != "720":
            cmd += ["--transition-jump", tj]

        ei = self.early_interval.get().strip()
        if ei and ei != "480":
            cmd += ["--early-interval", ei]

        ni = self.normal_interval.get().strip()
        if ni and ni != "1440":
            cmd += ["--normal-interval", ni]

        # Trainers
        trainers = self.trainers.get().strip()
        if trainers:
            cmd += ["--trainers"] + trainers.split()

        # Output
        out = self.output_path.get().strip()
        if out:
            cmd += ["--output", out]

        # Debug
        if self.debug_ocr.get():
            cmd.append("--debug-ocr")

        return cmd

    def run_analysis(self):
        try:
            cmd = self.build_command()
        except ValueError as e:
            self.log_append(f"Error: {e}\n")
            return

        # Clear log
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

        self.log_append(f"$ {' '.join(cmd)}\n\n")
        self.status.set("Running...")
        self.run_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.open_output_btn.config(state="disabled")

        thread = threading.Thread(target=self._run_process, args=(cmd,), daemon=True)
        thread.start()

    def _run_process(self, cmd):
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(SCRIPT_DIR),
            )
            for line in self.process.stdout:
                self.root.after(0, self.log_append, line)

            self.process.wait()
            rc = self.process.returncode
            msg = f"\nProcess finished with exit code {rc}\n"
            self.root.after(0, self.log_append, msg)
            self.root.after(0, self._on_done, rc)
        except Exception as e:
            self.root.after(0, self.log_append, f"\nError: {e}\n")
            self.root.after(0, self._on_done, 1)

    def _on_done(self, return_code):
        self.process = None
        self.run_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        if return_code == 0:
            self.status.set("Done!")
            self.open_output_btn.config(state="normal")
        else:
            self.status.set(f"Failed (exit code {return_code})")

    def stop_analysis(self):
        if self.process:
            self.process.terminate()
            self.log_append("\nProcess terminated by user.\n")
            self.status.set("Stopped")

    def open_output(self):
        """Open the output JSON file or the video's directory."""
        out = self.output_path.get().strip()
        if out and Path(out).exists():
            os.startfile(out)
        else:
            # Default output is next to the video file
            video = self.video_path.get().strip()
            if video:
                p = Path(video)
                if p.is_dir():
                    os.startfile(str(p))
                else:
                    json_path = p.with_suffix(".json")
                    if json_path.exists():
                        os.startfile(str(json_path))
                    else:
                        os.startfile(str(p.parent))


def main():
    root = tk.Tk()
    FuryCutterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
