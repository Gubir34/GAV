#pragma once
#include <cstddef>
#include <filesystem>
#include <string>
#include <system_error>

namespace gavcore::platform {

namespace fs = std::filesystem;

// Read-only handle to a regular file. Never follows a final symlink, never blocks on FIFOs.
class RegularFile {
public:
    RegularFile() = default;
    RegularFile(const RegularFile&) = delete;
    RegularFile& operator=(const RegularFile&) = delete;
    ~RegularFile();

    // Returns false and sets error on failure (including "not a regular file").
    bool open(const fs::path& path, std::string& error);
    // Returns bytes read (0 at EOF) or -1 on error.
    long long read(unsigned char* buffer, std::size_t size, std::string& error);

private:
#ifdef _WIN32
    void* handle_ = nullptr;
#else
    int fd_ = -1;
#endif
    void close();
};

std::string to_utf8(const fs::path& path);
std::string error_text(const std::error_code& ec);
fs::path executable_dir();

}  // namespace gavcore::platform
