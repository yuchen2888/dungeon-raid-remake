#include "interface.hpp"
#include "menu.hpp"
#include "recovered_tokens.hpp"
#include "recovered_turn.hpp"
#include <cmath>
#include <cstdio>
using namespace dungeonraid;
namespace drui {
namespace {
// Interpolate 0x1b800, ClampI 0x1b7ec as branched.
float interpolate(float a,float b,float t) {const float x=a*t;const float y=(1.0f-t)*b;return x+y;}
std::int32_t clampi(std::int32_t v,std::int32_t lo,std::int32_t hi) {if(v>=hi)return hi;if(lo>=v)return lo;return v;}
std::uint8_t to_u8(float v) {return static_cast<std::uint8_t>(v<=0.0f?0u:(v>=4294967295.0f?0xffffffffu:static_cast<std::uint32_t>(v)));}   // vcvt.u32.f32
constexpr Colour white{255,255,255,255};
// The four skill slots (static table 0x1eac44).
constexpr Point slots[4]={{0.1015625f,0.1015625f},{0.285937488f,0.1015625f},{0.470312506f,0.1015625f},{0.654687524f,0.1015625f}};
// The session's copies of Interface+0xcb8.. (Game+0x5994..).
std::int32_t ui_health(const SessionObjects& o) {return o.resources->ui_health;}
std::int32_t ui_ceiling(const SessionObjects& o) {return o.player->ui_health_ceiling_5998;}
// Game::GetEnemyCount 0x... on the board: skulls of the enemy type.
std::int32_t enemy_count(const SessionObjects& o,std::int32_t type) {
    std::int32_t n=0;
    for(const auto& t:o.stroke->selection.tiles)n+=t.rule.type==1 && t.rule.enemy_type==type;
    return n;
}
// The x of a centred label: its laid-out width times its scale, halved, off centre.
float centred(const Label& l,float centre) {const float w=l.width*l.scale.x;const float h=w*-0.5f;return h+centre;}
}
// Interface::Interface 0x1f350: the quads and labels it builds, with the sizes, texture coordinates, positions,
// colours and alphas it gives them (frontend/tools/trace_function.py '__ZN9InterfaceC2EP4Game').
InterfaceView::InterfaceView() {
    for(std::size_t off:{0x0,0x70,0xe0,0x150,0x1c0,0x230,0x2a0,0x310,0x380,0x3f0,0x460,0x620,0x690,0x700,0x770,0x7e0,
                         0x850,0x8c0,0x930,0x9a0,0xa10,0xa80,0xaf0,0xb60,0xbd4,0xc44})new (mem_+off) Quad();
    for(std::size_t off:{0x4d0,0x508,0x540,0x578,0x5b0,0x5e8,0x10b0,0x10e8})labels_[off]=Label();
    set_i(0xbd0,-1);
    for(std::size_t off:{0xcb8,0xcbc,0xcc0,0xcc4,0xcc8,0xcd0,0xcd4,0xcd8,0xcdc,0xce0,0xce4,0xce8,0xcec})set_i(off,-1);
    set_f(0x10a0,1.0f);
    q(0x0).set_size(Point2{1.0f,0.237499997f});q(0x0).set_uv(0.0f,0.42578125f,0.3125f,0.07421875f);
    q(0x0).position=Point2{0.5f,1.38125002f};
    q(0x620).set_size(Point2{1.0f,0.228125006f});q(0x620).set_uv(0.314453125f,0.427734375f,0.0009765625f,0.0712890625f);
    q(0x620).position=Point2{0.5f,0.114062503f};
    for(std::size_t k=0;k<4;++k) {
        Quad& slot=q(0x690+k*0x70);
        slot.set_size(Point2{0.165625006f,0.165625006f});
        slot.set_uv(Point2{0.196289062f,0.373046875f},Point2{0.248046875f,0.424804688f});
        slot.position=slots[k];slot.set_colour(white);
        Quad& glow=q(0xa10+k*0x70);
        glow.set_size(Point2{0.190624997f,0.190624997f});
        glow.set_uv(Point2{0.439453125f,0.180664062f},Point2{0.499023438f,0.240234375f});
        glow.position=slots[k];glow.set_alpha(0);
    }
    for(std::size_t off:{0x4d0,0x508,0x540,0x578,0x5b0})label(off).scale=Point2{0.0900000036f,0.0900000036f};
    label(0x508).colour=Colour{173,177,255,255};
    label(0x578).colour=Colour{249,172,98,255};
    label(0x5b0).colour=Colour{113,52,176,255};
    Label& level=label(0x5e8);
    level.scale=Point2{0.100000001f,0.100000001f};level.position=Point2{0.865625024f,0.075000003f};level.space_scale=2.0f;
    level.colour=Colour{130,120,220,255};
    set_f(0xd08,0.853124976f);set_f(0xcfc,1.46249998f);
    q(0xbd4).set_size(Point2{0.224999994f,0.081249997f});
    q(0xbd4).set_uv(Point2{0.333984375f,0.329101562f},Point2{0.404296875f,0.354492188f});
    q(0xbd4).position=Point2{0.868749976f,0.0562499985f};
    q(0xc44).set_size(Point2{0.224999994f,0.081249997f});
    q(0xc44).set_uv(Point2{0.262695312f,0.329101562f},Point2{0.333007812f,0.354492188f});
    q(0xc44).position=Point2{0.868749976f,0.143749997f};
    q(0x2a0).set_alpha(120);q(0x310).set_alpha(80);q(0x380).set_alpha(120);q(0x3f0).set_alpha(80);q(0x460).set_alpha(80);
    for(std::size_t off:{0x10b0,0x10e8}) {
        Label& l=label(off);l.scale=Point2{0.131249994f,0.131249994f};l.space_scale=2.0f;l.colour=Colour{64,226,0,200};
    }
    label(0x10b0).position=Point2{0.015625f,0.259375006f};
    label(0x10e8).position.y=0.259375006f;
}
void InterfaceView::set_fonts(const Font* font,const Font* score) {
    for(std::size_t off:{0x4d0,0x508,0x540,0x578,0x5b0,0x5e8})label(off).font=font;
    for(std::size_t off:{0x10b0,0x10e8})label(off).font=score;
    for(auto& l:labels_)l.second.update_colour();
}
// Interface::Reset 0x204a4 (the pressed skill +0xbd0 and the menu bytes are the session's; the Tooltip is separate).
void InterfaceView::reset() {
    set_i(0x1120,0);set_i(0x1124,0);set_i(0x1128,0);b(0x112c)=0;
    set_f(0x10a4,0.0f);set_f(0x109c,0.0f);set_f(0x10a0,1.0f);
    b(0xcb4)=0;b(0xcb5)=0;set_i(0xccc,0);
    set_i(0xcd0,-1);set_i(0xcd4,-1);set_i(0xcd8,-1);set_i(0xcdc,-1);
    for(std::size_t k=0;k<4;++k){q(0x690+k*0x70).set_colour(white);q(0xa10+k*0x70).set_colour(Colour{255,255,255,0});}
    q(0xbd4).set_colour(white);q(0xc44).set_colour(white);q(0x70).set_colour(white);
}
// Interface::UpdateHealthBar 0x21130: the jar's liquid up to health / ceiling, its picture cut from the bottom; the
// "health/ceiling" label centred at 0.853125; the jar's top (+0xd0c) is where potions fly.
void InterfaceView::update_health_bar(const SessionObjects& o,std::size_t quad,std::int32_t value) {
    const std::int32_t ceiling=ui_ceiling(o);
    if(value>=ceiling)value=ceiling;
    const float frac=static_cast<float>(value)/static_cast<float>(ceiling);
    Quad& jar=q(quad);
    jar.set_size(Point2{0.221874997f,frac*0.200000003f});
    const float y=(1.0f-frac)*0.0625f+0.436523438f;
    jar.set_uv(0.317382812f,y,0.0693359375f,frac*0.0625f);
    jar.position.y=jar.size.y*-0.5f+1.46875f;
    jar.position.x=jar.size.x*0.5f+0.746874988f;
    char text[32];std::snprintf(text,sizeof text,"%d/%d",ui_health(o),ceiling);
    Label& l=label(0x578);l.set_text(text);
    l.position.y=1.44687498f;l.position.x=centred(l,0.853124976f);
    set_f(0xd0c,1.46875f-q(0x70).size.y);
}
// Interface::UpdateXPBar 0x1ea2c: the bar's width value / 100 from 0.34375; its end (+0xcf8) is where skulls fly.
void InterfaceView::update_xp_bar(std::size_t quad,std::int32_t value) {
    const float frac=static_cast<float>(value)/100.0f;
    Quad& bar=q(quad);
    bar.set_size(Point2{frac*0.3125f,0.03125f});
    bar.set_uv(0.387695312f,0.489257812f,frac*0.09765625f,0.009765625f);
    bar.position.y=bar.size.y*0.5f+1.44687498f;
    bar.position.x=bar.size.x*0.5f+0.34375f;
    set_f(0xcf8,q(0xe0).size.x+0.34375f);
}
// Interface::UpdateUPBar 0x212bc: as the XP bar, above it.
void InterfaceView::update_up_bar(const SessionObjects& o,std::size_t quad,std::int32_t value) {
    const float frac=static_cast<float>(value)/100.0f;
    Quad& bar=q(quad);
    bar.set_size(Point2{frac*0.3125f,0.03125f});
    bar.set_uv(0.387695312f,0.478515625f,frac*0.09765625f,0.009765625f);
    bar.position.y=bar.size.y*0.5f+1.390625f;
    bar.position.x=bar.size.x*0.5f+0.34375f;
    update_shield_target(o);
}
// Interface::UpdateGoldBar 0x20600: a coin column per twenty (0.05 wide from 0.015625), the rest a shorter column;
// an empty part parked at (200, 200); the top of the stack (+0xcf0) is where coins fly.
void InterfaceView::update_gold_bar(std::size_t quads,std::int32_t value) {
    const std::int32_t tens=value/20,ones=value-tens*20;   // the names keep the asm's shape: columns of 20
    Quad& full=q(quads);Quad& part=q(quads+0x70);
    float t=0.0f,u=0.0f;
    if(tens==0)full.position=Point2{200.0f,200.0f};
    else {
        t=static_cast<float>(tens);
        full.set_size(Point2{t*0.0500000007f,0.190624997f});
        full.set_uv(0.387695312f,0.41796875f,t*0.015625f,0.0595703125f);
        full.position.y=full.size.y*-0.5f+1.48749995f;
        full.position.x=full.size.x*0.5f+0.015625f;
    }
    if(ones==0)part.position=Point2{200.0f,200.0f};
    else {
        u=static_cast<float>(ones);
        part.set_size(Point2{0.0500000007f,u*0.00937500037f});
        const float x=t*0.015625f+0.387695312f,y=u*-0.0029296875f+0.477539062f;
        part.set_uv(x,y,0.015625f,u*0.0029296875f);
        part.position.y=part.size.y*-0.5f+1.48749995f;
        const float left=t*0.0500000007f+0.015625f;
        part.position.x=left+part.size.x*0.5f;
    }
    const float x=t*0.0500000007f+0.015625f;
    set_f(0xcf0,x+0.0250000004f);
    set_f(0xcf4,u*-0.00937500037f+1.48749995f);
}
// Interface::UpdateSkullValue 0x20224 / UpdateSwordValue 0x1e708 / UpdateShieldValue 0x20294: "+n", "+n", "n/max"
// centred under their icons.
void InterfaceView::update_skull_value(const SessionObjects& o) {
    char text[32];std::snprintf(text,sizeof text,"+%d",o.player->ui_skull_59c8);
    Label& l=label(0x540);l.set_text(text);l.position.y=1.36562502f;l.position.x=centred(l,0.331250012f);
}
void InterfaceView::update_sword_value(const SessionObjects& o) {
    char text[32];std::snprintf(text,sizeof text,"+%d",o.player->ui_sword_59bc);
    Label& l=label(0x4d0);l.set_text(text);l.position.y=1.36562502f;l.position.x=centred(l,0.640625f);
}
void InterfaceView::update_shield_value(const SessionObjects& o) {
    char text[32];std::snprintf(text,sizeof text,"%d/%d",o.resources->ui_armour,o.player->ui_armour_max_59c4);
    Label& l=label(0x508);l.set_text(text);l.position.y=1.36562502f;l.position.x=centred(l,0.496874988f);
    update_shield_target(o);
}
// Interface::UpdateShieldTarget 0x1eb30: shields fly to the armour value while armour can grow (and no enemy 12 is on
// the board), else to the end of the upgrade bar.
void InterfaceView::update_shield_target(const SessionObjects& o) {
    if(o.resources->ui_armour<o.player->ui_armour_max_59c4 && enemy_count(o,12)==0) {set_f(0xd00,0.496874988f);set_f(0xd04,1.39687502f);}
    else {set_f(0xd00,q(0x150).size.x+0.34375f);set_f(0xd04,1.40625f);}
}
// Interface::SetPoison 0x201ac.
void InterfaceView::set_poison(std::int32_t poison) {
    set_i(0xccc,poison);
    update_health_colour();
    if(!i(0xccc))return;
    char text[32];std::snprintf(text,sizeof text,"%d poison",i(0xccc));
    Label& l=label(0x5b0);l.set_text(text);l.position.y=1.38437498f;l.position.x=centred(l,0.853124976f);
}
// Interface::Set*Shadow 0x2127c / 0x1eae4 / 0x21368 / 0x207e4: the preview of a stroke's gain (amount <= 0: none).
void InterfaceView::set_health_shadow(const SessionObjects& o,std::int32_t amount) {
    if(amount<=0){set_i(0xcd0,-1);return;}
    const std::int32_t v=clampi(ui_health(o)+amount,0,ui_ceiling(o));
    if(v!=i(0xcd0)){set_i(0xcd0,v);update_health_bar(o,0x2a0,v);}
}
void InterfaceView::set_xp_shadow(const SessionObjects& o,std::int32_t amount) {
    if(amount<=0){set_i(0xcd4,-1);return;}
    const std::int32_t v=clampi(o.resources->ui_xp+amount,0,100);
    if(v!=i(0xcd4)){set_i(0xcd4,v);update_xp_bar(0x310,v);}
}
void InterfaceView::set_up_shadow(const SessionObjects& o,std::int32_t amount) {
    if(amount<=0){set_i(0xcd8,-1);return;}
    const std::int32_t v=clampi(o.resources->ui_up+amount,0,100);
    if(v!=i(0xcd8)){set_i(0xcd8,v);update_up_bar(o,0x380,v);}
}
void InterfaceView::set_gold_shadow(const SessionObjects& o,std::int32_t amount) {
    if(amount<=0){set_i(0xcdc,-1);return;}
    const std::int32_t v=clampi(o.resources->ui_gold+amount,0,100);
    if(v!=i(0xcdc)){set_i(0xcdc,v);update_gold_bar(0x3f0,v);}
}
// Interface::UpdateHealthColour 0x1e7ac: the jar's liquid darkens with the heartbeat (+0x109c of +0x10a0), paler
// while poisoned.
void InterfaceView::update_health_colour() {
    float t=f(0x109c)/f(0x10a0);
    t=1.0f-t;set_f(0x10a8,t);
    if(t<0.200000003f){t=t/0.200000003f;t=t*t;}
    else {
        t=t-0.200000003f;t=t/0.800000012f;set_f(0x10a8,t);
        t=static_cast<float>(static_cast<double>(t)*3.141592653589793);
        t=static_cast<float>(std::cos(static_cast<double>(t)));   // cosf (the reference's model: double cos, rounded)
        t=t+1.0f;t=t*0.5f;
    }
    set_f(0x10a8,t);
    const float pale=i(0xccc)>0?200.0f:255.0f;
    const float r=interpolate(100.0f,pale,t),g=interpolate(100.0f,pale,t),bl=interpolate(100.0f,255.0f,t);
    q(0x70).set_colour(Colour{to_u8(r),to_u8(g),to_u8(bl),255});
}
// Interface::ProcessHeartbeat 0x1e8e8's picture: below 35% health the jar beats (the beat, its sound 32 and the
// low-health help are the session's, SessionObjects.heartbeat); the liquid follows the running beat
// (UpdateHealthColour) in the frames the original counts it down -- not while it waits for the next one.
void InterfaceView::process_heartbeat(const SessionObjects& o,const Heartbeat& before) {
    const Heartbeat& h=*o.heartbeat;
    set_f(0x109c,h.beat);set_f(0x10a0,h.beat_length);set_f(0x10a4,h.wait);
    const float ratio=static_cast<float>(ui_health(o))/static_cast<float>(ui_ceiling(o));
    const bool low=ratio<=0.349999994f;
    if(!low && before.beat==0.0f)return;
    if((low?before.wait:0.0f)>0.0f)return;
    update_health_colour();
}
// Interface::UpdateSkills 0x20820: each equipped skill's charge filling its slot from the bottom (dimmer until full).
// (The ready / active skill's help, HelpMenu::Initialise types 19 / 20, is the session's.)
void InterfaceView::update_skills(const SessionObjects& o) {
    constexpr float cell=0.0517578125f;
    for(std::int32_t k=0;k<o.resources->skill_count && k<4;++k) {
        const std::int32_t current=o.resources->skill_current[k],max=o.resources->skill_max[k];
        const float frac=static_cast<float>(current)/static_cast<float>(max);
        const float uv_h=frac*cell,h=frac*0.165625006f;
        Quad& fill=q(0x850+static_cast<std::size_t>(k)*0x70);
        fill.set_size(Point2{0.165625006f,h});
        fill.set_uv(0.249023438f,0.424804688f-uv_h,cell,uv_h);
        fill.position.x=slots[k].x;
        const float top=slots[k].y+0.082812503f;
        fill.position.y=top+h*-0.5f;
        fill.set_colour(frac==1.0f?white:Colour{200,200,200,255});
        if(current==max || current==0) {
            Quad& glow=q(0xa10+static_cast<std::size_t>(k)*0x70);
            glow.set_colour(Colour{static_cast<std::uint8_t>(o.skills->active[k]?254:255),255,255,glow.v[0].colour[3]});
        }
    }
}
void InterfaceView::set_clock_state(bool on) {
    if(on)q(0xbd4).set_uv(Point2{0.415039062f,0.681640625f},Point2{0.485351562f,0.70703125f});
    else q(0xbd4).set_uv(Point2{0.333984375f,0.329101562f},Point2{0.404296875f,0.354492188f});
    b(0x10ac)=on?1:0;
}
void InterfaceView::set_clock_string(const char* text) {
    if(!b(0x10ac))return;
    Label& l=label(0x5e8);l.set_text(text);
    l.position.x=centred(l,0.865625024f);
}
// Interface::Process 0x20c64, its own part (the menus' and the tooltip's are theirs; skill input is the session's):
// the heartbeat unless the foldout menu is open, and the skill highlights fading in while ready or active.
void InterfaceView::process(const SessionObjects& o,float dt,const Heartbeat& heartbeat_before) {
    if(!o.screens->menus[0])process_heartbeat(o,heartbeat_before);
    const float down=dt*-255.0f;const std::int32_t step=static_cast<std::int32_t>(down*5.0f);
    const float tint=dt*255.0f*-5.0f;
    for(std::int32_t k=0;k<o.resources->skill_count;++k) {
        const bool lit=o.resources->skill_current[k]==o.resources->skill_max[k] || o.skills->active[k];
        Quad& glow=q(0xa10+static_cast<std::size_t>(k)*0x70);
        const std::int32_t a=clampi(glow.v[0].colour[3]+(lit?-step:step),0,255);
        glow.set_alpha(static_cast<std::uint8_t>(a));
        const std::uint8_t r=glow.v[0].colour[0];
        if(r!=255) {
            const std::int32_t v=clampi(static_cast<std::int32_t>(static_cast<float>(r)+tint),150,255);
            glow.set_colour(Colour{static_cast<std::uint8_t>(v),static_cast<std::uint8_t>(v),255,static_cast<std::uint8_t>(a)});
        }
    }
    if(o.stroke->record_14aed && o.stroke->mode_14ae8!=3)challenge_score(o,dt);
}
// Interface::Process 0x20db0, a challenge game's score line (+0x10b0) and turn (+0x10e8): the round's points (+0x1124:
// the preview's total; mode 0 also its bonus +0x1128, the tokens' bonus total) wait under the score (+0x1120) and, once the
// round's tiles are all counted (both totals 0), pour into it after 0.2 s (+0x1130), faster each frame (+0x1134 x 1.5),
// the bonus first.
void InterfaceView::challenge_score(const SessionObjects& o,float dt) {
    const std::int32_t mode=o.stroke->mode_14ae8;
    const auto score=[&o]{return dr_get_score(o.resources,o.path,o.skills,o.end->victory!=0);};
    const std::int32_t pending=o.preview->total_165d0,bonus=dr_token_queue_counters(o.tokens)->bonus_total_165d4;
    if(b(0x112c)) {
        const float t=f(0x1130);
        if(t>0.0f) {
            const float left=t-dt;set_f(0x1130,left);
            if(!(left>0.0f))set_f(0x1134,1.0f);
        } else {
            if(mode==0 && i(0x1128)>0) {   // the bonus first
                const std::int32_t b2=i(0x1128);const std::int32_t step=static_cast<std::int32_t>(f(0x1134));
                const std::int32_t n=step<b2?step:b2;
                set_i(0x1128,b2-n);set_i(0x1124,i(0x1124)+n);
                if(b2-n==0)set_f(0x1134,1.0f);
            } else if(i(0x1124)>0) {
                const std::int32_t a=i(0x1124);const std::int32_t step=static_cast<std::int32_t>(f(0x1134));
                const std::int32_t n=step<a?step:a;
                set_i(0x1124,a-n);
                if(a-n==0){set_i(0x1128,0);set_i(0x1120,score());b(0x112c)=0;}
                else {const std::int32_t sum=n+i(0x1120);set_i(0x1120,sum);if(sum>score())set_i(0x1120,score());}
            }
            set_f(0x1134,f(0x1134)*1.5f);
        }
    } else {
        if(i(0x1124)==0 && i(0x1128)==0)set_i(0x1120,score());
        else if(pending==0 && bonus==0){b(0x112c)=1;set_f(0x1130,0.200000003f);}
        if(!b(0x112c)){set_i(0x1124,pending);set_i(0x1128,bonus);}
    }
    const std::int32_t shown=i(0x1120),a=i(0x1124),b2=i(0x1128);
    if(mode==0) {
        if(a>0)score_text_=b2>0?printf_string(texts_->get("challenge.score_both").c_str(),shown,a,b2)
                               :printf_string(texts_->get("challenge.score_plus").c_str(),shown,a);
        else score_text_=b2>0?printf_string(texts_->get("challenge.score_bonus").c_str(),shown,b2)
                             :printf_string(texts_->get("challenge.score").c_str(),shown);
    } else if(mode==1) {
        if(a==0)score_text_=printf_string(texts_->get("challenge.score").c_str(),shown);
        else {
            static const char* const keys[]={"challenge.score_plus","challenge.score_plus1","challenge.score_plus2","challenge.score_plus3"};
            score_text_=printf_string(texts_->get(keys[b2<0?3:b2>3?3:b2]).c_str(),shown,a);
        }
    }
    label(0x10b0).set_text(score_text_.c_str());
    const std::int32_t turn=o.path->turn+1;
    Label& t=label(0x10e8);
    t.set_text(printf_string(texts_->get("challenge.turn").c_str(),turn<1?1:turn>100?100:turn).c_str());
    t.position.x=0.975000024f-t.width*t.scale.x;
}
// Interface::Render 0x1ebe0 (the equipped skills: the presenter's SkillViews, Upgrade::RenderIcon).
Point2 InterfaceView::skill_position(std::int32_t slot) {
    return Point2{slots[slot].x-0.0765625015f,slots[slot].y-0.0765625015f};
}
void InterfaceView::render(GL& gl,const SessionObjects& o,const SkillView* skills) {
    q(0x0).render(gl);
    if(i(0xcd0)>0)q(0x2a0).render(gl);
    if(i(0xcd4)>0)q(0x310).render(gl);
    if(i(0xcd8)>0)q(0x380).render(gl);
    if(i(0xcdc)>0){q(0x3f0).render(gl);q(0x460).render(gl);}
    q(0x70).render(gl);q(0xe0).render(gl);q(0x150).render(gl);q(0x1c0).render(gl);q(0x230).render(gl);
    q(0x620).render(gl);
    for(std::int32_t k=0;k<4;++k) {
        q(0x690+static_cast<std::size_t>(k)*0x70).render(gl);
        if(o.resources->skill_count>k) {
            q(0x850+static_cast<std::size_t>(k)*0x70).render(gl);
            q(0xa10+static_cast<std::size_t>(k)*0x70).render(gl);
            if(skills)skills[k].render(gl,true);
            gl.bind_texture(Tiles);
        }
    }
    q(0xbd4).render(gl);q(0xc44).render(gl);
    if(b(0x10ac))label(0x5e8).render(gl);
    if(o.stroke->record_14aed) {   // a challenge game: its score (and in mode 0 the turn)
        if(o.stroke->mode_14ae8==0){label(0x10b0).render(gl);label(0x10e8).render(gl);}
        else if(o.stroke->mode_14ae8==1)label(0x10b0).render(gl);
    }
    label(0x4d0).render(gl);label(0x508).render(gl);label(0x540).render(gl);label(0x578).render(gl);
    if(i(0xccc)>0)label(0x5b0).render(gl);
}
Point InterfaceView::target(std::int32_t type) const {
    switch(type) {
    case 0: return Point{f(0xd08),f(0xd0c)};
    case 1: return Point{f(0xcf8),f(0xcfc)};
    case 2: return Point{f(0xcf0),f(0xcf4)};
    case 3: return Point{f(0xd00),f(0xd04)};
    default: return Point{0.0f,0.0f};
    }
}
Point InterfaceView::special_target(std::int32_t slot) const {return q(0x690+static_cast<std::size_t>(slot)*0x70).position;}
}
