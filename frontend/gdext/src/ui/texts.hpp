#pragma once
#include <map>
#include <string>
namespace drui {
// The original game's English texts the drawing shows (names, descriptions, the format strings the original fills),
// read from the local asset folder's texts.txt: frontend/tools/import_original_assets.py takes them from the original
// program, and like the art they stay on this machine. A missing key reads as "".
class Texts {
public:
    bool load(const std::string& path);
    const std::string& get(const std::string& key) const;
    const std::string& get(const std::string& key,int index) const;   // "key.index"
private:
    std::map<std::string,std::string> map_;
};
// sprintf as the original calls it, with one of the original's format strings.
std::string printf_string(const char* format,...);
}
