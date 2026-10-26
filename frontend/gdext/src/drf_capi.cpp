#include "front_requests.hpp"
#include "ui/presenter.hpp"
#include <cstring>
// A C face of the front end for the reference checks (frontend/tools/lockstep.py, ctypes): the same inputs go to
// the original in the emulator and to this, frame by frame, and the drawings are compared. Built by build.py as
// build/libdrf_check.dylib; not part of the game.
using namespace dungeonraid;
namespace {
struct Front {
    drfront::Bridge bridge;
    drui::Presenter ui;
    std::vector<std::int32_t> sounds;   // the last frame's sounds, as the platform takes them (dr_session_next_sound)
    static void listen(void* c,SessionSource s,const void* e) {Front& f=*static_cast<Front*>(c);f.ui.event(f.bridge.objects(),s,e);}
    static Point resource(void* c,std::int32_t type) {return static_cast<Front*>(c)->ui.iface.target(type);}
    static Point slot(void* c,std::int32_t i) {return static_cast<Front*>(c)->ui.iface.special_target(i);}
};
}
extern "C" {
// language: a language folder as the game's load_presentation takes it, or "" (T050-K: the languages' screens
// looked at without the simulator).
Front* drf_create_language(const char* assets,const char* language) {
    Front* f=new Front();f->ui.load(assets,language);f->bridge.set_listener(f,Front::listen);
    f->bridge.set_targets(f,Front::resource,Front::slot);
    f->ui.set_sound_sink(f,[](void* c,std::int32_t s){static_cast<Front*>(c)->bridge.queue_sound(s);});
    return f;
}
Front* drf_create(const char* assets) {return drf_create_language(assets,"");}
// Game::Start's seeding from the platform's time() (the emulated original's), once after drf_create.
void drf_seed(Front* f,std::uint32_t time) {f->bridge.seed(time);}
void drf_destroy(Front* f) {delete f;}
// A stored blob back, as the platform's start-up gives it (Bridge::restore: "classes", "scores0".., "game", "spawn").
void drf_restore(Front* f,const char* key,const std::uint8_t* bytes,std::uint32_t length) {
    f->bridge.restore(drfront::Blob{key,std::vector<std::uint8_t>(bytes,bytes+length)});
}
// The platform's time() the main menu's games seed with (SessionObjects.time).
void drf_set_time(Front* f,std::uint32_t t) {*f->bridge.objects().time=t;}
// FrameScreens: help, unlock, main menu, scores, setup, story.
void drf_screens(Front* f,std::int32_t* out) {
    const FrameScreens& s=*f->bridge.objects().screens;
    out[0]=s.help_102a4;out[1]=s.unlock_165a0;out[2]=s.main_menu_c400;out[3]=s.score_ef6c;out[4]=s.name_12c09;out[5]=s.intro_c3f0;
}
void drf_new_game(Front* f,std::int32_t kind,std::uint32_t seed) {f->bridge.new_game(kind,seed);}
void drf_setup_random_name(Front* f) {f->bridge.setup_random_name();}
bool drf_setup_start(Front* f,std::uint32_t seed) {return f->bridge.setup_start(seed);}
void drf_intro_done(Front* f) {f->bridge.intro_done();}
// skill / menu -2: the skill / menu button under the touch as the drawing hit-tests it (the game passes them so).
std::int32_t drf_frame(Front* f,float dt,std::int32_t phase,float x,float y,std::int32_t skill,std::int32_t menu) {
    f->ui.dt=dt;
    if(skill==-2)skill=phase?f->ui.skill_button_at(f->bridge.objects(),Point{x,y}):-1;
    const SessionObjects o=f->bridge.objects();
    const bool main_menu=o.screens->main_menu_c400 && !o.screens->score_ef6c && !o.screens->name_12c09;
    // (the main menu and the high scores act on the button under the last touch the frame after it ends)
    if(menu==-2)menu=phase || main_menu || o.screens->score_ef6c?f->ui.menu_button_at(o,Point{x,y}):-1;
    const auto route=f->bridge.frame(dt,phase,Point{x,y},skill,menu);
    run_front_requests(f->bridge,f->ui);
    f->ui.finish_frame(f->bridge.objects());
    f->sounds.clear();   // EAGLView drawView: every queued sound (its variant drawn); nothing plays here
    for(std::int32_t s,v;f->bridge.next_sound(s,v);)f->sounds.push_back(s);
    return static_cast<std::int32_t>(route);
}
// The board as the original stores it (type, special type, enemy type, enemy state, variant, glow flag per tile),
// and a few counters: turn, health, xp, gold, up, level, the menu open byte, the game-over byte.
void drf_board(Front* f,std::int32_t* out) {
    const SessionObjects o=f->bridge.objects();
    for(int i=0;i<36;++i) {
        const RuleTile& r=o.stroke->selection.tiles[i].rule;const GeneratedTile& g=o.generation->tiles[i];
        std::int32_t* t=out+6*i;
        t[0]=r.type;t[1]=r.special_type;t[2]=r.enemy_type;t[3]=r.enemy_state;t[4]=g.variant;t[5]=g.flag_224;
    }
}
// Per tile: attack, defence, health, max health (PathCombatTile, GeneratedTile).
void drf_combat(Front* f,std::int32_t* out) {
    const SessionObjects o=f->bridge.objects();
    for(int i=0;i<36;++i){const PathCombatTile& c=o.path->combat[i];out[4*i]=c.attack;out[4*i+1]=c.defence;out[4*i+2]=c.health;out[4*i+3]=o.generation->tiles[i].max_health;}
}
void drf_counters(Front* f,std::int32_t* out) {
    const SessionObjects o=f->bridge.objects();
    out[0]=o.path->turn;out[1]=o.resources->health;out[2]=o.resources->xp;out[3]=o.resources->gold;out[4]=o.resources->up;
    out[5]=o.resources->level;out[6]=o.screens->menus[0];out[7]=o.end->game_over_screen;
}
// Game::Render into the recorder; the number of draws. drf_draw gives one (texture, mode, first vertex, count);
// drf_vertices all vertices as 8 doubles each (x, y, u, v, r, g, b, a).
std::int32_t drf_render(Front* f) {f->ui.render(f->bridge.objects());return static_cast<std::int32_t>(f->ui.gl.draws().size());}
void drf_draw(Front* f,std::int32_t i,std::int32_t* out) {
    const drui::Draw& d=f->ui.gl.draws()[static_cast<std::size_t>(i)];
    out[0]=d.texture;out[1]=d.mode;out[2]=static_cast<std::int32_t>(d.first);out[3]=static_cast<std::int32_t>(d.count);out[4]=d.blend;
    out[5]=d.tag;
}
// The last frame's sounds (the session's queue as drf_frame took it): the count, the first max into out.
std::int32_t drf_sounds(Front* f,std::int32_t* out,std::int32_t max) {
    const auto& q=f->sounds;
    for(std::size_t i=0;i<q.size() && static_cast<std::int32_t>(i)<max;++i)out[i]=q[i];
    return static_cast<std::int32_t>(q.size());
}
// For the checks only: what a class scroll's UnlockMenu::Show(type, level) does (the session's ReleaseEventKind::UnlockMenu
// -- its unlock_show: open, not closing, the touch counted as down -- and the picture's Show), so the popup can be
// compared without waiting for a class scroll on the board.
void drf_test_unlock(Front* f,std::int32_t type,std::int32_t level) {
    const SessionObjects o=f->bridge.objects();
    f->bridge.queue_sound(12);o.screens->unlock_165a0=1;o.unlock->closing=0;o.unlock->previous_phase=1;
    const ReleaseEvent e{ReleaseEventKind::UnlockMenu,-1,type,level,0,0,0.0f,0.0f};
    f->ui.event(o,SessionSource::Release,&e);
}
// Debugging: an Interface int at its original offset.
std::int32_t drf_iface_i(Front* f,std::int32_t off) {return f->ui.iface.i(static_cast<std::size_t>(off));}
// Debug counts for the checks: 0 the session's flare count, 1 flare quads, 2 particles in use, 3 labels in use,
// 4 the attack phase.
std::int32_t drf_debug(Front* f,std::int32_t what) {
    const SessionObjects o=f->bridge.objects();
    switch(what) {
    case 0: return o.animation->flare_count;
    case 1: return static_cast<std::int32_t>(f->ui.flares.size());
    case 2: return f->ui.particles.count;
    case 3: return f->ui.labels.count;
    case 4: return o.damage->phase;
    default: break;
    }
    // 5.. : AttackAnimation bd5c, bd60, bd64, bd68, bd7c, bd6c, bd70 as float bits
    const float* fields[]={&o.animation->bd5c,&o.animation->bd60,&o.animation->bd64,&o.animation->bd68,&o.animation->bd7c,
                           &o.animation->bd6c,&o.animation->bd70};
    if(what>=5 && what<12) {std::int32_t b;std::memcpy(&b,fields[what-5],4);return b;}
    // 20.. : the current class record's perks, flaws, then the views' perks and flaws, the current class and its race
    const ClassProfile& c=o.classes[o.scroll->current];
    if(what>=20 && what<24)return c.perks[what-20];
    if(what>=24 && what<28)return c.flaws[what-24];
    if(what>=28 && what<32)return o.match->perks[what-28];
    if(what>=32 && what<36)return o.stroke->selection.character.flaws[what-32];
    if(what==36)return static_cast<std::int32_t>(o.scroll->current);
    if(what==37)return c.race;
    switch(what) {
    default: return 0;
    }
}
std::int32_t drf_vertices(Front* f,double* out) {
    const auto& v=f->ui.gl.vertices();
    for(std::size_t i=0;i<v.size();++i) {
        double* o=out+8*i;o[0]=v[i].x;o[1]=v[i].y;o[2]=v[i].u;o[3]=v[i].v;
        for(int k=0;k<4;++k)o[4+k]=v[i].colour[k];
    }
    return static_cast<std::int32_t>(v.size());
}
}
