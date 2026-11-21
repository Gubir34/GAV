#include "hasher.hpp"

#include <stdexcept>

#ifdef _WIN32
#include <windows.h>
#include <bcrypt.h>
#else
#include <openssl/evp.h>
#endif

namespace gavcore {

#ifdef _WIN32

namespace {

struct Providers {
    BCRYPT_ALG_HANDLE alg[3]{};
    Providers() {
        const wchar_t* ids[3] = {BCRYPT_SHA256_ALGORITHM, BCRYPT_SHA1_ALGORITHM, BCRYPT_MD5_ALGORITHM};
        for (int i = 0; i < 3; ++i)
            if (!BCRYPT_SUCCESS(BCryptOpenAlgorithmProvider(&alg[i], ids[i], nullptr, BCRYPT_HASH_REUSABLE_FLAG)))
                throw std::runtime_error("BCryptOpenAlgorithmProvider failed");
    }
    ~Providers() {
        for (auto a : alg)
            if (a) BCryptCloseAlgorithmProvider(a, 0);
    }
};

const Providers& providers() {
    static const Providers instance;  // thread-safe init; provider handles may be shared
    return instance;
}

}  // namespace

struct MultiHasher::Impl {
    BCRYPT_HASH_HANDLE hash[3]{};
};

MultiHasher::MultiHasher() : impl_(std::make_unique<Impl>()) {
    const auto& p = providers();
    for (int i = 0; i < 3; ++i)
        if (!BCRYPT_SUCCESS(BCryptCreateHash(p.alg[i], &impl_->hash[i], nullptr, 0, nullptr, 0,
                                             BCRYPT_HASH_REUSABLE_FLAG)))
            throw std::runtime_error("BCryptCreateHash failed");
}

MultiHasher::~MultiHasher() {
    for (auto h : impl_->hash)
        if (h) BCryptDestroyHash(h);
}

void MultiHasher::reset() {
    // Reusable hashes are reset by BCryptFinishHash; drain any partial state.
    unsigned char scratch[32];
    const ULONG sizes[3] = {32, 20, 16};
    for (int i = 0; i < 3; ++i) BCryptFinishHash(impl_->hash[i], scratch, sizes[i], 0);
}

void MultiHasher::update(const unsigned char* data, std::size_t size) {
    while (size > 0) {
        const ULONG chunk = size > 0x40000000 ? 0x40000000 : static_cast<ULONG>(size);
        for (auto h : impl_->hash) BCryptHashData(h, const_cast<PUCHAR>(data), chunk, 0);
        data += chunk;
        size -= chunk;
    }
}

void MultiHasher::finish(unsigned char sha256[32], unsigned char sha1[20], unsigned char md5[16]) {
    BCryptFinishHash(impl_->hash[0], sha256, 32, 0);
    BCryptFinishHash(impl_->hash[1], sha1, 20, 0);
    BCryptFinishHash(impl_->hash[2], md5, 16, 0);
}

#else  // OpenSSL

struct MultiHasher::Impl {
    EVP_MD_CTX* ctx[3]{};
};

MultiHasher::MultiHasher() : impl_(std::make_unique<Impl>()) {
    for (auto& c : impl_->ctx) {
        c = EVP_MD_CTX_new();
        if (!c) throw std::runtime_error("EVP_MD_CTX_new failed");
    }
    reset();
}

MultiHasher::~MultiHasher() {
    for (auto c : impl_->ctx) EVP_MD_CTX_free(c);
}

void MultiHasher::reset() {
    const EVP_MD* mds[3] = {EVP_sha256(), EVP_sha1(), EVP_md5()};
    for (int i = 0; i < 3; ++i)
        if (EVP_DigestInit_ex(impl_->ctx[i], mds[i], nullptr) != 1)
            throw std::runtime_error("EVP_DigestInit_ex failed");
}

void MultiHasher::update(const unsigned char* data, std::size_t size) {
    for (auto c : impl_->ctx) EVP_DigestUpdate(c, data, size);
}

void MultiHasher::finish(unsigned char sha256[32], unsigned char sha1[20], unsigned char md5[16]) {
    unsigned int len = 0;
    EVP_DigestFinal_ex(impl_->ctx[0], sha256, &len);
    EVP_DigestFinal_ex(impl_->ctx[1], sha1, &len);
    EVP_DigestFinal_ex(impl_->ctx[2], md5, &len);
    reset();
}

#endif

}  // namespace gavcore
