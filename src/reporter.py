import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LoginResult:
    site: str
    status: str
    timestamp: str
    data: dict = field(default_factory=dict)
    error: str | None = None


class Reporter:
    """Generates human-readable reports from login+scrape results."""

    @staticmethod
    def format(result: LoginResult) -> str:
        lines = [
            f"=== {result.site} Login Report ===",
            f"Status: {result.status.upper()}",
            f"Time:  {result.timestamp}",
        ]

        if result.data:
            lines.append("Scraped data:")
            for key, value in result.data.items():
                if value is None:
                    lines.append(f"  {key}: (not found)")
                elif isinstance(value, list):
                    lines.append(f"  {key}:")
                    for item in value:
                        lines.append(f"    - {item}")
                else:
                    lines.append(f"  {key}: {value}")

        if result.error:
            lines.append(f"Error:  {result.error}")

        return "\n".join(lines)

    @staticmethod
    def write(result: LoginResult, dest: Path | None = None):
        """Write the report to a file (or stderr if no dest)."""
        text = Reporter.format(result)
        if dest:
            with open(dest, "a") as f:
                f.write(text + "\n\n")
        else:
            print(text, file=sys.stderr)
