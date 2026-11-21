// GavCore: hash-based scan engine for GAV.
#pragma once

#include <array>
#include <atomic>
#include <cstdint>
#include <filesystem>
#include <functional>
#include <stdexcept>
#include <string>
#include <vector>

namespace gavcore {

namespace fs = std::filesystem;

enum class Algo { SHA256, SHA1, MD5 };
const char* algo_name(Algo algo);

struct Threat {
    fs::path path;
    Algo algo;
    std::string hash;  // lowercase hex
};

struct ScanError {
    fs::path path;
    std::string reason;
};

struct Summary {
    std::size_t total = 0;
    std::size_t scanned = 0;
    std::size_t skipped = 0;  // symlinks, FIFOs, sockets, devices
    std::size_t threats = 0;
    std::size_t errors = 0;
    bool cancelled = false;
    double elapsed = 0.0;
};

class NoSignaturesError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

// In-memory signature set: sorted binary digests, ~32 bytes per SHA256 entry.
class SignatureSet {
public:
    // Loads signatures_{sha256,sha1,md5}.db from db_dir. Throws NoSignaturesError if all are empty.
    static SignatureSet load(const fs::path& db_dir);

    // Adds a hex digest; the algorithm is inferred from its length. Returns false if malformed.
    bool add_hex(const std::string& hex);
    void finalize();  // sort + dedupe; call after the last add_hex
    bool contains(Algo algo, const unsigned char* digest) const;
    std::size_t size(Algo algo) const;
    std::size_t size() const;

private:
    std::vector<std::array<unsigned char, 32>> sha256_;
    std::vector<std::array<unsigned char, 20>> sha1_;
    std::vector<std::array<unsigned char, 16>> md5_;
};

struct Callbacks {
    // All callbacks are serialized (never called concurrently).
    std::function<void(std::size_t total)> on_start;
    std::function<void(std::size_t done, std::size_t total)> on_progress;
    std::function<void(const Threat&)> on_threat;
    std::function<void(const ScanError&)> on_error;
};

struct Options {
    unsigned threads = 0;                  // 0 = auto
    double progress_interval = 0.1;        // seconds between on_progress calls
    const std::atomic<bool>* cancel = nullptr;
};

Summary scan(const fs::path& root, const SignatureSet& signatures, const Callbacks& callbacks,
             const Options& options = {});

}  // namespace gavcore
