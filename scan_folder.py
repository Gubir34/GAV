import os
import sys

from tqdm import tqdm

import gav_core
from lang_loader import LangLoader

lang = LangLoader("lng.ltf", default="en")


def scan_folder(folder):
    """Scan a folder with a tqdm progress bar."""
    pbar = None

    def on_start(total):
        nonlocal pbar
        if total:
            pbar = tqdm(total=total, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')

    def on_progress(done, total):
        pbar.n = done
        pbar.refresh()
        pbar.set_description(lang.t("scan_progress", progress=int(done / total * 100)))

    def on_threat(threat):
        tqdm.write(lang.t("threat_detected", file=gav_core.safe_display(threat.path), hash=threat.hash))

    def on_error(err):
        tqdm.write(lang.t("permission_error", path=f"{gav_core.safe_display(err.path)} ({err.reason})"))

    try:
        summary = gav_core.scan(folder, on_start=on_start, on_progress=on_progress,
                                on_threat=on_threat, on_error=on_error)
    except gav_core.NoSignaturesError:
        print(lang.t("gui_no_signatures"))
        return None
    except gav_core.EngineNotFoundError as e:
        print(f"[x] {e}")
        return None
    finally:
        if pbar:
            pbar.close()

    if not summary.total:
        print(lang.t("no_files"))
    print(lang.t("gui_summary", scanned=summary.scanned, total=summary.total, threats=len(summary.threats),
                 errors=len(summary.errors), elapsed=f"{summary.elapsed:.1f}"))
    print(lang.t("scan_done"))
    return summary


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else input(lang.t("scan_prompt") + ": ")
    if not os.path.exists(folder):
        print(lang.t("invalid_path", path=gav_core.safe_display(folder)))
    else:
        scan_folder(folder)
