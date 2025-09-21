import os

LANG_DIR = "lang"
CURRENT_LANG = "en"

def set_lang(lng):
    global CURRENT_LANG
    CURRENT_LANG = lng

def get_text(key):
    file_path = os.path.join(LANG_DIR, f"{CURRENT_LANG}.ltf")
    if not os.path.exists(file_path):
        return key
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    section_start = content.find(f"[lng={CURRENT_LANG}]")
    if section_start == -1:
        return key
    section_end = content.find("[", section_start + 1)
    section = content[section_start:section_end] if section_end != -1 else content[section_start:]
    for line in section.splitlines():
        line = line.strip()
        if line.startswith(f"{key}"):
            return line.split("=", 1)[1].strip()
    return key
