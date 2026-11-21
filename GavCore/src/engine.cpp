#include <gavcore/engine.hpp>

#include <algorithm>
#include <chrono>
#include <mutex>
#include <thread>

#include "hasher.hpp"
#include "platform.hpp"
#include "text.hpp"

namespace gavcore {
namespace {

constexpr std::size_t kChunkSize = 1 << 20;

bool cancelled(const Options& options) {
    return options.cancel && options.cancel->load(std::memory_order_relaxed);
}

// Iterative walk that never follows symlinks/junctions and reports every unreadable directory.
template <typename OnError>
void collect_files(const fs::path& root, std::vector<fs::path>& files, std::size_t& skipped, const Options& options,
                   OnError&& on_error) {
    std::error_code ec;
    const auto root_status = fs::status(root, ec);
    if (ec) {
        on_error(ScanError{root, platform::error_text(ec)});
        return;
    }
    if (fs::is_regular_file(root_status)) {
        files.push_back(root);
        return;
    }

    std::vector<fs::path> pending{root};
    while (!pending.empty() && !cancelled(options)) {
        const fs::path dir = std::move(pending.back());
        pending.pop_back();

        fs::directory_iterator it(dir, fs::directory_options::none, ec);
        if (ec) {
            on_error(ScanError{dir, platform::error_text(ec)});
            ec.clear();
            continue;
        }
        const fs::directory_iterator end;
        while (it != end) {
            const auto& entry = *it;
            const auto status = entry.symlink_status(ec);
            if (ec) {
                on_error(ScanError{entry.path(), platform::error_text(ec)});
                ec.clear();
            } else if (fs::is_directory(status)) {
                pending.push_back(entry.path());
            } else if (fs::is_regular_file(status)) {
                files.push_back(entry.path());
            } else {
                ++skipped;  // symlink, junction, FIFO, socket, device
            }
            it.increment(ec);
            if (ec) {
                on_error(ScanError{dir, platform::error_text(ec)});
                ec.clear();
                break;
            }
        }
    }
}

}  // namespace

Summary scan(const fs::path& root, const SignatureSet& signatures, const Callbacks& callbacks,
             const Options& options) {
    using clock = std::chrono::steady_clock;
    const auto started = clock::now();

    Summary summary;
    std::mutex mutex;  // guards summary counters and serializes callbacks

    auto report_error = [&](const ScanError& error) {
        std::lock_guard<std::mutex> lock(mutex);
        ++summary.errors;
        if (callbacks.on_error) callbacks.on_error(error);
    };

    std::vector<fs::path> files;
    collect_files(root, files, summary.skipped, options, report_error);
    summary.total = files.size();
    if (callbacks.on_start) callbacks.on_start(summary.total);

    unsigned threads = options.threads;
    if (threads == 0) threads = std::clamp(std::thread::hardware_concurrency(), 1u, 8u);
    threads = static_cast<unsigned>(std::max<std::size_t>(1, std::min<std::size_t>(threads, files.size())));

    std::atomic<std::size_t> next{0};
    std::size_t done = 0;
    std::size_t last_reported = 0;
    auto last_progress = started;
    const auto interval = std::chrono::duration<double>(options.progress_interval);

    auto worker = [&] {
        MultiHasher hasher;
        std::vector<unsigned char> buffer(kChunkSize);
        unsigned char sha256[32], sha1[20], md5[16];

        while (!cancelled(options)) {
            const std::size_t index = next.fetch_add(1);
            if (index >= files.size()) break;
            const fs::path& path = files[index];

            std::string error;
            platform::RegularFile file;
            bool ok = file.open(path, error);
            while (ok) {
                const long long got = file.read(buffer.data(), buffer.size(), error);
                if (got < 0) {
                    ok = false;
                    hasher.reset();
                } else if (got == 0) {
                    break;
                } else {
                    hasher.update(buffer.data(), static_cast<std::size_t>(got));
                }
            }

            if (!ok) {
                report_error(ScanError{path, error});
            } else {
                hasher.finish(sha256, sha1, md5);
                const Threat* hit = nullptr;
                Threat threat;
                if (signatures.contains(Algo::SHA256, sha256)) {
                    threat = {path, Algo::SHA256, text::to_hex(sha256, 32)}, hit = &threat;
                } else if (signatures.contains(Algo::SHA1, sha1)) {
                    threat = {path, Algo::SHA1, text::to_hex(sha1, 20)}, hit = &threat;
                } else if (signatures.contains(Algo::MD5, md5)) {
                    threat = {path, Algo::MD5, text::to_hex(md5, 16)}, hit = &threat;
                }
                std::lock_guard<std::mutex> lock(mutex);
                ++summary.scanned;
                if (hit) {
                    ++summary.threats;
                    if (callbacks.on_threat) callbacks.on_threat(*hit);
                }
            }

            std::lock_guard<std::mutex> lock(mutex);
            ++done;
            const auto now = clock::now();
            if (callbacks.on_progress && done > last_reported &&
                (done == summary.total || now - last_progress >= interval)) {
                last_reported = done;
                last_progress = now;
                callbacks.on_progress(done, summary.total);
            }
        }
    };

    if (!files.empty()) {
        std::vector<std::thread> pool;
        for (unsigned i = 1; i < threads; ++i) pool.emplace_back(worker);
        worker();
        for (auto& t : pool) t.join();
    }

    summary.cancelled = done < summary.total && cancelled(options);
    summary.elapsed = std::chrono::duration<double>(clock::now() - started).count();
    return summary;
}

}  // namespace gavcore
