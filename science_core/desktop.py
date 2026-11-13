"""Russian desktop launcher for Earth System Trend Detective.

The scientific pipeline stays in science_core.cli. This module adds a small
Tkinter interface; all coordinate validation and command construction are
kept separate so they can be tested without opening a window.
"""
from __future__ import annotations

import math
import queue
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POWER_START = "20210101"
POWER_END = "20251231"
NDVI_START = "2001-01-01"
NDVI_END = "2025-12-31"


def validate_coordinates(latitude: str | float, longitude: str | float) -> tuple[float, float]:
    """Parse and validate WGS84 latitude and longitude."""
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError) as exc:
        raise ValueError("Введите широту и долготу числами.") from exc
    if not math.isfinite(lat) or not -90 <= lat <= 90:
        raise ValueError("Широта должна быть от −90 до 90.")
    if not math.isfinite(lon) or not -180 <= lon <= 180:
        raise ValueError("Долгота должна быть от −180 до 180.")
    return lat, lon


def build_cli_command(
    latitude: str | float,
    longitude: str | float,
    output_dir: str | Path = "artifacts",
    *,
    python_executable: str | None = None,
) -> list[str]:
    """Build a safe argument list for the real scientific pipeline."""
    lat, lon = validate_coordinates(latitude, longitude)
    folder = str(output_dir).strip()
    if not folder:
        raise ValueError("Укажите папку для результатов.")
    output = Path(folder).expanduser()
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    return [
        python_executable or sys.executable,
        "-m", "science_core.cli",
        "--latitude", str(lat), "--longitude", str(lon),
        "--start", POWER_START, "--end", POWER_END,
        "--imagery-start", "2021-01-01", "--imagery-end", "2025-12-31",
        "--image-count", "60", "--minimum-images", "50",
        "--skip-gibs",
        "--ndvi-start", NDVI_START, "--ndvi-end", NDVI_END,
        "--ndvi-radius-km", "2", "--ndvi-minimum-years", "15",
        "--output", str(output.resolve()),
    ]


