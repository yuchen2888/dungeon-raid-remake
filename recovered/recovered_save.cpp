#include "recovered_save.hpp"
#include "recovered_random.hpp"
#include <algorithm>
#include <cstring>
using namespace dungeonraid;
namespace {
struct Writer {
    std::uint8_t* p;
    void byte(std::int32_t v) {*p++=static_cast<std::uint8_t>(v);}
    void word(std::uint32_t v) {for(int i=0;i<4;++i)*p++=static_cast<std::uint8_t>(v>>(8*i));}
};
// The first icon of each item type's range (the icon tables at 0x1d6860..: types 0, 1, 3, 2, 4 in icon order).
std::int32_t icon_base(std::int32_t type) {
    switch(type) {case 0:return 0;case 1:return 80;case 2:return 240;case 3:return 160;default:return 320;}
}
// Original Tile::Serialise 0x3d378: the kind byte (potion: explosive 1, mana 2, acid 3; sword: magic 1, broken 2,
// arrow 3; shield: broken 1; scroll: its special type; others none), frozen 1 / burning 2 (and the flame damage),
// and for a skull attack, defence, health, max health, enemy type, enemy state, flag_25d and its poison values up to
// the first zero.
void tile(Writer& w,const SaveSources* s,int i) {
    const SelectionTile& t=s->stroke->selection.tiles[i];const PotionFlags& p=s->preview->potions[i];
    const PathCombatTile& c=s->path->combat[i];
    switch(t.rule.type) {
    case 0:w.byte(p.flag_234?1:p.flag_232?2:p.flag_233?3:0);break;
    case 4:w.byte(t.magic_sword?1:t.broken?2:t.rule.flag_231?3:0);break;
    case 3:w.byte(t.broken?1:0);break;
    case 6:w.byte(t.rule.special_type);break;
    default:break;
    }
    w.byte(t.rule.flag_255?1:t.flaming?2:0);
    if(t.flaming)w.byte(t.flame_damage);
    if(t.rule.type!=1)return;
    w.word(static_cast<std::uint32_t>(c.attack));w.word(static_cast<std::uint32_t>(c.defence));w.word(static_cast<std::uint32_t>(c.health));
    w.word(static_cast<std::uint32_t>(s->generation->tiles[i].max_health));
    w.byte(t.rule.enemy_type);w.byte(t.rule.enemy_state);w.byte(s->match->flag_25d[i]);
    const std::int32_t poison[3]={c.poison.current,c.poison.next,c.poison.following};
    for(int k=0;k<3;++k){w.byte(poison[k]);if(!poison[k])break;}
}
// Original Item::Serialise 0x262b0: the icon within its type's range, prefix level, prefix, name, a bit mask of the
// non-zero stats and their values; more than seven: achievement 72.
void item(Writer& w,const ItemRecord& it,const SaveHooks* h) {
    w.byte(it.icon-icon_base(it.type));w.byte(it.prefix_level);w.byte(it.prefix);w.byte(it.name);
    std::uint32_t mask=0;int n=0;
    for(int k=0;k<20;++k)if(it.stats.upgrade[k])mask|=1u<<k;
    w.word(mask);
    for(int k=0;k<20;++k)if(it.stats.upgrade[k]){w.word(static_cast<std::uint32_t>(it.stats.upgrade[k]));++n;}
    if(n>7 && h && h->event)h->event(h->context,SaveEventKind::Achievement,72,0x42c80000);
}
struct Reader {
    const std::uint8_t* p;
    std::int32_t byte() {return *p++;}
    std::int32_t word() {std::uint32_t v=0;for(int i=0;i<4;++i)v|=static_cast<std::uint32_t>(*p++)<<(8*i);return static_cast<std::int32_t>(v);}
};
void event(const SaveHooks* h,SaveEventKind kind,std::int32_t a=-1,std::int32_t b=0) {if(h && h->event)h->event(h->context,kind,a,b);}
void tile_event(const SaveHooks* h,GenerationEventKind kind,std::uint32_t i,std::int32_t a=0,std::int32_t b=0,std::int32_t c=0,std::int32_t d=0) {
    const GenerationHooks* g=h->generation;
    if(g && g->event){const GenerationEvent e{kind,static_cast<std::int32_t>(i),a,b,c,d};g->event(g->context,&e);}
}
std::int32_t float_bits(float f) {std::int32_t b;std::memcpy(&b,&f,4);return b;}
// Tile::MakeExplosivePotion / MakeAcidPotion: the potion row of the atlas (UV, as the generation unit reports it).
void potion_uv(const SaveHooks* h,const SaveSources* s,std::uint32_t i,float row) {
    constexpr float cell=.0517578125f;
    tile_event(h,GenerationEventKind::UV,i,float_bits(static_cast<float>(s->generation->tiles[i].variant)*cell),
               float_bits(static_cast<float>(s->stroke->selection.tiles[i].rule.type)*cell+row),float_bits(cell),float_bits(cell));
}
// Original Tile::Deserialise2 0x3f48c (with = the format has a header).
void load_tile(Reader& r,const SaveSources* s,std::uint32_t i,bool with,const SaveHooks* h) {
    SelectionTile& t=s->stroke->selection.tiles[i];PathCombatTile& c=s->path->combat[i];
    GenerationState* g=s->generation;const GenerationHooks* gh=h->generation;
    switch(t.rule.type) {
    case 0: {
        const int k=r.byte();PotionFlags& f=s->preview->potions[i];
        if(k==1){potion_uv(h,s,i,.6044921875f);f.flag_234=1;}   // Tile::MakeExplosivePotion
        else if(k==2)dr_make_mana_potion(g,i,gh);
        else if(k==3){potion_uv(h,s,i,.552734375f);f.flag_233=1;}   // Tile::MakeAcidPotion
        break;
    }
    case 4: {
        const int k=r.byte();
        if(k==1){tile_event(h,GenerationEventKind::Colour,i,static_cast<std::int32_t>(0xffff9696u));t.magic_sword=1;}   // Tile::MakeMagicSword (150,150,255,255)
        else if(k==2)dr_make_broken(g,i,gh);
        else if(k==3)dr_make_arrow(g,i,gh);
        break;
    }
    case 3:if(with){if(r.byte()==1)dr_make_broken(g,i,gh);}break;
    case 6:dr_set_special_type(g,i,r.byte(),gh);break;
    default:break;
    }
    const int state=r.byte();
    if(state==1){t.rule.flag_255=1;c.overlay=1;t.flaming=0;event(h,SaveEventKind::Freeze,static_cast<std::int32_t>(i),1);}   // Tile::SetFreezeVisibility(true)
    else if(state==2)dr_set_flame_visibility(s->path,i,true,0,false,h->turn);
    if(t.flaming)t.flame_damage=r.byte();
    if(t.rule.type!=1)return;
    c.attack=r.word();c.defence=r.word();c.health=r.word();g->tiles[i].max_health=r.word();
    dr_update_generated_values(g,i,gh);
    t.rule.enemy_type=r.byte();t.rule.enemy_state=r.byte();s->match->flag_25d[i]=r.byte()==1;
    tile_event(h,GenerationEventKind::Countdown,i);tile_event(h,GenerationEventKind::EnemyUV,i);   // Tile::UpdateCountdown, UpdateEnemyUV
    std::int32_t* poison[3]={&c.poison.current,&c.poison.next,&c.poison.following};
    for(int k=0;k<3;++k){*poison[k]=r.byte();if(!*poison[k])break;}
    if(c.poison.current){c.poison.effect_active=1;c.poison.effect_progress_bits=0x3f800000;}
}
// Original Item::Deserialise2 0x29a04 (the item keeps its type).
void load_item(Reader& r,ItemRecord& it,std::int32_t slot,const SaveHooks* h) {
    it.icon=icon_base(it.type)+r.byte();it.prefix_level=r.byte();it.prefix=r.byte();it.name=r.byte();
    if(it.prefix_level==255)it.prefix_level=-1;
    if(it.prefix==255)it.prefix=-1;
    event(h,SaveEventKind::ItemIcon,slot);
    const std::uint32_t mask=static_cast<std::uint32_t>(r.word());   // Item::ClearStats, then the masked stats
    for(int k=0;k<20;++k)it.stats.upgrade[k]=(mask>>k)&1;
    for(int k=0;k<20;++k)if(it.stats.upgrade[k])it.stats.upgrade[k]=r.word();
}
}
extern "C" std::uint32_t dr_serialise_state(const SaveSources* s,std::uint8_t* buffer,const SaveHooks* h) {
    Writer w{buffer};const StrokeState& st=*s->stroke;const MatchState& m=*s->match;const ResourceState& r=*s->resources;
    const PathState& p=*s->path;const auto& sel=st.selection;
    w.byte(0xff);w.byte(3);
    w.byte(st.record_14aed?st.mode_14ae8:0xff);
    w.word(static_cast<std::uint32_t>(p.total));w.word(static_cast<std::uint32_t>(p.crossing_samples));
    w.byte(p.crossing_average);w.byte(p.crossing_best);
    w.byte(static_cast<std::int32_t>(s->scroll->current));
    ClassProfile current=s->scroll->classes[s->scroll->current];   // the class record as the units hold it
    current.race=sel.character.race;
    for(int k=0;k<4;++k){current.perks[k]=m.perks[k];current.flaws[k]=sel.character.flaws[k];}
    std::int32_t none[20];   // no replacement list: none replaced (as the menus read it)
    if(!current.replacement_skills){for(auto& v:none)v=255;current.replacement_skills=none;current.replacement_skill_count=20;}
    w.p+=dr_class_write_game(&current,w.p,save_capacity);
    w.byte(m.spawn_count_1555c);
    for(int i=0;i<36;i+=2)w.byte((sel.tiles[i].rule.type<<4)|sel.tiles[i+1].rule.type);
    for(int i=0;i<36;++i)tile(w,s,i);
    w.word(static_cast<std::uint32_t>(p.turn));w.word(static_cast<std::uint32_t>(p.battle.kill_count_165b4));
    w.byte(m.bonus_chance[2]);w.byte(m.bonus_chance[0]);w.byte(m.bonus_chance[1]);w.byte(m.bonus_chance[3]);   // be18, be20, be28, be30
    w.byte(r.poison);++w.p;w.byte(s->generation->time_to_promotion);
    for(int k=0;k<4;++k)w.word(static_cast<std::uint32_t>(s->extra->base_bde8[k]));
    const std::int32_t values[]={sel.base_damage,s->preview->shield_value,s->preview->healing_value,r.health_max,r.health,
        r.xp+r.total_xp,r.up+r.total_up,r.gold+r.total_gold,s->preview->armour_current};
    for(std::int32_t v:values)w.word(static_cast<std::uint32_t>(v));
    for(int k=0;k<5;++k)item(w,s->items[k],h);
    w.byte(r.skill_count);
    for(int k=0;k<r.skill_count;++k){w.byte(s->skills->id[k]);w.byte(r.skill_max[k]);w.byte(r.skill_current[k]);w.byte(s->skills->level[k]);}
    for(int k=0;k<17;++k){w.byte(s->name[k]);if(!s->name[k])break;}
    for(int k=1;k<6;++k)w.word(m.random.seeds[k]);
    w.word(s->finish->help_flags_102d0);
    w.byte(m.spawn_enabled_14ae0);
    return static_cast<std::uint32_t>(w.p-buffer);
}
extern "C" bool dr_deserialise_state(const SaveSources* s,const std::uint8_t* buffer,const SaveHooks* h) {
    if(buffer[0]!=0xff)return false;   // Game::DeserialiseState1: the format before version 1
    const int version=buffer[1];const bool with=version!=0;
    Reader r{buffer+2};StrokeState& st=*s->stroke;SelectionState& sel=st.selection;MatchState& m=*s->match;
    ResourceState& res=*s->resources;PathState& p=*s->path;GenerationState& g=*s->generation;ResourcePreviewState& pv=*s->preview;
    m.spawn_count_1555c=0;
    if(version>2) {
        const int mode=r.byte();st.record_14aed=mode!=0xff;
        if(st.record_14aed)st.mode_14ae8=std::clamp(mode,0,1);
        p.total=r.word();p.crossing_samples=r.word();p.crossing_average=r.byte();p.crossing_best=r.byte();
    } else {p.total=0;st.record_14aed=0;}
    if(version>1) {
        const std::size_t index=static_cast<std::size_t>(r.byte());s->scroll->current=index;
        ClassProfile& c=s->scroll->classes[index];
        std::int32_t none[20];   // no replacement list: read into a scratch one (as the menus read none)
        ClassProfile read=c;if(!read.replacement_skills){for(auto& v:none)v=255;read.replacement_skills=none;read.replacement_skill_count=20;}
        r.p+=dr_class_read_game(&read,r.p,save_capacity);
        c.race=read.race;std::copy(read.perks,read.perks+4,c.perks);std::copy(read.flaws,read.flaws+4,c.flaws);
        sel.character.race=c.race;std::copy(c.perks,c.perks+4,m.perks);std::copy(c.flaws,c.flaws+4,sel.character.flaws);   // the units' views
        m.class_type=c.class_type;m.class_level=c.level;
        m.spawn_count_1555c=r.byte();
    } else {
        s->scroll->current=0;const ClassProfile& c=s->scroll->classes[0];
        sel.character.race=c.race;std::copy(c.perks,c.perks+4,m.perks);std::copy(c.flaws,c.flaws+4,sel.character.flaws);
        m.class_type=c.class_type;m.class_level=c.level;
    }
    g.time_to_promotion=1;
    for(std::uint32_t i=0;i<36;++i) {   // Tile::SetType from the nibbles (high first)
        const int type=i%2?r.p[0]&15:r.p[0]>>4;if(i%2)++r.p;
        dr_set_tile_type(&g,i,type,0,m.spawn_enabled_14ae0,h->generation);
    }
    for(std::uint32_t i=0;i<36;++i)load_tile(r,s,i,with,h);
    p.turn=r.word();
    if(version>1)p.battle.kill_count_165b4=r.word();
    m.bonus_chance[2]=r.byte();m.bonus_chance[0]=r.byte();m.bonus_chance[1]=r.byte();m.bonus_chance[3]=r.byte();   // be18, be20, be28, be30
    res.poison=r.byte();++r.p;g.time_to_promotion=r.byte();
    for(auto& v:s->extra->base_bde8)v=r.word();
    sel.base_damage=r.word();pv.shield_value=r.word();pv.healing_value=r.word();res.health_max=r.word();res.health=r.word();
    const std::int32_t xp=r.word(),up=r.word(),gold=r.word();pv.armour_current=r.word();
    res.xp=xp%100;res.up=up%100;res.gold=gold%100;res.total_up=up-res.up;res.total_gold=gold-res.gold;res.total_xp=xp-res.xp;
    res.level=res.total_xp/100+1;
    for(int k=0;k<5;++k)load_item(r,s->items[k],k,h);
    const std::int32_t armour=pv.armour_current,health=res.health;
    pv.armour_max=0;pv.armour_current=0;res.health_bonus=0;
    if(h->update_stats)h->update_stats(h->context);
    res.health=health;pv.armour_current=armour;
    PlayerStats& pl=*s->player;   // the interface values (and their updates where they change)
    auto ui=[&](std::int32_t& field,std::int32_t value,SaveEventKind kind){if(field!=value){field=value;event(h,kind,value);}};
    ui(pl.ui_skull_59c8,sel.bonus_base_damage+sel.base_damage,SaveEventKind::Skull);
    ui(pl.ui_health_ceiling_5998,res.health_bonus+res.health_max,SaveEventKind::HealthCeiling);
    ui(res.ui_health,res.health,SaveEventKind::Health);
    ui(pl.ui_armour_max_59c4,pv.armour_max,SaveEventKind::ArmourMax);
    ui(res.ui_armour,pv.armour_current,SaveEventKind::Armour);
    ui(res.ui_xp,res.xp,SaveEventKind::XP);ui(res.ui_up,res.up,SaveEventKind::UP);ui(res.ui_gold,res.gold,SaveEventKind::Gold);
    event(h,SaveEventKind::Poison,res.poison);
    res.skill_count=r.byte();
    for(int k=0;k<res.skill_count && k<4;++k) {   // Skill::Deserialise
        s->skills->id[k]=r.byte();res.skill_max[k]=r.byte();res.skill_current[k]=r.byte();s->skills->level[k]=r.byte();
        if(res.skill_max[k]==255)res.skill_max[k]=res.skill_current[k]=-1;
        event(h,SaveEventKind::SkillIcon,k);event(h,SaveEventKind::PositionSkill,k);
    }
    event(h,SaveEventKind::UpdateSkills);
    for(int k=0;k<17;++k){s->name[k]=static_cast<std::uint8_t>(r.byte());if(!s->name[k])break;}
    for(std::uint32_t k=1;k<6;++k)dr_random_set_seed(&m.random,static_cast<std::uint32_t>(r.word()),k);
    s->finish->help_flags_102d0=static_cast<std::uint32_t>(r.word());
    s->settings->help_13ec8=s->finish->help_flags_102d0!=0;event(h,SaveEventKind::HelpState,s->settings->help_13ec8);
    const std::int32_t difficulty=std::clamp(r.byte(),0,3);   // Game::SetDifficulty
    s->settings->difficulty_changed_14ae4=m.spawn_enabled_14ae0!=difficulty;m.spawn_enabled_14ae0=difficulty;
    return true;
}
namespace {
// The units read the current class record through views: SelectionState.character (race, flaws), MatchState.perks and
// its class_type / class_level.
void record_from_views(const SaveSources* s) {
    ClassProfile& c=s->scroll->classes[s->scroll->current];const auto& sel=s->stroke->selection;
    c.race=sel.character.race;std::copy(s->match->perks,s->match->perks+4,c.perks);std::copy(sel.character.flaws,sel.character.flaws+4,c.flaws);
}
void views_from_record(const SaveSources* s) {
    const ClassProfile& c=s->scroll->classes[s->scroll->current];auto& sel=s->stroke->selection;MatchState& m=*s->match;
    sel.character.race=c.race;std::copy(c.perks,c.perks+4,m.perks);std::copy(c.flaws,c.flaws+4,sel.character.flaws);
    m.class_type=c.class_type;m.class_level=c.level;
}
// Records without a replacement list get a scratch one of 255 (none replaced) while the progression functions run.
struct Scratch {
    ClassProfile* classes;std::int32_t lists[10][20];bool used[10]{};
    explicit Scratch(ClassProfile* c):classes(c) {
        for(int i=0;i<10;++i)if(!c[i].replacement_skills) {
            for(auto& v:lists[i])v=255;c[i].replacement_skills=lists[i];c[i].replacement_skill_count=20;used[i]=true;
        }
    }
    ~Scratch() {for(int i=0;i<10;++i)if(used[i]){classes[i].replacement_skills=nullptr;classes[i].replacement_skill_count=0;}}
};
}
extern "C" void dr_serialise_classes(const SaveSources* s,ClassSave* out) {
    record_from_views(s);
    {Scratch scratch(s->scroll->classes);out->length_14ad8=static_cast<std::int32_t>(dr_classes_write(s->scroll->classes,10,out->bytes,class_save_capacity));}
    views_from_record(s);out->changed_14adc=1;
}
extern "C" bool dr_deserialise_classes(const SaveSources* s,const ClassSave* in) {
    if(in->bytes[1]!=10)return false;
    {Scratch scratch(s->scroll->classes);dr_classes_read(s->scroll->classes,10,in->bytes,class_save_capacity);}
    views_from_record(s);return true;
}
