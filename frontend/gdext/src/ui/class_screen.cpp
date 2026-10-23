#include "class_screen.hpp"
#include "menu.hpp"
#include "setup.hpp"
#include "recovered_menu.hpp"
using namespace dungeonraid;
namespace drui {
namespace {
// The pictures the strips take (pixels of menus.png): a small slot (F), a small slot that takes a drag (E), a locked
// small slot (G), the class / race button (big), its unpressable form (button) and the empty icons (dummy).
const Point2 F0{23.0f,1.0f},F1{49.0f,27.0f},E0{104.0f,28.0f},E1{130.0f,54.0f},G0{23.0f,33.0f},G1{49.0f,59.0f};
const Point2 Big0{50.0f,1.0f},Big1{103.0f,54.0f},Button0{194.0f,1.0f},Button1{247.0f,54.0f};
const Point2 Dummy0{-51.0f,0.0f},Dummy1{0.0f,51.0f},Small0{-24.0f,0.0f},Small1{0.0f,24.0f};   // GetDummy(Small)IconCoords
constexpr Colour kBlack{0,0,0,255},kWhite{255,255,255,255};
float clampf(float v,float lo,float hi) {if(v>=hi)return hi;return v<=lo?lo:v;}                    // 0x1b73c
float interpolate(float a,float b,float t) {const float x=a*t;const float y=(1.0f-t)*b;return x+y;}  // 0x1b800
Point2 scaled(Point2 p) {return Point2{p.x*1024.0f,p.y*1024.0f};}   // a skill's 0..1 picture in the 1024-pixel tiles
void skill_pixels(std::int32_t skill,Point2& a,Point2& b) {skill_uvs(skill,a,b);a=scaled(a);b=scaled(b);}
void perk_icon(std::int32_t perk,Point2& a,Point2& b) {icon_coords(0,perk,0,a,b);}         // GetIconCoords(PerkType)
void flaw_icon(std::int32_t flaw,Point2& a,Point2& b) {icon_coords(0,flaw+10,0,a,b);}      // GetIconCoords(FlawType)
float dist_squared(Point2 a,Point2 b) {const float x=a.x-b.x,y=a.y-b.y;return x*x+y*y;}   // GLfloat2::DistSquared
bool is_replacement(const ClassProfile& c,std::int32_t skill) {   // CharacterClass::IsReplacementSkill 0x111aa8
    for(std::size_t i=0;i<c.replacement_skill_count;++i)if(c.replacement_skills[i]==skill)return true;
    return false;
}
std::int32_t replacement(const ClassProfile& c,std::int32_t k) {   // the record's replacement for base skill k (255 none)
    return c.replacement_skills && static_cast<std::size_t>(k)<c.replacement_skill_count?c.replacement_skills[k]:255;
}
std::int32_t other_skill(const ClassProfile& c,std::int32_t k) {std::int32_t s[20];dr_class_other_skills(c.class_type,s);return s[k];}
std::int32_t non_base_index(const ClassProfile& c,std::int32_t skill) {   // CharacterClass::GetNonBaseSkillIndex
    std::int32_t s[20];dr_class_other_skills(c.class_type,s);
    for(std::int32_t i=0;i<20;++i)if(s[i]==skill)return i;
    return -1;
}
Point2 middle_x(const QuadStrip& s) {const Point2 z=s.size();const float h=z.x*0.5f;return Point2{s.position.x+h,s.position.y};}
}
// ClassScreen::ClassScreen 0x10de24 (frontend/tools/trace_function.py '__ZN11ClassScreenC2EP4Game').
ClassView::ClassView(const Font* font):font_(font) {
    QuadStrip& black=s_[7];black.add_quad();black.fixed=Point2{1.0f,1.5f};black.has_fixed=true;black.update_size();
    black.set_position(Point2{0.0f,0.0f});black.set_colour(kBlack);
    QuadStrip& dim=s_[6];dim.add_quad();dim.fixed=Point2{1.0f,1.0f};dim.has_fixed=true;dim.update_size();
    dim.set_position(Point2{0.0f,0.0f});dim.set_colour(kBlack);
    const Point2 small{26.0f/320.0f,26.0f/320.0f},big{53.0f/320.0f,53.0f/320.0f};
    const float tab_w=big.x+0.0625f;
    const float a=small.x*4.0f;const float perks_w=a+0.0812499970f;
    float x;
    {const float b=tab_w*3.0f;const float c=perks_w+b;const float d=c-0.075000003f;const float e=d*-0.5f;x=e+0.5f;}
    for(int k=0;k<4;++k) {   // the tabs, their frames as wide as their pictures
        QuadStrip& s=s_[k];
        const auto add=[&](float u0,float v0,float u1,float v1,int p){s.add_quad(Point2{u0,v0},Point2{u1,v1},p,-1.0f);};
        add(1,1,11,9,2);add(11,1,12,9,1);add(12,1,22,9,2);
        s.row=1;
        add(1,9,11,63,0);add(11,9,12,63,3);add(12,9,22,63,0);
        s.row=2;
        add(1,63,11,69,2);add(11,63,12,69,1);add(12,63,22,69,2);
        const float w=k==2?perks_w:tab_w;
        s.has_fixed=true;s.fixed=Point2{w,0.25f};s.update_size();
        s.set_position(Point2{x,0.00312500005f});
        const float step=w-0.0250000004f;x=x+step;
        tab_labels_.emplace_back(font);
        Label& l=tab_labels_.back();l.space_scale=2.0f;l.scale=Point2{0.100000001f,0.100000001f};
    }
    s_[4].add_quad(Point2{1,65},Point2{11,69},2,-1.0f);s_[4].add_quad(Point2{11,65},Point2{12,69},1,-1.0f);
    s_[4].add_quad(Point2{12,65},Point2{22,69},2,-1.0f);
    {
        QuadStrip& line=s_[5];line.add_quad(Point2{24,28},Point2{25,32},1,-1.0f);line.fixed.x=1.0f;line.has_fixed=true;line.update_size();
        const float b=s_[0].position.y+s_[0].size().y;const float y=b-s_[4].size().y;
        line.set_position(Point2{0.0f,y});
    }
    {
        QuadStrip& ret=s_[10];ret.add_quad(Point2{104,1},Point2{193,27},2,-1.0f);
        const Point2 z=ret.size();
        const float b=1.0f-z.x;const float px=b-0.00937500037f;
        const float c=1.5f-z.y;const float py=c-0.00937500037f;
        ret.set_position(Point2{px,py});
        QuadStrip& help=s_[9];help.add_quad(Point2{422,285},Point2{511,311},2,-1.0f);
        help.set_position(Point2{0.00937500037f,ret.position.y});
    }
    QuadStrip& backing=s_[8];backing.add_quad(Point2{11,11},Point2{12,12},3,-1.0f);
    {
        const float y=s_[5].position.y+s_[5].fixed_size(-1,-1).y;backing.set_position(Point2{0.0f,y});
        backing.has_fixed=true;backing.fixed.x=1.0f;
        const float bottom=s_[10].position.y-0.00937500037f;backing.fixed.y=bottom-backing.position.y;
        backing.update_size();
    }
    for(int k=11;k<22;++k) {   // the tabs' slots: the class, the race, the eight perks & flaws, the skill
        const bool small_slot=static_cast<unsigned>(k-13)<=7u;
        s_[k].add_quad(small_slot?F0:Big0,small_slot?F1:Big1,2,-1.0f);
    }
    const auto slot_at=[](const QuadStrip& tab){const float x=tab.position.x+0.03125f;const float y=tab.position.y+0.0625f;return Point2{x,y};};
    s_[11].set_position(slot_at(s_[0]));s_[12].set_position(slot_at(s_[1]));s_[21].set_position(slot_at(s_[3]));
    {
        const Point2 base=slot_at(s_[2]);
        const float sy=small.y+0.00625000009f,sx=small.x+0.00625000009f;
        for(int k=13;k<21;++k) {
            const int column=k<=16?k-13:k-17,row=k<=16?0:1;
            const float a2=static_cast<float>(column)*sx;const float px=base.x+a2;
            const float b2=static_cast<float>(row)*sy;const float py=base.y+b2;
            s_[k].set_position(Point2{px,py});
        }
    }
    b_.add_quad(Dummy0,Dummy1,2,-1.0f);a_.add_quad(Dummy0,Dummy1,2,-1.0f);
    for(int k=22;k<33;++k) {   // their icons
        const bool small_icon=static_cast<unsigned>(k-24)<=7u;
        s_[k].add_quad(small_icon?Small0:Dummy0,small_icon?Small1:Dummy1,2,-1.0f);
        s_[k].align_with(s_[k-11]);
        if(k==32)s_[k].texture_size=1024;
    }
    const float bottom=s_[10].position.y-0.00937500037f;   // the buttons' rows end above Help and Return
    const auto button_grid=[&](Strips& v,int k,float& w,float& gap) {   // the class and race buttons, five a row
        v.emplace_back();QuadStrip& s=v.back();s.add_quad(Point2{248,1},Point2{301,54},2,-1.0f);
        w=s.fixed_size(-1,-1).x;
        {const float b=w*-5.0f;const float c=b+1.0f;gap=c/6.0f;}
        const float step=w+gap;
        const int column=k%5,rows=(9-k)/5+1;
        const float b=static_cast<float>(column)*step;const float px=b+gap;
        const float c=step*static_cast<float>(rows);const float py=bottom-c;
        s.set_position(Point2{px,py});
    };
    const auto icons=[](Strips& v,int first,int n,Point2 a0,Point2 a1) {   // an empty black icon over each of n strips
        for(int k=0;k<n;++k){v.emplace_back();QuadStrip& s=v.back();s.add_quad(a0,a1,2,-1.0f);s.align_with(v[static_cast<std::size_t>(first+k)]);s.set_colour(kBlack);}
    };
    // Tab 0, the class: the ten class buttons, the class panel, the level row and the text box.
    Strips& v=tabs_[0];
    float w=0.0f,gap=0.0f;
    for(int k=0;k<10;++k)button_grid(v,k,w,gap);
    icons(v,0,10,Dummy0,Dummy1);
    class_panels_=static_cast<std::int32_t>(v.size());
    const float W=gap*-2.0f+1.0f;   // (VMUL then VADD)
    const float half=gap*0.5f;
    const float top=s_[8].position.y;
    add_panel(0,W,0.360000014f,gap,half+top);
    float m;
    {
        const float a3=Small1.x-Small0.x;const float b3=a3*10.0f;const float c3=b3/320.0f;const float d3=c3+0.0562500022f;
        const float e3=W-d3;m=e3*0.25f;
    }
    {
        const float a3=Small1.y-Small0.y;const float b3=a3/320.0f;const float h2=b3+(m+m);
        const float y=v[20].position.y+v[20].size().y;
        add_panel(0,W,h2,gap,half+y);
    }
    {
        const float b3=v[21].position.y+v[21].size().y;const float c3=v[0].position.y-b3;const float h3=c3-gap;
        add_panel(0,W,h3,gap,half+b3);
    }
    {   // the class panel's lines: the class, then five names over five values
        float y=m+v[20].position.y,saved=0.0f;
        for(int k=0;k<11;++k) {
            info_.emplace_back(font);Label& l=info_.back();l.space_scale=2.0f;
            float s=0.0944999978f;
            if(k==0){s=0.119999997f;const float a3=s*0.349999994f;y=y+a3;}
            else if(k==6)y=saved;
            else {const float a3=s*0.519999981f;y=y+a3;}
            l.scale=Point2{s,s};
            l.position.x=m+v[20].position.x;l.position.y=y;
            if(k==1)saved=y;
        }
    }
    class_slots_=static_cast<std::int32_t>(v.size());
    for(int k=0;k<10;++k) {   // the level row's slots
        v.emplace_back();QuadStrip& s=v.back();s.add_quad(F0,F1,2,-1.0f);
        const float fs=s.fixed_size(-1,-1).x;s.align_with(v[21]);
        const float a3=gap+m;const float b3=fs+0.00625000009f;const float c3=static_cast<float>(k)*b3;
        s.set_position(Point2{a3+c3,s.position.y});
    }
    icons(v,class_slots_,10,Small0,Small1);
    // Tab 1, the race: the ten race buttons, the race and mortal enemy panels with their pictures, the text box.
    Strips& v2=tabs_[1];
    float w2=0.0f,gap2=0.0f;
    for(int k=0;k<10;++k)button_grid(v2,k,w2,gap2);
    icons(v2,0,10,Dummy0,Dummy1);
    race_panels_=static_cast<std::int32_t>(v2.size());
    {const float a3=w*1.35000002f;add_panel(1,W,gap+a3,gap,half+top);}
    {
        const float a3=w*1.54999995f;const float h=gap+a3;
        const float y=v2[20].position.y+v2[20].size().y;add_panel(1,W,h,gap,half+y);
    }
    {
        const float b3=v2[21].position.y+v2[21].size().y;const float c3=v2[0].position.y-b3;const float h3=c3-gap;
        add_panel(1,W,h3,gap,half+b3);
    }
    {
        const float x15=gap*1.5f;
        v2.emplace_back();v2.back().add_quad(Big0,Big1,2,-1.0f);v2.back().set_position(Point2{x15,half+v2[20].position.y});
        v2.emplace_back();v2.back().add_quad(Big0,Big1,2,-1.0f);v2.back().set_position(Point2{x15,half+v2[21].position.y});
    }
    race_icons_=static_cast<std::int32_t>(v2.size());
    v2.emplace_back();v2.back().add_quad(Dummy0,Dummy1,2,-1.0f);v2.back().align_with(v2[v2.size()-3]);v2.back().set_colour(kBlack);
    v2.emplace_back();v2.back().texture_size=1024;v2.back().add_quad(Dummy0,Dummy1,2,-1.0f);v2.back().align_with(v2[v2.size()-3]);
    v2.back().set_colour(kBlack);
    // Tab 2, perks & flaws: the twenty perks and flaws, the perk and flaw panels with their slots, the text box.
    Strips& v3=tabs_[2];
    float f3=0.0f,g3=0.0f;
    for(int k=0;k<20;++k) {
        v3.emplace_back();QuadStrip& s=v3.back();s.add_quad(G0,G1,2,-1.0f);
        f3=s.fixed_size(-1,-1).x;
        {const float b3=f3*-10.0f;const float c3=b3+1.0f;g3=c3/11.0f;}
        const float step=f3+g3;
        const int column=k%10,rows=(19-k)/10+1;
        const float b3=static_cast<float>(column)*step;const float px=b3+g3;
        const float c3=step*static_cast<float>(rows);const float py=bottom-c3;
        s.set_position(Point2{px,py});
    }
    icons(v3,0,20,Small0,Small1);
    perk_panels_=static_cast<std::int32_t>(v3.size());
    const float d=v3[0].position.y-top;
    float row_w;
    {const float b3=f3+0.0f;const float c3=b3*8.0f;const float e3=g3*6.0f;row_w=c3+e3;}
    float H;
    {const float b3=row_w*0.5f;H=b3-g3;}
    const float m2=g3*-2.0f;const float W3=m2+1.0f;
    add_panel(2,W3,H,g3,top+g3);
    {const float b3=g3+g3;const float c3=b3+top;add_panel(2,W3,H,g3,c3+H);}
    perk_text_=static_cast<std::int32_t>(v3.size());
    {
        const float b3=d-row_w;const float h=m2+b3;
        const float c3=g3*3.0f;const float e3=c3+top;const float hh=H+H;
        add_panel(2,W3,h,g3,e3+hh);
    }
    perk_slots_=static_cast<std::int32_t>(v3.size());
    for(int k=0;k<8;++k) {   // four perk slots, four flaw slots
        v3.emplace_back();QuadStrip& s=v3.back();s.add_quad(G0,G1,2,-1.0f);
        const Point2 fs=s.fixed_size(-1,-1);
        const float b3=fs.x+0.0f;const float c3=static_cast<float>(k%4)*b3;const float e3=g3+c3;
        const QuadStrip& panel=v3[static_cast<std::size_t>(k>3?perk_panels_+1:perk_panels_)];
        s.set_position(Point2{g3+g3,e3+panel.position.y});
    }
    icons(v3,perk_slots_,8,Small0,Small1);
    {
        v3.emplace_back();QuadStrip& s=v3.back();s.add_quad(Small0,Small1,2,-1.0f);
        const QuadStrip& p=v3[static_cast<std::size_t>(perk_text_)];s.align_with(p);
        const float b3=s.position.y-p.position.y;s.set_position(Point2{b3+p.position.x,s.position.y});s.set_colour(kBlack);
    }
    // Tab 3, skills: the class's twenty skills (big), the twenty others (small), the text box.
    Strips& v4=tabs_[3];
    float y_bottom=0.0f;
    for(int k=0;k<20;++k) {
        v4.emplace_back();QuadStrip& s=v4.back();s.add_quad(Big0,Big1,2,-1.0f);
        const float f4=s.fixed_size(-1,-1).x;
        const int row=k/5,column=k-row*5;
        const float b3=g3+f4;const float c3=static_cast<float>(row)*b3;const float py=(top+g3)+c3;
        float gap4;
        {const float e3=f4*-5.0f;const float h3=e3+1.0f;const float i3=m2+h3;gap4=i3*0.25f;}
        const float j3=f4+gap4;const float k3=static_cast<float>(column)*j3;const float px=g3+k3;
        s.set_position(Point2{px,py});
        y_bottom=py+f4;
    }
    float y_top=0.0f;
    for(int k=0;k<20;++k) {
        v4.emplace_back();QuadStrip& s=v4.back();s.add_quad(G0,G1,2,-1.0f);
        const float f5=s.fixed_size(-1,-1).x;
        float g5;
        {const float b3=f5*-10.0f;const float c3=b3+1.0f;g5=c3/11.0f;}
        const int rows=(19-k)/10+1;
        const float step=f5+g5;
        const float yrow=bottom-step*static_cast<float>(rows);
        if(k==0)y_top=yrow;
        const float c3=static_cast<float>(k%10)*step;const float px=c3+g5;
        s.set_position(Point2{px,yrow});
    }
    Point2 u0,u1;skill_pixels(0,u0,u1);
    for(int k=0;k<40;++k) {
        v4.emplace_back();QuadStrip& s=v4.back();s.texture_size=1024;s.add_quad(u0,u1,2,-1.0f);s.align_with(v4[static_cast<std::size_t>(k)]);
        if(k>=20)s.quads[0].scale=Point2{0.5f,0.5f};
        s.set_colour(kBlack);
    }
    {
        const float y=g3+y_bottom;const float b3=y_top-g3;const float h=b3-y;
        add_panel(3,W3,h,g3,y);
    }
    skill_panel_=static_cast<std::int32_t>(v4.size())-1;
    {
        v4.emplace_back();QuadStrip& s=v4.back();s.texture_size=1024;s.add_quad(u0,u1,2,-1.0f);
        const QuadStrip& p=v4[static_cast<std::size_t>(skill_panel_)];s.align_with(p);
        const float b3=s.position.y-p.position.y;s.set_position(Point2{b3+p.position.x,s.position.y});s.set_colour(kBlack);
    }
    // Each tab's colour: its tab and slots, and every strip of its list (its black icons white).
    const Colour colours[4]={Colour{150,150,255,255},Colour{200,200,150,255},Colour{255,150,230,255},Colour{50,200,200,255}};
    for(int t=0;t<4;++t) {
        s_[t].set_colour(colours[t]);
        if(t==0)s_[11].set_colour(colours[0]);
        if(t==1)s_[12].set_colour(colours[1]);
        if(t==2)for(int k=13;k<21;++k)s_[k].set_colour(colours[2]);
        if(t==3)s_[21].set_colour(colours[3]);
        for(QuadStrip& s:tabs_[t]) {
            const bool icon=!s.quads.empty() && s.quads[0].v[0].colour[0]==0;
            s.set_colour(icon?kWhite:colours[t]);
        }
    }
}
void ClassView::add_panel(std::int32_t tab,float w,float h,float x,float y) {
    Strips& v=tabs_[tab];v.emplace_back();QuadStrip& s=v.back();
    const auto add=[&](float u0,float v0,float u1,float v1,int p){s.add_quad(Point2{u0,v0},Point2{u1,v1},p,-1.0f);};
    add(50,1,55,6,2);add(55,1,98,6,1);add(98,1,103,6,2);
    s.row++;
    add(50,6,55,49,0);add(55,6,98,49,3);add(98,6,103,49,0);
    s.row++;
    add(50,49,55,54,2);add(55,49,98,54,1);add(98,49,103,54,2);
    s.has_fixed=true;s.fixed=Point2{w,h};s.update_size();
    s.set_position(Point2{x,y});
}
void ClassView::initialise(const Texts& t,const SessionObjects& o) {
    texts_=&t;
    open_=true;touch_=1;pressed_=-1;closing_=false;back_=false;fade_=0.0f;
    const char* names[5]={"class.games","class.kills","class.normal","class.hard","class.harder"};
    for(int k=0;k<5;++k)info_[static_cast<std::size_t>(k+1)].set_text(t.get(names[k]).c_str());
    for(int k=0;k<4;++k)tab_labels_[static_cast<std::size_t>(k)].set_text(t.get("class.tab",k).c_str());
    for(int k=0;k<4;++k) {
        Label& l=tab_labels_[static_cast<std::size_t>(k)];const QuadStrip& s=s_[k];
        const Point2 z=s.size();
        l.position.y=s.position.y+0.0500000007f;
        const float a=z.x*0.5f;const float b=s.position.x+a;
        const float c=l.width*l.scale.x;const float d=c*-0.5f;l.position.x=b+d;
    }
    Point2 a,b;
    for(int k=0;k<10;++k) {
        const ClassProfile& c=o.classes[k];
        if(!c.level)continue;
        icon_coords(0,k,-1,a,b);tabs_[0][static_cast<std::size_t>(10+k)].set_uv(a,b);
        tabs_[0][static_cast<std::size_t>(k)].set_uv(Button0,Button1);
        set_class_level(c.level,k,k==0?s_[11]:tabs_[0][static_cast<std::size_t>(k)]);
    }
    for(int k=0;k<10;++k) {
        if(!dr_race_unlocked(o.classes,k))continue;
        icon_coords(1,k,-1,a,b);tabs_[1][static_cast<std::size_t>(10+k)].set_uv(a,b);
        tabs_[1][static_cast<std::size_t>(k)].set_uv(Button0,Button1);
    }
    for(int k=0;k<10;++k) {
        if(!dr_perk_unlocked(o.classes,k))continue;
        perk_icon(k,a,b);tabs_[2][static_cast<std::size_t>(20+k)].set_uv(a,b);
        flaw_icon(k,a,b);tabs_[2][static_cast<std::size_t>(30+k)].set_uv(a,b);
    }
    update_class(o);
    select_tab(o,0);
    set_alpha(0);
}
void ClassView::select_tab(const SessionObjects& o,std::int32_t tab) {
    tab_=tab;
    QuadStrip& line=s_[4];line.fixed.x=s_[tab].size().x;line.has_fixed=true;line.update_size();
    line.set_position(Point2{s_[tab].position.x,s_[5].position.y});
    skill_icon_=false;text_count_=0;perk_icon_=false;
    // (CharacterClass::Validate of the current record here is the session's: dr_session_class_open / class_tab)
    update_perks(o);
    if(tab!=2)text_count_=0;
    const ClassProfile& c=record(o);
    const Texts& t=*texts_;
    const std::string& name=t.get("class.name",c.class_type);
    Colour colour{255,255,255,255};
    switch(tab) {
    case 0: show_text(nullptr,t.get("class.text.class"),false);colour=Colour{150,150,255,255};break;
    case 1:
        if(c.class_type==0)show_text(nullptr,t.get("class.text.race0"),false);
        else if(c.level<=4)show_text(nullptr,printf_string(t.get("class.text.race_locked").c_str(),name.c_str(),t.get("race.name",c.race).c_str()),false);
        else show_text(nullptr,t.get("class.text.race"),false);
        colour=Colour{200,200,150,255};break;
    case 2:
        if(c.class_type==0)show_text(nullptr,t.get("class.text.perks0"),false);
        else if(perk_unlocked(c,1))show_text(nullptr,printf_string(t.get("class.text.perks").c_str(),name.c_str()),false);
        else show_text(nullptr,printf_string(t.get("class.text.perks_locked").c_str(),name.c_str()),false);
        colour=Colour{255,150,230,255};break;
    case 3:
        if(c.class_type==0)show_text(nullptr,t.get("class.text.skills0"),false);
        else if(!dr_class_replacements_allowed(&c))show_text(nullptr,printf_string(t.get("class.text.skills_locked").c_str(),name.c_str()),false);
        else show_text(nullptr,printf_string(t.get("class.text.skills").c_str(),name.c_str(),static_cast<int>(dr_class_replacements_allowed(&c)),
                                             static_cast<int>(dr_replacement_skill_count(&c))),false);
        colour=Colour{50,200,200,255};break;
    default: break;
    }
    line.set_colour(colour);s_[8].set_colour(colour);s_[5].set_colour(colour);a_.set_colour(colour);
}
void ClassView::set_alpha(std::uint32_t value) {
    const auto a=static_cast<std::uint8_t>(value);
    for(QuadStrip& s:s_)s.set_alpha(a);
    s_[6].set_alpha(static_cast<std::uint8_t>(value/3u));
    const auto labels=[a](std::vector<Label>& v,std::size_t n){for(std::size_t i=0;i<n && i<v.size();++i){v[i].colour.a=a;v[i].update_colour();}};
    labels(text_,text_.size());labels(levels_,levels_.size());labels(info_,info_.size());
    for(Strips& v:tabs_)for(QuadStrip& s:v)s.set_alpha(a);
    labels(tab_labels_,tab_labels_.size());
    labels(race_,static_cast<std::size_t>(race_count_));
}
void ClassView::render_tab(GL& gl,std::int32_t tab) const {
    gl.bind_texture(Menus);
    s_[tab].render(gl);
    switch(tab) {
    case 0: s_[11].render(gl);s_[22].render(gl);break;
    case 1: s_[12].render(gl);s_[23].render(gl);break;
    case 2:
        s_[13].render(gl);s_[24].render(gl);
        for(int k=14;k<21;++k){s_[k].render(gl);s_[k+11].render(gl);}
        break;
    case 3: s_[21].render(gl);gl.bind_texture(Tiles);s_[32].render(gl);break;
    default: break;
    }
    if(tab==0 && level_first_<levels_.size())levels_[level_first_].render(gl);   // the current class's level
    tab_labels_[static_cast<std::size_t>(tab)].render(gl);
}
void ClassView::render(GL& gl) const {
    gl.bind_texture(NoTexture);
    s_[7].render(gl);
    for(int k=0;k<4;++k)if(k!=tab_)render_tab(gl,k);
    gl.bind_texture(NoTexture);
    s_[6].render(gl);
    render_tab(gl,tab_);
    gl.bind_texture(Menus);
    s_[5].render(gl);s_[4].render(gl);s_[8].render(gl);s_[10].render(gl);s_[9].render(gl);
    const Strips& v=tabs_[tab_];
    bool stopped=false;
    for(std::size_t k=0;k<v.size();++k) {
        if(tab_==3) {
            if(k==40)gl.bind_texture(Tiles);
            else if(static_cast<std::int32_t>(k)==skill_panel_)gl.bind_texture(Menus);
            else if(static_cast<std::int32_t>(k)==skill_panel_+1) {
                if(skill_icon_)gl.bind_texture(Tiles);
                else {stopped=true;break;}
            }
        } else if(tab_==2) {
            if(!perk_icon_ && k==v.size()-1){stopped=true;break;}
        } else if(tab_==1) {
            if(static_cast<std::int32_t>(k)==race_icons_+1)gl.bind_texture(Tiles);
        }
        v[k].render(gl);
    }
    const std::size_t first=level_first_;
    const std::size_t end=(tab_==0 && !stopped)?levels_.size():1;
    for(std::size_t i=first;i<end && i<levels_.size();++i)levels_[i].render(gl);
    for(std::int32_t i=0;i<text_count_ && static_cast<std::size_t>(i)<text_.size();++i)text_[static_cast<std::size_t>(i)].render(gl);
    if(tab_==1)for(std::int32_t i=0;i<race_count_;++i)race_[static_cast<std::size_t>(i)].render(gl);
    else if(tab_==0)for(const Label& l:info_)l.render(gl);
    if(dragged_perk_>=0 || dragged_skill_>=0) {
        gl.bind_texture(Menus);a_.render(gl);
        if(dragged_skill_>=0)gl.bind_texture(Tiles);
        b_.render(gl);
    }
}
void ClassView::set_text(std::int32_t i,const std::string& text,std::vector<Label>& lines,std::int32_t& count) {
    const std::int32_t n=i+1;if(n>=count)count=n;
    while(lines.size()<=static_cast<std::size_t>(i)){lines.emplace_back(font_);lines.back().space_scale=2.0f;}
    Label& l=lines[static_cast<std::size_t>(i)];l.scale=Point2{0.0900000036f,0.0900000036f};l.set_text(text.c_str());
}
void ClassView::set_text(const std::string& text,float x,float y,float width,float scale,std::vector<Label>& lines,
                         std::int32_t& count,Colour colour) {
    if(y<0.0f){const float a=scale*0.150000006f;y=a+lines[static_cast<std::size_t>(count-1)].position.y;}   // under the last line
    const std::vector<std::string> split=split_lines(*font_,text,scale,width);
    const float first=scale*0.349999994f,next=scale*0.5f;
    const std::int32_t start=count;
    for(std::size_t j=0;j<split.size();++j) {
        y=y+(j==0?first:next);
        const std::int32_t i=start+static_cast<std::int32_t>(j);
        set_text(i,split[j],lines,count);
        Label& l=lines[static_cast<std::size_t>(i)];l.scale=Point2{scale,scale};l.position=Point2{x,y};
        l.colour=colour;l.update_colour();
    }
}
void ClassView::set_class_level(std::int32_t level,std::int32_t i,const QuadStrip& strip) {
    while(levels_.size()<=static_cast<std::size_t>(i)){levels_.emplace_back(font_);levels_.back().scale=Point2{0.0799999982f,0.0799999982f};}
    Label& l=levels_[static_cast<std::size_t>(i)];l.set_text(printf_string("%d",level).c_str());
    const Point2 z=strip.size();
    const float a=strip.position.x+z.x;const float b=l.width*l.scale.x;const float c=b+0.00937500037f;l.position.x=a-c;
    const float d=strip.position.y+z.y;l.position.y=d-0.00937500037f;
}
void ClassView::grab_icon(const SessionObjects& o,std::int32_t tab,std::int32_t from,std::int32_t to,std::int32_t type) {
    (void)from;   // (the original works out its offset too and drops it)
    const QuadStrip& s=tabs_[tab][static_cast<std::size_t>(to)];const Point2 t=o.touch->position;
    const Point2 off{s.position.x-t.x,s.position.y-t.y};
    grab_=off;grab_icon_=off;
    Point2 a,b;
    if(tab==3) {
        grab_.x=off.x-0.00625000009f;grab_.y=off.y-0.00625000009f;
        skill_pixels(other_skill(record(o),type),a,b);
        b_.texture_size=1024;b_.set_uv(a,b);b_.fixed=Point2{0.0f,0.0f};b_.has_fixed=true;b_.update_size();b_.quads[0].scale=Point2{0.5f,0.5f};
        a_.set_uv(Button0,Button1);a_.has_fixed=true;a_.fixed=Point2{0.0f,0.0f};a_.update_size();a_.quads[0].scale=Point2{0.5f,0.5f};
    } else {
        if(type<=9)perk_icon(type,a,b);else flaw_icon(type-10,a,b);
        b_.texture_size=512;b_.set_uv(a,b);b_.fixed=Point2{0.0f,0.0f};b_.has_fixed=true;b_.update_size();b_.quads[0].scale=Point2{1.0f,1.0f};
        a_.set_uv(E0,E1);a_.has_fixed=true;a_.fixed=Point2{0.0f,0.0f};a_.update_size();a_.quads[0].scale=Point2{1.0f,1.0f};
    }
    a_.set_position(Point2{t.x+grab_.x,t.y+grab_.y});
    b_.set_position(Point2{t.x+grab_icon_.x,t.y+grab_icon_.y});
}
void ClassView::update_perks(const SessionObjects& o) {
    const ClassProfile& c=record(o);const Texts& t=*texts_;
    Strips& v=tabs_[2];
    const auto at=[&](std::int32_t i)->QuadStrip&{return v[static_cast<std::size_t>(i)];};
    const QuadStrip& first=at(perk_slots_);
    float tx;{const float a=first.position.x+first.size().x;tx=a+at(perk_panels_).position.x;}
    float ty;{const float a=first.size().y+0.0315000005f;ty=a*0.5f;}
    Point2 a,b;
    for(int k=0;k<4;++k) {
        if(c.class_type!=0 && perk_unlocked(c,k)) {
            s_[13+k].set_uv(F0,F1);s_[17+k].set_uv(F0,F1);
            const std::int32_t perk=c.perks[k];
            if(perk!=255) {
                perk_icon(perk,a,b);s_[24+k].set_uv(a,b);
                if(k==0)at(perk_slots_).set_uv(F0,F1);else at(perk_slots_+k).set_uv(E0,E1);
                at(perk_slots_+8+k).set_uv(a,b);
                set_text(k,t.get("perk.desc",perk),text_,text_count_);
                Label& l=text_[static_cast<std::size_t>(k)];l.position.x=tx;l.position.y=ty+at(perk_slots_+k).position.y;
            } else {
                at(perk_slots_+k).set_uv(F0,F1);at(perk_slots_+8+k).set_uv(Small0,Small1);s_[24+k].set_uv(Small0,Small1);
                set_text(k,"",text_,text_count_);
            }
            const std::int32_t flaw=c.flaws[k];
            if(flaw!=255) {
                flaw_icon(flaw,a,b);s_[28+k].set_uv(a,b);
                if(k==0)at(perk_slots_+4).set_uv(F0,F1);else at(perk_slots_+4+k).set_uv(E0,E1);
                at(perk_slots_+12+k).set_uv(a,b);
                set_text(4+k,t.get("flaw.desc",flaw),text_,text_count_);
                Label& l=text_[static_cast<std::size_t>(4+k)];l.position.x=tx;l.position.y=ty+at(perk_slots_+4+k).position.y;
            } else {
                at(perk_slots_+4+k).set_uv(F0,F1);at(perk_slots_+12+k).set_uv(Small0,Small1);s_[28+k].set_uv(Small0,Small1);
                set_text(4+k,"",text_,text_count_);
            }
        } else {   // a slot the class has not opened yet
            s_[13+k].set_uv(G0,G1);s_[17+k].set_uv(G0,G1);s_[24+k].set_uv(Small0,Small1);s_[28+k].set_uv(Small0,Small1);
            at(perk_slots_+k).set_uv(G0,G1);at(perk_slots_+4+k).set_uv(G0,G1);
            at(perk_slots_+8+k).set_uv(Small0,Small1);at(perk_slots_+12+k).set_uv(Small0,Small1);
            set_text(k,"",text_,text_count_);set_text(4+k,"",text_,text_count_);
        }
    }
    for(int j=0;j<10;++j) {   // what can be dragged in: unlocked perks and flaws, once the class's slot 1 is open
        if(!dr_perk_unlocked(o.classes,j)){draggable_[j]=false;draggable_[10+j]=false;continue;}
        if(c.class_type!=0 && perk_unlocked(c,1)) {
            draggable_[j]=true;draggable_[10+j]=true;at(j).set_uv(E0,E1);at(10+j).set_uv(E0,E1);
        } else {at(j).set_uv(F0,F1);at(10+j).set_uv(F0,F1);draggable_[j]=false;draggable_[10+j]=false;}
    }
    for(int i=0;i<4;++i) {   // not those the class has
        if(c.perks[i]!=255){at(c.perks[i]).set_uv(F0,F1);draggable_[c.perks[i]]=false;}
        if(c.flaws[i]!=255){at(c.flaws[i]+10).set_uv(F0,F1);draggable_[10+c.flaws[i]]=false;}
    }
    if(dragged_perk_>=0){at(dragged_perk_).set_uv(F0,F1);draggable_[dragged_perk_]=false;}
}
void ClassView::show_race(std::int32_t race) {
    const Texts& t=*texts_;Strips& v=tabs_[1];
    Point2 a,b;
    icon_coords(1,race,-1,a,b);v[static_cast<std::size_t>(race_icons_)].set_uv(a,b);
    const std::int32_t enemy=std::atoi(t.get("race.enemy",race).c_str());   // CharacterClass::GetMortalEnemyType
    enemy_uv(enemy,a,b);v[static_cast<std::size_t>(race_icons_+1)].set_uv(scaled(a),scaled(b));
    const QuadStrip& icon=v[static_cast<std::size_t>(race_icons_)];const QuadStrip& panel=v[static_cast<std::size_t>(race_panels_)];
    const float inset=icon.position.x-panel.position.x;
    float tx;{const float c=icon.position.x+icon.size().x;tx=inset+c;}
    const float ty=icon.position.y;
    float width;{const float c=panel.position.x+panel.size().x;const float e=c-tx;width=e-inset;}
    race_count_=0;
    set_text(t.get("race.name",race),tx,ty,width,0.0949999988f,race_,race_count_,kWhite);
    set_text(printf_string(t.get("class.racial").c_str(),t.get("race.bonusname",race).c_str()),tx,-1.0f,width,0.0949999988f,race_,race_count_,kWhite);
    set_text(t.get("race.bonus",race),tx,-1.0f,width,0.0850000009f,race_,race_count_,kWhite);
    const QuadStrip& foe=v[static_cast<std::size_t>(race_icons_+1)];
    float tx2;{const float c=foe.position.x+foe.size().x;tx2=inset+c;}
    set_text(printf_string(t.get("class.mortal").c_str(),t.get("enemy.name",enemy).c_str()),tx2,foe.position.y,width,0.0949999988f,
             race_,race_count_,kWhite);
    if(race==0)set_text(t.get("race.mortaldesc",0),tx2,-1.0f,width,0.0850000009f,race_,race_count_,kWhite);
    else {
        set_text(t.get("enemy.desc",enemy),tx2,-1.0f,width,0.0850000009f,race_,race_count_,kWhite);
        set_text(t.get("race.mortaldesc",race),tx2,-1.0f,width,0.0850000009f,race_,race_count_,Colour{255,0,0,255});
    }
}
void ClassView::update_race(const SessionObjects& o) {
    const ClassProfile& c=record(o);Strips& v=tabs_[1];
    for(int k=0;k<10;++k) {
        if(!dr_race_unlocked(o.classes,k))continue;
        if(dr_class_can_choose_race(&c) && c.race!=k)v[static_cast<std::size_t>(k)].set_uv(Button0,Button1);
        else v[static_cast<std::size_t>(k)].set_uv(Big0,Big1);
    }
    Point2 a,b;icon_coords(1,c.race,-1,a,b);s_[23].set_uv(a,b);
    show_race(c.race);
}
void ClassView::show_text(const char* title,const std::string& text,bool icon) {
    bool centre=false;float x=0.0f,width=0.0f,y=0.0f;std::int32_t start=0;
    const auto half_down=[](const QuadStrip& p){const float h=p.size().y*0.5f;return p.position.y+h;};
    switch(tab_) {
    case 0: case 1: {
        const Strips& v=tabs_[tab_];
        const float inset=tab_==0?v[static_cast<std::size_t>(class_slots_)].position.x-v[static_cast<std::size_t>(class_panels_+1)].position.x
                                 :v[static_cast<std::size_t>(race_icons_)].position.x-v[static_cast<std::size_t>(race_panels_)].position.x;
        centre=tab_==0?title==nullptr:true;
        const QuadStrip& p=v[static_cast<std::size_t>((tab_==0?class_panels_:race_panels_)+2)];
        x=inset+p.position.x;
        {const float a=p.position.x+p.size().x;const float b=a-inset;width=b-x;}
        y=half_down(p);
        break;
    }
    case 2: case 3: {
        const Strips& v=tabs_[tab_];
        const QuadStrip& back=v.back();
        const QuadStrip& p=v[static_cast<std::size_t>(tab_==2?perk_text_:skill_panel_)];
        float inset;
        if(tab_==2) {
            perk_icon_=icon;
            if(icon){const float a=back.position.x+back.size().x;const float b=back.position.y-p.position.y;x=a+b;}
            else {centre=true;x=p.position.x+p.position.x;}
            inset=p.position.x;
            start=8;
        } else {
            skill_icon_=icon;
            inset=back.position.y-p.position.y;
            if(icon){const float a=back.position.x+back.size().x;x=a+inset;}
            else {centre=true;inset=inset+0.00937500037f;x=inset+p.position.x;}
        }
        {const float a=p.position.x+p.size().x;const float b=a-inset;width=b-x;}
        y=half_down(p);
        break;
    }
    default: break;
    }
    const std::vector<std::string> lines=split_lines(*font_,text,0.0900000036f,width);
    float h;{const float n=static_cast<float>(static_cast<std::uint32_t>(lines.size()));const float a=n*0.5f;h=a*0.0900000036f;}
    float ty;
    const std::int32_t extra=title?1:0;
    if(title){const float a=h+0.0599999987f;const float b=a*-0.5f;const float c=b+y;ty=c-0.0120000010f;}
    else {const float a=h*-0.5f;const float b=a+y;ty=b-0.00900000054f;}
    text_count_=start+static_cast<std::int32_t>(lines.size())+extra;
    for(std::int32_t i=start;i<text_count_;++i) {
        const bool heading=title && i==start;
        const float s=heading?0.119999997f:0.0900000036f;
        const std::string& txt=heading?std::string(title):lines[static_cast<std::size_t>((i-start)-extra)];
        const float a=s*0.5f;ty=ty+a;
        set_text(i,txt,text_,text_count_);
        Label& l=text_[static_cast<std::size_t>(i)];l.scale=Point2{s,s};
        float px=x;
        if(centre){const float w=l.width*l.scale.x;const float b=width-w;const float c=b*0.5f;px=c+x;}
        l.position=Point2{px,ty};
    }
}
void ClassView::show_skill_text(std::int32_t skill) {
    const Texts& t=*texts_;
    Point2 a,b;skill_pixels(skill,a,b);tabs_[3].back().set_uv(a,b);
    const std::int32_t cooldown=dr_skill_base_cooldown(skill);
    const std::string title=cooldown>0?printf_string(t.get("class.cooldown").c_str(),t.get("skill.name",skill).c_str(),cooldown)
                                      :t.get("skill.name",skill);
    show_text(title.c_str(),t.get("skill.desc",skill),true);
}
void ClassView::show_flaw_text(std::int32_t flaw) {
    Point2 a,b;flaw_icon(flaw,a,b);tabs_[2].back().set_uv(a,b);
    show_text(texts_->get("flaw.name",flaw).c_str(),texts_->get("flaw.desc",flaw),true);
}
void ClassView::show_perk_text(std::int32_t perk) {
    Point2 a,b;perk_icon(perk,a,b);tabs_[2].back().set_uv(a,b);
    show_text(texts_->get("perk.name",perk).c_str(),texts_->get("perk.desc",perk),true);
}
void ClassView::update_class(const SessionObjects& o) {
    const ClassProfile& c=record(o);const Texts& t=*texts_;
    Strips& v=tabs_[0];
    const auto at=[&](std::int32_t i)->QuadStrip&{return v[static_cast<std::size_t>(i)];};
    for(int k=0;k<10;++k)if(o.classes[k].level)at(k).set_uv(c.class_type==k?Big0:Button0,c.class_type==k?Big1:Button1);
    Point2 a,b;icon_coords(0,c.class_type,-1,a,b);s_[22].set_uv(a,b);
    for(int k=0;k<10;++k) {   // the level row
        if(k!=0 && c.class_type==0){at(class_slots_+k).set_uv(G0,G1);at(class_slots_+10+k).set_uv(Small0,Small1);continue;}
        if(c.level>k)at(class_slots_+k).set_uv(E0,E1);else at(class_slots_+k).set_uv(F0,F1);
        const float u=static_cast<float>(26*k);
        at(class_slots_+10+k).set_uv(Point2{u,196.0f},Point2{u+26.0f,222.0f});
    }
    level_first_=c.class_type==0?1:0;
    set_class_level(c.level,0,s_[11]);
    update_race(o);update_perks(o);update_abilities(o);
    show_text(nullptr,t.get("class.apart"),false);
    info_[0].set_text(printf_string(t.get("class.title").c_str(),t.get("class.name",c.class_type).c_str(),static_cast<int>(c.level)).c_str());
    const std::uint32_t values[5]={c.games_played,c.enemies_killed,c.normal_score,c.hard_score,c.harder_score};
    for(int i=0;i<5;++i)info_[static_cast<std::size_t>(6+i)].set_text(printf_string("%d",static_cast<int>(values[i])).c_str());
    const float inset=at(class_slots_).position.x-at(class_panels_+2).position.x;
    for(int i=6;i<11;++i) {   // the values right-aligned in the class panel
        Label& l=info_[static_cast<std::size_t>(i)];const QuadStrip& p=at(class_panels_);
        const float e=p.position.x+p.size().x;const float f=e-inset;const float w=l.width*l.scale.x;l.position.x=f-w;
    }
}
void ClassView::update_abilities(const SessionObjects& o) {
    const ClassProfile& c=record(o);
    Strips& v=tabs_[3];
    const auto at=[&](std::int32_t i)->QuadStrip&{return v[static_cast<std::size_t>(i)];};
    Point2 a,b;
    if(c.class_type==0){skill_pixels(7,a,b);s_[32].set_uv(a,b);}
    for(int k=0;k<20;++k) {   // the class's skills (a replacement on a button that shows it)
        skill_uvs(dr_class_base_skills[c.class_type][k],a,b);
        if(k==0 && c.class_type!=0)s_[32].set_uv(scaled(a),scaled(b));
        else {
            const std::int32_t r=replacement(c,k);
            if(r!=255){at(k).set_uv(Button0,Button1);skill_uvs(r,a,b);}
            else at(k).set_uv(Big0,Big1);
        }
        at(40+k).set_uv(scaled(a),scaled(b));
    }
    for(int k=0;k<20;++k) {   // the others: those that can be dragged onto the class's
        const std::int32_t s=other_skill(c,k);
        skill_draggable_[k]=false;
        if(dr_skill_unlocked(o.classes,s)) {
            skill_pixels(s,a,b);at(60+k).set_uv(a,b);
            if(dr_class_replacements_allowed(&c) && !is_replacement(c,s) && dragged_skill_!=k && c.class_type!=0) {
                at(20+k).set_uv(E0,E1);skill_draggable_[k]=true;
            } else at(20+k).set_uv(F0,F1);
        } else {at(60+k).set_uv(Point2{0.0f,0.0f},Point2{0.0f,0.0f});at(20+k).set_uv(G0,G1);}
    }
}
HelpPlace ClassView::help_place(std::int32_t text) const {
    const auto t0=[this](std::int32_t i)->const QuadStrip&{return tabs_[0][static_cast<std::size_t>(i)];};
    const auto t1=[this](std::int32_t i)->const QuadStrip&{return tabs_[1][static_cast<std::size_t>(i)];};
    const auto t2=[this](std::int32_t i)->const QuadStrip&{return tabs_[2][static_cast<std::size_t>(i)];};
    const auto t3=[this](std::int32_t i)->const QuadStrip&{return tabs_[3][static_cast<std::size_t>(i)];};
    const auto below=[](const QuadStrip& s){const Point2 m=middle_x(s);const float y=s.position.y+s.size().y;return HelpPlace{Point2{m.x,y},0.0f};};
    const auto under=[](const QuadStrip& s){const Point2 m=middle_x(s);const float y=s.position.y+s.size().y;return HelpPlace{Point2{m.x,y+0.00999999978f},0.0f};};
    const auto centre=[](const QuadStrip& s){const Point2 m=middle_x(s);const float h=s.size().y*0.5f;return HelpPlace{Point2{m.x,s.position.y+h},0.0f};};
    switch(text) {
    case 105: return below(s_[0]);
    case 106: return under(t0(class_panels_+2));
    case 107: {const HelpPlace p=centre(t0(class_panels_+2));return HelpPlace{Point2{middle_x(t0(class_panels_+1)).x,p.at.y},t0(class_panels_+2).size().y};}
    case 108: return below(s_[1]);
    case 109: return HelpPlace{middle_x(t0(0)),0.0f};
    case 110: return below(s_[1]);
    case 111: return below(t1(race_panels_));
    case 112: {HelpPlace p=centre(t1(race_panels_+1));p.size=t1(race_panels_+1).size().y*0.5f;return p;}
    case 113: return under(t1(race_panels_+2));
    case 114: return below(s_[2]);
    case 115: return centre(t2(perk_panels_));
    case 116: return centre(t2(perk_panels_+1));
    case 117: return under(t2(perk_text_));
    case 118: return below(s_[3]);
    case 119: case 122: return HelpPlace{Point2{0.5f,0.5f},0.0f};
    case 120: return under(t3(skill_panel_));
    case 121: return below(t3(0));
    default: return HelpPlace{Point2{0.0f,0.0f},0.0f};
    }
}
void ClassView::process(const SessionObjects& o,float dt) {
    if(fade_<1.0f || closing_) {   // fading in, or out after Return (then the screen closes)
        const float rate=closing_?-5.0f:5.0f;const float a=dt*rate;fade_=fade_+a;
        if(fade_<0.0f)open_=false;
        fade_=clampf(fade_,0.0f,1.0f);
        const float b=fade_*255.0f;set_alpha(static_cast<std::uint32_t>(b));
        return;
    }
    const TouchState& touch=*o.touch;
    if(touch_!=0) {
        if(touch_==1 && touch.phase==0){release(o);return;}
        if(touch.phase==1)drag(o);
        return;
    }
    if(touch.phase!=1)return;
    touch_=1;
    const Point2 p=touch.position;
    const Texts& t=*texts_;
    const ClassProfile& c=record(o);
    const auto click=[this]{if(sounds)sounds->push_back(0);};   // Game::QueueSound(0)
    if(s_[10].contains(p)){back_=true;s_[10].set_alpha(150);click();return;}   // Return
    if(s_[9].contains(p)){help_=true;s_[9].set_alpha(150);click();return;}     // Help
    for(int k=0;k<4;++k) {   // another tab (Game::SerialiseClasses)
        if(k==tab_ || !s_[k].contains(p))continue;
        click();select_tab(o,k);requests.push_back({ClassAction::Tab,k,0,false});
        return;
    }
    switch(tab_) {
    case 0: {
        Strips& v=tabs_[0];
        for(int k=0;k<10;++k) {   // a class button: pressed (Game::SetCurrentClass when let go on it)
            if(!v[static_cast<std::size_t>(k)].contains(p))continue;
            if(!o.classes[k].level)return;
            v[static_cast<std::size_t>(k)].set_alpha(150);pressed_=k;click();return;
        }
        for(int k=0;k<10;++k) {   // a level slot: what that level brings
            if(!v[static_cast<std::size_t>(class_slots_+k)].contains(p))continue;
            if(c.class_type!=0 || k==0) {
                const std::string title=printf_string(t.get("class.level").c_str(),k+1);
                show_text(title.c_str(),t.get("class.leveldesc."+std::to_string(c.class_type),k+1),false);
            } else show_text(t.get("class.adventurer").c_str(),t.get("class.adventurer_levels"),false);
            click();return;
        }
        return;
    }
    case 1: {
        Strips& v=tabs_[1];
        for(int k=0;k<10;++k) {   // a race: pressed (the class's race when let go on it), or only shown
            if(!v[static_cast<std::size_t>(k)].contains(p))continue;
            if(!dr_race_unlocked(o.classes,k))return;
            if(dr_class_can_choose_race(&c)){v[static_cast<std::size_t>(k)].set_alpha(150);pressed_=k;}
            else show_race(k);
            click();return;
        }
        if(v[static_cast<std::size_t>(race_panels_)].contains(p)){click();show_text(nullptr,t.get("class.racial_help"),false);return;}
        if(v[static_cast<std::size_t>(race_panels_+1)].contains(p)){click();show_text(nullptr,t.get("class.mortal_help"),false);return;}
        return;
    }
    case 2: {
        Strips& v=tabs_[2];
        for(int k=0;k<20;++k) {   // a perk or flaw: picked up when it can be dragged in, and described
            if(!v[static_cast<std::size_t>(k)].contains(p))continue;
            if(draggable_[k]){click();dragged_perk_=k;grab_icon(o,2,k,k+20,k);update_perks(o);}
            const std::int32_t q=k%10;
            if(!dr_perk_unlocked(o.classes,q))return;
            click();
            if(k<=9)show_perk_text(k);else show_flaw_text(q);
            return;
        }
        for(int k=0;k<8;++k) {   // one of the class's: described (the fixed first one) or taken out to drag
            if(!v[static_cast<std::size_t>(perk_slots_+k)].contains(p))continue;
            const std::int32_t i=k&3;
            if(k<=3?c.perks[k]==255:c.flaws[i]==255)return;
            if(i==0){click();if(k<=3)show_perk_text(c.perks[0]);else show_flaw_text(c.flaws[0]);continue;}
            if(k<=3){dragged_perk_=c.perks[k];show_perk_text(dragged_perk_);requests.push_back({ClassAction::Perk,k,255,true});}
            else {dragged_perk_=c.flaws[i]+10;show_flaw_text(c.flaws[i]);requests.push_back({ClassAction::Flaw,i,255,true});}
            click();
            grab_icon(o,2,perk_slots_+k,perk_slots_+8+k,dragged_perk_);   // (UpdatePerks once the session took it out)
            return;
        }
        return;
    }
    case 3: {
        Strips& v=tabs_[3];
        for(int k=0;k<20;++k) {   // another skill: picked up when it can replace one, and described
            if(!v[static_cast<std::size_t>(20+k)].contains(p))continue;
            if(skill_draggable_[k]){click();dragged_skill_=k;grab_icon(o,3,20+k,60+k,k);update_abilities(o);}
            const std::int32_t s=other_skill(c,k);
            if(!dr_skill_unlocked(o.classes,s))return;
            click();
            show_skill_text(s);
            return;
        }
        for(int k=0;k<20;++k) {   // one of the class's: a replacement taken out to drag, else described
            if(!v[static_cast<std::size_t>(k)].contains(p))continue;
            const std::int32_t r=replacement(c,k);
            click();
            if(r!=255) {
                dragged_skill_=non_base_index(c,r);
                requests.push_back({ClassAction::Skill,k,255,true});
                grab_icon(o,3,k,k+40,dragged_skill_);
                b_.quads[0].scale=Point2{1.0f,1.0f};a_.quads[0].scale=Point2{1.0f,1.0f};
            } else show_skill_text(dr_class_base_skills[c.class_type][k]);
            return;
        }
        return;
    }
    default: return;
    }
}
void ClassView::release(const SessionObjects& o) {
    touch_=0;
    const Point2 p=o.touch->position;
    if(back_) {   // Return: the record validated and made the current class, the screen fades out
        if(s_[10].contains(p)){requests.push_back({ClassAction::Done,0,0,false});closing_=true;}
        s_[10].set_alpha(255);back_=false;return;
    }
    if(help_) {
        if(s_[9].contains(p))requests.push_back({ClassAction::Help,tab_,0,false});
        s_[9].set_alpha(255);help_=false;return;
    }
    const ClassProfile& c=record(o);
    switch(tab_) {
    case 0: case 1:
        if(pressed_<0)return;
        tabs_[tab_][static_cast<std::size_t>(pressed_)].set_alpha(255);
        if(tabs_[tab_][static_cast<std::size_t>(pressed_)].contains(p))
            requests.push_back({tab_==0?ClassAction::Select:ClassAction::Race,pressed_,0,false});
        pressed_=-1;
        return;
    case 2: {
        if(dragged_perk_<0)return;
        const Strips& v=tabs_[2];
        bool asked=false;
        if(p.y>v[static_cast<std::size_t>(perk_panels_)].position.y && p.y<v[static_cast<std::size_t>(perk_text_)].position.y) {
            const bool perk=dragged_perk_<=9;
            float best=999999.0f;std::int32_t slot=0;
            for(int k=0;k<8;++k) {   // the nearest open slot of its row (not the fixed first)
                if(perk?k>3:k<=3){if(perk)break;continue;}
                if((k&3)==0)continue;
                if(!perk_unlocked(c,k&3))break;
                const QuadStrip& s=v[static_cast<std::size_t>(perk_slots_+k)];
                const Point2 z=s.size();const Point2 hz{z.x/2.0f,z.y/2.0f};
                const float d=dist_squared(s.position,Point2{p.x-hz.x,p.y-hz.y});
                if(d<best){best=d;slot=k;}
            }
            if(best<=999999.0f) {
                if(perk)requests.push_back({ClassAction::Perk,slot,dragged_perk_,false});
                else requests.push_back({ClassAction::Flaw,slot-4,dragged_perk_-10,false});
                if(sounds)sounds->push_back(0);
                asked=true;
            } else for(int j=1;j<4;++j) {   // (never reached: the first empty open slot)
                if(!perk_unlocked(c,j))break;
                if(perk?c.perks[j]==255:c.flaws[j]==255) {
                    requests.push_back({perk?ClassAction::Perk:ClassAction::Flaw,j,perk?dragged_perk_:dragged_perk_-10,false});
                    if(sounds)sounds->push_back(0);
                    asked=true;break;
                }
            }
        }
        dragged_perk_=-1;
        if(!asked)update_perks(o);
        return;
    }
    case 3: {
        if(dragged_skill_<0)return;
        const Strips& v=tabs_[3];
        bool asked=false;
        if(p.y>s_[8].position.y && p.y<v[static_cast<std::size_t>(skill_panel_)].position.y) {
            float best=999999.0f;std::int32_t slot=0;
            for(int k=0;k<20;++k) {   // the nearest of the class's skills
                const QuadStrip& s=v[static_cast<std::size_t>(k)];
                const Point2 z=s.size();const Point2 hz{z.x/2.0f,z.y/2.0f};
                const float d=dist_squared(s.position,Point2{p.x-hz.x,p.y-hz.y});
                if(d<best){best=d;slot=k;}
            }
            const Texts& t=*texts_;
            const std::string& name=t.get("class.name",c.class_type);
            const std::int32_t skill=other_skill(c,dragged_skill_);
            if(slot==0) {
                show_text(nullptr,printf_string(t.get("class.skill_fixed").c_str(),name.c_str(),
                                                t.get("skill.name",dr_class_base_skills[c.class_type][0]).c_str()),false);
                if(sounds)sounds->push_back(0);
            }
            else if(replacement(c,slot)!=255 || dr_replacement_skill_count(&c)<dr_class_replacements_allowed(&c)) {
                requests.push_back({ClassAction::Skill,slot,skill,false});asked=true;
            } else {
                const int allowed=static_cast<int>(dr_class_replacements_allowed(&c));
                std::string message;
                if(allowed==0)message=printf_string(t.get("class.skill_locked").c_str(),name.c_str());
                else if(allowed==10)message=printf_string(t.get("class.skill_max").c_str(),allowed,name.c_str());
                else message=printf_string(t.get("class.skill_more").c_str(),allowed,name.c_str());
                show_text(nullptr,message,false);
                if(sounds)sounds->push_back(0);
            }
        }
        dragged_skill_=-1;
        if(!asked)update_abilities(o);
        return;
    }
    default: return;
    }
}
void ClassView::drag(const SessionObjects& o) {   // the dragged picture follows the touch (a skill shrinks over its row)
    if(dragged_perk_<0 && dragged_skill_<0)return;
    const Point2 p=o.touch->position;
    a_.set_position(Point2{p.x+grab_.x,p.y+grab_.y});
    b_.set_position(Point2{p.x+grab_icon_.x,p.y+grab_icon_.y});
    if(dragged_skill_<0)return;
    const QuadStrip& panel=tabs_[3][static_cast<std::size_t>(skill_panel_)];
    const float y=panel.position.y;const Point2 z=panel.size();
    const float a=p.y-y;const float b=y+z.y;const float c=b-y;
    const float t=clampf(a/c,0.0f,1.0f);const float s=interpolate(0.5f,1.0f,t);
    a_.quads[0].scale=Point2{s,s};b_.quads[0].scale=Point2{s,s};
}
void ClassView::after_request(const SessionObjects& o,const ClassRequest& r) {
    switch(r.action) {
    case ClassAction::Select: update_class(o);break;
    case ClassAction::Race: update_race(o);break;
    case ClassAction::Perk: case ClassAction::Flaw: update_perks(o);break;
    case ClassAction::Skill:
        update_abilities(o);
        if(r.grabbed)show_skill_text(other_skill(record(o),dragged_skill_));
        break;
    default: break;
    }
}
}
