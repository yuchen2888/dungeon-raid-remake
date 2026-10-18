#include "recovered_generation.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>
using namespace dungeonraid;
namespace {
void emit(const GenerationHooks* h,GenerationEventKind k,int i,int a=0,int b=0,int c=0,int d=0) {
    if(h && h->event) {const GenerationEvent e{k,i,a,b,c,d};h->event(h->context,&e);}
}
PathState& path(GenerationState* s) {return *s->refill->path;}
MatchState& match(GenerationState* s) {return *path(s).match;}
SelectionState& board(GenerationState* s) {return match(s).stroke->selection;}
int bits(float f) {int i;std::memcpy(&i,&f,4);return i;}
void uv(const GenerationHooks* h,int i,float x,float y,float w=.0517578125f,float z=.0517578125f) {
    emit(h,GenerationEventKind::UV,i,bits(x),bits(y),bits(w),bits(z));
}
int random(GenerationState* s,const GenerationHooks* h,int lo,int hi,int stream=1) {
    const int v=dr_random_int(&match(s).random,lo,hi,stream);
    emit(h,GenerationEventKind::Random,-1,lo,hi,stream,v);return v;
}
bool perk(GenerationState* s,int p) {for(int n:match(s).perks)if(n==p && p!=255)return true;return false;}
bool flaw(GenerationState* s,int f) {return dr_have_flaw(&board(s).character,f);}
int enemy_count(GenerationState* s,int e) {int n=0;for(auto& t:board(s).tiles)if(t.rule.type==1 && t.rule.enemy_type==e)++n;return n;}
}
extern "C" int dr_generation_total_xp(const GenerationState* s) {
    int n=s->resources->xp+s->resources->total_xp;
    auto& stroke=*s->refill->path->match->stroke;
    return stroke.record_14aed && stroke.mode_14ae8==0?n/4:n;
}
extern "C" bool dr_time_to_promote(GenerationState* s) {
    auto& stroke=*match(s).stroke;
    if(stroke.record_14aed && stroke.mode_14ae8==0) {
        if(s->time_to_promotion==0)return true;
        if(s->time_to_promotion==200)return false;
        const int t=path(s).turn;
        const bool result=flaw(s,8)?(t-3)%9==0:(t-4)%10==0;
        if(result)s->time_to_promotion=0;
        return result;
    }
    // RSBS result is 1 only for zero; one yields zero, negatives are rejected.
    return s->time_to_promotion==0;
}
extern "C" void dr_set_time_to_promotion(GenerationState* s,int value,const GenerationHooks* h) {
    if(!s->promotion_enabled)return;
    auto& stroke=*match(s).stroke;
    s->time_to_promotion=stroke.record_14aed && stroke.mode_14ae8==0?200:value;
    emit(h,GenerationEventKind::Sound,-1,14);
}
extern "C" void dr_generate_stats(GenerationState* s,std::uint32_t i,int t,int difficulty,const GenerationHooks* h) {
    auto& c=path(s).combat[i];auto& tile=board(s).tiles[i];auto& stroke=*match(s).stroke;
    const int xp=dr_generation_total_xp(s)/100;
    const int mode=stroke.record_14aed && stroke.mode_14ae8==1?1:difficulty;
    int cooldown=1;
    // Valid game domain: nonnegative turn; positive turn for finite cooldowns.
    // Formula evaluation deliberately retains every original float rounding.
    if(mode>=1 && mode<=3) {
        const float divisor=mode==1?700.f:mode==2?750.f:500.f;
        t=int(float(t)*std::max(1.f,1.f+float(t-500)/divisor));
        if(xp>40)t=int(float(t)*(1.f+float(xp-40)/60.f));
    }
    if(mode>=0 && mode<=3) {
        constexpr int ranges[4][6]={{80,70,70,55,25,20},{65,55,50,40,20,15},{50,40,40,37,17,12},{40,35,30,35,15,10}};
        const auto& r=ranges[mode];
        c.attack=std::max(1,random(s,h,t/r[0],t/r[1]));
        c.defence=std::max(0,random(s,h,t/r[2],t/r[3]));
        c.health=std::max(mode==0?3:4,random(s,h,t/r[4],t/r[5]));
        const float root=std::sqrt(float(t));
        cooldown=random(s,h,int((mode<2?200.f:150.f)/root),int(300.f/root))+(mode==0?5:0);
    }
    if(stroke.record_14aed && stroke.mode_14ae8==0) {
        c.attack=std::max(1,random(s,h,t/20,t/12));
        c.defence=std::max(0,random(s,h,t/10,t/6));
        c.health=std::max(4,random(s,h,t/8,t/4));
    }
    const int e=tile.rule.enemy_type;
    if(e) {
        if(flaw(s,8))cooldown=std::max(1,cooldown-1);
        dr_set_time_to_promotion(s,cooldown,h);
        if(!c.defence)c.defence=1;
    } else if(flaw(s,3))++c.health;
    switch(e) {
        case 0:break;
        case 1:c.attack*=3;c.defence*=3;c.health*=6;break;
        case 2:c.attack*=2;c.health*=3;break;
        case 3:c.attack=0;c.defence*=6;c.health*=6;tile.rule.enemy_state=5;break;
        case 5:c.attack*=2;c.defence*=10;c.health/=2;break;
        case 9:c.defence*=2;c.health*=4;break;
        case 10:c.defence*=2;c.health*=6;tile.rule.enemy_state=5;break;
        case 16:c.attack*=3;c.defence*=2;c.health*=3;break;
        case 17:c.attack*=2;c.defence=match(s).preview->armour_current;c.health*=4;break;
        case 19:c.attack*=4;c.health*=5;tile.rule.enemy_state=5;break;
        case 27:c.attack*=2;c.defence*=4;c.health*=3;break;
        case 28:c.attack*=2;c.defence*=2;c.health*=4;tile.rule.enemy_state=5;break;
        case 30:c.attack/=2;c.health*=5;break;
        default:c.attack*=2;c.defence*=2;c.health*=4;break;
    }
    if(e && flaw(s,9))c.health=int(float(c.health)*1.05f);
    if(dr_mortal_enemy(board(s).character.race)==5 && enemy_count(s,5))c.defence*=2;
    emit(h,GenerationEventKind::Countdown,i);
    s->tiles[i].max_health=c.health;
}
extern "C" void dr_update_generated_values(GenerationState* s,std::uint32_t i,const GenerationHooks* h) {
    emit(h,GenerationEventKind::Text,i,1,1,1);
    const auto& c=path(s).combat[i];s->tiles[i].label_offset=float((c.attack>9 || c.defence>9 || c.health>199?2:1)*-.01);
    emit(h,GenerationEventKind::Countdown,i);
}
extern "C" void dr_promote_tile(GenerationState* s,std::uint32_t i,int turn,int difficulty,bool flag,const GenerationHooks* h) {
    auto& t=board(s).tiles[i];t.rule.enemy_type=random(s,h,1,32);
    if(match(s).class_type && random(s,h,1,200)<=(perk(s,8)?5:10))t.rule.enemy_type=dr_mortal_enemy(board(s).character.race);
    dr_generate_stats(s,i,turn,difficulty,h);emit(h,GenerationEventKind::EnemyUV,i);
    dr_update_generated_values(s,i,h);
    int n=0;for(auto& v:board(s).tiles)if(v.rule.type==1 && v.rule.enemy_type)++n;
    if(n>2)emit(h,GenerationEventKind::Achievement,-1,41,bits(100.f));
    match(s).flag_25d[i]=flag;
}
extern "C" void dr_set_tile_type(GenerationState* s,std::uint32_t i,int kind,int turn,int difficulty,const GenerationHooks* h) {
    auto& t=board(s).tiles[i];auto& c=path(s).combat[i];auto& m=match(s);
    t.rule.type=kind;t.rule.enemy_type=0;t.rule.special_type=3;
    const int variant=random(s,h,0,7,0);
    t.magic_sword=0;t.rule.flag_231=0;m.preview->potions[i]={};t.rule.flag_255=0;t.flaming=0;t.self_flame=0;t.broken=0;t.selected=0;
    t.rule.enemy_state=0;s->tiles[i].flag_224=0;m.flag_25d[i]=0;c.flag_25e=0;s->tiles[i].variant=variant;
    emit(h,GenerationEventKind::Colour,i,-1);
    uv(h,i,float(variant)*.0517578125f,float(t.rule.type)*.0517578125f);
    c.overlay=0;c.poison.effect_active=0;c.poison.effect_clearing=0;
    if(t.rule.type==1) {
        c.poison.current=c.poison.next=c.poison.following=0;
        if(dr_time_to_promote(s))dr_promote_tile(s,i,turn,difficulty,false,h);
        else {dr_generate_stats(s,i,turn,difficulty,h);dr_update_generated_values(s,i,h);}
    }
}
extern "C" void dr_make_arrow(GenerationState* s,std::uint32_t i,const GenerationHooks* h) {
    uv(h,i,.5517578125f,.4482421875f);board(s).tiles[i].rule.flag_231=1;
}
extern "C" void dr_make_mana_potion(GenerationState* s,std::uint32_t i,const GenerationHooks* h) {
    uv(h,i,float(s->tiles[i].variant)*.0517578125f,float(board(s).tiles[i].rule.type)*.0517578125f+.5009765625f);
    match(s).preview->potions[i].flag_232=1;
}
extern "C" void dr_make_broken(GenerationState* s,std::uint32_t i,const GenerationHooks* h) {
    auto& t=board(s).tiles[i];if(t.rule.type!=3 && t.rule.type!=4)return;
    t.broken=1;uv(h,i,.4140625f,t.rule.type==4?.759765625f:.7080078125f);
}
extern "C" void dr_randomise_tile(GenerationState* s,std::uint32_t i,const GenerationHooks* h) {
    auto& m=match(s);auto& t=board(s).tiles[i];auto& stroke=*m.stroke;
    int kind=s->force_coins && !s->filter_enabled && !s->inhibit_force_coins?2:random(s,h,0,4);
    if(stroke.record_14aed && stroke.mode_14ae8==0 && dr_time_to_promote(s))kind=1;
    if(s->filter_enabled)while(kind==(s->filter_swords?4:1))kind=random(s,h,0,4);
    dr_set_tile_type(s,i,kind,path(s).turn,m.spawn_enabled_14ae0,h);
    ++s->generated_count;if(t.rule.type==1)++s->generated_enemies;
    if(kind==4) {if(perk(s,6) && random(s,h,1,100)<=5)dr_make_arrow(s,i,h);}
    else if(kind==0) {if(perk(s,1) && random(s,h,1,100)<=5)dr_make_mana_potion(s,i,h);}
    else if(kind==3) {if(flaw(s,7) && random(s,h,1,100)<=3)dr_make_broken(s,i,h);}
    else if(kind==1) {
        if(s->one_health) {
            path(s).combat[i].health=1;emit(h,GenerationEventKind::Text,i,0,0,1);
            if(t.rule.enemy_type)emit(h,GenerationEventKind::Achievement,-1,62,bits(100.f));
        }
        if(dr_mortal_enemy(board(s).character.race)==12 && t.rule.enemy_type==12) {
            m.preview->armour_current=0;
            if(s->resources->ui_armour) {s->resources->ui_armour=0;emit(h,GenerationEventKind::ShieldValue,-1);}
            emit(h,GenerationEventKind::ShieldShatter,-1);emit(h,GenerationEventKind::Sound,-1,16);
        }
        if(t.rule.enemy_type==31)emit(h,GenerationEventKind::JumpDown,i);
    }
}
