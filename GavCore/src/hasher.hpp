#pragma once
#include <cstddef>
#include <memory>

namespace gavcore {

// Computes SHA256, SHA1 and MD5 in a single pass. One instance per thread.
class MultiHasher {
public:
    MultiHasher();
    ~MultiHasher();
    MultiHasher(const MultiHasher&) = delete;
    MultiHasher& operator=(const MultiHasher&) = delete;

    void reset();
    void update(const unsigned char* data, std::size_t size);
    void finish(unsigned char sha256[32], unsigned char sha1[20], unsigned char md5[16]);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace gavcore
