import sys
import tempfile
import time
import zipfile
from pathlib import Path

from src.notifications.telegram import TelegramNotifier


def _escape_html(text: str) -> str:
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def _format_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    else:
        return f"{num_bytes / (1024 * 1024):.1f} MB"


class NotificationManager:
    def __init__(self, telegram: TelegramNotifier):
        self.telegram = telegram

    def _zip_files(self, files: list[Path], zip_name: str) -> Path | None:
        existing = [f for f in files if f.exists()]
        if not existing:
            return None

        tmp = Path(tempfile.mkdtemp())
        zip_path = tmp / zip_name
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in existing:
                zf.write(f, f.name)
        return zip_path

    def notify_lab_saved(self, site_name: str, output_file: Path,
                         content_length: int, verbose: bool = False) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        escaped_name = _escape_html(site_name)
        escaped_file = _escape_html(str(output_file))
        size_str = _format_size(content_length)

        message = (
            f"\U0001f4da <b>Nova tarefa da disciplina Projeto de Programas!</b>\n\n"
            f"Mas n\u00e3o se preocupe, aqui est\u00e1 o enunciado \U0001f60a\n\n"
            f"\U0001f4c4 Arquivo: <code>{escaped_file}</code>\n"
            f"\U0001f4cf Tamanho: {size_str}\n"
            f"\U0001f550 Hora: {ts}"
        )

        if verbose:
            print(f"  [notify] sending notification for lab: {site_name}",
                  file=sys.stderr)

        self.telegram.send_message(message, verbose=verbose)

        zip_path = self._zip_files([output_file], "lab-pp-enunciado.zip")
        if zip_path:
            try:
                self.telegram.send_document(zip_path, verbose=verbose)
            finally:
                import shutil
                shutil.rmtree(zip_path.parent, ignore_errors=True)

    def notify_solutions_saved(self, site_name: str, output_dir: Path,
                               solved: list[str], failed: list[str],
                               verbose: bool = False) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        escaped_name = _escape_html(site_name)

        solved_count = len(solved)
        failed_count = len(failed)

        lines = [
            f"\u2705 <b>Respostas geradas com sucesso!</b>",
            f"\n\U0001f4da Disciplina: <i>Projeto de Programas</i>",
        ]

        if solved_count:
            lines.append(f"\n\U0001f4dd {solved_count} arquivo(s) resolvido(s):")
            for fname in solved:
                lines.append(f"  \u2705 <code>{_escape_html(fname)}</code>")

        if failed_count:
            lines.append(f"\n\u274c {failed_count} arquivo(s) com erro:")
            for fname in failed:
                lines.append(f"  \u274c <code>{_escape_html(fname)}</code>")

        lines.append(f"\n\U0001f550 Hora: {ts}")
        message = "\n".join(lines)

        if verbose:
            print(f"  [notify] sending notification for solutions: {site_name}",
                  file=sys.stderr)

        self.telegram.send_message(message, verbose=verbose)

        if solved_count:
            solved_files = [output_dir / f for f in solved if (output_dir / f).exists()]
            zip_path = self._zip_files(solved_files, "lab-pp-solutions.zip")
            if zip_path:
                try:
                    self.telegram.send_document(zip_path, verbose=verbose)
                finally:
                    import shutil
                    shutil.rmtree(zip_path.parent, ignore_errors=True)
