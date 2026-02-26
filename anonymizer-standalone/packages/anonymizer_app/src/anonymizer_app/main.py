"""Local desktop UI with two tabs for anonymization and deanonymization."""

from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


def _run_cli(args: list[str], stdin_text: str | None = None) -> tuple[int, str, str]:
    cmd = [sys.executable, "-m", "anonymizer_core.cli", *args]
    proc = subprocess.run(
        cmd,
        input=stdin_text,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _set_entry(entry: ttk.Entry, value: str) -> None:
    entry.delete(0, tk.END)
    entry.insert(0, value)


def launch() -> None:
    root = tk.Tk()
    root.title("Anonymizer Standalone")
    root.geometry("920x620")

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    tab_anonymize = ttk.Frame(notebook)
    tab_deanonymize = ttk.Frame(notebook)
    notebook.add(tab_anonymize, text="Anonymiser")
    notebook.add(tab_deanonymize, text="Desanonymiser")

    # Anonymiser tab
    ttk.Label(tab_anonymize, text="Input directory").grid(row=0, column=0, sticky="w", padx=8, pady=6)
    input_dir = ttk.Entry(tab_anonymize, width=90)
    input_dir.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

    def pick_input_dir() -> None:
        selected = filedialog.askdirectory(title="Select input directory")
        if selected:
            _set_entry(input_dir, selected)

    ttk.Button(tab_anonymize, text="Browse", command=pick_input_dir).grid(row=0, column=2, padx=8, pady=6)

    ttk.Label(tab_anonymize, text="Output directory").grid(row=1, column=0, sticky="w", padx=8, pady=6)
    output_dir = ttk.Entry(tab_anonymize, width=90)
    output_dir.grid(row=1, column=1, sticky="ew", padx=8, pady=6)

    def pick_output_dir() -> None:
        selected = filedialog.askdirectory(title="Select output directory")
        if selected:
            _set_entry(output_dir, selected)

    ttk.Button(tab_anonymize, text="Browse", command=pick_output_dir).grid(row=1, column=2, padx=8, pady=6)

    ttk.Label(tab_anonymize, text="Case ID").grid(row=2, column=0, sticky="w", padx=8, pady=6)
    case_id = ttk.Entry(tab_anonymize, width=40)
    case_id.grid(row=2, column=1, sticky="w", padx=8, pady=6)
    case_id.insert(0, "CASE-001")

    concat_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(tab_anonymize, text="Concat outputs in one file", variable=concat_var).grid(
        row=3,
        column=1,
        sticky="w",
        padx=8,
        pady=6,
    )

    anon_log = tk.Text(tab_anonymize, height=18, wrap="word")
    anon_log.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=8, pady=6)

    def run_anonymize() -> None:
        in_dir = input_dir.get().strip()
        out_dir = output_dir.get().strip()
        cid = case_id.get().strip()
        if not in_dir or not out_dir or not cid:
            messagebox.showerror("Missing input", "input directory, output directory and case ID are required")
            return
        args = [
            "anonymize",
            "--input",
            in_dir,
            "--output",
            out_dir,
            "--case-id",
            cid,
            "--report",
            str(Path(out_dir) / "report.json"),
        ]
        if concat_var.get():
            args.append("--concat")

        code, out, err = _run_cli(args)
        anon_log.delete("1.0", tk.END)
        anon_log.insert(tk.END, f"exit_code={code}\n")
        if out:
            anon_log.insert(tk.END, f"\nSTDOUT:\n{out}\n")
        if err:
            anon_log.insert(tk.END, f"\nSTDERR:\n{err}\n")

    ttk.Button(tab_anonymize, text="Run", command=run_anonymize).grid(row=4, column=1, sticky="w", padx=8, pady=6)

    tab_anonymize.columnconfigure(1, weight=1)
    tab_anonymize.rowconfigure(5, weight=1)

    # Deanonymiser tab
    ttk.Label(tab_deanonymize, text="Mapping file").grid(row=0, column=0, sticky="w", padx=8, pady=6)
    mapping_file = ttk.Entry(tab_deanonymize, width=90)
    mapping_file.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

    def pick_mapping_file() -> None:
        selected = filedialog.askopenfilename(
            title="Select mapping.json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if selected:
            _set_entry(mapping_file, selected)

    ttk.Button(tab_deanonymize, text="Browse", command=pick_mapping_file).grid(row=0, column=2, padx=8, pady=6)

    ttk.Label(tab_deanonymize, text="Input text").grid(row=1, column=0, sticky="nw", padx=8, pady=6)
    input_text = tk.Text(tab_deanonymize, height=12, wrap="word")
    input_text.grid(row=1, column=1, columnspan=2, sticky="nsew", padx=8, pady=6)

    ttk.Label(tab_deanonymize, text="Output text").grid(row=2, column=0, sticky="nw", padx=8, pady=6)
    output_text = tk.Text(tab_deanonymize, height=12, wrap="word")
    output_text.grid(row=2, column=1, columnspan=2, sticky="nsew", padx=8, pady=6)

    def run_deanonymize() -> None:
        mapping = mapping_file.get().strip()
        text = input_text.get("1.0", tk.END)
        if not mapping:
            messagebox.showerror("Missing input", "mapping file is required")
            return
        tmp_out = Path.cwd() / ".tmp_deanonymized_output.txt"
        args = [
            "deanonymize",
            "--mapping",
            mapping,
            "--text-stdin",
            "--output",
            str(tmp_out),
        ]
        code, out, err = _run_cli(args, stdin_text=text)
        output_text.delete("1.0", tk.END)
        if code == 0 and tmp_out.exists():
            output_text.insert(tk.END, tmp_out.read_text(encoding="utf-8"))
            try:
                tmp_out.unlink()
            except OSError:
                pass
        else:
            output_text.insert(tk.END, f"exit_code={code}\n{out}\n{err}")

    ttk.Button(tab_deanonymize, text="Run", command=run_deanonymize).grid(row=3, column=1, sticky="w", padx=8, pady=6)

    tab_deanonymize.columnconfigure(1, weight=1)
    tab_deanonymize.rowconfigure(1, weight=1)
    tab_deanonymize.rowconfigure(2, weight=1)

    root.mainloop()


if __name__ == "__main__":
    launch()