class DesktopApp:
    """Tkinter desktop interface for starting and monitoring one analysis."""

    def __init__(self, root: object) -> None:
        import tkinter as tk
        from tkinter import filedialog, ttk

        self.tk, self.ttk = tk, ttk
        self.filedialog, self.root = filedialog, root
        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self.process: subprocess.Popen[str] | None = None
        self.latitude = tk.StringVar(value="38.5598")
        self.longitude = tk.StringVar(value="68.7870")
        self.output = tk.StringVar(value=str(PROJECT_ROOT / "artifacts"))
        self.status = tk.StringVar(value="Готово к запуску")
        self._build()
        self.root.after(100, self._poll)

    def _build(self) -> None:
        tk, ttk = self.tk, self.ttk
        self.root.title("Earth System Trend Detective")
        self.root.geometry("820x650")
        self.root.minsize(700, 540)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Header.TLabel", font=("Segoe UI", 19, "bold"))
        style.configure("Run.TButton", font=("Segoe UI", 10, "bold"), padding=8)

        page = ttk.Frame(self.root, padding=18)
        page.pack(fill="both", expand=True)
        ttk.Label(page, text="Earth System Trend Detective", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            page,
            text="Исследование NDVI растительности и климатических рядов NASA",
        ).pack(anchor="w", pady=(4, 14))

        area = ttk.LabelFrame(page, text="Область исследования", padding=12)
        area.pack(fill="x")
        row = ttk.Frame(area)
        row.pack(anchor="w")
        ttk.Label(row, text="Широта").grid(row=0, column=0, sticky="w")
        ttk.Entry(row, textvariable=self.latitude, width=18).grid(row=1, column=0, padx=(0, 14))
        ttk.Label(row, text="Долгота").grid(row=0, column=1, sticky="w")
        ttk.Entry(row, textvariable=self.longitude, width=18).grid(row=1, column=1, padx=(0, 14))
        ttk.Button(row, text="Душанбе по умолчанию", command=self._dushanbe).grid(row=1, column=2)
        ttk.Label(area, text="Локальное окно около 4 × 4 км. Период NDVI: 2001–2025.").pack(anchor="w", pady=(9, 0))
        ttk.Label(area, text="NASA POWER: дневные данные за 2021–2025 годы.").pack(anchor="w")

        output_box = ttk.LabelFrame(page, text="Папка результатов", padding=12)
        output_box.pack(fill="x", pady=(12, 0))
        output_row = ttk.Frame(output_box)
        output_row.pack(fill="x")
        ttk.Entry(output_row, textvariable=self.output).pack(side="left", fill="x", expand=True)
        ttk.Button(output_row, text="Обзор…", command=self._browse).pack(side="left", padx=(8, 0))

        ttk.Label(
            page,
            text=(
                "Интернет нужен для первого скачивания библиотек и получения данных NASA. "
                "После создания HTML-отчёт открывается без интернета. "
                "Обзорные цветные снимки GIBS отключены: расчёт NDVI использует количественный продукт MODIS."
            ),
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(12, 10))

        buttons = ttk.Frame(page)
        buttons.pack(fill="x")
        self.run_button = ttk.Button(buttons, text="Запустить анализ", style="Run.TButton", command=self._start)
        self.run_button.pack(side="left")
        self.open_button = ttk.Button(buttons, text="Открыть HTML-отчёт", command=self._open_report, state="disabled")
        self.open_button.pack(side="left", padx=(8, 0))
        self.stop_button = ttk.Button(buttons, text="Остановить", command=self._stop, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))
        ttk.Label(buttons, textvariable=self.status).pack(side="right")

        log_box = ttk.LabelFrame(page, text="Ход работы", padding=8)
        log_box.pack(fill="both", expand=True, pady=(12, 0))
        self.log = tk.Text(log_box, height=12, wrap="word", state="disabled", font=("Consolas", 9))
        scroll = ttk.Scrollbar(log_box, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        ttk.Label(
            page,
            text="Ограничение: локальные результаты не описывают весь Таджикистан. Корреляция не доказывает причинность.",
            wraplength=760,
        ).pack(anchor="w", pady=(10, 0))

    def _write_log(self, line: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", line.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _dushanbe(self) -> None:
        self.latitude.set("38.5598")
        self.longitude.set("68.7870")

    def _browse(self) -> None:
        chosen = self.filedialog.askdirectory(initialdir=self.output.get() or str(PROJECT_ROOT))
        if chosen:
            self.output.set(chosen)

    def _start(self) -> None:
        if self.process and self.process.poll() is None:
            return
        try:
            command = build_cli_command(self.latitude.get(), self.longitude.get(), self.output.get())
        except ValueError as exc:
            from tkinter import messagebox
            messagebox.showerror("Проверьте ввод", str(exc), parent=self.root)
            return
        self._write_log("=" * 56)
        self._write_log("Запущен сбор и анализ реальных данных. Не закрывайте окно.")
        self.status.set("Выполняется…")
        self.run_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        try:
            self.process = subprocess.Popen(
                command,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError as exc:
            self._write_log(f"Не удалось запустить Python: {exc}")
            self._finish(-1)
            return

        process = self.process

        def collect_output() -> None:
            assert process.stdout is not None
            for line in process.stdout:
                self.messages.put(("log", line.rstrip()))
            self.messages.put(("done", process.wait()))

        threading.Thread(target=collect_output, daemon=True).start()

    def _poll(self) -> None:
        try:
            while True:
                kind, value = self.messages.get_nowait()
                if kind == "log":
                    self._write_log(str(value))
                elif kind == "done":
                    self._finish(int(value))
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _report_path(self) -> Path:
        folder = Path(self.output.get()).expanduser()
        if not folder.is_absolute():
            folder = PROJECT_ROOT / folder
        return folder / "report.html"

    def _open_report(self) -> None:
        path = self._report_path()
        if path.is_file():
            webbrowser.open(path.resolve().as_uri())
        else:
            from tkinter import messagebox
            messagebox.showinfo("Отчёт не найден", "Сначала запустите анализ.", parent=self.root)

    def _finish(self, code: int) -> None:
        self.stop_button.configure(state="disabled")
        self.run_button.configure(state="normal")
        self.process = None
        if code == 0:
            self.status.set("Анализ завершён")
            self._write_log("Готово. Отчёт сохранён.")
            if self._report_path().is_file():
                self.open_button.configure(state="normal")
                self._open_report()
        else:
            self.status.set(f"Ошибка (код {code})")
            self._write_log("Анализ не завершён. Проверьте журнал и подключение к интернету.")

    def _stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.status.set("Остановка…")
            self._write_log("Отправлена команда остановки.")

    def _close(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
        self.root.destroy()


def main() -> int:
    if sys.version_info < (3, 12):
        print("Требуется Python 3.12 или новее.", file=sys.stderr)
        return 2
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError:
        print("Tkinter недоступен в этой сборке Python.", file=sys.stderr)
        return 2
    root = tk.Tk()
    try:
        DesktopApp(root)
    except Exception as exc:
        messagebox.showerror("Ошибка запуска", str(exc), parent=root)
        root.destroy()
        return 1
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
