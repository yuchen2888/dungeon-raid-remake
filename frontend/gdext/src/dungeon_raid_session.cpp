#include "dungeon_raid_session.hpp"
#include "front_requests.hpp"
#include "recovered_tokens.hpp"
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/packed_color_array.hpp>
#include <godot_cpp/variant/packed_vector2_array.hpp>
#include <cstdio>
#include <ctime>
using namespace godot;
using namespace dungeonraid;
namespace {
Vector2 v(Point p) {return Vector2(p.x,p.y);}
PackedInt32Array ints(const std::int32_t* p,int n) {PackedInt32Array a;a.resize(n);for(int i=0;i<n;++i)a.set(i,p[i]);return a;}
Dictionary skill(const SkillRecord& s) {
    Dictionary d;
    d["type"]=s.type;d["level"]=s.level;d["max"]=s.max;d["current"]=s.current;d["active"]=s.active!=0;d["lines"]=s.lines;
    d["health"]=s.health;d["healing"]=s.healing;d["shield"]=s.shield;d["damage"]=s.damage;d["chance"]=ints(s.chance,4);
    return d;
}
Dictionary item(const ItemRecord& r) {
    Dictionary d;
    d["type"]=r.type;d["icon"]=r.icon;d["prefix_level"]=r.prefix_level;d["prefix"]=r.prefix;d["name"]=r.name;
    d["stats"]=ints(r.stats.upgrade,20);
    return d;
}
}
DungeonRaidSession::DungeonRaidSession():bridge_(std::make_unique<drfront::Bridge>()) {
    bridge_->seed(static_cast<std::uint32_t>(std::time(nullptr)));   // Game::Start, before the stored blobs come back
    bridge_->platform_defaults();
}
void DungeonRaidSession::restore(const String& key,const PackedByteArray& bytes) {
    drfront::Blob b{key.utf8().get_data(),std::vector<std::uint8_t>(bytes.ptr(),bytes.ptr()+bytes.size())};
    bridge_->restore(b);
}
void DungeonRaidSession::new_game(int kind,int seed) {bridge_->new_game(kind,static_cast<std::uint32_t>(seed));}
bool DungeonRaidSession::continue_game(int seed) {return bridge_->continue_game(static_cast<std::uint32_t>(seed));}
bool DungeonRaidSession::has_save() {return bridge_->has_save();}
Dictionary DungeonRaidSession::setup() {
    const SessionObjects o=bridge_->objects();const SetupScreen& n=*o.setup;
    Dictionary d;
    d["open"]=o.screens->name_12c09!=0;d["intro"]=o.screens->intro_c3f0!=0;d["challenge"]=n.challenge!=0;
    d["name"]=String::utf8(n.name,n.length>=0 && n.length<19?n.length:0);d["named"]=n.named!=0;
    d["class"]=static_cast<int>(o.scroll->current);d["difficulty"]=o.match->spawn_enabled_14ae0;d["mode"]=o.stroke->mode_14ae8;
    Array classes;
    for(int i=0;i<10;++i) {
        Dictionary c;c["type"]=o.classes[i].class_type;c["level"]=o.classes[i].level;c["unlocked"]=o.classes[i].level!=0;
        c["games"]=static_cast<int64_t>(o.classes[i].games_played);classes.push_back(c);
    }
    d["classes"]=classes;
    return d;
}
void DungeonRaidSession::setup_random_name() {bridge_->setup_random_name();}
bool DungeonRaidSession::setup_select_class(int type) {return bridge_->setup_select_class(type);}
bool DungeonRaidSession::setup_difficulty(int difficulty) {return bridge_->setup_difficulty(difficulty);}
bool DungeonRaidSession::setup_mode(int mode) {return bridge_->setup_mode(mode);}
bool DungeonRaidSession::setup_start(int seed) {return bridge_->setup_start(static_cast<std::uint32_t>(seed));}
void DungeonRaidSession::intro_done() {bridge_->intro_done();}
int DungeonRaidSession::frame(double dt,int phase,Vector2 touch,int skill_button,int menu_button) {
    if(ui_)ui_->dt=static_cast<float>(dt);   // Interface::Process gets the frame's dt
    *bridge_->objects().time=static_cast<std::uint32_t>(std::time(nullptr));   // the platform's time() (new games' seeds)
    const auto route=bridge_->frame(static_cast<float>(dt),phase,Point{touch.x,touch.y},skill_button,menu_button);
    if(ui_)run_front_requests(*bridge_,*ui_);
    sounds_.clear();
    if(ui_)ui_->finish_frame(bridge_->objects());
    for(std::int32_t s,v;bridge_->next_sound(s,v);) {   // EAGLView drawView: each queued sound and its variant
        if(v<0)continue;   // (a sound without files)
        Array a;a.push_back(s);a.push_back(v);sounds_.push_back(a);
    }
    return static_cast<int>(route);
}
Array DungeonRaidSession::sounds() {return sounds_;}
Array DungeonRaidSession::take_changed() {
    Array out;
    for(auto& b:bridge_->take_changed()) {
        PackedByteArray bytes;bytes.resize(static_cast<std::int64_t>(b.bytes.size()));
        for(std::size_t i=0;i<b.bytes.size();++i)bytes.set(static_cast<std::int64_t>(i),b.bytes[i]);
        Array pair;pair.push_back(String(b.key.c_str()));pair.push_back(bytes);out.push_back(pair);
    }
    return out;
}
Array DungeonRaidSession::board() {
    const SessionObjects o=bridge_->objects();Array out;
    for(int i=0;i<36;++i) {
        const SelectionTile& t=o.stroke->selection.tiles[i];const PathCombatTile& c=o.path->combat[i];
        const PotionFlags& potion=o.preview->potions[i];
        Dictionary d;
        d["type"]=t.rule.type;d["special"]=t.rule.special_type;d["enemy_type"]=t.rule.enemy_type;d["enemy_state"]=t.rule.enemy_state;
        d["x"]=t.rule.x;d["y"]=t.rule.y;d["pos"]=v(t.geometry.center);d["size"]=t.size;
        d["selected"]=t.selected!=0;d["dimmed"]=o.dimmed[i]!=0;d["arrow"]=t.rule.flag_231!=0;d["frozen"]=c.overlay!=0;
        d["magic_sword"]=t.magic_sword!=0;d["broken"]=t.broken!=0;d["flaming"]=t.flaming!=0;d["flame_damage"]=t.flame_damage;
        d["mana"]=potion.flag_232!=0;d["explosive"]=potion.flag_234!=0;
        d["attack"]=c.attack;d["defence"]=c.defence;d["health"]=c.health;d["max_health"]=o.generation->tiles[i].max_health;
        d["poison"]=c.poison.current;d["variant"]=o.generation->tiles[i].variant;
        out.push_back(d);
    }
    return out;
}
PackedInt32Array DungeonRaidSession::path() {
    const SelectionState& s=bridge_->objects().stroke->selection;PackedInt32Array a;
    for(std::size_t i=0;i<s.path_length;++i)a.push_back(s.path[i]);
    return a;
}
Dictionary DungeonRaidSession::state() {
    const SessionObjects o=bridge_->objects();const ResourceState& r=*o.resources;const SelectionState& s=o.stroke->selection;
    Dictionary d;
    d["started"]=bridge_->started();d["route"]=static_cast<int>(bridge_->last_route());
    d["health"]=r.health;d["health_max"]=r.health_max+r.health_bonus;d["armour"]=o.preview->armour_current;d["armour_max"]=o.preview->armour_max;
    d["xp"]=r.xp;d["gold"]=r.gold;d["up"]=r.up;d["level"]=r.level;d["poison"]=r.poison;
    d["total_xp"]=r.total_xp;d["total_gold"]=r.total_gold;d["total_up"]=r.total_up;
    d["turn"]=o.path->turn;d["path_length"]=static_cast<int>(o.stroke->selection.path_length);d["input_ready"]=o.path->input_ready!=0;d["kills"]=o.path->battle.kill_count_165b4;
    d["attack_phase"]=o.damage->phase;d["incoming_damage"]=o.damage->incoming_damage;
    d["falling"]=static_cast<int>(o.falling_count);d["tokens_pending"]=static_cast<int>(dr_token_queue_counters(o.tokens)->pending);
    d["game_over"]=o.end->game_over_screen!=0;d["victory"]=o.end->victory!=0;d["has_save"]=o.end->flag_146d0!=0;
    d["menu_open"]=o.screens->menus[0]!=0;d["game_menu_open"]=o.screens->menus[1]!=0;d["stats_menu_open"]=o.screens->menus[2]!=0;
    d["main_menu"]=o.screens->main_menu_c400!=0;d["help_open"]=o.screens->help_102a4!=0;
    d["high_framerate"]=o.settings->framerate_13ecb!=0;d["sound"]=o.settings->sound_13ec6!=0;
    d["current_damage"]=s.current_damage;d["weapon_damage"]=s.weapon_damage;d["base_damage"]=s.base_damage+s.bonus_base_damage;
    d["counts"]=ints(o.stroke->resource_counts_164b0,6);
    d["record"]=o.stroke->record_14aed!=0;d["class"]=static_cast<int>(o.scroll->current);
    d["skill_pressed"]=o.skill_input->pressed;d["events"]=static_cast<int64_t>(bridge_->events());
    return d;
}
Array DungeonRaidSession::skills() {
    const SessionObjects o=bridge_->objects();Array out;
    for(int i=0;i<o.resources->skill_count && i<4;++i) {
        Dictionary d;
        d["type"]=o.skills->id[i];d["level"]=o.skills->level[i];d["active"]=o.skills->active[i]!=0;
        d["max"]=o.resources->skill_max[i];d["current"]=o.resources->skill_current[i];
        d["ready"]=o.resources->skill_current[i]==o.resources->skill_max[i];
        out.push_back(d);
    }
    return out;
}
Dictionary DungeonRaidSession::menu() {
    const SessionObjects o=bridge_->objects();const MenuState& m=*o.menu;
    Dictionary d;
    d["open"]=o.screens->menus[0]!=0;d["type"]=m.type;d["first"]=m.first;d["second"]=m.second;d["timer"]=m.timer;
    d["opening"]=m.opening!=0;d["confirm_ready"]=m.confirm_ready!=0;d["confirm_pressed"]=m.confirm_pressed!=0;
    d["skill_options"]=m.skill_options;
    Array options;for(const auto& s:m.options)options.push_back(skill(s));d["options"]=options;
    Array shop;for(const auto& it:m.items)shop.push_back(item(it));d["items"]=shop;
    d["scroll_slot"]=m.scroll_slot;d["scroll"]=skill(m.scroll);
    d["upgrade_items"]=ints(m.upgrade_items,4);d["upgrade_type"]=ints(m.upgrade_type,4);d["upgrade_amount"]=ints(m.upgrade_amount,4);
    return d;
}
Array DungeonRaidSession::items() {
    const SessionObjects o=bridge_->objects();Array out;
    for(int i=0;i<5;++i)out.push_back(item(o.items[i]));
    return out;
}
Array DungeonRaidSession::tokens() {
    const SessionObjects o=bridge_->objects();Array out;
    for(std::uint32_t i=0;i<o.motion_count;++i) {
        const TokenMotion& t=o.motions[i];if(!t.active)continue;
        Dictionary d;d["pos"]=v(t.position);d["scale"]=v(t.scale);d["reward_type"]=t.reward_type;d["token_type"]=t.token_type;
        out.push_back(d);
    }
    return out;
}
Array DungeonRaidSession::labels() {
    const SessionObjects o=bridge_->objects();Array out;
    for(int i=0;i<3;++i) {
        const SimpleLabelState& l=o.damage_labels[i];if(!o.extra->label_active[i])continue;
        Dictionary d;d["kind"]=i;d["type"]=l.type;d["pos"]=Vector2(l.x,l.y);d["scale"]=l.scale;d["number"]=l.number;d["alpha"]=l.alpha;
        out.push_back(d);
    }
    return out;
}
PackedInt32Array DungeonRaidSession::hint() {
    PackedInt32Array a;for(int i:drfront::pick_path(bridge_->objects().stroke->selection,hint_seed_))a.push_back(i);
    return a;
}
namespace {
struct Hooks {
    static void listen(void* c,SessionSource s,const void* e) {
        auto& d=*static_cast<std::pair<drfront::Bridge*,drui::Presenter*>*>(c);d.second->event(d.first->objects(),s,e);
    }
    static Point resource(void* c,std::int32_t type) {
        return static_cast<std::pair<drfront::Bridge*,drui::Presenter*>*>(c)->second->iface.target(type);
    }
    static Point slot(void* c,std::int32_t i) {
        return static_cast<std::pair<drfront::Bridge*,drui::Presenter*>*>(c)->second->iface.special_target(i);
    }
};
}
bool DungeonRaidSession::load_presentation(const String& assets,const String& language) {
    ui_=std::make_unique<drui::Presenter>();
    const bool ok=ui_->load(assets.utf8().get_data(),language.utf8().get_data());
    ui_->main_menu.start_cycling();   // EAGLView startAnimation: "more games" cycles its colour
    link_=std::make_unique<std::pair<drfront::Bridge*,drui::Presenter*>>(bridge_.get(),ui_.get());
    bridge_->set_listener(link_.get(),Hooks::listen);
    bridge_->set_targets(link_.get(),Hooks::resource,Hooks::slot);
    ui_->set_sound_sink(bridge_.get(),[](void* c,std::int32_t s){static_cast<drfront::Bridge*>(c)->queue_sound(s);});
    return ok;
}
Array DungeonRaidSession::render(double scale) {
    Array out;
    if(!ui_)return out;
    const SessionObjects o=bridge_->objects();
    if(o.settings->clock_13ec9) {   // EAGLView drawView: the time (NSDateFormatter short time style; English, as the
        const std::time_t now=std::time(nullptr);   // original's texts)
        std::tm t{};localtime_r(&now,&t);
        char text[16];std::snprintf(text,sizeof text,"%d:%02d %s",(t.tm_hour+11)%12+1,t.tm_min,t.tm_hour<12?"AM":"PM");
        ui_->set_clock(o,text);
    } else ui_->set_clock(o,"");
    ui_->render(o);
    const auto& draws=ui_->gl.draws();const auto& verts=ui_->gl.vertices();
    std::int32_t texture=-1;
    PackedVector2Array points,uvs;PackedColorArray colours;PackedInt32Array indices;
    const auto flush=[&]() {
        if(texture<0 || indices.is_empty())return;
        Array b;b.push_back(texture);b.push_back(points);b.push_back(colours);b.push_back(uvs);b.push_back(indices);out.push_back(b);
        points=PackedVector2Array();uvs=PackedVector2Array();colours=PackedColorArray();indices=PackedInt32Array();
    };
    for(const auto& d:draws) {
        if(d.texture!=texture){flush();texture=d.texture;}
        const std::int32_t base=static_cast<std::int32_t>(points.size());
        for(std::uint32_t k=0;k<d.count;++k) {
            const auto& v=verts[d.first+k];
            points.push_back(Vector2(static_cast<real_t>(v.x*scale),static_cast<real_t>(v.y*scale)));
            uvs.push_back(Vector2(v.u,v.v));
            colours.push_back(Color(v.colour[0]/255.0f,v.colour[1]/255.0f,v.colour[2]/255.0f,v.colour[3]/255.0f));
        }
        const std::int32_t n=static_cast<std::int32_t>(d.count);
        if(d.mode==5)for(std::int32_t k=0;k+2<n;++k) {   // triangle strip
            indices.push_back(base+k);indices.push_back(base+k+1);indices.push_back(base+k+2);
        } else if(d.mode==6)for(std::int32_t k=1;k+1<n;++k) {   // triangle fan
            indices.push_back(base);indices.push_back(base+k);indices.push_back(base+k+1);
        } else if(d.mode==4)for(std::int32_t k=0;k+2<n;k+=3) {
            indices.push_back(base+k);indices.push_back(base+k+1);indices.push_back(base+k+2);
        }
    }
    flush();
    return out;
}
int DungeonRaidSession::skill_button_at(Vector2 touch) {
    return ui_?ui_->skill_button_at(bridge_->objects(),Point{touch.x,touch.y}):-1;
}
int DungeonRaidSession::menu_button_at(Vector2 touch) {
    if(!ui_)return -1;
    return ui_->menu_button_at(bridge_->objects(),Point{touch.x,touch.y});
}
void DungeonRaidSession::leave_game_over() {bridge_->leave_game_over();}
bool DungeonRaidSession::settings_open() {return ui_ && ui_->settings.is_open();}
void DungeonRaidSession::settings_configure(const PackedInt32Array& name_rows,int language,double volume,bool vibration,
                                            bool hd,bool fast) {
    if(!ui_)return;
    std::vector<std::int32_t> rows;
    for(int64_t i=0;i<name_rows.size();++i)rows.push_back(name_rows[i]);
    drui::SettingsValues v;v.language=language;v.volume=static_cast<float>(volume);v.vibration=vibration;v.hd=hd;v.fast=fast;
    ui_->settings.configure(rows,v);
}
Dictionary DungeonRaidSession::settings_values() {
    Dictionary d;
    if(!ui_)return d;
    const drui::SettingsValues& v=ui_->settings.values();
    d["language"]=v.language;d["volume"]=v.volume;d["vibration"]=v.vibration;d["hd"]=v.hd;d["fast"]=v.fast;
    return d;
}
int DungeonRaidSession::settings_touch(int phase,Vector2 touch) {
    if(!ui_)return -1;
    const SessionObjects o=bridge_->objects();
    const int r=ui_->settings.touch(phase,Point{touch.x,touch.y},*o.settings);
    if(r==drui::SettingsView::Switch)ui_->iface.set_clock_state(o.settings->clock_13ec9!=0);   // (Game::SetClockState)
    if(r>=0 && r!=drui::SettingsView::Volume)ui_->queue_sound(0);   // (a button's sound, as the original's menus)
    return r;
}
bool DungeonRaidSession::scores_open() {return bridge_->objects().screens->score_ef6c!=0;}
bool DungeonRaidSession::main_menu_open() {
    const SessionObjects o=bridge_->objects();
    return o.screens->main_menu_c400 && !o.screens->score_ef6c && !o.screens->name_12c09;
}
void DungeonRaidSession::_bind_methods() {
    ClassDB::bind_method(D_METHOD("restore","key","bytes"),&DungeonRaidSession::restore);
    ClassDB::bind_method(D_METHOD("new_game","kind","seed"),&DungeonRaidSession::new_game);
    ClassDB::bind_method(D_METHOD("continue_game","seed"),&DungeonRaidSession::continue_game);
    ClassDB::bind_method(D_METHOD("has_save"),&DungeonRaidSession::has_save);
    ClassDB::bind_method(D_METHOD("setup"),&DungeonRaidSession::setup);
    ClassDB::bind_method(D_METHOD("setup_random_name"),&DungeonRaidSession::setup_random_name);
    ClassDB::bind_method(D_METHOD("setup_select_class","type"),&DungeonRaidSession::setup_select_class);
    ClassDB::bind_method(D_METHOD("setup_difficulty","difficulty"),&DungeonRaidSession::setup_difficulty);
    ClassDB::bind_method(D_METHOD("setup_mode","mode"),&DungeonRaidSession::setup_mode);
    ClassDB::bind_method(D_METHOD("setup_start","seed"),&DungeonRaidSession::setup_start);
    ClassDB::bind_method(D_METHOD("intro_done"),&DungeonRaidSession::intro_done);
    ClassDB::bind_method(D_METHOD("frame","dt","phase","touch","skill_button","menu_button"),&DungeonRaidSession::frame);
    ClassDB::bind_method(D_METHOD("take_changed"),&DungeonRaidSession::take_changed);
    ClassDB::bind_method(D_METHOD("sounds"),&DungeonRaidSession::sounds);
    ClassDB::bind_method(D_METHOD("board"),&DungeonRaidSession::board);
    ClassDB::bind_method(D_METHOD("path"),&DungeonRaidSession::path);
    ClassDB::bind_method(D_METHOD("state"),&DungeonRaidSession::state);
    ClassDB::bind_method(D_METHOD("skills"),&DungeonRaidSession::skills);
    ClassDB::bind_method(D_METHOD("menu"),&DungeonRaidSession::menu);
    ClassDB::bind_method(D_METHOD("items"),&DungeonRaidSession::items);
    ClassDB::bind_method(D_METHOD("tokens"),&DungeonRaidSession::tokens);
    ClassDB::bind_method(D_METHOD("labels"),&DungeonRaidSession::labels);
    ClassDB::bind_method(D_METHOD("hint"),&DungeonRaidSession::hint);
    ClassDB::bind_method(D_METHOD("load_presentation","assets","language"),&DungeonRaidSession::load_presentation,DEFVAL(String()));
    ClassDB::bind_method(D_METHOD("render","scale"),&DungeonRaidSession::render);
    ClassDB::bind_method(D_METHOD("skill_button_at","touch"),&DungeonRaidSession::skill_button_at);
    ClassDB::bind_method(D_METHOD("menu_button_at","touch"),&DungeonRaidSession::menu_button_at);
    ClassDB::bind_method(D_METHOD("main_menu_open"),&DungeonRaidSession::main_menu_open);
    ClassDB::bind_method(D_METHOD("settings_configure","name_rows","language","volume","vibration","hd","fast"),
                         &DungeonRaidSession::settings_configure);
    ClassDB::bind_method(D_METHOD("settings_values"),&DungeonRaidSession::settings_values);
    ClassDB::bind_method(D_METHOD("settings_open"),&DungeonRaidSession::settings_open);
    ClassDB::bind_method(D_METHOD("settings_touch","phase","touch"),&DungeonRaidSession::settings_touch);
    ClassDB::bind_method(D_METHOD("scores_open"),&DungeonRaidSession::scores_open);
    ClassDB::bind_method(D_METHOD("leave_game_over"),&DungeonRaidSession::leave_game_over);
}
