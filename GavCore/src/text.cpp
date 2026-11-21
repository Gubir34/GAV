#include "text.hpp"

#include <cstdio>

namespace gavcore::text {
namespace {

// Decodes one UTF-8 sequence at s[i]. Returns its length, or 0 if invalid.
std::size_t decode_utf8(std::string_view s, std::size_t i, char32_t& cp) {
    const auto b0 = static_cast<unsigned char>(s[i]);
    if (b0 < 0x80) {
        cp = b0;
        return 1;
    }
    std::size_t len;
    char32_t min;
    if ((b0 & 0xE0) == 0xC0) {
        len = 2, cp = b0 & 0x1F, min = 0x80;
    } else if ((b0 & 0xF0) == 0xE0) {
        len = 3, cp = b0 & 0x0F, min = 0x800;
    } else if ((b0 & 0xF8) == 0xF0) {
        len = 4, cp = b0 & 0x07, min = 0x10000;
    } else {
        return 0;
    }
    if (i + len > s.size()) return 0;
    for (std::size_t k = 1; k < len; ++k) {
        const auto b = static_cast<unsigned char>(s[i + k]);
        if ((b & 0xC0) != 0x80) return 0;
        cp = (cp << 6) | (b & 0x3F);
    }
    if (cp < min || cp > 0x10FFFF || (cp >= 0xD800 && cp <= 0xDFFF)) return 0;
    return len;
}

bool is_unsafe_codepoint(char32_t cp) {
    return cp < 0x20 || cp == 0x7F || (cp >= 0x80 && cp <= 0x9F)  // C0, DEL, C1 (incl. 8-bit CSI)
           || cp == 0x200E || cp == 0x200F || (cp >= 0x202A && cp <= 0x202E)  // bidi marks/overrides
           || (cp >= 0x2066 && cp <= 0x2069) || cp == 0xFEFF;
}

void append_fmt(std::string& out, const char* fmt, unsigned value) {
    char buf[16];
    std::snprintf(buf, sizeof buf, fmt, value);
    out += buf;
}

}  // namespace

std::string to_hex(const unsigned char* data, std::size_t size) {
    static const char digits[] = "0123456789abcdef";
    std::string out(size * 2, '0');
    for (std::size_t i = 0; i < size; ++i) {
        out[2 * i] = digits[data[i] >> 4];
        out[2 * i + 1] = digits[data[i] & 0x0F];
    }
    return out;
}

bool parse_hex(std::string_view hex, unsigned char* out, std::size_t size) {
    if (hex.size() != size * 2) return false;
    auto nibble = [](char c) -> int {
        if (c >= '0' && c <= '9') return c - '0';
        if (c >= 'a' && c <= 'f') return c - 'a' + 10;
        if (c >= 'A' && c <= 'F') return c - 'A' + 10;
        return -1;
    };
    for (std::size_t i = 0; i < size; ++i) {
        const int hi = nibble(hex[2 * i]), lo = nibble(hex[2 * i + 1]);
        if (hi < 0 || lo < 0) return false;
        out[i] = static_cast<unsigned char>((hi << 4) | lo);
    }
    return true;
}

void append_json_string(std::string& out, std::string_view s) {
    out += '"';
    for (std::size_t i = 0; i < s.size();) {
        char32_t cp;
        const std::size_t len = decode_utf8(s, i, cp);
        if (len == 0) {
            out += "\\ufffd";
            ++i;
            continue;
        }
        switch (cp) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (cp < 0x20 || cp == 0x7F) {
                    append_fmt(out, "\\u%04x", static_cast<unsigned>(cp));
                } else {
                    out.append(s.data() + i, len);
                }
        }
        i += len;
    }
    out += '"';
}

std::string display_safe(std::string_view s) {
    std::string out;
    out.reserve(s.size());
    for (std::size_t i = 0; i < s.size();) {
        char32_t cp;
        const std::size_t len = decode_utf8(s, i, cp);
        if (len == 0) {
            append_fmt(out, "\\x%02x", static_cast<unsigned char>(s[i]));
            ++i;
        } else if (is_unsafe_codepoint(cp)) {
            append_fmt(out, cp <= 0xFF ? "\\x%02x" : "\\u%04x", static_cast<unsigned>(cp));
            i += len;
        } else {
            out.append(s.data() + i, len);
            i += len;
        }
    }
    return out;
}

}  // namespace gavcore::text
