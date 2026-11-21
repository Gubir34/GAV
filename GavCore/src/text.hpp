#pragma once
#include <cstddef>
#include <string>
#include <string_view>

namespace gavcore::text {

std::string to_hex(const unsigned char* data, std::size_t size);
bool parse_hex(std::string_view hex, unsigned char* out, std::size_t size);

// Appends s as a JSON string literal (with quotes). Invalid UTF-8 becomes U+FFFD.
void append_json_string(std::string& out, std::string_view s);

// Makes a file name safe for a terminal: control, bidi and invalid bytes are escaped.
std::string display_safe(std::string_view s);

}  // namespace gavcore::text
