#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "cleaner.h"

namespace py = pybind11;

PYBIND11_MODULE(text_cleaner, m) {
    m.def("clean_text", &clean_text, 
        "Очищает текст от HTML-сущностей, спецсимволов, приводит к нижнему регистру и нормализует пробелы.",
        py::arg("text"));
}