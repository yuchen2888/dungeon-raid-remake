#include "settings.hpp"
#include <algorithm>
#include <cmath>
namespace drui {
namespace {
// The pages' places, in points of the 320-point-wide screen: the panel (the game menu's pieces), its rows, the purple
// buttons (the empty button of the menu button's "on" picture, 72 x 26 pixels of tiles.png, widened by its middle).
constexpr float kPanelX=8.0f, kPanelY=14.0f, kPanelW=304.0f, kPanelH=456.0f;
constexpr float kLeft=24.0f, kRight=296.0f;
constexpr float kToggleX=204.0f, kToggleW=44.0f, kToggleH=22.0f;      // two halves: on / off, the lit one chosen
constexpr float kSliderX0=172.0f, kSliderX1=284.0f;
constexpr float kLanguageX=158.0f, kLanguageW=138.0f, kLanguageH=24.0f;
constexpr float kBottomY=428.0f, kBottomH=28.0f;
constexpr float kListTop=56.0f, kListBottom=412.0f, kRowH=34.0f;      // the language page's rows
constexpr float kNameW=192.0f, kNameH=24.0f;   // a name in the LangNames picture: a row of 1024 x 64 of its 1024ths
// The rows of the settings page: a heading, or a setting (its kind), each at its own height.
enum Kind { Heading, LanguageRow, Slider, Vibration, Pictures, Smooth, Dimming, Clock, Speed };
struct Row { Kind kind; const char* key; const char* english; float y; };
constexpr Row kRows[]={
    {Heading,"settings.general","General",64.0f},  {LanguageRow,"settings.language","Language",88.0f},
    {Heading,"settings.sound","Sound",119.0f},      {Slider,"settings.volume","Volume",143.0f},
    {Vibration,"settings.vibration","Vibration",174.0f},
    {Heading,"settings.display","Display",205.0f},  {Pictures,"settings.pictures","Graphics",229.0f},
    {Smooth,"settings.smooth","Smooth motion",260.0f},{Dimming,"settings.dimming","Dim in attacks",291.0f},
    {Clock,"settings.clock","Clock",322.0f},
    {Heading,"settings.game","Game",353.0f},        {Speed,"settings.speed","Animations",377.0f}};
constexpr Colour kTitle{255,255,255,255}, kHeading{122,103,211,255}, kText{214,208,245,255}, kLit{255,255,255,255},
                 kDim{140,130,190,255}, kButtonText{122,103,211,255};
// A label's vertical place: the menu font's letters sit above its position (its middle is 71 points per unit of
// scale above), the plain font's likewise (56).
constexpr float kMenuRaise=71.4f, kFontRaise=56.0f;
bool inside(Point2 p,float x,float y,float w,float h) {return p.x>x && p.x<x+w && p.y>y && p.y<y+h;}
}
SettingsView::SettingsView(const Font* font,const Font* menu_font):font_(font),menu_font_(menu_font) {
    background_.set_size(Point2{2.0f,2.0f});background_.position=Point2{0.5f,0.5f};background_.set_colour(Colour{0,0,0,170});
}
void SettingsView::configure(const std::vector<std::int32_t>& name_rows,const SettingsValues& v) {
    name_rows_=name_rows;values_=v;
}
void SettingsView::open(const Texts& t) {
    texts_=&t;open_=true;previous_=1;shown_=Main;sliding_=false;
}
const std::string& SettingsView::word(const char* key,const char* english) const {
    static std::string fallback;
    const std::string& s=texts_?texts_->get(key):fallback;
    if(!s.empty())return s;
    fallback=english;return fallback;
}
float SettingsView::row_y(std::int32_t i) const {return kListTop+kRowH*static_cast<float>(i)-scroll_;}
// ---- drawing: the pieces (a quad each: tiles, plain colour or the names picture) and labels, made again whenever
// what is shown changes (layout), drawn in order
void SettingsView::add(std::int32_t texture,float x,float y,float w,float h,Point2 uv,Point2 uv_size,Colour c) {
    Piece p{texture,{}};
    const float xs[4]={x,x+w,x+w,x},ys[4]={y,y,y+h,y+h};
    const float us[4]={uv.x,uv.x+uv_size.x,uv.x+uv_size.x,uv.x},vs[4]={uv.y,uv.y,uv.y+uv_size.y,uv.y+uv_size.y};
    for(int k=0;k<4;++k)p.v[k]=Vertex{xs[k]/320.0f,ys[k]/320.0f,{c.r,c.g,c.b,c.a},us[k]/1024.0f,vs[k]/1024.0f};
    pieces_.push_back(p);
}
void SettingsView::panel() {   // as GameMenu::GameMenu's corners, edges and fill
    const Colour w{255,255,255,255};
    const float iw=kPanelW-28.0f,ih=kPanelH-28.0f,x1=kPanelX+13.0f,x2=x1+iw,y1=kPanelY+13.0f,y2=y1+ih;
    const auto t=[&](float x,float y,float u,float v,float pw,float ph,float sx,float sy) {
        add(Tiles,x,y,pw*sx,ph*sy,Point2{u,v},Point2{pw,ph},w);
    };
    t(kPanelX,kPanelY,498,498,13,13,1,1);t(x1,kPanelY,479,472,1,13,iw,1);t(x2,kPanelY,380,415,15,13,1,1);
    t(kPanelX,y1,478,487,13,1,1,ih);t(x1,y1,145,399,1,1,iw,ih);t(x2,y1,380,430,15,1,1,ih);
    t(kPanelX,y2,498,482,13,15,1,1);t(x1,y2,483,470,1,15,iw,1);t(x2,y2,380,433,15,13,1,1);
}
void SettingsView::button(float x,float y,float w,float h,bool lit) {   // its ends as they are, its middle widened
    const std::uint8_t c=lit?255:140;
    const Colour col{c,c,c,255};
    const float end=std::min(8.0f,w*0.5f);
    add(Tiles,x,y,end,h,Point2{425.0f,698.0f},Point2{end,26.0f},col);
    add(Tiles,x+end,y,w-2.0f*end,h,Point2{425.0f+end,698.0f},Point2{72.0f-2.0f*end,26.0f},col);
    add(Tiles,x+w-end,y,end,h,Point2{497.0f-end,698.0f},Point2{end,26.0f},col);
}
// align: 0 left at x, 1 centred on x, 2 right at x; y is the letters' middle; room: when given, the widest it may be
// (a longer word is drawn smaller: other languages' words are longer).
void SettingsView::label(const Font* f,const std::string& text,float x,float y,float scale,Colour c,int align,float room) {
    if(label_count_>=labels_.size())labels_.emplace_back(f);
    Label& l=labels_[label_count_++];
    if(l.font!=f){l.font=f;l.text.clear();}   // (set_text keeps an unchanged text's glyphs)
    l.space_scale=2.0f;l.set_text(text.c_str());
    if(room>0.0f && l.width*scale*320.0f>room)scale=room/(l.width*320.0f);
    l.scale=Point2{scale,scale};l.colour=c;l.update_colour();
    const float w=l.width*scale*320.0f;
    const float left=align==0?x:align==1?x-w*0.5f:x-w;
    l.position=Point2{left/320.0f,(y+(f==menu_font_?kMenuRaise:kFontRaise)*scale)/320.0f};
}
void SettingsView::layout(const dungeonraid::SaveSettings& s) {
    pieces_.clear();label_count_=0;
    panel();
    const auto toggle=[&](float y,const char* on_key,const char* on_en,const char* off_key,const char* off_en,bool on) {
        for(int k=0;k<2;++k) {
            const bool lit=(k==0)==on;
            const float x=kToggleX+static_cast<float>(k)*(kToggleW+2.0f);
            button(x,y-kToggleH*0.5f,kToggleW,kToggleH,lit);
            label(menu_font_,k==0?word(on_key,on_en):word(off_key,off_en),x+kToggleW*0.5f,y,0.05f,lit?kLit:kDim,1,kToggleW-6.0f);
        }
    };
    const auto bottom=[&](float x,float w,const char* key,const char* english) {
        button(x,kBottomY,w,kBottomH,true);
        label(menu_font_,word(key,english),x+w*0.5f,kBottomY+kBottomH*0.5f,0.06f,kButtonText,1,w-12.0f);
    };
    if(shown_==Main) {
        label(menu_font_,word("settings.title","Settings"),160.0f,36.0f,0.09f,kTitle,1);
        for(const Row& r:kRows) {
            if(r.kind==Heading){label(menu_font_,word(r.key,r.english),kLeft,r.y,0.055f,kHeading,0);continue;}
            label(menu_font_,word(r.key,r.english),kLeft+6.0f,r.y,0.05f,kText,0,
                  (r.kind==LanguageRow?kLanguageX:r.kind==Slider?kSliderX0-44.0f:kToggleX)-kLeft-12.0f);
            switch(r.kind) {
            case LanguageRow: {
                button(kLanguageX,r.y-kLanguageH*0.5f,kLanguageW,kLanguageH,true);
                const std::size_t i=static_cast<std::size_t>(values_.language);
                if(i<name_rows_.size()) {   // the chosen language's name, at the left of its button
                    const float h=16.0f,w=h*kNameW/kNameH;
                    add(LangNames,kLanguageX+kLanguageW*0.5f-w*0.5f-6.0f,r.y-h*0.5f,w,h,
                        Point2{0.0f,64.0f*static_cast<float>(name_rows_[i])},Point2{1024.0f,64.0f},kLit);
                }
                {   // an arrow: the page it opens (a quad with two corners together, a triangle)
                    const float ax=kLanguageX+kLanguageW-16.0f;
                    Piece p{NoTexture,{}};
                    const float xs[4]={ax,ax+6.0f,ax+6.0f,ax},ys[4]={r.y-5.0f,r.y,r.y,r.y+5.0f};
                    for(int k=0;k<4;++k)p.v[k]=Vertex{xs[k]/320.0f,ys[k]/320.0f,{255,255,255,255},0.0f,0.0f};
                    pieces_.push_back(p);
                }
                break;
            }
            case Slider: {
                const float v=std::clamp(values_.volume,0.0f,1.0f),x=kSliderX0+(kSliderX1-kSliderX0)*v;
                add(NoTexture,kSliderX0,r.y-3.0f,kSliderX1-kSliderX0,6.0f,Point2{},Point2{},Colour{40,36,90,255});
                add(NoTexture,kSliderX0,r.y-3.0f,x-kSliderX0,6.0f,Point2{},Point2{},kHeading);
                button(x-8.0f,r.y-10.0f,16.0f,20.0f,true);
                label(font_,std::to_string(static_cast<int>(std::lround(v*100.0f)))+"%",kSliderX0-12.0f,r.y,0.095f,kText,2);
                break;
            }
            case Vibration: toggle(r.y,"settings.on","On","settings.off","Off",values_.vibration);break;
            case Pictures: toggle(r.y,"settings.hd","HD","settings.original","Original",values_.hd);break;
            case Smooth: toggle(r.y,"settings.on","On","settings.off","Off",s.framerate_13ecb!=0);break;
            case Dimming: toggle(r.y,"settings.on","On","settings.off","Off",s.dimming_13eca!=0);break;
            case Clock: toggle(r.y,"settings.on","On","settings.off","Off",s.clock_13ec9!=0);break;
            case Speed: toggle(r.y,"settings.normal","Normal","settings.fast","Fast",!values_.fast);break;
            default: break;
            }
        }
        bottom(kLeft,130.0f,"settings.about","About");
        bottom(kRight-130.0f,130.0f,"settings.back","Back");
    } else if(shown_==Languages) {
        label(menu_font_,word("settings.language","Language"),160.0f,36.0f,0.09f,kTitle,1);
        for(std::size_t i=0;i<name_rows_.size();++i) {
            const float y=row_y(static_cast<std::int32_t>(i));
            if(y<kListTop-0.5f || y+kRowH>kListBottom+0.5f)continue;   // (only whole rows: the list scrolls)
            const bool chosen=static_cast<std::int32_t>(i)==values_.language;
            if(chosen)add(NoTexture,kLeft-2.0f,y+2.0f,kRight-kLeft+4.0f,kRowH-4.0f,Point2{},Point2{},Colour{70,60,150,255});
            add(LangNames,160.0f-kNameW*0.5f,y+(kRowH-kNameH)*0.5f,kNameW,kNameH,
                Point2{0.0f,64.0f*static_cast<float>(name_rows_[i])},Point2{1024.0f,64.0f},chosen?kLit:kText);
            if(chosen)add(Tiles,kRight-22.0f,y+(kRowH-16.0f)*0.5f,16.0f,16.0f,Point2{405.0f,394.0f},Point2{16.0f,16.0f},kLit);
            add(NoTexture,kLeft+6.0f,y+kRowH-0.5f,kRight-kLeft-12.0f,1.0f,Point2{},Point2{},Colour{50,46,105,255});
        }
        const float all=kRowH*static_cast<float>(name_rows_.size()),room=kListBottom-kListTop;
        if(all>room) {   // the scroll bar
            const float h=room*room/all,y=kListTop+(room-h)*scroll_/(all-room);
            add(NoTexture,kRight+3.0f,y,3.0f,h,Point2{},Point2{},Colour{150,140,230,255});
        }
        bottom(160.0f-65.0f,130.0f,"settings.back","Back");
    } else {
        label(menu_font_,word("settings.about","About"),160.0f,36.0f,0.09f,kTitle,1);
        static const char* const english[]={"Dungeon Raid (remake)","Version 0.2","Original game: Firemint (2011)",
            "An unofficial remake, for study only","Chinese, Japanese, Korean letters:","Source Han Sans (SIL OFL 1.1)",
            "HD pictures: enlarged with Real-ESRGAN"};
        float y=84.0f;
        for(int k=0;k<7;++k) {   // the texts about.1 .. about.7
            const std::string key="about."+std::to_string(k+1);
            label(font_,word(key.c_str(),english[k]),160.0f,y,k==0?0.1f:0.085f,k==0?kTitle:kText,1,kRight-kLeft);
            y+=k==0?42.0f:(k==3 || k==5)?40.0f:28.0f;
        }
        bottom(160.0f-65.0f,130.0f,"settings.back","Back");
    }
}
std::int32_t SettingsView::touch(std::int32_t phase,Point2 p,dungeonraid::SaveSettings& s) {
    const bool began=phase==1 && previous_==0,ended=phase==2 && previous_==1;
    previous_=phase==2?0:phase;
    if(!open_)return Nothing;
    const Point2 at{p.x*320.0f,p.y*320.0f};
    if(shown_==Main) {
        if(sliding_) {   // the volume follows the touch until it ends
            values_.volume=std::clamp((at.x-kSliderX0)/(kSliderX1-kSliderX0),0.0f,1.0f);
            if(phase!=1){sliding_=false;return Changed;}
            return Volume;
        }
        if(!began)return Nothing;
        if(inside(at,kLeft,kBottomY,130.0f,kBottomH)){shown_=About;return Page;}
        if(inside(at,kRight-130.0f,kBottomY,130.0f,kBottomH)){open_=false;return Closed;}
        for(const Row& r:kRows) {
            if(r.kind==Heading || std::fabs(at.y-r.y)>13.0f)continue;
            if(r.kind==LanguageRow) {
                if(at.x<kLanguageX)return Nothing;
                shown_=Languages;
                const float all=kRowH*static_cast<float>(name_rows_.size()),room=kListBottom-kListTop;
                scroll_=std::clamp(kRowH*static_cast<float>(values_.language)-room*0.5f,0.0f,std::max(0.0f,all-room));
                scroll_=std::floor(scroll_/kRowH)*kRowH;
                return Page;
            }
            if(r.kind==Slider) {
                if(at.x<kSliderX0-12.0f)return Nothing;
                sliding_=true;values_.volume=std::clamp((at.x-kSliderX0)/(kSliderX1-kSliderX0),0.0f,1.0f);
                return Volume;
            }
            int half=-1;
            for(int k=0;k<2;++k)if(inside(at,kToggleX+static_cast<float>(k)*(kToggleW+2.0f),r.y-kToggleH*0.5f,kToggleW,kToggleH))half=k;
            if(half<0)return Nothing;
            const bool on=half==0;
            switch(r.kind) {   // the original's switches as GameMenu's: the value, its changed flag (kept by the platform)
            case Vibration: values_.vibration=on;return Changed;
            case Pictures: values_.hd=on;return Changed;
            case Speed: values_.fast=!on;return Changed;
            case Smooth: if(s.framerate_13ecb!=on){s.framerate_13ecb=on;s.framerate_changed_13ece=1;}return Switch;
            case Dimming: if(s.dimming_13eca!=on){s.dimming_13eca=on;s.dimming_changed_13ecd=1;}return Switch;
            case Clock: if(s.clock_13ec9!=on){s.clock_13ec9=on;s.clock_changed_13ecc=1;}return Switch;
            default: return Nothing;
            }
        }
        return Nothing;
    }
    if(shown_==About) {
        if(began && inside(at,160.0f-65.0f,kBottomY,130.0f,kBottomH)){shown_=Main;return Page;}
        return Nothing;
    }
    // the languages: Back, or a drag that scrolls the list, or a tap on a row
    if(began && inside(at,160.0f-65.0f,kBottomY,130.0f,kBottomH)){shown_=Main;return Page;}
    if(began && at.y>kListTop && at.y<kListBottom){touch_from_=at.y;scroll_from_=scroll_;scrolled_=false;return Nothing;}
    if(phase==1 && previous_==1 && touch_from_>0.0f) {
        if(std::fabs(at.y-touch_from_)>6.0f)scrolled_=true;
        if(scrolled_) {
            const float all=kRowH*static_cast<float>(name_rows_.size()),room=kListBottom-kListTop;
            scroll_=std::clamp(scroll_from_-(at.y-touch_from_),0.0f,std::max(0.0f,all-room));
        }
        return Nothing;
    }
    if(ended && touch_from_>0.0f) {
        touch_from_=0.0f;
        if(scrolled_){scroll_=std::round(scroll_/kRowH)*kRowH;return Nothing;}   // (it settles on whole rows)
        const auto i=static_cast<std::int32_t>(std::floor((at.y-kListTop+scroll_)/kRowH));
        if(i>=0 && i<static_cast<std::int32_t>(name_rows_.size())) {
            const bool changed=i!=values_.language;
            values_.language=i;shown_=Main;
            return changed?Language:Page;
        }
    }
    return Nothing;
}
void SettingsView::render(GL& gl,const dungeonraid::SaveSettings& s) {
    if(!open_)return;
    layout(s);
    gl.push();gl.load_identity();
    gl.bind_texture(NoTexture);background_.render(gl);
    std::int32_t bound=-1;
    for(const Piece& p:pieces_) {
        if(p.texture!=bound){gl.bind_texture(p.texture);bound=p.texture;}
        gl.draw(6,p.v,4);
    }
    for(std::size_t i=0;i<label_count_;++i)labels_[i].render(gl);
    gl.pop();
}
}
