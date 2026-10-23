#include "setup.hpp"
#include "recovered_menu.hpp"
#include <cmath>
using namespace dungeonraid;
namespace drui {
namespace {
float interpolate(float a,float b,float t) {const float x=a*t;const float y=(1.0f-t)*b;return x+y;}   // 0x1b800
float clamp(float v,float lo,float hi) {if(v>=hi)return hi;return v<=lo?lo:v;}                            // 0x1b73c
std::int32_t clampi(std::int32_t v,std::int32_t lo,std::int32_t hi) {if(v>=hi)return hi;if(lo>=v)return lo;return v;}   // 0x1b7ec
Colour divided(Colour c,float f) {   // GLcolour4::operator/ 0x36c78 (the alpha kept)
    const auto d=[f](std::uint8_t v){const float x=static_cast<float>(v)/f;return static_cast<std::uint8_t>(static_cast<std::uint32_t>(x));};
    return Colour{d(c.r),d(c.g),d(c.b),c.a};
}
}
Point2 texels(Point2 p) {return Point2{p.x/512.0f,p.y/512.0f};}   // GLfloat2::operator/(512)
// CharacterClass::GetIconCoords 0x1113e4: a 51-pixel picture (row a, column b; small < 0) or a 24-pixel one (row small).
void icon_coords(std::int32_t a,std::int32_t b,std::int32_t small,Point2& p0,Point2& p1) {
    if(small<0) {
        p0=Point2{static_cast<float>(51*b),static_cast<float>(51*a+70)};
        p1=Point2{static_cast<float>(51*(b+1)),static_cast<float>(51*(a+1)+70)};
    } else {
        p0=Point2{static_cast<float>(24*b),static_cast<float>(24*small+172)};
        p1=Point2{static_cast<float>(24*(b+1)),static_cast<float>(24*(small+1)+172)};
    }
}
// Tile::GetEnemyUV 0x3d2c4 (0..1 of tiles.png; 53-pixel cells, enemies eight a row from v 0.65625)
void enemy_uv(std::int32_t e,Point2& a,Point2& b) {
    constexpr float cell=0.0517578125f;
    if(e==0)a=Point2{0.0f,cell};
    else {
        const std::int32_t k=e-1;
        a.x=static_cast<float>(k%8)*cell;
        const float row=static_cast<float>(k/8)*cell;a.y=row+0.65625f;
    }
    b.x=a.x+cell;b.y=a.y+cell;
}
// Skill::GetIconUVs 0x2ac38 -> Upgrade::GetIconUVs 0x261b4 (column t % 10, row t / 10, 1024 wide, 512 across).
void skill_uvs(std::int32_t t,Point2& p0,Point2& p1) {
    const std::int32_t column=t%10,row=t/10;
    const float size=1024.0f;
    const float cell=50.0299988f/size,border=1.0f/size;
    const float u=cell*static_cast<float>(column)+border;
    p0.x=u+512.0f/size;
    p0.y=border+cell*static_cast<float>(row);
    const float icon=49.0f/size;
    p1.x=p0.x+icon;p1.y=icon+p0.y;
}
bool perk_unlocked(const ClassProfile& c,int k) {   // CharacterClass::IsPerkUnlocked 0x111548
    switch(k) {
    case 0: return c.level!=0;
    case 1: return c.level>2;
    case 2: return c.level>6;
    case 3: return c.level>8;
    default: return false;
    }
}
namespace {
constexpr Colour kChosen{75,75,127,255};   // (150, 150, 255, 255) / 2
constexpr Colour kButton{150,150,255,255};   // QuadStrip::SetColour(150, 150, 255, 255)
}
// NameScreen::NameScreen 0x3a232 (frontend/tools/trace_function.py '__ZN10NameScreenC2EP4Game').
SetupView::SetupView(const Font* font,const Font* menu_font):menu_font_(menu_font),mode_(font,menu_font),class_(font) {
    mode_.sounds=&sounds;class_.sounds=&sounds;
    Quad& black=quad(0x4);black.set_size(Point2{2.0f,2.0f});black.position=Point2{0.5f,0.5f};black.set_colour(Colour{0,0,0,255});
    Quad& back=quad(0x74);back.set_size(Point2{2.0f,1.62f});back.position=Point2{0.5f,0.5f};back.set_colour(Colour{45,45,75,255});
    Quad& keys=quad(0xe4);keys.set_size(Point2{1.0f,1.0f});keys.position=Point2{0.5f,0.449999988f};keys.set_colour(Colour{0,0,0,255});
    // the keyboard: three rows of letter keys, offset by half and two and a half keys
    const Point2 key{0.081249997f,0.121875003f};
    const Point2 half{key.x/2.0f,key.y/2.0f};
    const Point2 base{half.x+0.00937500037f,half.y+0.00937500037f};
    for(int k=0;k<30;++k) {
        key_label(k)=Label(font);key_label(k).scale=Point2{0.140000001f,0.140000001f};
        if(k>25)continue;
        Quad& q=quad(0x1b90+0x70*static_cast<std::size_t>(k));
        q.set_uv(Point2{0.947265625f,0.921875f},Point2{0.998046875f,0.998046875f});
        q.scale=key;
        const int column=k%10;
        float x=static_cast<float>(column),row=0.0f;
        if(k>9) {
            x=x+0.5f;
            if(k<=18)row=1.0f;
            else {if(k==19)x=1.5f;else x=x+2.0f;row=2.0f;}
        }
        const float px=base.x+x*0.081249997f;q.position.x=px+x*0.0187500007f;
        const float py=base.y+row*0.121875003f;q.position.y=py+row*0.046875f;
    }
    for(int j=0;j<10;++j){Label& l=label(0x1044+0x38*static_cast<std::size_t>(j));l=Label(font);l.scale=Point2{0.0799999982f,0.0799999982f};}
    const auto special=[&](std::size_t off,Point2 uv0,Point2 uv1,float w,Point2 at) {
        Quad& q=quad(off);q.set_uv(uv0,uv1);q.scale=Point2{w,0.121875003f};q.position=at;
    };
    special(0x26f0,Point2{0.875f,0.921875f},Point2{0.9453125f,0.998046875f},0.112499997f,Point2{0.065624997f,0.407812506f});   // shift
    special(0x2760,Point2{0.802734375f,0.921875f},Point2{0.873046875f,0.998046875f},0.112499997f,Point2{0.934374988f,0.407812506f});   // delete
    special(0x27d0,Point2{0.5f,0.921875f},Point2{0.80078125f,0.998046875f},0.481249988f,Point2{0.5f,0.576562524f});   // space
    special(0x2840,Point2{0.853515625f,0.84375f},Point2{0.998046875f,0.919921875f},0.231250003f,Point2{0.875f,0.576562524f});   // OK
    label(0x2964)=Label(font);label(0x2a8)=Label(font);
    make_panel(0x1d8,true,0.96875f,0.184374988f,0.015625f,0.015625f);   // the name: its box and Random
    make_button(0x25c,0.69921875f,0.081249997f,0.03125f,0.103124991f);
    make_button(0x2e0,0.22265625f,0.081249997f,0.74609375f,0.103124991f);
    strip(0x25c).set_colour(Colour{95,95,150,255});
    make_panel(0x364,true,0.96875f,0.268750012f,0.015625f,0.231249988f);   // the difficulty (or the challenge's modes)
    const float column[4]={0.03125f,0.26953125f,0.5078125f,0.74609375f};
    for(int k=0;k<4;++k)make_button(0x3e8+0x4c*static_cast<std::size_t>(k),0.22265625f,0.165625006f,column[k],0.318749994f);
    make_button(0x630,0.165625006f,0.065624997f,0.803125024f,0.234374985f);
    make_button(0x6b4,0.4609375f,0.165625006f,0.03125f,0.318749994f);
    strip(0x74c).add_quad(Point2{399.0f,378.0f},Point2{511.0f,431.0f},2,-1.0f);strip(0x74c).align_with(strip(0x6b4));
    make_button(0x700,0.4609375f,0.165625006f,0.5078125f,0.318749994f);
    strip(0x798).add_quad(Point2{409.0f,324.0f},Point2{511.0f,377.0f},2,-1.0f);strip(0x798).align_with(strip(0x700));
    make_panel(0x7e4,true,0.96875f,0.461718768f,0.015625f,0.53125f);   // the classes
    make_button(0x868,0.165625006f,0.065624997f,0.803125024f,0.534375012f);
    const float cx[5]={0.03125f,0.224218756f,0.417187512f,0.610156298f,0.803125024f};
    const Point2 big{51.0f/320.0f,51.0f/320.0f};
    for(int k=0;k<10;++k) {
        const std::size_t s=0x8ec+0x4c*static_cast<std::size_t>(k);
        make_button(s,0.165625006f,0.165625006f,cx[k%5],k<5?0.618749976f:0.811718702f);
        Quad& q=quad(0xbe4+0x70*static_cast<std::size_t>(k));q.scale=big;q.position=strip(s).middle();
    }
    make_panel(0x1274,true,0.96875f,0.268750012f,0.015625f,1.0242188f);   // the class's properties
    make_button(0x12f8,0.165625006f,0.065624997f,0.803125024f,1.02734375f);
    make_panel(0x137c,false,0.165625006f,0.165625006f,0.03125f,1.11171877f);
    make_panel(0x13c8,false,0.165625006f,0.165625006f,0.224218756f,1.11171877f);
    make_panel(0x1674,false,0.165625006f,0.165625006f,0.803125024f,1.11171877f);
    const std::pair<std::size_t,std::size_t> slots[3]={{0x137c,0x16c0},{0x13c8,0x1730},{0x1674,0x1b20}};
    for(const auto& s:slots){Quad& q=quad(s.second);q.scale=big;q.position=strip(s.first).middle();}
    const Point2 small{24.0f/320.0f,24.0f/320.0f};
    const float px[4]={0.430468768f,0.514843762f,0.599218726f,0.68359375f};
    for(int k=0;k<4;++k)for(int row=0;row<2;++row) {   // the perks (top) and flaws
        const std::size_t s=(row?0x1544:0x1414)+0x4c*static_cast<std::size_t>(k);
        make_panel(s,false,0.081249997f,0.081249997f,px[k],row?1.1960938f:1.11171877f);
        Quad& q=quad(0x16c0+0x70*static_cast<std::size_t>(2+k+4*row));q.scale=small;q.position=strip(s).middle();
    }
    make_button(0x154,0.181250006f,0.158749998f,0.015625f,1.32562494f);   // Back
}
void make_panel(QuadStrip& s,bool heading,float w,float h,float x,float y,float band) {
    const auto add=[&](float u0,float v0,float u1,float v1,int policy,float extent){s.add_quad(Point2{u0,v0},Point2{u1,v1},policy,extent);};
    if(heading) {
        add(194,1,199,6,2,-1.0f);add(199,1,242,6,1,-1.0f);add(242,1,247,6,2,-1.0f);
        s.row++;
        add(194,6,199,49,2,band);add(199,6,242,49,1,band);add(242,6,247,49,2,band);
        s.row++;
        add(194,6,199,49,2,0.00312500005f);add(199,6,242,49,1,0.00312500005f);add(242,6,247,49,2,0.00312500005f);
    } else {
        add(50,1,55,6,2,-1.0f);add(55,1,98,6,1,-1.0f);add(98,1,103,6,2,-1.0f);
    }
    s.row++;
    add(50,6,55,49,0,-1.0f);add(55,6,98,49,3,-1.0f);add(98,6,103,49,0,-1.0f);
    s.row++;
    add(50,49,55,54,2,-1.0f);add(55,49,98,54,1,-1.0f);add(98,49,103,54,2,-1.0f);
    s.has_fixed=true;s.fixed=Point2{w,h};s.update_size();
    s.set_position(Point2{x,y});
    s.set_colour(kButton);
    if(heading) {   // the heading's band
        const Colour c{95,95,150,255};
        for(int q=0;q<6;++q)s.quads[static_cast<std::size_t>(q)].set_colour(c);
        for(int q=6;q<9;++q)s.quads[static_cast<std::size_t>(q)].set_colour(divided(c,1.70000005f));
    }
}
void make_button(QuadStrip& s,float w,float h,float x,float y) {
    const auto add=[&](float u0,float v0,float u1,float v1,int policy){s.add_quad(Point2{u0,v0},Point2{u1,v1},policy,-1.0f);};
    add(194,1,199,6,2);add(199,1,242,6,1);add(242,1,247,6,2);
    s.row++;
    add(194,6,199,49,0);add(199,6,242,49,3);add(242,6,247,49,0);
    s.row++;
    add(194,49,199,54,2);add(199,49,242,54,1);add(242,49,247,54,2);
    s.has_fixed=true;s.fixed=Point2{w,h};s.update_size();
    s.set_position(Point2{x,y});
    s.set_colour(kButton);
}
void SetupView::make_button_label(std::size_t off,std::size_t l,const std::string& text) {
    Label& b=label(l);b.font=menu_font_;b.scale=Point2{0.0593749993f,0.0593749993f};b.space_scale=2.0f;
    b.set_text(text.c_str());b.colour=Colour{122,103,211,255};b.update_colour();
    const QuadStrip& s=strip(off);
    const Point2 size=s.size();
    const float centre=s.position.x+size.x*0.5f;
    const float w=b.width*b.scale.x;const float h=w*-0.5f;
    const float x=centre+h;b.position.x=x-0.00625000009f;
    const float middle=s.position.y+size.y*0.5f;b.position.y=middle+0.0187500007f;
}
void make_heading_label(const QuadStrip& s,Label& b,const Font* font,const std::string& text) {
    b.font=font;b.scale=Point2{0.0593749993f,0.0593749993f};b.space_scale=2.0f;
    b.set_text(text.c_str());b.colour=Colour{122,103,211,255};b.update_colour();
    b.position.y=s.position.y+0.0562499985f;b.position.x=s.position.x+0.015625f;
}
void SetupView::make_panel(std::size_t off,bool heading,float w,float h,float x,float y) {drui::make_panel(strip(off),heading,w,h,x,y);}
void SetupView::make_button(std::size_t off,float w,float h,float x,float y) {drui::make_button(strip(off),w,h,x,y);}
void SetupView::make_heading_label(std::size_t off,std::size_t l,const std::string& text) {
    drui::make_heading_label(strip(off),label(l),menu_font_,text);
}
void SetupView::initialise(const Texts& t) {
    mode_.initialise(t);texts_=&t;
    Label& begin=label(0x2964);begin.scale=Point2{0.129999995f,0.129999995f};begin.set_text(t.get("setup.begin").c_str());
    const float wb=begin.width*begin.scale.x;const float x=1.0f-wb;begin.position.x=x*0.5f;begin.position.y=1.42999995f;
    for(int k=0;k<30;++k) {
        Label& l=key_label(k);l.set_text(t.get("setup.key",k).c_str());
        const Quad& q=quad(0x1b90+0x70*static_cast<std::size_t>(k));
        const float w=l.width*l.scale.x;const float h=w*-0.5f;
        l.position.x=h+q.position.x;l.position.y=q.position.y+0.0234375f;
    }
    Label& name=label(0x2a8);name.scale=Point2{0.119999997f,0.119999997f};name.space_scale=2.0f;
    make_heading_label(0x1d8,0x224,t.get("setup.name"));
    make_heading_label(0x364,0x3b0,t.get("setup.difficulty"));
    make_heading_label(0x364,0x5f8,t.get("setup.challenge"));
    make_heading_label(0x7e4,0x830,t.get("setup.class"));
    make_heading_label(0x1274,0x12c0,t.get("setup.properties"));
    make_button_label(0x2e0,0x32c,t.get("setup.random"));
    make_button_label(0x630,0x67c,t.get("setup.help"));
    make_button_label(0x868,0x8b4,t.get("setup.help"));
    make_button_label(0x12f8,0x1344,t.get("setup.edit"));
    make_button_label(0x154,0x1a0,t.get("setup.back"));
    for(int k=0;k<4;++k)
        make_button_label(0x3e8+0x4c*static_cast<std::size_t>(k),0x518+0x38*static_cast<std::size_t>(k),t.get("difficulty.name",k));
}
void SetupView::update_name(const SessionObjects& o) {
    SetupScreen& n=*o.setup;
    Label& l=label(0x2a8);
    const QuadStrip& box=strip(0x25c);
    // (the placeholder the session writes, "Enter name", is shown in the game's language: the text setup.enter_name)
    const std::string* placeholder=!n.named && texts_?&texts_->get("setup.enter_name"):nullptr;
    l.set_text(placeholder && !placeholder->empty()?placeholder->c_str():n.name);
    for(;placeholder==nullptr || placeholder->empty();) {
        const float w=l.width*l.scale.x;
        const float room=box.size().x-0.015625f;
        if(!(w>room))break;
        n.length-=1;n.name[n.length]=0;
        l.set_text(n.name);
    }
    l.position.x=box.position.x+0.015625f;
    const float bottom=box.position.y+box.size().y;l.position.y=bottom-0.015625f;
}
void SetupView::update_difficulty(const SessionObjects& o) {
    for(int k=0;k<4;++k)strip(0x3e8+0x4c*static_cast<std::size_t>(k)).set_colour(k==o.match->spawn_enabled_14ae0?kChosen:kButton);
}
void SetupView::update_mode(const SessionObjects& o) {
    for(int k=0;k<2;++k)strip(0x6b4+0x4c*static_cast<std::size_t>(k)).set_colour(k==o.stroke->mode_14ae8?kChosen:kButton);
    mode_.update_mode(o);
}
void SetupView::select_class(const SessionObjects& o) {
    const ClassProfile& c=o.classes[o.scroll->current];
    Point2 a,b;
    icon_coords(0,c.class_type,-1,a,b);quad(0x16c0).set_uv(texels(a),texels(b));
    icon_coords(1,c.race,-1,a,b);quad(0x1730).set_uv(texels(a),texels(b));
    const std::int32_t skill=c.class_type==0?7:dr_class_base_skills[c.class_type][0];   // the class's first base skill (Class+0x30)
    skill_uvs(skill,a,b);quad(0x1b20).set_uv(a,b);
    const Point2 dummy0{-24.0f,0.0f},dummy1{0.0f,24.0f};   // CharacterClass::GetDummySmallIconCoords, given as they are
    for(int k=0;k<4;++k) {
        Quad& perk=quad(0x16c0+0x70*static_cast<std::size_t>(2+k));
        Quad& flaw=quad(0x16c0+0x70*static_cast<std::size_t>(6+k));
        if(perk_unlocked(c,k) && c.class_type!=0) {
            if(c.perks[k]==255)perk.set_uv(dummy0,dummy1);
            else {icon_coords(0,c.perks[k],0,a,b);perk.set_uv(texels(a),texels(b));}
            if(c.flaws[k]==255)flaw.set_uv(dummy0,dummy1);
            else {icon_coords(0,c.flaws[k]+10,0,a,b);flaw.set_uv(texels(a),texels(b));}
        } else {   // a lock
            const Point2 l0=texels(Point2{345.0f,287.0f}),l1=texels(Point2{369.0f,311.0f});
            perk.set_uv(l0,l1);flaw.set_uv(l0,l1);
        }
    }
    for(int k=0;k<10;++k) {
        const bool chosen=k==c.class_type,unlocked=o.classes[k].level!=0;
        strip(0x8ec+0x4c*static_cast<std::size_t>(k)).set_colour(!chosen && unlocked?kButton:kChosen);
    }
}
void SetupView::set_alpha(std::int32_t value) {
    const auto a=static_cast<std::uint8_t>(value);
    const auto lab=[&](std::size_t off){Label& l=label(off);l.colour.a=a;l.update_colour();};
    quad(0x4).set_alpha(a);quad(0x74).set_alpha(a);quad(0xe4).set_alpha(a);
    strip(0x1d8).set_alpha(a);lab(0x224);strip(0x25c).set_alpha(a);lab(0x2a8);strip(0x2e0).set_alpha(a);lab(0x32c);
    strip(0x364).set_alpha(a);lab(0x3b0);
    for(int k=0;k<4;++k){strip(0x3e8+0x4c*static_cast<std::size_t>(k)).set_alpha(a);lab(0x518+0x38*static_cast<std::size_t>(k));}
    lab(0x5f8);strip(0x630).set_alpha(a);lab(0x67c);
    strip(0x6b4).set_alpha(a);strip(0x74c).set_alpha(a);strip(0x700).set_alpha(a);strip(0x798).set_alpha(a);
    strip(0x7e4).set_alpha(a);lab(0x830);strip(0x868).set_alpha(a);lab(0x8b4);
    for(int k=0;k<10;++k) {
        strip(0x8ec+0x4c*static_cast<std::size_t>(k)).set_alpha(a);quad(0xbe4+0x70*static_cast<std::size_t>(k)).set_alpha(a);
        lab(0x1044+0x38*static_cast<std::size_t>(k));
    }
    strip(0x1274).set_alpha(a);lab(0x12c0);strip(0x12f8).set_alpha(a);lab(0x1344);
    for(int k=0;k<11;++k){strip(0x137c+0x4c*static_cast<std::size_t>(k)).set_alpha(a);quad(0x16c0+0x70*static_cast<std::size_t>(k)).set_alpha(a);}
    for(int k=0;k<30;++k){quad(0x1b90+0x70*static_cast<std::size_t>(k)).set_alpha(a);Label& l=key_label(k);l.colour.a=a;l.update_colour();}
    strip(0x154).set_alpha(a);lab(0x1a0);
    Label& begin=label(0x2964);   // Begin keeps its own fade, scaled
    const std::int32_t scaled=static_cast<std::int32_t>(begin.colour.a)*value;
    const float f=static_cast<float>(scaled)/255.0f;
    begin.colour.a=static_cast<std::uint8_t>(static_cast<std::uint32_t>(f));begin.update_colour();
}
void SetupView::show(const Texts& t,const SessionObjects& o) {
    open_=true;timer_=0.300000012f;keyboard_=false;slide_=0.0f;closing_=false;
    Label& begin=label(0x2964);begin.colour=Colour{255,255,0,0};begin.update_colour();
    update_name(o);update_difficulty(o);update_mode(o);
    for(int k=0;k<10;++k) {
        Point2 a,b;
        if(o.classes[k].level)icon_coords(0,k,-1,a,b);else {a=Point2{370.0f,260.0f};b=Point2{421.0f,311.0f};}
        quad(0xbe4+0x70*static_cast<std::size_t>(k)).set_uv(texels(a),texels(b));
    }
    for(int k=0;k<10;++k) {
        Label& l=label(0x1044+0x38*static_cast<std::size_t>(k));
        if(k!=0 && o.classes[k].level)l.set_text(printf_string(t.get("setup.level").c_str(),static_cast<int>(o.classes[k].level)).c_str());
        else l.set_text("");
        const QuadStrip& s=strip(0x8ec+0x4c*static_cast<std::size_t>(k));
        const Point2 size=s.size();
        const float right=s.position.x+size.x;const float w=l.width*l.scale.x;const float x=right-w;
        l.position.x=x-0.00937500037f;
        const float bottom=s.position.y+size.y;l.position.y=bottom-0.00937500037f;
    }
    select_class(o);
    set_alpha(0);
}
void SetupView::process(const SessionObjects& o,float dt) {
    if(class_.open()) {   // the class screen over it
        class_.process(o,dt);
        if(class_.open() && class_.fade()>=1.0f && pressed_==31) {   // NameScreen::Render, once it covers the screen: Edit let go
            strip(0x12f8).set_colour(kButton);Label& l=label(0x1344);l.colour=Colour{122,103,211,255};l.update_colour();pressed_=-1;
        }
        return;
    }
    if(mode_.open()) {   // the mode screen over it
        update_mode(o);
        const std::int32_t m=mode_.process(o,dt);
        if(m>=0)requests.push_back({SetupAction::ScreenMode,m});
        return;
    }
    SetupScreen& n=*o.setup;
    if(timer_>0.0f) {   // the fades
        timer_=timer_-dt;
        if(timer_<0.0f){timer_=0.0f;if(closing_){open_=false;o.screens->name_12c09=0;}}
        const float x=timer_/0.300000012f;
        std::int32_t a=static_cast<std::int32_t>(interpolate(0.0f,255.0f,x));
        if(closing_)a=255-a;
        set_alpha(a);
        return;
    }
    const float step=dt*3.0f;
    const float s=slide_+(keyboard_?step:-step);
    slide_=clamp(s,0.0f,1.0f);
    process_input(o,dt);
    previous_=o.touch->phase;
    update_difficulty(o);update_mode(o);
    Label& begin=label(0x2964);
    begin_before_=begin.colour.a;dt_=dt;
    fade_begin(n,dt);
    if(keyboard_) {   // the cursor blinks
        const float b=blink_+dt;blink_=std::fmod(b,1.0f);
        if(blink_>0.5f)n.name[n.length]=0;
        else {n.name[n.length]='|';n.name[n.length+1]=0;}
        update_name(o);
        const std::uint8_t ok=n.length>0?255:64;
        quad(0x2840).set_alpha(ok);Label& l=key_label(29);l.colour.a=ok;l.update_colour();
        if(shift_)quad(0x26f0).set_uv(Point2{0.5625f,0.765625f},Point2{0.6328125f,0.841796875f});
        else quad(0x26f0).set_uv(Point2{0.875f,0.921875f},Point2{0.9453125f,0.998046875f});
    } else if(n.named) {n.name[n.length]=0;update_name(o);}
}
// Begin fades in while there is a name and the keyboard is down, out otherwise.
void SetupView::fade_begin(const SetupScreen& n,float dt) {
    Label& begin=label(0x2964);
    std::int32_t a=begin.colour.a;
    if(!keyboard_ && n.named && n.length)a=a+static_cast<std::int32_t>(dt*300.0f);
    else a=a-static_cast<std::int32_t>(dt*900.0f);
    begin.colour.a=static_cast<std::uint8_t>(clampi(a,0,255));begin.update_colour();
}
void SetupView::after_request(const SessionObjects& o,const SetupRequest& r) {
    SetupScreen& n=*o.setup;
    switch(r.action) {
    case SetupAction::RandomName:
        if(!keyboard_ && n.named){n.name[n.length]=0;update_name(o);}
        // (the original names inside ProcessInput, before the frame's Begin fade: that fade again, with the name)
        {Label& begin=label(0x2964);begin.colour.a=begin_before_;fade_begin(n,dt_);}
        break;
    case SetupAction::Difficulty: update_difficulty(o);break;
    case SetupAction::Mode: update_mode(o);break;
    case SetupAction::Class: select_class(o);break;   // Game::SetCurrentClass -> NameScreen::SelectClass
    case SetupAction::Edit: class_.initialise(*texts_,o);break;
    default: break;
    }
}
void SetupView::press(std::size_t s,std::size_t l) {
    strip(s).set_colour(divided(kButton,1.20000005f));
    Label& b=label(l);b.colour=divided(Colour{122,103,211,255},1.20000005f);b.update_colour();
}
void SetupView::release(std::size_t s,std::size_t l) {
    strip(s).set_colour(kButton);
    Label& b=label(l);b.colour=Colour{122,103,211,255};b.update_colour();
}
Point2 SetupView::help_place(std::int32_t text) const {
    switch(text) {
    case 100: case 101: return strip(0x7e4).middle();
    case 102: return quad(0xbe4).position;
    case 103: return strip(0x1274).middle();
    case 104: {const QuadStrip& s=strip(0x12f8);const float h=s.size().x*0.5f;return Point2{s.position.x+h,s.position.y};}
    default: return Point2{0.0f,0.0f};
    }
}
void SetupView::process_input(const SessionObjects& o,float dt) {
    SetupScreen& n=*o.setup;
    const std::int32_t phase=o.touch->phase;
    const Point2 key_up{0.947265625f,0.921875f},key_down{0.998046875f,0.998046875f};
    if(phase==0) {   // the touch has ended: the pressed key or button back as it was
        const std::int32_t k=pressed_;
        if(k<0)return;
        if(k<=25)quad(0x1b90+0x70*static_cast<std::size_t>(k)).set_uv(key_up,key_down);
        else if(k==28)quad(0x27d0).set_uv(Point2{0.5f,0.921875f},Point2{0.80078125f,0.998046875f});
        else if(k==27)quad(0x2760).set_uv(Point2{0.802734375f,0.921875f},Point2{0.873046875f,0.998046875f});
        else if(k==29)quad(0x2840).set_uv(Point2{0.853515625f,0.84375f},Point2{0.998046875f,0.919921875f});
        else if(k==30)release(0x2e0,0x32c);
        else if(k==31)release(0x12f8,0x1344);
        else if(k==32)release(0x868,0x8b4);
        else if(k==33)release(0x154,0x1a0);
        else if(k==34)release(0x630,0x67c);
        pressed_=-1;
        return;
    }
    const Point2 touch=o.touch->position;
    if(phase!=1)return;
    if(keyboard_ && pressed_==27) {   // the delete key held: one more every 0.1 s
        const Point2 local{touch.x,touch.y-0.853124976f};
        if(quad(0x2760).contains(local)) {
            repeat_=repeat_-dt;
            if(!(repeat_<0.0f) || n.length<=0)return;
            sounds.push_back(0);
            repeat_=0.100000001f;
            n.length-=1;
            shift_=n.length==0 || (n.name[n.length]>='A' && n.name[n.length]<='Z');
            return;
        }
    }
    if(previous_!=0)return;   // a touch's start only
    if(strip(0x25c).contains(touch)) {   // the name: the keyboard comes up
        if(!keyboard_)sounds.push_back(0);
        keyboard_=true;
        if(!n.named){n.length=0;n.named=1;blink_=0.0f;}
        return;
    }
    if(strip(0x2e0).contains(touch)) {   // Random (its sound: the session's)
        pressed_=30;press(0x2e0,0x32c);
        requests.push_back({SetupAction::RandomName,0});
        n.named=1;shift_=false;
        return;
    }
    if(!keyboard_) {
        if(strip(0x12f8).contains(touch)) {   // Edit: the class screen opens (ClassScreen::Initialise once the session validated)
            sounds.push_back(0);pressed_=31;press(0x12f8,0x1344);requests.push_back({SetupAction::Edit,0});return;
        }
        if(strip(0x868).contains(touch)){pressed_=32;press(0x868,0x8b4);requests.push_back({SetupAction::Help,0});return;}   // (its sound: the session's)
        if(strip(0x154).contains(touch)) {   // Back: the screen fades out over the main menu (its sound: the session's)
            pressed_=33;press(0x154,0x1a0);
            closing_=true;timer_=0.300000012f;
            requests.push_back({SetupAction::Back,0});
            return;
        }
    }
    if(strip(0x630).contains(touch)){sounds.push_back(0);pressed_=34;press(0x630,0x67c);mode_.show();return;}
    if(n.challenge) {
        for(int k=0;k<2;++k)if(strip(0x6b4+0x4c*static_cast<std::size_t>(k)).contains(touch)){requests.push_back({SetupAction::Mode,k});return;}
    } else {
        for(int k=0;k<4;++k)if(strip(0x3e8+0x4c*static_cast<std::size_t>(k)).contains(touch)){requests.push_back({SetupAction::Difficulty,k});return;}
    }
    if(!keyboard_) {
        for(int k=0;k<10;++k)
            if(o.classes[k].level && strip(0x8ec+0x4c*static_cast<std::size_t>(k)).contains(touch)){requests.push_back({SetupAction::Class,k});return;}
        Label& begin=label(0x2964);
        if(begin.colour.a==255 && touch.y>1.32999992f && touch.x>0.25f && touch.x<0.75f) {   // Begin
            begin.colour=Colour{180,180,0,255};begin.update_colour();
            requests.push_back({SetupAction::Start,0});
            open_=false;
        }
        return;
    }
    const Point2 local{touch.x,touch.y-0.853124976f};   // the keyboard
    for(int k=0;k<30;++k) {
        Quad& q=quad(0x1b90+0x70*static_cast<std::size_t>(k));
        if(!q.contains(local))continue;
        if(k<=25) {   // a letter (a capital after Shift)
            if(n.length<=15) {
                char c=key_label(k).text.empty()?' ':key_label(k).text[0];
                if(!shift_ && c>='A' && c<='Z')c=static_cast<char>(c-'A'+'a');
                n.name[n.length]=c;n.length+=1;shift_=false;
            }
            pressed_=k;q.set_uv(Point2{0.80078125f,0.84375f},Point2{0.8515625f,0.919921875f});
        } else if(k==28) {   // space
            if(n.length!=0 && n.length<=15){n.name[n.length]=' ';n.length+=1;shift_=false;}
            pressed_=28;q.set_uv(Point2{0.498046875f,0.84375f},Point2{0.798828125f,0.919921875f});
        } else if(k==27) {   // delete (repeats while held)
            if(n.length>0) {
                n.length-=1;
                shift_=n.length==0 || (n.name[n.length]>='A' && n.name[n.length]<='Z');
            }
            repeat_=0.5f;pressed_=27;
            q.set_uv(Point2{0.634765625f,0.765625f},Point2{0.705078125f,0.841796875f});
        } else if(k==26) {   // shift
            shift_=!shift_;
        } else if(k==29) {   // OK: the keyboard goes down
            if(n.length>0) {
                keyboard_=false;pressed_=29;
                q.set_uv(Point2{0.560546875f,0.6875f},Point2{0.705078125f,0.763671875f});
                sounds.push_back(0);
            }
            blink_=0.0f;
            return;
        }
        sounds.push_back(0);
        blink_=0.0f;
        return;
    }
}
void SetupView::render(GL& gl,const SessionObjects& o) const {
    if(class_.open() && class_.fade()>=1.0f){class_.render(gl);return;}   // the class screen covers it
    const bool challenge=o.setup->challenge!=0;
    gl.bind_texture(NoTexture);
    quad(0x4).render(gl);quad(0x74).render(gl);label(0x2964).render(gl);
    gl.bind_texture(Menus);
    for(std::size_t s:{0x154u,0x1d8u,0x25cu,0x2e0u,0x364u})strip(s).render(gl);
    if(challenge)for(std::size_t s:{0x630u,0x6b4u,0x74cu,0x700u,0x798u})strip(s).render(gl);
    else for(std::size_t s:{0x3e8u,0x434u,0x480u,0x4ccu})strip(s).render(gl);
    strip(0x7e4).render(gl);strip(0x868).render(gl);
    for(int k=0;k<10;++k){strip(0x8ec+0x4c*static_cast<std::size_t>(k)).render(gl);quad(0xbe4+0x70*static_cast<std::size_t>(k)).render(gl);}
    strip(0x1274).render(gl);strip(0x12f8).render(gl);strip(0x137c).render(gl);
    for(int k=0;k<10;++k){quad(0x16c0+0x70*static_cast<std::size_t>(k)).render(gl);strip(0x137c+0x4c*static_cast<std::size_t>(k+1)).render(gl);}
    gl.bind_texture(Tiles);quad(0x1b20).render(gl);gl.bind_texture(Menus);
    for(int j=0;j<10;++j)label(0x1044+0x38*static_cast<std::size_t>(j)).render(gl);
    label(0x224).render(gl);label(0x2a8).render(gl);label(0x32c).render(gl);
    if(challenge){label(0x5f8).render(gl);label(0x67c).render(gl);}
    else for(std::size_t l:{0x3b0u,0x518u,0x550u,0x588u,0x5c0u})label(l).render(gl);
    for(std::size_t l:{0x830u,0x8b4u,0x12c0u,0x1344u,0x1a0u})label(l).render(gl);
    gl.bind_texture(Menus);
    gl.push();
    gl.translate(0.0f,interpolate(0.853124976f,1.60000002f,slide_));
    gl.bind_texture(NoTexture);quad(0xe4).render(gl);
    gl.bind_texture(Menus);
    for(int k=0;k<30;++k)quad(0x1b90+0x70*static_cast<std::size_t>(k)).render(gl);
    for(int k=0;k<30;++k)key_label(k).render(gl);
    gl.pop();
    if(class_.open())class_.render(gl);
    else if(mode_.open())mode_.render(gl);   // (with its fade never reaching 1, the setup screen stays drawn beneath)
}
void SetupView::class_after(const SessionObjects& o,const ClassRequest& r) {
    class_.after_request(o,r);
    if(r.action==ClassAction::Select || r.action==ClassAction::Done)select_class(o);
}
}
