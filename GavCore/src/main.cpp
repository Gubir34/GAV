// gavcore: command-line front-end of the GavCore engine.
//
//   gavcore [--json] [--db-dir DIR] [--threads N] [--] <path>
//
// --json prints one JSON object per line: start, progress, threat, error, done, fatal.
// Exit codes: 0 clean, 1 threats found, 2 no signatures, 64 usage error, 130 cancelled.
#include <gavcore/engine.hpp>

#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

#include "platform.hpp"
#include "text.hpp"

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#include <windows.h>
#endif

using namespace gavcore;
namespace fs = std::filesystem;

namespace {

std::atomic<bool> g_cancel{false};

extern "C" void on_signal(int) { g_cancel.store(true); }

void write_line(const std::string& line) {
    std::fwrite(line.data(), 1, line.size(), stdout);
    std::fputc('\n', stdout);
    std::fflush(stdout);
}

std::string utf8(const fs::path& p) { return platform::to_utf8(p); }

struct JsonObject {
    std::string s = "{";
    JsonObject& key(const char* k) {
        if (s.size() > 1) s += ", ";
        text::append_json_string(s, k);
        s += ": ";
        return *this;
    }
    JsonObject& str(const char* k, const std::string& v) {
        key(k);
        text::append_json_string(s, v);
        return *this;
    }
    JsonObject& num(const char* k, std::size_t v) {
        key(k);
        s += std::to_string(v);
        return *this;
    }
    JsonObject& real(const char* k, double v) {
        char buf[32];
        std::snprintf(buf, sizeof buf, "%.3f", v);
        key(k);
        s += buf;
        return *this;
    }
    JsonObject& boolean(const char* k, bool v) {
        key(k);
        s += v ? "true" : "false";
        return *this;
    }
    void emit() { write_line(s + "}"); }
};

// Default signature folder: next to the executable, or the closest parent that has the databases.
fs::path default_db_dir() {
    const fs::path exe_dir = platform::executable_dir();
    for (fs::path dir = exe_dir; !dir.empty(); dir = dir.parent_path()) {
        std::error_code ec;
        for (const char* name : {"signatures_sha256.db", "signatures_sha1.db", "signatures_md5.db"})
            if (fs::is_regular_file(dir / name, ec)) return dir;
        if (dir == dir.parent_path()) break;
    }
    return exe_dir;
}

int usage() {
    std::fprintf(stderr,
                 "usage: gavcore [--json] [--db-dir DIR] [--threads N] [--] <path>\n"
                 "       gavcore --version\n");
    return 64;
}

int run(const std::vector<fs::path>& args) {
    bool json = false;
    unsigned threads = 0;
    fs::path db_dir, target;
    bool have_target = false;
    bool options_done = false;

    for (std::size_t i = 0; i < args.size(); ++i) {
        const std::string a = utf8(args[i]);
        if (options_done) {
            if (have_target) return usage();
            target = args[i];
            have_target = true;
        } else if (a == "--") {
            options_done = true;
        } else if (a == "--json") {
            json = true;
        } else if (a == "--version") {
            std::printf("gavcore %s\n", GAVCORE_VERSION);
            return 0;
        } else if (a == "--db-dir" && i + 1 < args.size()) {
            db_dir = args[++i];
        } else if (a == "--threads" && i + 1 < args.size()) {
            threads = static_cast<unsigned>(std::strtoul(utf8(args[++i]).c_str(), nullptr, 10));
        } else if (a == "--help" || a == "-h") {
            usage();
            return 0;
        } else if (!a.empty() && a[0] == '-' && a != "-") {
            return usage();
        } else if (!have_target) {
            target = args[i];
            have_target = true;
        } else {
            return usage();
        }
    }
    if (!have_target) return usage();

    std::error_code ec;
    if (!fs::exists(target, ec)) {
        if (json) {
            JsonObject().str("type", "fatal").str("message", "Invalid path: " + utf8(target)).emit();
        } else {
            std::fprintf(stderr, "Invalid path: %s\n", text::display_safe(utf8(target)).c_str());
        }
        return 64;
    }
    if (db_dir.empty()) db_dir = default_db_dir();

    SignatureSet signatures;
    try {
        signatures = SignatureSet::load(db_dir);
    } catch (const NoSignaturesError& e) {
        if (json) {
            JsonObject().str("type", "fatal").str("message", e.what()).emit();
        } else {
            std::fprintf(stderr, "[x] %s\n", e.what());
        }
        return 2;
    }

    std::signal(SIGINT, on_signal);
    std::signal(SIGTERM, on_signal);

    Callbacks cb;
    if (json) {
        const std::size_t sig_count = signatures.size();
        cb.on_start = [sig_count](std::size_t total) {
            JsonObject().str("type", "start").num("total", total).num("signatures", sig_count).emit();
        };
        cb.on_progress = [](std::size_t done, std::size_t total) {
            JsonObject().str("type", "progress").num("done", done).num("total", total).emit();
        };
        cb.on_threat = [](const Threat& t) {
            JsonObject().str("type", "threat").str("path", utf8(t.path)).str("algo", algo_name(t.algo)).str("hash", t.hash).emit();
        };
        cb.on_error = [](const ScanError& e) {
            JsonObject().str("type", "error").str("path", utf8(e.path)).str("reason", e.reason).emit();
        };
    } else {
        cb.on_threat = [](const Threat& t) {
            write_line("[!] Threat: " + text::display_safe(utf8(t.path)) + " -> " + algo_name(t.algo) + " " + t.hash);
        };
        cb.on_error = [](const ScanError& e) {
            write_line("[?] Not scanned: " + text::display_safe(utf8(e.path)) + " (" + text::display_safe(e.reason) + ")");
        };
    }

    Options options;
    options.threads = threads;
    options.cancel = &g_cancel;
    const Summary s = scan(target, signatures, cb, options);

    if (json) {
        JsonObject()
            .str("type", "done")
            .num("total", s.total)
            .num("scanned", s.scanned)
            .num("skipped", s.skipped)
            .num("threats", s.threats)
            .num("errors", s.errors)
            .boolean("cancelled", s.cancelled)
            .real("elapsed", s.elapsed)
            .emit();
    } else {
        char line[256];
        std::snprintf(line, sizeof line, "%sScanned %zu/%zu, skipped %zu, threats %zu, errors %zu in %.1fs",
                      s.cancelled ? "[cancelled] " : "", s.scanned, s.total, s.skipped, s.threats, s.errors,
                      s.elapsed);
        write_line(line);
    }
    if (s.cancelled) return 130;
    return s.threats ? 1 : 0;
}

}  // namespace

#ifdef _WIN32
int wmain(int argc, wchar_t** argv) {
    _setmode(_fileno(stdout), _O_BINARY);
    SetConsoleOutputCP(CP_UTF8);
    std::vector<fs::path> args;
    for (int i = 1; i < argc; ++i) args.emplace_back(argv[i]);
    try {
        return run(args);
    } catch (const std::exception& e) {
        std::fprintf(stderr, "gavcore: %s\n", e.what());
        return 70;
    }
}
#else
int main(int argc, char** argv) {
    std::vector<fs::path> args;
    for (int i = 1; i < argc; ++i) args.emplace_back(argv[i]);
    try {
        return run(args);
    } catch (const std::exception& e) {
        std::fprintf(stderr, "gavcore: %s\n", e.what());
        return 70;
    }
}
#endif
