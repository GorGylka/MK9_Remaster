"""Mortal Kombat 9 Remaster build 206 for PS Vita."""

import argparse
from pathlib import Path
from queue import Empty, SimpleQueue
from threading import Thread
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from PIL import Image, ImageTk

from assembler import Inputs, KRATOS, XDELTA, assemble, find_eboot, is_decrypted_eboot, vita_root
from localization import BuildError, text


TITLE = "Mortal Kombat 9 Remaster"
PC_EXECUTABLE = "MKKE.exe"
HELP_IMAGES = Path(__file__).resolve().parent / "help-images"
KRATOS_MOD_URL = "https://www.nexusmods.com/mortalkombat9/mods/132"


class GifGuide(ttk.Label):
    """Loop a guide while its source is selected."""

    def __init__(self, parent, filename):
        super().__init__(parent)
        self.path = HELP_IMAGES / filename
        self.animation = None
        self.picture = None
        self.timer = None

    def show(self):
        self.grid()
        if self.animation is None:
            self.animation = Image.open(self.path)
            self.show_frame()

    def hide(self):
        self.grid_remove()
        if self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None
        if self.animation is not None:
            self.animation.close()
            self.animation = None

    def show_frame(self):
        frame = self.animation.convert("RGBA")
        if self.picture is None:
            self.picture = ImageTk.PhotoImage(frame, master=self)
            self.configure(image=self.picture)
        else:
            self.picture.paste(frame)
        delay = self.animation.info.get("duration") or 100
        self.timer = self.after(delay, self.next_frame)

    def next_frame(self):
        self.animation.seek((self.animation.tell() + 1) % self.animation.n_frames)
        self.show_frame()


