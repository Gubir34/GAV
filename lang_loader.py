# lang_loader.py
import re

class LangLoader:
    def __init__(self, filepath, default="en"):
        self.filepath = filepath
        self.default = default
        self.data = {}
        self.load_file()

    def load_file(self):
        current_lang = None
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("[lng="):
                    current_lang = line[5:-1]
                    self.data[current_lang] = {}
                elif "=" in line and current_lang:
                    key, val = line.split("=", 1)
                    self.data[current_lang][key.strip()] = val.strip()

    def t(self, key, **kwargs):
        lang_data = self.data.get(self.default, {})
        text = lang_data.get(key, f"[!]{key}")
        if kwargs:
            return text.format(**kwargs)
        return text
