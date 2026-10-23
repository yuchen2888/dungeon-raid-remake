#include "dr_bridge.hpp"
#include "recovered_tokens.hpp"
#include <cstring>
using namespace dungeonraid;
namespace drfront {
// The resource bars (0 health, 1 XP, 2 gold, 3 shield / upgrade points, 4 armour) across the top, the skill
// buttons in a row below the board; the Godot layout (main.gd) draws them at these points.
Point resource_target(std::int32_t index) {return Point{0.1f+0.2f*static_cast<float>(index),0.12f};}
Point skill_target(std::int32_t slot) {return Point{0.125f+0.25f*static_cast<float>(slot),1.37f};}
void Bridge::on_event(void* c,SessionSource source,const void* e) {
    Bridge& b=*static_cast<Bridge*>(c);++b.events_;
    if(b.listener_)b.listener_(b.listener_context_,source,e);
}
void Bridge::on_target(void* c,std::int32_t kind,std::int32_t index,Point* p) {
    const Bridge& b=*static_cast<Bridge*>(c);
    if(b.resource_)*p=kind?b.slot_(b.target_context_,index):b.resource_(b.target_context_,index);
    else *p=kind?skill_target(index):resource_target(index);
}
void Bridge::on_token_start(void* c,std::int32_t kind,Point* p) {
    const Bridge& b=*static_cast<Bridge*>(c);
    *p=b.resource_?b.resource_(b.target_context_,kind):Point{0.5f,board_top+0.5f};
}
Bridge::Bridge():host_{this,on_event,on_target,on_token_start},session_(dr_session_create(&host_,1)) {
    const SessionObjects o=dr_session_objects(session_);
    std::memset(o.name,0,17);   // (EAGLView initWithCoder: Game::SetName(the stored name, none at first))
}
void Bridge::seed(std::uint32_t time) {dr_session_seed(session_,time);}
void Bridge::platform_defaults() {
    SaveSettings& s=*objects().settings;
    s.clock_13ec9=0;s.dimming_13eca=1;s.framerate_13ecb=1;
    s.clock_changed_13ecc=s.dimming_changed_13ecd=s.framerate_changed_13ece=0;
}
Bridge::~Bridge() {dr_session_destroy(session_);}
SessionObjects Bridge::objects() {return dr_session_objects(session_);}
void Bridge::restore(const Blob& b) {
    const SessionObjects o=objects();
    const auto n=static_cast<std::uint32_t>(b.bytes.size());
    if(b.key=="classes")dr_session_restore_classes(session_,b.bytes.data(),n);
    else if(b.key=="game" && n<=save_capacity)dr_session_restore_save(session_,b.bytes.data(),n);
    else if(b.key=="spawn" && n==4)std::memcpy(&o.match->spawn_remaining_15558,b.bytes.data(),4);
    else if(b.key.size()==7 && b.key.compare(0,6,"scores")==0)dr_session_restore_scores(session_,b.key[6]-'0',b.bytes.data(),n);
    else if(b.key=="settings" && n==4) {   // the Game::Set*State calls of the platform's start-up
        SaveSettings& s=*o.settings;
        s.sound_13ec6=b.bytes[0]!=0;s.clock_13ec9=b.bytes[1]!=0;s.dimming_13eca=b.bytes[2]!=0;s.framerate_13ecb=b.bytes[3]!=0;
    }
}
void Bridge::new_game(std::int32_t kind,std::uint32_t seed) {
    dr_session_start_game(session_,kind,seed);started_=true;route_=FrameRoute::Done;
}
void Bridge::setup_random_name() {dr_session_setup_random_name(session_);}
bool Bridge::setup_select_class(std::int32_t type) {return dr_session_setup_select_class(session_,type);}
bool Bridge::setup_difficulty(std::int32_t difficulty) {return dr_session_setup_difficulty(session_,difficulty);}
bool Bridge::setup_mode(std::int32_t mode) {return dr_session_setup_mode(session_,mode);}
bool Bridge::setup_start(std::uint32_t seed) {return dr_session_setup_start(session_,seed);}
void Bridge::intro_done() {dr_session_intro_done(session_);}
void Bridge::setup_help() {dr_session_setup_help(session_);}
void Bridge::class_tab() {dr_session_class_tab(session_);}
bool Bridge::class_select(std::int32_t type) {return dr_session_class_select(session_,type);}
bool Bridge::class_race(std::int32_t race) {return dr_session_class_set_race(session_,race);}
void Bridge::class_perk(std::int32_t slot,std::int32_t perk) {dr_session_class_set_perk(session_,slot,perk);}
void Bridge::class_flaw(std::int32_t slot,std::int32_t flaw) {dr_session_class_set_flaw(session_,slot,flaw);}
void Bridge::class_skill(std::int32_t slot,std::int32_t skill) {dr_session_class_set_skill(session_,slot,skill);}
void Bridge::class_help(std::int32_t tab) {dr_session_class_help(session_,tab);}
void Bridge::class_done() {dr_session_class_done(session_);}
void Bridge::class_open() {dr_session_class_open(session_);}
void Bridge::setup_back() {dr_session_setup_back(session_);}
void Bridge::queue_sound(std::int32_t sound) {dr_session_queue_sound(session_,sound);}
bool Bridge::next_sound(std::int32_t& sound,std::int32_t& variant) {return dr_session_next_sound(session_,&sound,&variant);}
bool Bridge::continue_game(std::uint32_t seed) {
    if(!dr_session_continue_game(session_,seed))return false;
    objects().screens->main_menu_c400=0;started_=true;route_=FrameRoute::Done;return true;
}
bool Bridge::has_save() {return objects().end->flag_146d0!=0;}
void Bridge::leave_game_over() {
    const SessionObjects o=objects();o.end->game_over_screen=0;o.screens->game_over_state_cc1c=0;started_=false;
}
FrameRoute Bridge::frame(float dt,std::int32_t phase,Point touch,std::int32_t skill_button,std::int32_t menu_button) {
    const SessionObjects o=objects();
    *o.skill_button=skill_button;*o.menu_button=menu_button;
    o.release_inputs->health_target=resource_target(0);
    route_=dr_session_frame(session_,dt,phase,touch);++frames_;
    return route_;
}
std::vector<Blob> Bridge::take_changed() {
    std::vector<Blob> out;const SessionObjects o=objects();
    if(o.end->flag_146d4) {   // the saved game changed (length 0: no saved game)
        const auto n=static_cast<std::size_t>(o.end->flag_146d0);
        out.push_back({"game",std::vector<std::uint8_t>(o.save,o.save+(n<=save_capacity?n:0))});o.end->flag_146d4=0;
    }
    if(o.class_save->changed_14adc) {
        const auto n=static_cast<std::size_t>(o.class_save->length_14ad8);
        out.push_back({"classes",std::vector<std::uint8_t>(o.class_save->bytes,o.class_save->bytes+(n<=class_save_capacity?n:0))});
        o.class_save->changed_14adc=0;
    }
    for(std::int32_t type;(type=dr_session_save_changed_scores(session_))>=0;) {
        const auto n=static_cast<std::size_t>(o.scores->length);
        out.push_back({"scores"+std::to_string(type),std::vector<std::uint8_t>(o.scores->bytes,o.scores->bytes+(n<=sizeof o.scores->bytes?n:0))});
    }
    SaveSettings& set=*o.settings;   // EAGLView drawView stores a switch whose changed flag is set, and clears it
    if(set.sound_changed_13ec7 || set.clock_changed_13ecc || set.dimming_changed_13ecd || set.framerate_changed_13ece) {
        out.push_back({"settings",{set.sound_13ec6,set.clock_13ec9,set.dimming_13eca,set.framerate_13ecb}});
        set.sound_changed_13ec7=set.clock_changed_13ecc=set.dimming_changed_13ecd=set.framerate_changed_13ece=0;
    }
    if(o.match->spawn_dirty_15555) {
        std::vector<std::uint8_t> b(4);std::memcpy(b.data(),&o.match->spawn_remaining_15558,4);
        out.push_back({"spawn",b});o.match->spawn_dirty_15555=0;
    }
    return out;
}
std::vector<int> pick_path(const SelectionState& s,std::uint32_t& seed) {
    auto next=[&seed](int n){seed=seed*1103515245u+12345u;return static_cast<int>((seed>>16)%static_cast<std::uint32_t>(n));};
    std::vector<int> best;
    for(int start=0;start<36;++start)for(int tries=0;tries<4;++tries) {
        if(s.tiles[start].rule.flag_255)continue;
        std::vector<int> path{start};const RuleTile* rules[36]{&s.tiles[start].rule};
        while(path.size()<12) {
            std::vector<int> options;const int x=path.back()%6,y=path.back()/6;
            for(int ny=y-1;ny<=y+1;++ny)for(int nx=x-1;nx<=x+1;++nx) {
                const int n=ny*6+nx;
                if(nx<0||nx>5||ny<0||ny>5||n==path.back())continue;
                bool used=false;for(int p:path)used|=p==n;
                if(!used && !s.tiles[n].rule.flag_255 && dr_can_match(&s.tiles[n].rule,rules,path.size(),true))options.push_back(n);
            }
            if(options.empty())break;
            const int n=options[static_cast<std::size_t>(next(static_cast<int>(options.size())))];
            rules[path.size()]=&s.tiles[n].rule;path.push_back(n);
        }
        if(path.size()>best.size())best=path;
    }
    if(best.size()<3)best.clear();
    return best;
}
}
