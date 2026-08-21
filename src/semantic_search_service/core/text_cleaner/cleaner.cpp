#include "cleaner.h"
#include <regex>
#include <algorithm>
#include <cctype>
#include <string>

std::string clean_text(const std::string& input) {
    if (input.empty()) return "";

    std::string result = input;

    result = std::regex_replace(result, std::regex("&quot;"), "\"");
    result = std::regex_replace(result, std::regex("&#39;"), "'");
    result = std::regex_replace(result, std::regex("&amp;"), "&");
    result = std::regex_replace(result, std::regex("&lt;"), "<");
    result = std::regex_replace(result, std::regex("&gt;"), ">");

    result = std::regex_replace(result, std::regex("[^\\w\\s\\.\\,\\-\\!\?\"\'\\:\\;\\%\\(\\)]"), "");

    std::transform(result.begin(), result.end(), result.begin(), [](unsigned char c){
        return std::tolower(c);
    });

    result = std::regex_replace(result, std::regex("\\s+"), " ");

    result = std::regex_replace(result, std::regex("^\\s+|\\s+$"), "");

    result = std::regex_replace(result, std::regex("«"), "\"");
    result = std::regex_replace(result, std::regex("»"), "\"");

    return result;
};