class InstallerWindow:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{TITLE} · 206")
        self.root.minsize(650, 480)
        width = min(760, root.winfo_screenwidth() - 28)
        height = min(720, root.winfo_screenheight() - 85)
        left = max(0, (root.winfo_screenwidth() - width) // 2)
        top = max(8, (root.winfo_screenheight() - height - 48) // 2)
        self.root.geometry(f"{width}x{height}+{left}+{top}")
        self.root.state("zoomed")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.language = tk.StringVar(value="en")
        self.mode = tk.StringVar(value="vita3k")
        self.source_mode = self.mode.get()
        self.translated = {}
        self.folder_help = tk.StringVar()
        self.eboot_help = tk.StringVar()
        self.eboot_status = tk.StringVar()
        self.pc = tk.StringVar()
        self.vita = tk.StringVar()
        self.eboot = tk.StringVar()
        self.output = tk.StringVar()
        self.use_kratos = tk.BooleanVar(value=False)
        self.kratos = tk.StringVar()
        self.status = tk.StringVar()
        self.status_key = "ready"
        self.messages = SimpleQueue()
        self.controls = []
        self.worker = None
        self.result = None
        self.auto_eboot_path = None
        self.help_images = {
            language: tk.PhotoImage(file=HELP_IMAGES / f"vita3k-{language}-inline.png")
            for language in ("en", "ru")
        }

        root.configure(background="#18191b")
        style = ttk.Style(root)
        style.configure("Heading.TLabel", font=("Segoe UI Semibold", 22), background="#18191b", foreground="#f3f1ec")
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10), background="#18191b", foreground="#d8b993")
        style.configure("Action.TButton", font=("Segoe UI Semibold", 10))
        style.configure("Valid.TLabel", foreground="#167043", font=("Segoe UI Symbol", 12))
        style.configure("Invalid.TLabel", foreground="#a6262f", font=("Segoe UI Symbol", 12))
        style.configure("Link.TLabel", foreground="#0a5da5", font=("Segoe UI", 9, "underline"))
        hero = tk.Frame(root, background="#18191b", padx=25, pady=16)
        hero.grid(row=0, sticky="ew")
        hero.columnconfigure(0, weight=1)
        ttk.Label(hero, text=TITLE, style="Heading.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(hero, textvariable=self.localized_var("subtitle"), style="Subtitle.TLabel").grid(row=1, column=0, sticky="w")
        for column, code in enumerate(("en", "ru"), 1):
            button = ttk.Radiobutton(hero, text=code.upper(), value=code, variable=self.language,
                                     command=self.change_language, style="Toolbutton", width=4)
            button.grid(row=0, column=column, padx=(8 if column == 1 else 2, 0))
            self.controls.append(button)

        body = ttk.Frame(root)
        body.grid(row=1, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(body, highlightthickness=0, background=style.lookup("TFrame", "background"))
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        panel = ttk.Frame(self.canvas, padding=(25, 15, 20, 12))
        panel_item = self.canvas.create_window(0, 0, window=panel, anchor="nw")
        panel.bind("<Configure>", lambda _: self.canvas.configure(scrollregion=self.canvas.bbox(panel_item)))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(panel_item, width=event.width))
        self.root.bind("<MouseWheel>", self.scroll_form)
        panel.bind("<Map>", lambda _: self.canvas.yview_moveto(0))
        self.root.bind("<FocusIn>", lambda event: self.reveal_control(event.widget, panel), add=True)
        panel.columnconfigure(1, weight=1)
        self.path_field(panel, 0, "pc_game", self.pc, self.select_pc, check_asset=True, readonly=True)

        kratos_option = ttk.Frame(panel)
        kratos_option.grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 2))
        kratos = ttk.Checkbutton(kratos_option, textvariable=self.localized_var("hd_kratos"),
                                variable=self.use_kratos, command=self.refresh_controls)
        kratos.pack(side="left")
        self.controls.append(kratos)
        kratos_requirement = ttk.Label(kratos_option, textvariable=self.localized_var("installed_kratos_mod"),
                                       style="Link.TLabel", cursor="hand2", takefocus=True)
        kratos_requirement.pack(side="left")
        for event in ("<Button-1>", "<Return>", "<space>"):
            kratos_requirement.bind(event, self.open_kratos_mod)
        ttk.Label(kratos_option, text=")").pack(side="left")

        self.kratos_fields = self.path_field(panel, 2, KRATOS, self.kratos, self.select_kratos)
        self.kratos_mark = self.path_mark(panel, 2)
        self.kratos.trace_add("write", self.update_kratos_mark)

        ttk.Label(panel, textvariable=self.localized_var("vita_source")).grid(row=3, column=0, sticky="w", pady=(12, 4))
        options = ttk.Frame(panel)
        options.grid(row=3, column=1, columnspan=2, sticky="w", pady=(12, 4))
        emulator = ttk.Radiobutton(options, text="Vita3K", value="vita3k", variable=self.mode, command=self.change_source)
        console = ttk.Radiobutton(options, textvariable=self.localized_var("real_vita"), value="vita", variable=self.mode,
                                  command=self.change_source)
        for option in (emulator, console):
            option.pack(side="left", padx=(0, 16))
            self.controls.append(option)
        self.help_label(panel, 4, self.folder_help, pady=(0, 5))
        self.vita_shell_guide = GifGuide(panel, "vita-shell.gif")
        self.vita_shell_guide.grid(row=5, column=0, columnspan=4, sticky="w", pady=(0, 5))
        self.path_field(panel, 6, "vita_files", self.vita, self.select_vita, check_asset=True)
        self.help_label(panel, 7, self.eboot_help, pady=(9, 4))
        self.help_picture = ttk.Label(panel)
        self.help_picture.grid(row=8, column=0, columnspan=4, sticky="w", pady=(0, 5))
        self.fagdec_guide = GifGuide(panel, "fagdec.gif")
        self.fagdec_guide.grid(row=8, column=0, columnspan=4, sticky="w", pady=(0, 5))
        self.path_field(panel, 9, "decrypted_eboot", self.eboot, self.select_eboot, pady=(4, 3))
        self.eboot_mark = self.path_mark(panel, 9)
        self.help_label(panel, 10, self.eboot_status)
        for value in (self.vita, self.eboot):
            value.trace_add("write", self.update_eboot_mark)

        ttk.Separator(panel).grid(row=11, column=0, columnspan=4, sticky="ew", pady=9)
        self.path_field(panel, 12, "output", self.output, self.select_output)

        footer = ttk.Frame(root, padding=(25, 0, 25, 15))
        footer.grid(row=2, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Separator(footer).grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.progress = ttk.Progressbar(footer, mode="determinate", maximum=100)
        self.progress.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        self.help_label(footer, 2, self.status)

        actions = ttk.Frame(footer)
        actions.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(actions, textvariable=self.localized_var("license"), command=self.show_license).pack(side="left")
        self.build = ttk.Button(actions, textvariable=self.localized_var("build"), command=self.start, style="Action.TButton")
        self.build.pack(side="right")
        self.open_folder = ttk.Button(actions, textvariable=self.localized_var("open_output"), command=self.open_result)
        self.open_folder.pack(side="right", padx=(0, 8))
        self.controls.append(self.build)
        self.change_language()
        self.refresh_controls()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def tr(self, key):
        return text(self.language.get(), key)

    def localized_var(self, key):
        if key not in self.translated:
            self.translated[key] = tk.StringVar(value=self.tr(key))
        return self.translated[key]

    def change_language(self):
        for key, variable in self.translated.items():
            variable.set(self.tr(key))
        self.update_source_help()
        self.set_status(self.status_key)

    def set_status(self, key):
        self.status_key = key
        self.status.set(self.tr(key))

    @staticmethod
    def help_label(panel, row, variable, pady=0):
        label = ttk.Label(panel, textvariable=variable, wraplength=580, justify="left")
        label.grid(row=row, column=0, columnspan=4, sticky="ew", pady=pady)
        label.bind("<Configure>", lambda event: label.configure(wraplength=max(300, event.width - 4)))

    def path_field(self, panel, row, label, value, choose, *, check_asset=False, readonly=False, pady=3):
        heading = ttk.Label(panel, text=label) if label == KRATOS else ttk.Label(panel, textvariable=self.localized_var(label))
        heading.grid(row=row, column=0, sticky="w", padx=(0, 12), pady=pady)
        entry = ttk.Entry(panel, textvariable=value)
        entry.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=pady)
        if readonly:
            entry.state(["readonly"])
        button = ttk.Button(panel, textvariable=self.localized_var("browse"), command=choose)
        button.grid(row=row, column=2, sticky="ew")
        if check_asset:
            mark = self.path_mark(panel, row)
            value.trace_add("write", lambda *_: mark.configure(text="✓" if self.has_asset(value.get()) else ""))
        self.controls.extend((entry, button))
        return entry, button

    @staticmethod
    def path_mark(panel, row):
        mark = ttk.Label(panel, width=2, style="Valid.TLabel", anchor="center")
        mark.grid(row=row, column=3, padx=(5, 0))
        return mark

    @staticmethod
    def open_kratos_mod(_event):
        webbrowser.open(KRATOS_MOD_URL)
        return "break"

    def scroll_form(self, event):
        self.canvas.yview_scroll(-int(event.delta / 120), "units")

    def reveal_control(self, widget, panel):
        if not str(widget).startswith(f"{panel}."):
            return
        viewport = self.canvas.winfo_height()
        top = widget.winfo_rooty() - panel.winfo_rooty()
        bottom = top + widget.winfo_height()
        visible_top = self.canvas.canvasy(0)
        if top < visible_top:
            self.canvas.yview_moveto(top / max(1, panel.winfo_height()))
        elif bottom > visible_top + viewport:
            self.canvas.yview_moveto((bottom - viewport) / max(1, panel.winfo_height()))

    @staticmethod
    def has_asset(folder):
        try:
            return bool(folder.strip()) and (Path(folder.strip()) / "Asset").is_dir()
        except OSError:
            return False

    @staticmethod
    def choose_folder(variable, title):
        folder = filedialog.askdirectory(title=title, initialdir=variable.get() or None)
        if folder:
            variable.set(folder)
        return folder

    def select_pc(self):
        path = filedialog.askopenfilename(title=self.tr("select_pc"), initialdir=self.pc.get() or None,
                                          filetypes=[(PC_EXECUTABLE, PC_EXECUTABLE)])
        if not path:
            return
        executable = Path(path)
        if executable.name.casefold() != PC_EXECUTABLE.casefold():
            messagebox.showerror(TITLE, self.tr("valid_pc"))
            return
        self.pc.set(str(executable.parent))
        if not self.kratos.get():
            candidate = executable.parent / "Asset" / KRATOS
            if candidate.is_file():
                self.kratos.set(str(candidate))

    def select_vita(self):
        if self.choose_folder(self.vita, self.tr(f"select_{self.mode.get()}")):
            if self.mode.get() == "vita":
                self.vita.set(str(vita_root(Path(self.vita.get()))))
            self.auto_eboot(replace_manual=self.mode.get() == "vita3k")

    def select_eboot(self):
        path = filedialog.askopenfilename(title=self.tr("select_eboot"),
                                          filetypes=[(self.tr("vita_executable"), "*.bin *.elf"),
                                                     (self.tr("all_files"), "*.*")])
        if path:
            self.auto_eboot_path = None
            self.eboot.set(path)

    def select_kratos(self):
        path = filedialog.askopenfilename(title=self.tr("select_kratos"),
                                          filetypes=[(self.tr("mk9_package"), "*.xxx"),
                                                     (self.tr("all_files"), "*.*")])
        if path:
            self.kratos.set(path)

    def select_output(self):
        self.choose_folder(self.output, self.tr("select_output"))

    def change_source(self):
        mode = self.mode.get()
        if mode == self.source_mode:
            return
        self.source_mode = mode
        self.auto_eboot_path = None
        self.vita.set("")
        self.eboot.set("")
        self.update_source_help()

    def update_source_help(self):
        mode = self.mode.get()
        self.folder_help.set(self.tr(f"{mode}_folder_help"))
        self.eboot_help.set(self.tr(f"{mode}_eboot_help"))
        if mode == "vita3k":
            self.vita_shell_guide.hide()
            self.fagdec_guide.hide()
            self.help_picture.configure(image=self.help_images[self.language.get()])
            self.help_picture.grid()
        else:
            self.help_picture.grid_remove()
            self.vita_shell_guide.show()
            self.fagdec_guide.show()
        self.update_eboot_mark()

    def auto_eboot(self, *, replace_manual=False):
        current = self.eboot.get().strip()
        if current and current != self.auto_eboot_path and not replace_manual:
            return
        selected = self.vita.get().strip()
        candidate = None
        if selected:
            emulator = self.mode.get() == "vita3k"
            folder = Path(selected) if emulator else vita_root(Path(selected))
            if self.has_asset(str(folder)):
                candidate = find_eboot(folder, emulator)
        self.auto_eboot_path = str(candidate) if candidate else None
        self.eboot.set(self.auto_eboot_path or "")

    def update_eboot_mark(self, *_):
        path = self.eboot.get().strip()
        if path and is_decrypted_eboot(Path(path)):
            self.eboot_mark.configure(text="✓", style="Valid.TLabel")
            self.eboot_status.set("")
            return
        no_cache = not path and self.mode.get() == "vita3k" and bool(self.vita.get().strip())
        self.eboot_mark.configure(text="✗" if path or no_cache else "", style="Invalid.TLabel")
        key = "invalid_eboot" if path else "eboot_not_found"
        self.eboot_status.set(self.tr(key) if path or no_cache else "")

    def update_kratos_mark(self, *_):
        selected = self.kratos.get().strip()
        available = self.use_kratos.get() and selected and Path(selected).is_file()
        self.kratos_mark.configure(text="✓" if available else "")

    def refresh_controls(self):
        busy = self.worker is not None
        for widget in self.controls:
            widget.state(["disabled" if busy else "!disabled"])
        if not self.use_kratos.get():
            for widget in self.kratos_fields:
                widget.state(["disabled"])
        self.update_kratos_mark()
        self.open_folder.state(["!disabled" if self.result and not busy else "disabled"])

    def start(self):
        self.auto_eboot()
        if not all(value.get().strip() for value in (self.pc, self.vita, self.output)):
            messagebox.showerror(TITLE, self.tr("required_folders"))
            return
        pc = Path(self.pc.get().strip())
        vita = Path(self.vita.get().strip())
        if self.mode.get() == "vita":
            vita = vita_root(vita)
        elif not self.has_asset(str(vita)) or not (vita / "eboot.bin").is_file():
            messagebox.showerror(TITLE, self.tr("valid_vita3k"))
            return
        for folder in (pc, vita):
            if not self.has_asset(str(folder)):
                messagebox.showerror(TITLE, f"{self.tr('asset_missing')}\n{folder}")
                return
        if not self.eboot.get().strip():
            messagebox.showerror(TITLE, f"{self.tr('required_eboot')}\n\n{self.eboot_help.get()}")
            return
        if not is_decrypted_eboot(Path(self.eboot.get().strip())):
            messagebox.showerror(TITLE, self.tr("invalid_eboot"))
            return
        inputs = Inputs(pc, vita, Path(self.output.get().strip()), Path(self.eboot.get().strip()), self.use_kratos.get(),
                        Path(self.kratos.get().strip()) if self.use_kratos.get() and self.kratos.get().strip() else None)
        self.result = None
        self.progress.configure(value=0)
        self.set_status("checking")
        self.worker = Thread(target=self.run_assembly, args=(inputs, self.language.get()))
        self.refresh_controls()
        self.worker.start()
        self.root.after(100, self.poll)

    def run_assembly(self, inputs, language):
        try:
            result = assemble(inputs, lambda *update: self.messages.put(("progress", update)), language=language)
        except Exception as error:
            self.messages.put(("error", error.localized(language) if isinstance(error, BuildError) else str(error)))
        else:
            self.messages.put(("done", result))

    def poll(self):
        while True:
            try:
                event, data = self.messages.get_nowait()
            except Empty:
                self.root.after(100, self.poll)
                return
            if event == "progress":
                index, total, label = data
                self.progress.configure(value=100 * index / total)
                self.status.set(label)
                continue
            self.worker = None
            if event == "done":
                self.result = data
                self.set_status("done_copy")
            else:
                self.set_status("stopped")
                messagebox.showerror(TITLE, data)
            self.refresh_controls()
            return

    def open_result(self):
        os.startfile(self.result.parent.parent)

    def show_license(self):
        license_window = tk.Toplevel(self.root)
        license_window.title("xdelta3 · Apache License 2.0")
        text = tk.Text(license_window, width=78, height=32, padx=12, pady=12, wrap="word")
        text.pack(fill="both", expand=True)
        text.insert("1.0", XDELTA.with_name("LICENSE").read_text(encoding="utf-8-sig"))
        text.configure(state="disabled")

    def close(self):
        if self.worker:
            self.set_status("wait_before_exit")
        else:
            self.vita_shell_guide.hide()
            self.fagdec_guide.hide()
            self.root.destroy()


def cli():
    parser = argparse.ArgumentParser(description="Assemble MK9 Remaster 206 rePatch for PCSB00106.")
    parser.add_argument("--pc", type=Path, required=True)
    parser.add_argument("--vita", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    executable = parser.add_mutually_exclusive_group(required=True)
    executable.add_argument("--eboot", type=Path)
    executable.add_argument("--assets-only", action="store_true")
    parser.add_argument("--hd-kratos", action="store_true")
    parser.add_argument("--kratos-donor", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    def report(message):
        if args.report:
            with args.report.open("a", encoding="utf-8") as stream:
                stream.write(f"{message}\n")
        if sys.stdout:
            print(message, flush=True)

    if args.report:
        args.report.write_text("", encoding="utf-8")
    try:
        result = assemble(Inputs(args.pc, args.vita, args.output, args.eboot,
                                 args.hd_kratos or bool(args.kratos_donor), args.kratos_donor),
                          lambda index, total, label: report(f"[{index}/{total}] {label}"))
    except Exception as error:
        report(f"Error: {error}")
        return 1
    report(result)
    return 0


def main():
    if len(sys.argv) > 1:
        return cli()
    root = tk.Tk()
    InstallerWindow(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
