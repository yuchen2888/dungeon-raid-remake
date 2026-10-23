#include "text.hpp"
#include <cctype>
#include <cstdio>
#include <cstring>
namespace drui {
namespace {
int clamp_char(int c) {return c<0?0:(c>127?127:c);}   // ClampI(c, 0, 127)
}
// Font::LoadFont 0x1c930: the "common" line, the "chars count" line, then one "char" line per character (ids
// above 127 skipped). Every value in the original's order of float operations.
bool Font::load(const std::string& path,std::int32_t tex) {
    texture=tex;
    std::FILE* f=std::fopen(path.c_str(),"r");
    if(!f)return false;
    char line[256];
    int scale_w=0,scale_h=0,count=0;
    std::fgets(line,256,f);std::fgets(line,256,f);
    std::sscanf(line,"common lineHeight=%d base=%d scaleW=%d scaleH=%d",&line_height,&base,&scale_w,&scale_h);
    std::fgets(line,256,f);std::fgets(line,256,f);
    std::sscanf(line,"chars count=%d",&count);
    for(int i=0;i<count;++i) {
        int id=0,x=0,y=0,w=0,h=0,ox=0,oy=0,adv=0;
        std::fgets(line,256,f);
        std::sscanf(line,"char id=%d x=%d y=%d width=%d height=%d xoffset=%d yoffset=%d xadvance=%d",&id,&x,&y,&w,&h,&ox,&oy,&adv);
        if(static_cast<unsigned>(id)>0x7f)continue;
        FontCharacter& c=chars[id];
        const float sw=static_cast<float>(scale_w),sh=static_cast<float>(scale_h),fw=static_cast<float>(w),fh=static_cast<float>(h);
        c.u0=static_cast<float>(x)/sw;
        c.v0=static_cast<float>(y)/sh;
        c.u1=c.u0+fw/sw;
        c.v1=c.v0+fh/sh;
        c.w=fw/static_cast<float>(line_height);
        const float hh=fh/static_cast<float>(line_height);
        c.h=hh;
        c.ox=static_cast<float>(ox)/static_cast<float>(line_height)*0.5f;
        const float lh=static_cast<float>(line_height);
        const float top=static_cast<float>(oy)/lh+hh*0.5f;
        c.oy=top-static_cast<float>(base)/lh;
        c.advance=static_cast<float>(adv)/static_cast<float>(line_height)*0.5f;
    }
    std::fclose(f);
    return true;
}
// Font::UseSmallCaps 0x1cb24: with s >= 0 each lower-case character becomes its capital scaled by s.
void Font::use_small_caps(float s) {
    small_caps=s;
    if(s<0)return;
    for(int c=0;c<128;++c) {
        if(!std::islower(c))continue;
        const FontCharacter& u=chars[std::toupper(c)];
        FontCharacter& d=chars[c];
        d.u0=u.u0;d.v0=u.v0;d.u1=u.u1;d.v1=u.v1;
        d.w=s*u.w;d.h=s*u.h;d.ox=s*u.ox;d.oy=s*u.oy;d.advance=u.advance*s;
    }
}
// Font::GetAdvance 0x1c884: a space's advance is scaled (Label+0x34), the others not; plus the spacing.
float Font::advance(char c,float space_scale) const {
    if(c==' '){const float a=space_scale*chars[32].advance;return a+spacing;}
    return chars[clamp_char(c)].advance+spacing;
}
Point2 Font::offset(char c) const {const FontCharacter& f=chars[clamp_char(c)];return Point2{f.ox,f.oy};}
Point2 Font::size(char c) const {const FontCharacter& f=chars[clamp_char(c)];return Point2{f.w,f.h};}
Point2 Font::top_left(char c) const {
    if(small_caps>0)c=static_cast<char>(std::toupper(c));
    const FontCharacter& f=chars[clamp_char(c)];return Point2{f.u0,f.v0};
}
Point2 Font::bottom_right(char c) const {
    if(small_caps>0)c=static_cast<char>(std::toupper(c));
    const FontCharacter& f=chars[clamp_char(c)];return Point2{f.u1,f.v1};
}
// Label::SetText 0x1d528: unchanged text does nothing; quads are added for new characters (coloured); a character
// that differs from the old text's at its index gets its texture coordinates, size and offset; every character is
// placed at the pen plus half its width, and the pen moves on by that plus the advance.
void Label::set_text(const char* s,int length) {
    if(text.compare(s)==0)return;
    const int n=length>=0?length:static_cast<int>(std::strlen(s));
    for(int i=count;i<n;++i) {glyphs.push_back(Quad());glyphs[static_cast<std::size_t>(i)].set_colour(colour);}
    count=n;width=0.0f;
    float pen=0.0f;
    for(int i=0;i<count;++i) {
        char c=s[i];
        if(c=='\t')c=' ';
        Quad& q=glyphs[static_cast<std::size_t>(i)];
        if(!(static_cast<std::size_t>(i)<text.size() && text[static_cast<std::size_t>(i)]==s[i])) {
            q.set_uv(font->top_left(c),font->bottom_right(c));
            q.set_size(font->size(c));
            q.set_offset(font->offset(c));
        }
        const float centre=font->size(c).x*0.5f+pen;
        q.position=Point2{centre,0.0f};
        pen=font->advance(c,space_scale)+centre;
    }
    width=pen;
    text.assign(s,static_cast<std::size_t>(n));
}
// Label::UpdateColour 0x1d490: the colour on every quad.
void Label::update_colour() {for(auto& q:glyphs)q.set_colour(colour);}
void Label::set_sub_colour(std::uint32_t first,std::uint32_t last,Colour c) {
    for(std::uint32_t i=first;i<last && i<glyphs.size();++i)glyphs[i].set_colour(c);
}
// Label::Render 0x1d4c4: the font's texture, translate, scale, rotate, the characters in use.
void Label::render(GL& gl) const {
    if(!count)return;
    gl.bind_texture(font->texture);
    gl.push();gl.translate(position.x,position.y);gl.scale(scale.x,scale.y);gl.rotate(rotation,1.0f);
    for(int i=0;i<count;++i)glyphs[static_cast<std::size_t>(i)].render(gl);
    gl.pop();
}
}
