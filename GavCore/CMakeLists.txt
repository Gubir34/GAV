cmake_minimum_required(VERSION 3.20)
project(GavCore VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

find_package(Threads REQUIRED)

add_library(gavcore_engine STATIC
  src/engine.cpp
  src/hasher.cpp
  src/signatures.cpp
  src/platform.cpp
  src/text.cpp)
target_include_directories(gavcore_engine PUBLIC include PRIVATE src)
target_compile_definitions(gavcore_engine PRIVATE GAVCORE_VERSION="${PROJECT_VERSION}")
target_link_libraries(gavcore_engine PUBLIC Threads::Threads)

if(WIN32)
  # CNG for hashing, the SQLite that ships with Windows 10+ (winsqlite3) for signatures.
  target_compile_definitions(gavcore_engine PUBLIC UNICODE _UNICODE NOMINMAX WIN32_LEAN_AND_MEAN)
  target_link_libraries(gavcore_engine PUBLIC bcrypt winsqlite3)
else()
  find_package(OpenSSL REQUIRED COMPONENTS Crypto)
  find_package(SQLite3 REQUIRED)
  target_link_libraries(gavcore_engine PUBLIC OpenSSL::Crypto SQLite::SQLite3)
endif()

if(MSVC)
  target_compile_options(gavcore_engine PRIVATE /W4 /permissive- /utf-8)
else()
  target_compile_options(gavcore_engine PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(gavcore src/main.cpp)
target_link_libraries(gavcore PRIVATE gavcore_engine)
target_compile_definitions(gavcore PRIVATE GAVCORE_VERSION="${PROJECT_VERSION}")
if(MSVC)
  target_compile_options(gavcore PRIVATE /W4 /permissive- /utf-8)
  set_property(TARGET gavcore_engine gavcore PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
endif()

install(TARGETS gavcore RUNTIME DESTINATION .)
