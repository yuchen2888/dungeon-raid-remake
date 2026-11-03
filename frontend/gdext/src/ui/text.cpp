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
// The wide characters' file (T050-D: frontend/tools/make_cjk_font.py writes it in the BMFont layout above): ids from
// 128 up, the same units as load's.
bool Font::load_wide(const std::string& path,std::int32_t tex) {
    std::FILE* f=std::fopen(path.c_str(),"r");
    if(!f)return false;
    wide_texture=tex;wide.clear();
    char line[256];
    int lh=0,base_px=0,scale_w=0,scale_h=0,count=0;
    std::fgets(line,256,f);std::fgets(line,256,f);
    std::sscanf(line,"common lineHeight=%d base=%d scaleW=%d scaleH=%d",&lh,&base_px,&scale_w,&scale_h);
    std::fgets(line,256,f);std::fgets(line,256,f);
    std::sscanf(line,"chars count=%d",&count);
    for(int i=0;i<count && std::fgets(line,256,f);++i) {
        int id=0,x=0,y=0,w=0,h=0,ox=0,oy=0,adv=0;
        std::sscanf(line,"char id=%d x=%d y=%d width=%d height=%d xoffset=%d yoffset=%d xadvance=%d",&id,&x,&y,&w,&h,&ox,&oy,&adv);
        if(id<128 || lh<=0 || scale_w<=0 || scale_h<=0)continue;
        FontCharacter c;
        const float sw=static_cast<float>(scale_w),sh=static_cast<float>(scale_h),l=static_cast<float>(lh);
        c.u0=static_cast<float>(x)/sw;c.v0=static_cast<float>(y)/sh;
        c.u1=c.u0+static_cast<float>(w)/sw;c.v1=c.v0+static_cast<float>(h)/sh;
        c.w=static_cast<float>(w)/l;c.h=static_cast<float>(h)/l;
        c.ox=static_cast<float>(ox)/l*0.5f;
        c.oy=static_cast<float>(oy)/l+c.h*0.5f-static_cast<float>(base_px)/l;
        c.advance=static_cast<float>(adv)/l*0.5f;
        wide[static_cast<std::uint32_t>(id)]=c;
    }
    std::fclose(f);
    return true;
}
const FontCharacter& Font::glyph(std::uint32_t code,std::int32_t& texture_out) const {
    const auto it=wide.find(code);
    if(it==wide.end()){texture_out=texture;return chars['?'];}
    texture_out=wide_texture;return it->second;
}
std::uint32_t Font::shown(std::uint32_t code) const {
    if(code<0x80 || code>0xff || wide.count(code))return code;
    static const char plain[]=   // Latin-1 0xc0..0xff without their marks
        "AAAAAAACEEEEIIII" "DNOOOOOxOUUUUYTs" "aaaaaaaceeeeiiii" "dnooooo/ouuuuyty";
    if(code>=0xc0)return static_cast<std::uint8_t>(plain[code-0xc0]);
    if(code==0xa1)return '!';
    if(code==0xbf)return '?';
    return code;
}
// (the font's spacing is for its own letters: fontMenu's -0.225 pulls Latin capitals together but would run Chinese
// characters into each other; the wide glyphs' advance already holds their spacing)
float Font::wide_advance(std::uint32_t code) const {std::int32_t t;return glyph(code,t).advance;}
std::uint32_t next_code(const char* s,std::size_t& i) {
    const auto b=[&](std::size_t k){return static_cast<std::uint8_t>(s[k]);};
    const std::uint8_t c=b(i);
    int n=c>=0xf0?3:c>=0xe0?2:c>=0xc0?1:0;
    if(c<0x80 || n==0){++i;return c;}
    std::uint32_t code=c&(0x3fu>>n);
    for(int k=1;k<=n;++k) {
        if((b(i+static_cast<std::size_t>(k))&0xc0)!=0x80){++i;return c;}
        code=(code<<6)|(b(i+static_cast<std::size_t>(k))&0x3fu);
    }
    i+=static_cast<std::size_t>(n)+1;
    return code;
}
bool no_line_start(std::uint32_t code) {
    switch(code) {
    case 0xff0c:case 0x3002:case 0xff01:case 0xff1f:case 0xff1b:case 0xff1a:case 0x3001:case 0xff09:case 0x300b:case 0x300d:
    case 0x300f:case 0x201d:case 0x2019:case 0x2026:case 0xff05:case 0x3009:case 0x3011:return true;
    // (T050-K) Japanese: the small kana, the long vowel mark and the repeat marks
    case 0x3041:case 0x3043:case 0x3045:case 0x3047:case 0x3049:case 0x3063:case 0x3083:case 0x3085:case 0x3087:case 0x308e:
    case 0x30a1:case 0x30a3:case 0x30a5:case 0x30a7:case 0x30a9:case 0x30c3:case 0x30e3:case 0x30e5:case 0x30e7:case 0x30ee:
    case 0x30f5:case 0x30f6:case 0x30fc:case 0x3005:case 0x309d:case 0x309e:case 0x30fd:case 0x30fe:case 0x30fb:return true;
    default:return false;
    }
}
// (T050-K) Korean is written with spaces between words: its syllables and letters break only there, as English does
static bool hangul(std::uint32_t code) {
    return (code>=0xac00 && code<=0xd7a3) || (code>=0x1100 && code<=0x11ff) || (code>=0x3130 && code<=0x318f);
}
bool breaks_around(std::uint32_t code) {return code>=0x2e80 && !no_line_start(code) && !hangul(code);}
bool has_wide(const char* s) {for(;*s;++s)if(static_cast<std::uint8_t>(*s)>=0x80)return true;return false;}
std::vector<TextLine> wrap_wide(const Font& font,const char* s,float limit) {
    std::vector<TextLine> lines;
    std::size_t start=0,i=0,cut=0,next=0;
    bool can_cut=false;
    float w=0.0f,at=0.0f;
    std::uint32_t previous=0;
    while(s[i]) {
        const std::size_t pos=i;
        const std::uint32_t c=font.shown(next_code(s,i));
        if(c==' '){cut=pos;next=i;at=w;can_cut=true;}
        else if(pos>start && (breaks_around(c) || (breaks_around(previous) && !no_line_start(c)))){cut=pos;next=pos;at=w;can_cut=true;}
        float add;
        if(c<0x80){const char a=static_cast<char>(c);add=font.size(a).x*0.5f+font.advance(a,2.0f);}
        else {std::int32_t t;const FontCharacter& g=font.glyph(c,t);add=g.w*0.5f+g.advance;}
        w+=add;previous=c;
        if(w>limit && pos>start) {
            if(!can_cut){cut=pos;next=pos;at=w-add;}   // (no place to cut: before this character)
            lines.push_back(TextLine{start,cut,at});
            start=next;i=next;w=0.0f;can_cut=false;previous=0;
        }
    }
    lines.push_back(TextLine{start,i,w});
    return lines;
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
    bool has_wide=false;
    for(int i=0;i<n;++i)if(static_cast<std::uint8_t>(s[i])>=0x80)has_wide=true;
    if(has_wide || wide) {set_wide_text(s,n);return;}
    for(int i=count;i<n;++i) {glyphs.push_back(Quad());glyphs[static_cast<std::size_t>(i)].set_colour(colour);}
    if(textures.size()<glyphs.size())textures.resize(glyphs.size(),font->texture);
    count=n;width=0.0f;
    float pen=0.0f;
    for(int i=0;i<count;++i) {
        char c=s[i];
        if(c=='\t')c=' ';
        Quad& q=glyphs[static_cast<std::size_t>(i)];
        textures[static_cast<std::size_t>(i)]=font->texture;   // (an earlier wide text's glyph textures do not carry over)
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
// A text with wide characters (T050-D): one glyph per code point, every glyph set again (its byte offsets do not
// match the glyphs'), the same placing.
void Label::set_wide_text(const char* s,int n) {
    std::vector<std::uint32_t> codes;
    bool has_wide=false;
    for(std::size_t i=0;i<static_cast<std::size_t>(n);) {
        const std::uint32_t c=font->shown(next_code(s,i));
        codes.push_back(c=='\t'?' ':c);has_wide=has_wide || c>=0x80;
    }
    const int m=static_cast<int>(codes.size());
    for(int i=count;i<m;++i) {glyphs.push_back(Quad());glyphs[static_cast<std::size_t>(i)].set_colour(colour);}
    if(textures.size()<glyphs.size())textures.resize(glyphs.size(),font->texture);
    count=m;width=0.0f;
    float pen=0.0f;
    for(int i=0;i<m;++i) {
        const std::uint32_t c=codes[static_cast<std::size_t>(i)];
        Quad& q=glyphs[static_cast<std::size_t>(i)];
        float w,adv;
        if(c<0x80) {
            const char a=static_cast<char>(c);
            q.set_uv(font->top_left(a),font->bottom_right(a));q.set_size(font->size(a));q.set_offset(font->offset(a));
            textures[static_cast<std::size_t>(i)]=font->texture;w=font->size(a).x;adv=font->advance(a,space_scale);
        } else {
            std::int32_t tex=0;const FontCharacter& g=font->glyph(c,tex);
            q.set_uv(Point2{g.u0,g.v0},Point2{g.u1,g.v1});q.set_size(Point2{g.w,g.h});q.set_offset(Point2{g.ox,g.oy});
            textures[static_cast<std::size_t>(i)]=tex;w=g.w;adv=g.advance;   // (see wide_advance)
        }
        const float centre=w*0.5f+pen;
        q.position=Point2{centre,0.0f};
        pen=adv+centre;
    }
    width=pen;
    text.assign(s,static_cast<std::size_t>(n));
    wide=has_wide;
}
// Label::UpdateColour 0x1d490: the colour on every quad.
void Label::update_colour() {for(auto& q:glyphs)q.set_colour(colour);}
void Label::set_sub_colour(std::uint32_t first,std::uint32_t last,Colour c) {
    if(wide) {   // byte offsets to glyphs: the code points that start before them
        std::uint32_t a=0,b=0;
        for(std::uint32_t k=0;k<text.size() && k<last;++k) {
            if((static_cast<std::uint8_t>(text[k])&0xc0)==0x80)continue;
            if(k<first)++a;
            ++b;
        }
        first=a;last=b;
    }
    for(std::uint32_t i=first;i<last && i<glyphs.size();++i)glyphs[i].set_colour(c);
}
// Label::Render 0x1d4c4: the font's texture, translate, scale, rotate, the characters in use.
void Label::render(GL& gl) const {
    if(!count)return;
    gl.bind_texture(font->texture);
    gl.push();gl.translate(position.x,position.y);gl.scale(scale.x,scale.y);gl.rotate(rotation,1.0f);
    std::int32_t bound=font->texture;
    for(int i=0;i<count;++i) {
        const std::int32_t t=i<static_cast<int>(textures.size())?textures[static_cast<std::size_t>(i)]:font->texture;
        if(t!=bound){gl.bind_texture(t);bound=t;}   // (a wide glyph's texture, T050-D)
        glyphs[static_cast<std::size_t>(i)].render(gl);
    }
    if(bound!=font->texture)gl.bind_texture(font->texture);
    gl.pop();
}
}
