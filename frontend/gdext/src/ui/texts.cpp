#include "texts.hpp"
#include <cstdarg>
#include <cstdio>
#include <fstream>
namespace drui {
namespace {
std::string unescape(const std::string& v) {
    std::string out;
    for(std::size_t i=0;i<v.size();++i) {
        if(v[i]!='\\' || i+1>=v.size()){out+=v[i];continue;}
        const char c=v[++i];
        out+=c=='n'?'\n':(c=='t'?'\t':c);
    }
    return out;
}
}
// Lines "key<tab>value" (backslash escapes \n, \t, \\); lines starting with # are comments.
bool Texts::load(const std::string& path) {
    std::ifstream f(path);
    if(!f)return false;
    std::string line;
    while(std::getline(f,line)) {
        if(line.empty() || line[0]=='#')continue;
        const auto tab=line.find('\t');
        if(tab==std::string::npos)continue;
        map_[line.substr(0,tab)]=unescape(line.substr(tab+1));
    }
    return true;
}
const std::string& Texts::get(const std::string& key) const {
    static const std::string none;
    const auto it=map_.find(key);
    return it==map_.end()?none:it->second;
}
const std::string& Texts::get(const std::string& key,int index) const {return get(key+"."+std::to_string(index));}
std::string printf_string(const char* format,...) {
    char buffer[512];
    va_list args;va_start(args,format);
    std::vsnprintf(buffer,sizeof buffer,format,args);
    va_end(args);
    return buffer;
}
}
