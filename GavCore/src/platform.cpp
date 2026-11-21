#include "platform.hpp"

#ifdef _WIN32
#include <windows.h>
#else
#include <cerrno>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#ifdef __APPLE__
#include <mach-o/dyld.h>
#endif
#endif

namespace gavcore::platform {

#ifdef _WIN32

namespace {

std::string wide_to_utf8(const wchar_t* s, int len) {
    if (len == 0) return {};
    const int size = WideCharToMultiByte(CP_UTF8, 0, s, len, nullptr, 0, nullptr, nullptr);
    std::string out(static_cast<std::size_t>(size), '\0');
    WideCharToMultiByte(CP_UTF8, 0, s, len, out.data(), size, nullptr, nullptr);
    return out;
}

std::string win32_message(DWORD code) {
    wchar_t* buffer = nullptr;
    const DWORD len = FormatMessageW(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM |
                                         FORMAT_MESSAGE_IGNORE_INSERTS,
                                     nullptr, code, 0, reinterpret_cast<wchar_t*>(&buffer), 0, nullptr);
    std::string text = len ? wide_to_utf8(buffer, static_cast<int>(len)) : "error " + std::to_string(code);
    if (buffer) LocalFree(buffer);
    while (!text.empty() && (text.back() == '\n' || text.back() == '\r' || text.back() == ' ' || text.back() == '.'))
        text.pop_back();
    return text;
}

// Prefix long absolute paths with \\?\ so CreateFileW is not limited to MAX_PATH.
std::wstring extended_path(const fs::path& path) {
    std::wstring p = path.native();
    if (p.size() < MAX_PATH - 12 || p.rfind(L"\\\\?\\", 0) == 0 || !path.is_absolute()) return p;
    for (auto& c : p)
        if (c == L'/') c = L'\\';
    if (p.rfind(L"\\\\", 0) == 0) return L"\\\\?\\UNC\\" + p.substr(2);
    return L"\\\\?\\" + p;
}

}  // namespace

RegularFile::~RegularFile() { close(); }

void RegularFile::close() {
    if (handle_) {
        CloseHandle(static_cast<HANDLE>(handle_));
        handle_ = nullptr;
    }
}

bool RegularFile::open(const fs::path& path, std::string& error) {
    close();
    HANDLE h = CreateFileW(extended_path(path).c_str(), GENERIC_READ,
                           FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING,
                           FILE_FLAG_SEQUENTIAL_SCAN | FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
    if (h == INVALID_HANDLE_VALUE) {
        error = win32_message(GetLastError());
        return false;
    }
    BY_HANDLE_FILE_INFORMATION info{};
    if (GetFileType(h) != FILE_TYPE_DISK || !GetFileInformationByHandle(h, &info) ||
        (info.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT))) {
        CloseHandle(h);
        error = "not a regular file";
        return false;
    }
    handle_ = h;
    return true;
}

long long RegularFile::read(unsigned char* buffer, std::size_t size, std::string& error) {
    DWORD got = 0;
    const DWORD want = size > 0x40000000 ? 0x40000000 : static_cast<DWORD>(size);
    if (!ReadFile(static_cast<HANDLE>(handle_), buffer, want, &got, nullptr)) {
        error = win32_message(GetLastError());
        return -1;
    }
    return static_cast<long long>(got);
}

std::string to_utf8(const fs::path& path) {
    const auto& w = path.native();
    return wide_to_utf8(w.data(), static_cast<int>(w.size()));
}

std::string error_text(const std::error_code& ec) {
    if (ec.category() == std::system_category()) return win32_message(static_cast<DWORD>(ec.value()));
    return ec.message();
}

fs::path executable_dir() {
    std::wstring buffer(MAX_PATH, L'\0');
    for (;;) {
        const DWORD len = GetModuleFileNameW(nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));
        if (len == 0) return fs::current_path();
        if (len < buffer.size()) {
            buffer.resize(len);
            return fs::path(buffer).parent_path();
        }
        buffer.resize(buffer.size() * 2);
    }
}

#else  // POSIX

RegularFile::~RegularFile() { close(); }

void RegularFile::close() {
    if (fd_ >= 0) {
        ::close(fd_);
        fd_ = -1;
    }
}

bool RegularFile::open(const fs::path& path, std::string& error) {
    close();
    const int fd = ::open(path.c_str(), O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) {
        error = std::generic_category().message(errno);
        return false;
    }
    struct stat st {};
    if (fstat(fd, &st) != 0 || !S_ISREG(st.st_mode)) {
        ::close(fd);
        error = "not a regular file";
        return false;
    }
    const int flags = fcntl(fd, F_GETFL);
    if (flags >= 0) fcntl(fd, F_SETFL, flags & ~O_NONBLOCK);
#ifdef POSIX_FADV_SEQUENTIAL
    posix_fadvise(fd, 0, 0, POSIX_FADV_SEQUENTIAL);
#endif
    fd_ = fd;
    return true;
}

long long RegularFile::read(unsigned char* buffer, std::size_t size, std::string& error) {
    for (;;) {
        const ssize_t got = ::read(fd_, buffer, size);
        if (got >= 0) return static_cast<long long>(got);
        if (errno == EINTR) continue;
        error = std::generic_category().message(errno);
        return -1;
    }
}

std::string to_utf8(const fs::path& path) { return path.native(); }

std::string error_text(const std::error_code& ec) { return ec.message(); }

fs::path executable_dir() {
#ifdef __APPLE__
    char buffer[4096];
    uint32_t size = sizeof buffer;
    if (_NSGetExecutablePath(buffer, &size) == 0) {
        std::error_code ec;
        auto exe = fs::canonical(buffer, ec);
        return (ec ? fs::path(buffer) : exe).parent_path();
    }
#else
    std::error_code ec;
    auto exe = fs::read_symlink("/proc/self/exe", ec);
    if (!ec) return exe.parent_path();
#endif
    return fs::current_path();
}

#endif

}  // namespace gavcore::platform
