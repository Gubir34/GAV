#include <gavcore/engine.hpp>

#include <algorithm>

#include "platform.hpp"
#include "text.hpp"

#ifdef _WIN32
#include <winsqlite/winsqlite3.h>
#else
#include <sqlite3.h>
#endif

namespace gavcore {

const char* algo_name(Algo algo) {
    switch (algo) {
        case Algo::SHA256: return "SHA256";
        case Algo::SHA1: return "SHA1";
        case Algo::MD5: return "MD5";
    }
    return "?";
}

namespace {

template <std::size_t N>
bool add_to(std::vector<std::array<unsigned char, N>>& bucket, const std::string& hex) {
    std::array<unsigned char, N> digest{};
    if (!text::parse_hex(hex, digest.data(), N)) return false;
    bucket.push_back(digest);
    return true;
}

template <std::size_t N>
void sort_unique(std::vector<std::array<unsigned char, N>>& bucket) {
    std::sort(bucket.begin(), bucket.end());
    bucket.erase(std::unique(bucket.begin(), bucket.end()), bucket.end());
    bucket.shrink_to_fit();
}

template <std::size_t N>
bool find_in(const std::vector<std::array<unsigned char, N>>& bucket, const unsigned char* digest) {
    std::array<unsigned char, N> key;
    std::copy(digest, digest + N, key.begin());
    return std::binary_search(bucket.begin(), bucket.end(), key);
}

void load_db(SignatureSet& set, const fs::path& path) {
    sqlite3* db = nullptr;
    if (sqlite3_open_v2(platform::to_utf8(path).c_str(), &db, SQLITE_OPEN_READONLY, nullptr) != SQLITE_OK) {
        sqlite3_close(db);
        return;
    }
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db, "SELECT hash FROM signatures", -1, &stmt, nullptr) == SQLITE_OK) {
        while (sqlite3_step(stmt) == SQLITE_ROW) {
            const auto* value = sqlite3_column_text(stmt, 0);
            if (value) set.add_hex(reinterpret_cast<const char*>(value));
        }
    }
    sqlite3_finalize(stmt);
    sqlite3_close(db);
}

}  // namespace

bool SignatureSet::add_hex(const std::string& hex) {
    switch (hex.size()) {
        case 64: return add_to(sha256_, hex);
        case 40: return add_to(sha1_, hex);
        case 32: return add_to(md5_, hex);
        default: return false;
    }
}

void SignatureSet::finalize() {
    sort_unique(sha256_);
    sort_unique(sha1_);
    sort_unique(md5_);
}

bool SignatureSet::contains(Algo algo, const unsigned char* digest) const {
    switch (algo) {
        case Algo::SHA256: return find_in(sha256_, digest);
        case Algo::SHA1: return find_in(sha1_, digest);
        case Algo::MD5: return find_in(md5_, digest);
    }
    return false;
}

std::size_t SignatureSet::size(Algo algo) const {
    switch (algo) {
        case Algo::SHA256: return sha256_.size();
        case Algo::SHA1: return sha1_.size();
        case Algo::MD5: return md5_.size();
    }
    return 0;
}

std::size_t SignatureSet::size() const { return sha256_.size() + sha1_.size() + md5_.size(); }

SignatureSet SignatureSet::load(const fs::path& db_dir) {
    SignatureSet set;
    for (const char* name : {"signatures_sha256.db", "signatures_sha1.db", "signatures_md5.db"}) {
        const auto path = db_dir / name;
        std::error_code ec;
        if (fs::is_regular_file(path, ec)) load_db(set, path);
    }
    set.finalize();
    if (set.size() == 0)
        throw NoSignaturesError("No signatures loaded from " + platform::to_utf8(db_dir) +
                                "; run recompile.py and import_hashes.py first");
    return set;
}

}  // namespace gavcore
