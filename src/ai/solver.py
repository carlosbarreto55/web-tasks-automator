import re
import sys
from pathlib import Path

from src.ai.ai_client import AIClient

SOLVE_SYSTEM_PROMPT = (
    "You are a Java programming tutor. Output ONLY the solution code for the "
    "described problem. No markdown fences (no ```java or ```), no explanations, "
    "no comments beyond what the problem asks for. The code must compile and "
    "run. Return ONLY the Java source code."
)

FILE_MARKER_RE = re.compile(r'Enviar\s+"([^"]+\.java)"', re.IGNORECASE)


class LabSolver:
    def __init__(self, client: AIClient, model: str, output_dir: Path):
        self.client = client
        self.model = model
        self.output_dir = output_dir

    def _clean_response(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if len(lines) > 1:
                lines = lines[1:]
            else:
                lines = []
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text + "\n"

    def solve(self, lab_file: Path, verbose: bool = False) -> dict:
        if not lab_file.exists():
            raise FileNotFoundError(f"Lab file not found: {lab_file}")

        content = lab_file.read_text(encoding="utf-8").strip()
        if not content:
            if verbose:
                print("  [solve] empty lab file, nothing to solve", file=sys.stderr)
            return {"solved": [], "failed": []}

        self.output_dir.mkdir(parents=True, exist_ok=True)

        markers = list(FILE_MARKER_RE.finditer(content))
        if not markers:
            return self._solve_single(content, "solution.txt", verbose)

        solved = []
        failed = []
        prev_end = 0

        for i, match in enumerate(markers):
            filename = match.group(1)
            end = match.end()

            question_text = content[prev_end:end].strip()
            prev_end = end

            if not question_text or question_text.startswith("Enviar"):
                continue

            if verbose:
                print(f"  [solve] solving {filename} ({len(question_text)} chars)",
                      file=sys.stderr)

            try:
                answer = self.client.chat(
                    system_prompt=SOLVE_SYSTEM_PROMPT,
                    user_prompt=question_text,
                )
                answer = self._clean_response(answer)
                out_path = self.output_dir / filename
                out_path.write_text(answer, encoding="utf-8")
                solved.append(filename)
                if verbose:
                    print(f"  [solve] saved {len(answer)} chars to {out_path}",
                          file=sys.stderr)
            except Exception as exc:
                failed.append(filename)
                if verbose:
                    print(f"  [solve] FAILED {filename}: {exc}", file=sys.stderr)

        return {"solved": solved, "failed": failed}

    def _solve_single(self, content: str, filename: str,
                      verbose: bool) -> dict:
        if verbose:
            print(f"  [solve] no file markers found, solving as single file",
                  file=sys.stderr)
        try:
            answer = self.client.chat(
                system_prompt=SOLVE_SYSTEM_PROMPT,
                user_prompt=content,
            )
            answer = self._clean_response(answer)
            out_path = self.output_dir / filename
            out_path.write_text(answer, encoding="utf-8")
            if verbose:
                print(f"  [solve] saved {len(answer)} chars to {out_path}",
                      file=sys.stderr)
            return {"solved": [filename], "failed": []}
        except Exception as exc:
            if verbose:
                print(f"  [solve] FAILED: {exc}", file=sys.stderr)
            return {"solved": [], "failed": [filename]}
