"""File agent that reads text files and returns their content."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime

from fpdf import FPDF

from src.agents.base_agent import BaseAgent


class FileAgent(BaseAgent):
    """Agent that reads a text file and returns its contents."""

    def __init__(self, name: str = "FileAgent") -> None:
        super().__init__(name=name)

    def run(self, task: Any) -> str:
        """Extract a file path from the task and return the file's content."""
        text = str(task)
        path = self._extract_path(text)

        if path is None:
            return "Nisam prepoznala putanju do fajla u tvom zahtevu."

        file_path = Path(path)
        if not file_path.exists():
            return f"Fajl ne postoji: {path}"

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            return f"Greska pri citanju fajla: {exc}"

        return content

    def _extract_path(self, text: str) -> str | None:
        """Very simple path extraction: look for a word containing a dot and slash-like pattern."""
        for word in text.split():
            if "." in word and ("/" in word or "\\" in word or word.count(".") == 1):
                return word.strip('",.')
        return None

    def napravi_pdf_izvestaj(self, naslov: str, sadrzaj: str, folder: str = "izvestaji_sajtova") -> str:
        """Napravi PDF izvestaj od teksta i sacuvaj ga u poseban folder."""
        folder_path = Path(folder)
        folder_path.mkdir(parents=True, exist_ok=True)

        pdf = FPDF()
        pdf.add_page()
        pdf.add_font("Arial", "", "C:/Windows/Fonts/arial.ttf", uni=True)
        pdf.set_font("Arial", size=14)
        pdf.multi_cell(0, 10, naslov)
        pdf.ln(5)

        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 8, sadrzaj)

        datum = datetime.now().strftime("%Y-%m-%d_%H-%M")
        naziv_fajla = folder_path / f"izvestaj_{datum}.pdf"
        pdf.output(str(naziv_fajla))

        return str(naziv_fajla)