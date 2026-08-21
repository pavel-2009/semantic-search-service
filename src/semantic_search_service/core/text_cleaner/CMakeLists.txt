# src/core/text_cleaner/CMakeLists.txt

cmake_minimum_required(VERSION 3.15)
project(text_cleaner)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# pybind11
include(FetchContent)
FetchContent_Declare(
    pybind11
    GIT_REPOSITORY https://github.com/pybind/pybind11.git
    GIT_TAG v2.13.6
)
FetchContent_MakeAvailable(pybind11)

# Модуль
pybind11_add_module(text_cleaner
    bindings.cpp
    cleaner.cpp
)

# Установка
install(TARGETS text_cleaner DESTINATION .)