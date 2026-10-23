#include "recovered_session.hpp"
#include "recovered_preview.hpp"
#include "recovered_rune.hpp"
#include "recovered_stroke.hpp"
#include "recovered_tokens.hpp"
#include "recovered_path.hpp"
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <utility>
#include <vector>
using namespace dungeonraid;
namespace dungeonraid {
struct Session {
    SessionHost host{};
    std::int32_t difficulty=1;
    // state (one object per Game field)
    StrokeState stroke{};
    ResourcePreviewState preview{};
    MatchState match{};
    RuneState rune{};
    TokenQueue* tokens=nullptr;
    ResourceState resources{};
    PathState path{};
    RefillState refill{};
    GenerationState generation{};
    std::vector<TokenMotion> motions;
    std::vector<std::int32_t> falling;
    AttackDamageState damage{};
    AttackAnimation animation{};
    std::uint8_t overlay_alpha=0;
    AttackProcessInputs attack_inputs{};
    SkillSlots skills{};
    TurnFlags turn_flags{};
    TurnFinishFlags finish{};
    EndGameState end{};
    std::uint8_t activated[36]{};
    EndOfTurnState end_of_turn{};
    ReleaseFlights flights{};
    ReleaseInputs release_inputs{};
    ReleaseState release{};
    ClassProfile classes[10]{};
    ClassScrollState scroll{};
    PlayerStats player{};
    NewGameExtra extra{};
    ShieldShatterState shatter{};
    TouchState touch{};
    FrameScreens screens{};
    std::uint8_t current_label_active=0;
    std::int32_t skill_button=-1;
    SkillInput skill_input{-1,0};   // .pressed is Game+0x58ac (Interface+0xbd0), the gate's input target
    SkillState skill_state{};
    InputGateInputs gate_inputs{};
    FrameState frame_state{};
    BoardEffectsState effects{};
    DamageLabelState labels{};
    GameFrame frame{};
    NewGameState new_game{};
    float dt=0.0f;
    std::int32_t input_route=-1;
    // hooks
    SelectionHooks selection_hooks{};
    MatchHooks match_hooks{};
    TokenHooks token_hooks{};
    MotionHooks motion_hooks{};
    ResourceHooks resource_hooks{};
    PathHooks path_hooks{};
    RefillHooks refill_hooks{};
    GenerationHooks generation_hooks{};
    EncounterHooks encounter_hooks{};
    AttackFlareHooks flare_hooks{};
    AttackAnimHooks anim_hooks{};
    AttackAbsorbHooks absorb_hooks{};
    AttackShieldHooks shield_hooks{};
    AttackWeakenHooks weaken_hooks{};
    AttackAllHooks all_hooks{};
    AttackHealthHooks health_hooks{};
    AttackFadeHooks fade_hooks{};
    AttackProcessHooks process_hooks{};
    EncounterHooks vampire_hooks{};
    TurnHooks turn_hooks{};
    EndGameHooks end_hooks{};
    GameOverHooks over_hooks{};
    ScheduleHooks schedule_hooks{};
    ReleaseHooks release_hooks{};
    InputHooks input_hooks{};
    BoardEffectHooks effect_hooks{};
    FrameHooks part_hooks{};
    LabelHooks label_hooks{};
    GameFrameHooks frame_hooks{};
    NewGameHooks new_game_hooks{};
    ItemRecord items[5]{};          // Game+0xbe88..0xbe98
    MenuState menu{};
    std::int32_t menu_button=-1;
    std::uint8_t dimmed[36]{};      // Game::UpdateDimming: tiles that cannot continue the path (the renderer dims them)
    std::uint32_t probe[40]{};      // the words at Game+0xbf90 the shop's scroll draw reads
    MenuHooks menu_hooks{};
    std::uint8_t save[save_capacity]{};   // Game+0x13ecf: the saved game (length / changed: end.flag_146d0 / flag_146d4)
    std::uint8_t name[17]{};              // Game+0xbe38: the player's name (the renderer's name entry)
    SaveHooks save_hooks{};
    SaveSettings settings{};              // Game+0x13ec8 help switch, Game+0x14ae4 difficulty changed (DeserialiseState)
    ClassSave class_save{};               // Game+0x146d5: the class records' save
    ScoreBoard scores{};                  // ScoreScreen's high-score tables (Game+0xef68)
    SimpleLabelState damage_labels[3]{};  // leech, flame, spike SimpleLabels (Game+0xbfc0 / 0x14afc / 0x14e70)
    std::int32_t class_replacements[10][20]{};   // the class records' replacement skill lists
    SetupScreen setup{};                  // the new-game setup screen (NameScreen)
    OverlayMenu game_menu{0,-1,0,0.0f};   // GameMenu (Interface+0xe24)
    OverlayMenu stats_menu{0,-1,0,0.0f};  // StatsMenu (Interface+0xeb4)
    InterfaceButtons interface_buttons{}; // Interface+0xcb4 / +0xcb5
    MainMenuScreen main_menu{};           // MainMenu+0x8 / +0xc
    HelpPopup help{0,0.0f,0,-1,{},0.0f,0.0f,-1,0,{}};   // HelpMenu (Game+0x10298)
    StatsTargets stats_targets{};
    StatsHooks stats_hooks{};
    CrossHooks cross_hooks{};
    SkillHooks skill_hooks{};
};
}
namespace {
Session& self(void* c) {return *static_cast<Session*>(c);}
void forward(Session& s,SessionSource source,const void* e) {if(s.host.event)s.host.event(s.host.context,source,e);}
void open_menu(Session& s,std::int32_t type);
void save_state(Session& s);
void help_topic(Session& s,std::int32_t type,Point at,float width,float height,std::int32_t slot=-1);
void update_skills(Session& s);
float as_float(std::int32_t bits) {float f;std::memcpy(&f,&bits,4);return f;}
Point tile_center(const Session& s,std::int32_t tile) {return s.stroke.selection.tiles[tile].geometry.center;}
// Interface::ShowHelp* (fixed places): Gold 7, BaseDmg 9, WeaponDmg 10, Armour 11, UP 12, XP 13, Health 18
void show_help(Session& s,std::int32_t type) {
    switch(type) {
    case 7:help_topic(s,7,Point{as_float(0x3e100000),as_float(0x3fa60000)},0.0f,0.0f);break;
    case 9:help_topic(s,9,Point{as_float(0x3ea9999a),as_float(0x3fa20000)},0.0f,0.0f);break;
    case 10:help_topic(s,10,Point{as_float(0x3f240000),as_float(0x3fa20000)},0.0f,0.0f);break;
    case 11:help_topic(s,11,Point{as_float(0x3efe6666),as_float(0x3fa20000)},0.0f,0.0f);break;
    case 12:help_topic(s,12,Point{as_float(0x3f000000),as_float(0x3fb20000)},0.0f,0.0f);break;
    case 13:help_topic(s,13,Point{as_float(0x3f000000),as_float(0x3fb93333)},0.0f,0.0f);break;
    case 18:help_topic(s,18,Point{as_float(0x3f5b9999),as_float(0x3fa26666)},0.0f,0.0f);break;
    default:break;
    }
}
template<SessionSource source,class Event> void forward_event(void* c,const Event* e) {forward(self(c),source,e);}

// Game::AddFlare: every unit's Flare event is one call (dr_add_flare: rotation from stream 0, count + 1).
void add_flare(Session& s) {dr_add_flare(&s.animation.flare_count,&s.match.random);}
// Game::AddParticles / Game::AddSimpleLabel: their random draws on stream 0 (dr_add_particles / dr_add_simple_label).
void particles(Session& s,std::int32_t type) {dr_add_particles(&s.match.random,type);}
void label(Session& s,std::int32_t type) {dr_add_simple_label(&s.match.random,type);}
// Game::UpdateStats over the equipped items (the Item** vector Game+0xbe9c: slots 0..4 in order). The item parts of
// the bonus chances (Game+0xbe1c / be24 / be2c / be34) are PlayerStats.chance_*; MatchState reads them as
// bonus_chance_extra (Game+0xbe24 / be2c / be1c / be34 in its order), kept equal here.
void sync_chances(Session& s) {
    auto& x=s.match.bonus_chance_extra;const auto& p=s.player;
    x[0]=p.chance_be24;x[1]=p.chance_be2c;x[2]=p.chance_be1c;x[3]=p.chance_be34;
}
void update_stats(Session& s) {
    const ItemStats* items[5];for(int i=0;i<5;++i)items[i]=&s.items[i].stats;
    dr_update_stats(&s.stats_targets,items,5,&s.stats_hooks);
    sync_chances(s);
}
bool check_end_game(Session& s) {return dr_check_end_game(&s.resources,&s.end,&s.end_hooks);}
void move_matched_tiles(Session& s) {dr_move_matched_tiles(&s.refill,&s.refill_hooks);}
bool attack_skull(Session& s,std::int32_t tile,std::int32_t amount,bool effects) {
    return dr_path_attack_skull(&s.path,static_cast<std::uint32_t>(tile),amount,effects,&s.path_hooks);
}
TokenMotion& motion(Session& s,std::uint32_t slot) {
    if(slot>=s.motions.size()) {
        TokenMotion fresh{};fresh.target_or_amount=-1;fresh.linked_tile=-1;
        s.motions.resize(slot+1,fresh);
    }
    return s.motions[slot];
}

// SelectionHooks: the stroke's boundaries that are game rules run here.
void selection_event(void* c,SelectionEvent kind,std::int32_t index,std::int32_t a,std::int32_t b) {
    Session& s=self(c);const SessionSmallEvent e{static_cast<std::int32_t>(kind),index,a,b};forward(s,SessionSource::Selection,&e);
    if(kind==SelectionEvent::UpdateDimming)dr_update_dimming(&s.stroke.selection,s.dimmed);
    else if(kind==SelectionEvent::ResourceShadows)dr_preview_resources(&s.stroke,&s.preview,&s.selection_hooks);
    else if(kind==SelectionEvent::ProcessRune)dr_process_rune(&s.stroke,&s.rune,a!=0,&s.selection_hooks);
    else if(kind==SelectionEvent::RuneMatchTile)dr_match_tile(&s.match,static_cast<std::uint32_t>(index),a,&s.match_hooks);
    else if(kind==SelectionEvent::CrossVisibility)dr_update_cross_visibility(&s.path,&s.cross_hooks);
    else if(kind==SelectionEvent::ProcessPretzels)dr_process_pretzels(&s.stroke.selection,&s.preview,s.tokens);
}
void match_event(void* c,const MatchEvent* e) {
    Session& s=self(c);forward(s,SessionSource::Match,e);
    switch(e->kind) {
    case MatchEventKind::Flare:add_flare(s);break;
    case MatchEventKind::Particles:particles(s,e->a);break;
    case MatchEventKind::Label:label(s,0);break;   // AddSimpleLabel(Tile*, TileType): label type 0
    case MatchEventKind::Token:dr_enqueue_token(s.tokens,static_cast<std::uint32_t>(e->tile),e->a,e->b!=0,e->c,&s.token_hooks);break;
    case MatchEventKind::SetSpecialType:dr_set_special_type(&s.generation,static_cast<std::uint32_t>(e->tile),e->a,&s.generation_hooks);break;
    case MatchEventKind::Shapeshift:dr_shapeshift(&s.resources,&s.resource_hooks);break;
    case MatchEventKind::Help:help_topic(s,e->a,tile_center(s,e->tile),as_float(e->b),as_float(e->c));break;
    default:break;
    }
}
// A token request becomes a flying token in its slot (Token::InitialiseFromTile).
void token_event(void* c,const TokenEvent* e) {
    Session& s=self(c);forward(s,SessionSource::Token,e);
    if(e->kind==TokenEventKind::Help)help_topic(s,e->a,tile_center(s,e->index),as_float(e->b),as_float(e->c));
    if(e->kind!=TokenEventKind::Initialise)return;
    TokenMotion& t=motion(s,static_cast<std::uint32_t>(e->index));t.scale=Point{1.0f,1.0f};
    const std::int32_t position=e->c;
    const Point centre=position>=0?s.stroke.selection.tiles[position].geometry.center:Point{};
    dr_initialise_token(&t,&s.match,static_cast<std::uint32_t>(e->a),e->b,position>=0?&centre:nullptr,e->d,&s.motion_hooks);
}
void motion_event(void* c,MotionEventKind kind,std::int32_t index) {
    const SessionSmallEvent e{static_cast<std::int32_t>(kind),index,0,0};forward(self(c),SessionSource::Motion,&e);
}
void motion_target(void* c,std::int32_t kind,std::int32_t index,Point* out) {Session& s=self(c);s.host.target(s.host.context,kind,index,out);}
// Interface::GetSpecialTarget(Token*): the skill slot a mana potion recharges (a rule, not layout: dr_special_target).
std::int32_t choose_special(void* c,TokenMotion* t) {return dr_special_target(&self(c).skill_state,t->token_type);}
// The resource and encounter units call Game::Healing and Game::CheckEndGame (their result is not used there).
void resource_event(void* c,const ResourceEvent* e) {
    Session& s=self(c);forward(s,SessionSource::Resource,e);
    if(e->kind==ResourceEventKind::Healing)dr_healing(&s.resources,&s.resource_hooks);
    else if(e->kind==ResourceEventKind::CheckEndGame)check_end_game(s);
    else if(e->kind==ResourceEventKind::Label)label(s,e->a);
    else if(e->kind==ResourceEventKind::Menu)open_menu(s,e->a);
    else if(e->kind==ResourceEventKind::Help) {static const std::int32_t types[]={7,13,12,11};show_help(s,types[e->a&3]);}   // gold, XP, UP, armour
    else if(e->kind==ResourceEventKind::Skills)update_skills(s);
}
void encounter_event(void* c,const EncounterEvent* e) {
    Session& s=self(c);forward(s,SessionSource::Encounter,e);
    if(e->kind==EncounterEventKind::CheckEndGame)check_end_game(s);
    else if(e->kind==EncounterEventKind::Flare)add_flare(s);
    else if(e->kind==EncounterEventKind::Label)label(s,e->a);
}
void path_event(void* c,const RoundEvent* e) {
    Session& s=self(c);forward(s,SessionSource::Path,e);
    if(e->kind==BattleEvent::MoveMatchedTiles)move_matched_tiles(s);   // Game::MoveMatchedTiles at its place inside MatchTiles
    else if(e->kind==BattleEvent::Flare)add_flare(s);                 // AttackSkull's flare
    else if(e->kind==BattleEvent::Particles)particles(s,e->a);
    else if(e->kind==BattleEvent::Label)label(s,e->a);
}
void refill_event(void* c,RefillEventKind kind,std::int32_t i,std::int32_t j) {
    Session& s=self(c);const SessionSmallEvent e{static_cast<std::int32_t>(kind),i,j,0};forward(s,SessionSource::Refill,&e);
    switch(kind) {
    case RefillEventKind::Swap:   // per-tile state the refill does not own moves with the tile
        std::swap(s.generation.tiles[i],s.generation.tiles[j]);std::swap(s.activated[i],s.activated[j]);break;
    case RefillEventKind::AppendMoving:s.falling.push_back(i);break;
    case RefillEventKind::Randomise:dr_randomise_tile(&s.generation,static_cast<std::uint32_t>(i),&s.generation_hooks);break;
    case RefillEventKind::Stab:dr_stab(&s.generation,static_cast<std::uint32_t>(i),&s.encounter_hooks);break;
    }
}
void generation_event(void* c,const GenerationEvent* e) {
    Session& s=self(c);forward(s,SessionSource::Generation,e);
    if(e->kind==GenerationEventKind::JumpDown)dr_jump_down(&s.generation,static_cast<std::uint32_t>(e->tile),&s.encounter_hooks);
    else if(e->kind==GenerationEventKind::ShieldShatter)dr_initialise_shield_shatter(&s.shatter,&s.effect_hooks);
}
// ProcessAttack
void flare_event(void* c,const AttackFlareEvent* e) {
    Session& s=self(c);forward(s,SessionSource::AttackFlare,e);
    if(e->kind==AttackFlareEventKind::Flare)add_flare(s);   // InitialiseFlares' AddFlare
}
void anim_event(void* c,const AttackAnimEvent* e) {
    Session& s=self(c);forward(s,SessionSource::AttackAnim,e);if(e->kind==AttackAnimEventKind::AddLabel)label(s,e->a);
    if(e->kind==AttackAnimEventKind::HelpMenu)help_topic(s,e->c,Point{as_float(e->a),as_float(e->b)},0.0f,e->c==17?as_float(0x3dcccccd):0.0f);
}
void absorb_event(void* c,const AttackAbsorbEvent* e) {
    Session& s=self(c);forward(s,SessionSource::AttackAbsorb,e);if(e->kind==AttackAbsorbEventKind::Label)label(s,e->a);
}
void weaken_event(void* c,const AttackWeakenEvent* e) {
    Session& s=self(c);forward(s,SessionSource::AttackWeaken,e);
    if(e->kind==AttackWeakenEventKind::Label)label(s,e->a);else if(e->kind==AttackWeakenEventKind::Particles)particles(s,e->a);
}
void all_event(void* c,const AttackAllEvent* e) {
    Session& s=self(c);forward(s,SessionSource::AttackAll,e);if(e->kind==AttackAllEventKind::Label)label(s,e->a);
}
void vampire_event(void* c,const EncounterEvent* e) {
    Session& s=self(c);forward(s,SessionSource::Vampires,e);if(e->kind==EncounterEventKind::Label)label(s,e->a);
}
void end_event(void* c,const TurnEvent* e) {
    Session& s=self(c);forward(s,SessionSource::EndGame,e);if(e->kind==TurnEventKind::LabelPoison)label(s,e->a);
}
void counterattack(void* c) {Session& s=self(c);dr_do_counterattack(&s.path,&s.all_hooks);}
void health_event(void* c,const AttackHealthEvent* e) {
    Session& s=self(c);forward(s,SessionSource::AttackHealth,e);
    if(e->kind==AttackHealthEventKind::Vampires)dr_process_vampires(&s.generation,&s.vampire_hooks);
    else if(e->kind==AttackHealthEventKind::Label)label(s,e->a);
    else if(e->kind==AttackHealthEventKind::HelpHealth)show_help(s,18);
}
bool all_attack_skull(void* c,std::int32_t tile,std::int32_t amount,bool effects) {return attack_skull(self(c),tile,amount,effects);}
void all_move(void* c) {move_matched_tiles(self(c));}
// EndOfTurn
void turn_event(void* c,const TurnEvent* e) {
    Session& s=self(c);forward(s,SessionSource::Turn,e);
    switch(e->kind) {
    case TurnEventKind::Flare:case TurnEventKind::FlareRest:case TurnEventKind::FlareTarget:add_flare(s);break;
    case TurnEventKind::Label:case TurnEventKind::LabelRest:case TurnEventKind::LabelTarget:case TurnEventKind::LabelPoison:label(s,e->a);break;
    case TurnEventKind::Particles:particles(s,e->a);break;
    case TurnEventKind::SerialiseState:save_state(s);break;
    case TurnEventKind::Help:help_topic(s,e->a,tile_center(s,e->tile),as_float(e->b),as_float(e->c));break;
    case TurnEventKind::UpdateSkills:update_skills(s);break;
    default:break;
    }
}
void turn_match_tile(void* c,std::int32_t tile,std::int32_t reward) {
    Session& s=self(c);dr_match_tile(&s.match,static_cast<std::uint32_t>(tile),reward,&s.match_hooks);
}
bool turn_check_end_game(void* c) {return check_end_game(self(c));}
void turn_ability(void* c,std::int32_t kind,std::int32_t tile) {   // enemy 28: Game::DestroyUpgrade
    Session& s=self(c);const SessionSmallEvent e{kind,tile,0,0};forward(s,SessionSource::Ability,&e);
    ItemStats* items[5];for(int i=0;i<5;++i)items[i]=&s.items[i].stats;
    dr_destroy_upgrade(&s.stats_targets,items,5,static_cast<std::uint32_t>(tile),&s.stats_hooks);
    sync_chances(s);
}
// Game::UpdateStats / DestroyUpgrade / IncreaseStat presentation; DestroyUpgrade's label draws on stream 0.
void stats_event(void* c,const StatsEvent* e) {
    Session& s=self(c);forward(s,SessionSource::Stats,e);if(e->kind==StatsEventKind::Label)label(s,e->a);
    if(e->kind==StatsEventKind::UpdateSkills)update_skills(s);
}
// FoldoutMenu: what it reads and writes. The scroll draw of the shop reads the 40 words at Game+0xbf90 (the
// original reads past the four Skill pointers, docs/T040_MENU.md): pointers (non-zero), skill_count, matched_counts
// 0..4, the bytes 0xbfb8..0xbfbb, next coin at 0xbfbc, then the leech SimpleLabel at Game+0xbfc0 (its active byte,
// type and first vertices: the label model's bytes 4..0x6f).
MenuSources menu_sources(Session& s) {
    std::uint32_t* w=s.probe;
    for(int t=0;t<4;++t)w[t]=1;
    w[4]=static_cast<std::uint32_t>(s.resources.skill_count);
    for(int t=0;t<5;++t)w[5+t]=static_cast<std::uint32_t>(s.match.matched_counts[t]);
    w[10]=s.generation.filter_enabled|(s.generation.filter_swords<<8)|(s.animation.counterattack<<16)|
          (static_cast<std::uint32_t>(s.path.battle.grant_coin_on_attack)<<24);
    w[11]=s.turn_flags.next_coin_bfbc;w[12]=s.extra.label_active[0];
    std::memcpy(w+13,reinterpret_cast<const std::uint8_t*>(&s.damage_labels[0])+4,27*sizeof *w);
    return MenuSources{&s.resources,&s.skills,s.classes,static_cast<std::int32_t>(s.scroll.current),&s.screens.menus[0],&s.preview,
                       &s.stroke.selection,&s.player,s.extra.base_bde8,s.items,&s.stats_targets,&s.stats_hooks,&s.skill_state,s.probe};
}
void open_menu(Session& s,std::int32_t type) {   // Interface::ShowMenu -> FoldoutMenu::Initialise
    const MenuSources src=menu_sources(s);
    if(type==0)dr_menu_open_level(&s.menu,&src,&s.menu_hooks);
    else if(type==1)dr_menu_open_shop(&s.menu,&src,&s.menu_hooks);
    else if(type==2)dr_menu_open_upgrade(&s.menu,&src,&s.menu_hooks);
}
SaveSources save_sources(Session& s) {
    return SaveSources{&s.stroke,&s.match,&s.preview,&s.resources,&s.path,&s.generation,&s.scroll,&s.extra,&s.skills,s.items,&s.finish,
                       s.name,&s.player,&s.settings};
}
void load_update_stats(void* c) {update_stats(self(c));}
// Game::SerialiseState: the saved game into the buffer, its length and the changed flag (the platform stores it).
void save_state(Session& s) {
    const SaveSources src=save_sources(s);
    s.end.flag_146d0=static_cast<std::int32_t>(dr_serialise_state(&src,s.save,&s.save_hooks));s.end.flag_146d4=1;
}
void save_event(void* c,SaveEventKind kind,std::int32_t a,std::int32_t b) {
    const SessionSmallEvent e{static_cast<std::int32_t>(kind),-1,a,b};forward(self(c),SessionSource::Save,&e);
    if(kind==SaveEventKind::UpdateSkills)update_skills(self(c));
}
void menu_event(void* c,const MenuEvent* e) {
    Session& s=self(c);forward(s,SessionSource::Menu,e);
    if(e->kind==MenuEventKind::UpdateSkills)update_skills(s);
    if(e->kind==MenuEventKind::ActivateScroll) {   // the bought scroll: Skill::Activate on the unequipped object
        sync_chances(s);   // after the shop's Game::UpdateStats
        dr_skill_activate(&s.skill_state,e->a,-1,&s.menu.scroll.active,&s.skill_hooks);
    }
}
// Game::InitNewGame's items: Item(Game, type) in each slot, then Game::UpdateStats.
void new_game_event(void* c,const NewGameEvent* e) {
    Session& s=self(c);forward(s,SessionSource::NewGame,e);
    if(e->kind==NewGameEventKind::Item)dr_item_make(&s.stats_targets,&s.items[e->a],e->b,nullptr);
    else if(e->kind==NewGameEventKind::UpdateStats)update_stats(s);
    else if(e->kind==NewGameEventKind::InterfaceReset) {   // Interface::Reset 0x204a4: its input state (the rest is presentation)
        s.skill_input.pressed=-1;s.interface_buttons=InterfaceButtons{};s.screens.menus[1]=s.screens.menus[2]=0;
    }
}
void turn_swap(void* c,std::int32_t x1,std::int32_t y1,std::int32_t x2,std::int32_t y2) {
    Session& s=self(c);dr_swap_tiles(&s.refill,x1,y1,x2,y2,&s.refill_hooks);
}
std::uint32_t push_token(void* c,std::int32_t tile,std::int32_t reward,std::int32_t token_type,std::int32_t value) {
    Session& s=self(c);const TokenRequest request{tile,reward,-1,token_type};
    const std::uint32_t slot=dr_token_queue_push(s.tokens,&request,&s.token_hooks);
    if(value>=0)motion(s,slot).target_or_amount=value;
    return slot;
}
void token_target(void* c,std::uint32_t slot,std::int32_t tile) {Session& s=self(c);dr_token_set_target_tile(&motion(s,slot),&s.stroke,tile);}
void token_start(void* c,std::uint32_t slot,std::int32_t kind) {Session& s=self(c);s.host.token_start(s.host.context,kind,&motion(s,slot).position);}
void game_over(void* c,bool win) {
    Session& s=self(c);dr_game_over(&s.resources,&s.path,&s.classes[s.scroll.current],&s.skills,&s.end,win,&s.over_hooks);
}
// ScoreScreen::AddScore(name, ...) with the GameMode (variant 1: type mode + 4) or Difficulty (variant 0) overload.
void add_score(void* c,const ScoreEntry* e) {
    Session& s=self(c);forward(s,SessionSource::Score,e);
    char name[18]{};std::copy(s.name,s.name+17,name);   // Game::SetName keeps names to 16 characters and their terminator
    dr_score_add(&s.scores,name,e->turn,e->a,e->b,e->c,e->score,e->variant?e->mode+4:e->mode);
}
void over_event(void* c,const TurnEvent* e) {
    Session& s=self(c);forward(s,SessionSource::GameOver,e);
    // GameOverScreen::Initialise (0x307f8): the screen shows (Game+0xcac4 = 1, 0x30898) in its state 0
    // (Game+0xcc1c = 0, 0x30868); the rest of it is presentation.
    if(static_cast<std::int32_t>(e->kind)==static_cast<std::int32_t>(EndGameEventKind::SetSkills))dr_score_set_skills(&s.scores,e->a,e->b,e->c,e->d);
    if(static_cast<std::int32_t>(e->kind)==static_cast<std::int32_t>(EndGameEventKind::SerialiseClasses)) {
        const SaveSources src=save_sources(s);dr_serialise_classes(&src,&s.class_save);
    }
    if(static_cast<std::int32_t>(e->kind)==static_cast<std::int32_t>(EndGameEventKind::GameOverScreen)) {
        s.end.game_over_screen=1;s.screens.game_over_state_cc1c=0;
    }
}
void end_of_turn(void* c) {
    Session& s=self(c);dr_end_of_turn(&s.resources,&s.path,&s.generation,&s.end_of_turn,&s.turn_hooks,&s.generation_hooks);
}
// Release
void release_event(void* c,const ReleaseEvent* e) {
    Session& s=self(c);forward(s,SessionSource::Release,e);
    SelectionState& sel=s.stroke.selection;
    switch(e->kind) {
    case ReleaseEventKind::Label:label(s,e->a);break;
    case ReleaseEventKind::IncreaseStat:dr_item_increase_stat(&s.stats_targets,&s.items[2].stats,2,e->a,&s.stats_hooks);break;   // Game+0xbe90
    case ReleaseEventKind::UpdateStats:update_stats(s);break;
    case ReleaseEventKind::CrossVisibility:dr_update_cross_visibility(&s.path,&s.cross_hooks);break;
    case ReleaseEventKind::MatchTiles: {   // Game::MatchTiles: the path without its fake tiles
        std::uint8_t excluded[36];std::size_t n=0;
        for(std::uint8_t i=0;i<36;++i)if(sel.fake[i])excluded[n++]=i;
        dr_commit_path(&s.path,sel.path,sel.path_length,excluded,n,&s.path_hooks);break;
    }
    case ReleaseEventKind::MatchTile:dr_match_tile(&s.match,static_cast<std::uint32_t>(e->tile),e->a,&s.match_hooks);break;
    case ReleaseEventKind::MoveMatchedTiles:move_matched_tiles(s);break;
    case ReleaseEventKind::SerialiseState:save_state(s);break;
    case ReleaseEventKind::SerialiseClasses: {const SaveSources src=save_sources(s);dr_serialise_classes(&src,&s.class_save);break;}
    case ReleaseEventKind::Help:help_topic(s,e->a,Point{e->x,e->y},as_float(e->d),as_float(e->d));break;
    default:break;
    }
}
bool release_check_end_game(void* c) {return check_end_game(self(c));}
// Skills: the board calls of Skill::Activate and the skill events that are other units' functions.
void skill_event(void* c,const SkillEvent* e) {
    Session& s=self(c);forward(s,SessionSource::Skill,e);
    const auto tile=static_cast<std::uint32_t>(e->b);
    switch(e->kind) {
    case SkillEventKind::Flare:add_flare(s);break;
    case SkillEventKind::Particles:particles(s,e->a);break;
    case SkillEventKind::Label:label(s,e->a);break;
    case SkillEventKind::MoveMatchedTiles:move_matched_tiles(s);break;
    case SkillEventKind::JumpDown:dr_jump_down(&s.generation,tile,&s.encounter_hooks);break;
    case SkillEventKind::SwapTiles:dr_swap_tiles(&s.refill,e->a,e->b,e->c,e->d,&s.refill_hooks);break;
    case SkillEventKind::SetSpecialType:dr_set_special_type(&s.generation,tile,e->a,&s.generation_hooks);break;
    case SkillEventKind::FlameVisibility:dr_set_flame_visibility(&s.path,tile,true,e->a,true,&s.turn_hooks);break;
    case SkillEventKind::Menu:open_menu(s,e->a);break;   // Game::Upgrade (skill 10): the upgrade menu
    case SkillEventKind::UpdateSkills:update_skills(s);break;
    default:break;
    }
}
void skill_action(void* c,SkillAction action,std::int32_t a,std::int32_t b) {
    Session& s=self(c);dr_skill_action(&s.skill_state,action,a,b,&s.skill_hooks,&s.generation_hooks);
}
// The game menu, the stats menu and Interface's buttons (T040-M5)
void interface_event(Session& s,InterfaceEventKind kind,std::int32_t index,std::int32_t a) {
    const SessionSmallEvent e{static_cast<std::int32_t>(kind),index,a,0};forward(s,SessionSource::Interface,&e);
}
void menu_sound(Session& s) {interface_event(s,InterfaceEventKind::Sound,-1,0);}
// Game::UpdateHelpState 0x9edc
void update_help_state(Session& s) {
    std::uint32_t& queued=s.finish.help_flags_102d0;
    if(queued) {if(!s.settings.help_13ec8)queued=0;}   // HelpMenu::ClearHelp
    else if(s.settings.help_13ec8)queued|=0x7fffffu;    // HelpMenu::ResetHelp: topics 0..22
}
// GameMenu's switches: Game::SetSoundState / SetHelpState / SetClockState / SetAttackDimmingState / SetHighFramerate with
// the switch flipped (its byte xor 1); the changed flag is whether it changed (SetHelpState has none).
void flip_switch(Session& s,std::int32_t button,std::uint8_t& value,std::uint8_t* changed) {
    const std::uint8_t to=value^1;
    if(changed)*changed=value!=to;
    value=to;interface_event(s,InterfaceEventKind::Setting,button,to);
}
// GameMenu::Show 0x31b88 / StatsMenu::Show 0x3381c
void show_menu(OverlayMenu& m,std::uint8_t& open) {m.pressed=-1;m.previous_phase=0;m.closing=0;m.timer=0.2f;open=1;}
// The menus' fade: true while it runs; a closing menu closes when it runs out.
bool menu_fade(Session& s,OverlayMenu& m,std::uint8_t& open) {
    if(!(m.timer>0.0f))return false;
    m.timer-=s.dt;
    if(!(m.timer>0.0f)) {m.timer=0.0f;if(m.closing)open=0;}
    return true;
}
// GameMenu::Process 0x32580
void game_menu_process(Session& s) {
    OverlayMenu& m=s.game_menu;SaveSettings& set=s.settings;
    if(menu_fade(s,m,s.screens.menus[1]))return;
    const std::int32_t phase=s.touch.phase,button=s.menu_button;
    if(phase==1) {
        if(m.previous_phase==0 && button>=9 && button<=15) {m.pressed=button;menu_sound(s);}
    } else if((phase==2 || phase==3) && m.pressed>=0) {
        if(button==m.pressed)switch(button) {
        case 9:m.timer=0.2f;m.closing=1;update_help_state(s);break;
        case 10:flip_switch(s,10,set.sound_13ec6,&set.sound_changed_13ec7);if(set.sound_13ec6)menu_sound(s);break;
        case 11:flip_switch(s,11,set.help_13ec8,nullptr);break;
        case 12:flip_switch(s,12,set.clock_13ec9,&set.clock_changed_13ecc);break;
        case 13:flip_switch(s,13,set.dimming_13eca,&set.dimming_changed_13ecd);break;
        case 14:flip_switch(s,14,set.framerate_13ecb,&set.framerate_changed_13ece);break;
        case 15:   // MainMenu::FadeIn 0x2e214
            s.screens.main_menu_c400=1;s.main_menu.fading=1;s.main_menu.timer=0.5f;
            interface_event(s,InterfaceEventKind::MainMenu,-1,0);break;
        default:break;
        }
        m.pressed=-1;
    }
    m.previous_phase=phase;
}
// StatsMenu::Process 0x33c0c (the shown tab's labels and the menu's height are the renderer's)
void stats_menu_process(Session& s) {
    OverlayMenu& m=s.stats_menu;
    if(menu_fade(s,m,s.screens.menus[2]))return;
    const std::int32_t phase=s.touch.phase,button=s.menu_button;
    if(phase==1 && m.previous_phase==0) {
        if(button==-1) {menu_sound(s);m.timer=0.2f;m.closing=1;return;}   // StatsMenu::CursorOutsideMenu (the phase is not kept)
        if(button>=10 && button<=15 && button!=m.pressed) {m.pressed=button;menu_sound(s);}
    }
    m.previous_phase=phase;
}
// Interface::ProcessInput 0x209e4: the skill buttons (dr_skill_input), then the menu and stats buttons
void interface_input(Session& s) {
    const std::int32_t previous=s.skill_input.previous_phase,phase=s.touch.phase,button=s.skill_button;
    dr_skill_input(&s.skill_state,&s.skill_input,phase,button,&s.skill_hooks,&s.generation_hooks);
    InterfaceButtons& b=s.interface_buttons;
    if(phase==1) {
        if(previous==0 && (button==4 || button==5)) {menu_sound(s);(button==4?b.menu_pressed:b.stats_pressed)=1;}
    } else if(phase==2 || phase==3) {
        if(b.menu_pressed) {show_menu(s.game_menu,s.screens.menus[1]);b.menu_pressed=0;}
        if(b.stats_pressed) {show_menu(s.stats_menu,s.screens.menus[2]);b.stats_pressed=0;}
    }
}
// The help popup (T040-M6). HelpMenu::Show 0x37f04
void help_show(Session& s,std::int32_t text,Point at,float width,float height,std::int32_t slot) {
    HelpPopup& p=s.help;p.timer=0.2f;p.closing=0;s.screens.help_102a4=1;p.previous_phase=1;
    p.text=text;p.at=at;p.width=width;p.height=height;p.skill_slot=slot;
    interface_event(s,InterfaceEventKind::Help,text,0);
}
// HelpMenu::Initialise 0x380b8: a queued topic shows once (the last one turns the help switch off: Game::SetHelpState(false))
void help_topic(Session& s,std::int32_t type,Point at,float width,float height,std::int32_t slot) {
    std::uint32_t& queued=s.finish.help_flags_102d0;
    if(s.screens.help_102a4 || !((static_cast<std::int32_t>(queued)>>type)&1))return;
    queued^=1u<<type;
    if(!queued) {s.settings.help_13ec8=0;interface_event(s,InterfaceEventKind::Setting,11,0);}
    help_show(s,type,at,width,height,slot);
}
// HelpMenu::QueueHelp 0x38268 (a screen text; its place is the renderer's)
void help_queue(Session& s,std::int32_t text) {
    if(!s.screens.help_102a4) {help_show(s,text,Point{},0.0f,0.0f,-1);return;}
    HelpPopup& p=s.help;if(p.queued<64)p.queue[p.queued++]=text;
}
// HelpMenu::Process 0x38128
void help_process(Session& s) {
    HelpPopup& p=s.help;
    if(p.timer>0.0f) {
        p.timer-=s.dt;
        if(p.timer>0.0f)return;
        p.timer=0.0f;
        if(!p.closing)return;
        s.screens.help_102a4=0;
        if(p.queued) {const std::int32_t next=p.queue[0];std::copy(p.queue+1,p.queue+p.queued,p.queue);--p.queued;help_queue(s,next);}
        return;
    }
    const std::int32_t phase=s.touch.phase;
    if(phase==1 && p.previous_phase==0 && s.menu_button>=0) {p.closing=1;p.timer=0.2f;}
    p.previous_phase=phase;
}
// Interface::UpdateSkills 0x20820: a skill whose cooldown is full or empty points help 19 (inactive) / 20 (active) at its
// button (the buttons' sizes, pictures and colours are presentation)
void update_skills(Session& s) {
    for(std::int32_t i=0;i<s.resources.skill_count;++i) {
        const std::int32_t current=s.resources.skill_current[i];
        if(current!=s.resources.skill_max[i] && current!=0)continue;
        help_topic(s,s.skills.active[i]?20:19,Point{},as_float(0x3dc33333),as_float(0x3dc33333),i);
    }
}
// Interface::ProcessHeartbeat 0x1e8e8: help 14 at low health (the beat is presentation)
void heartbeat(Session& s) {
    const float ratio=static_cast<float>(s.resources.ui_health)/static_cast<float>(s.player.ui_health_ceiling_5998);
    if(ratio<=0.35f)help_topic(s,14,Point{as_float(0x3f5b9999),as_float(0x3fa26666)},0.0f,0.0f);
}
void effect_event(void* c,const BoardEffectEvent* e) {
    Session& s=self(c);forward(s,SessionSource::BoardEffect,e);
    if(e->kind==BoardEffectEventKind::Help)help_topic(s,0,Point{e->x,e->y},0.0f,0.0f);   // Game::Process: a random tile
}
// Interface::Process 0x20c64: an open menu runs, else (with input ready) Interface::ProcessInput; then, with no FoldoutMenu
// open, ProcessHeartbeat.
void interface_process(Session& s,bool input_ready) {
    const auto& m=s.screens.menus;
    if(m[0]) {   // the shop and upgrade menus end in Game::UpdateStats
        const MenuSources src=menu_sources(s);dr_menu_process(&s.menu,&src,s.dt,s.touch.phase,s.menu_button,&s.menu_hooks);sync_chances(s);
    } else if(m[1])game_menu_process(s);
    else if(m[2])stats_menu_process(s);
    else if(input_ready)interface_input(s);
    if(!m[0])heartbeat(s);
}
void frame_event(void* c,const GameFrameEvent* e) {
    Session& s=self(c);forward(s,SessionSource::GameFrame,e);
    if(e->kind==GameFrameEventKind::InterfaceProcess)interface_process(s,e->a!=0);
    else if(e->kind==GameFrameEventKind::Screen && e->a==static_cast<std::int32_t>(FrameRoute::Help))help_process(s);
}
// Frame steps
void step_input(Session& s) {
    s.stroke.selection.touch=s.touch.position;
    s.gate_inputs=InputGateInputs{static_cast<std::uint32_t>(s.falling.size()),static_cast<std::int32_t>(dr_token_queue_counters(s.tokens)->pending),
                                  s.animation.flare_count,s.touch.phase,s.skill_input.pressed};
    // a released damage label flies from its position (SimpleLabel+0x334: Game+0xc2f4 / 0x14e30 / 0x151a4)
    const auto at=[&](int i) {return Point{s.damage_labels[i].x,s.damage_labels[i].y};};
    s.release_inputs.leech_label=at(0);s.release_inputs.flame_label=at(1);s.release_inputs.spike_label=at(2);
    InputState state{&s.path,&s.damage,&s.rune,&s.gate_inputs,&s.release,&s.release_inputs,&s.scroll};
    s.input_route=static_cast<std::int32_t>(dr_process_input(&state,&s.input_hooks));
}
void frame_input(void* c) {step_input(self(c));}
void part_event(void* c,const FrameEvent* e) {
    Session& s=self(c);forward(s,SessionSource::Frame,e);
    if(e->kind==FrameEventKind::ProcessInput)step_input(s);   // the stroke cancelled by help 10 (touch phase 3)
    else if(e->kind==FrameEventKind::Help)help_topic(s,e->a,Point{e->x,e->y},as_float(0x3d4ccccd),0.0f);
    else if(e->kind==FrameEventKind::BaseDamageHelp)show_help(s,9);
    else if(e->kind==FrameEventKind::WeaponDamageHelp)show_help(s,10);
}
void frame_effects(void* c) {Session& s=self(c);dr_process_board_effects(&s.effects,s.dt,&s.effect_hooks);}
void frame_falling(void* c) {
    Session& s=self(c);
    if(s.falling.empty()) {dr_reset_round_counters(&s.frame_state,0);return;}
    std::uint32_t count=static_cast<std::uint32_t>(s.falling.size());
    dr_process_falling_list(&s.refill,s.falling.data(),&count,s.dt);s.falling.resize(count);
}
bool frame_tokens(void* c) {
    Session& s=self(c);
    // one pending count: the token queue's (Game+0xb52c), used by AddToken and by the Process token loop
    TokenQueueCounters counters=*dr_token_queue_counters(s.tokens);std::uint32_t pending=counters.pending;
    if(s.motions.size()<pending)motion(s,pending-1);
    const bool continued=dr_process_reward_tokens(s.motions.data(),&pending,&s.resources,s.dt,&s.motion_hooks,&s.resource_hooks,s.screens.menus);
    counters.pending=pending;dr_token_queue_restore(s.tokens,&counters);
    return continued;
}
void frame_pools(void*) {}   // Particles / SimpleLabel pools: presentation, owned by the renderer
void frame_flare_fade(void* c) {Session& s=self(c);dr_process_flare_fade(&s.frame_state,s.dt,&s.part_hooks);}
void frame_damage_label(void* c) {Session& s=self(c);dr_process_damage_label(&s.frame_state,s.current_label_active,s.dt,&s.part_hooks);}
bool frame_damage_labels(void* c) {Session& s=self(c);return dr_process_damage_labels(&s.labels,s.dt,s.touch.position,&s.label_hooks);}
bool label_check_end_game(void* c) {return check_end_game(self(c));}
// The damage labels' SimpleLabel calls (Game::Process) on their models. A label's active byte is
// NewGameExtra.label_active (Game::InitNewGame clears it there); the model follows it.
void label_event(void* c,const LabelEvent* e) {
    Session& s=self(c);
    if(e->label>=0 && e->label<3) {
        SimpleLabelState& l=s.damage_labels[e->label];l.active=s.extra.label_active[e->label];
        float value;std::memcpy(&value,&e->a,sizeof value);
        switch(e->kind) {
        case LabelEventKind::Process:dr_label_process(&l,value);break;
        case LabelEventKind::Initialise:dr_label_initialise(&l,e->a,Point{e->x,e->y},e->b,1.0f,&s.match.random);break;
        case LabelEventKind::Position:dr_label_set_position(&l,Point{e->x,e->y});break;
        case LabelEventKind::Number:dr_label_set_number(&l,e->a);break;
        case LabelEventKind::Alpha:   // SetAlpha, then Game::Process stores it as the fade's base (Game+0xc314)
            dr_label_set_alpha(&l,static_cast<std::uint8_t>(e->a));l.alpha=static_cast<std::uint8_t>(e->a);break;
        case LabelEventKind::Scale:l.scale=value;break;   // SimpleLabel+0x33c
        default:break;
        }
        s.extra.label_active[e->label]=l.active;
    }
    forward(s,SessionSource::Label,e);
}
void follow_label_active(Session& s) {for(int i=0;i<3;++i)s.damage_labels[i].active=s.extra.label_active[i];}
// NameScreen::GenerateRandomName's parts (five-byte entries at 0x18da29 and 0x18d934).
constexpr const char* name_starts[50]={"Ar","Ang","Bal","Bee","Clen","Coy","Def","Dil","En","Eck","Fan","Fen","Gam","Gil","Hel",
    "Har","Il","Ink","Jos","Jen","Kart","Kea","Lid","Lin","Mer","Mond","Neg","Non","Orn","Oart","Pey","Put","Quo","Quin","Rin",
    "Roz","So","Sit","Tec","Tint","Vin","Vam","Wel","Wit","Xer","Xin","Ye","Yon","Zil","Zar"};
constexpr const char* name_ends[49]={"","and","aar","bole","bea","cor","cut","din","dier","een","ell","fet","fall","gren","gap",
    "het","hob","inn","ire","jat","jel","kenn","kaf","lyt","lack","mon","mud","ney","nant","ons","ore","pol","pent","rew","rog",
    "sear","sen","ten","treb","un","ure","ved","vie","wim","wed","yet","yore","zim","zes"};
void set_name(Session& s,const char* name) {   // Game::SetName
    char* own=reinterpret_cast<char*>(s.name);
    s.settings.name_changed_be49=std::strcmp(own,name)!=0;std::strncpy(own,name,16);own[16]=0;
}
void show_setup(Session& s,bool challenge) {   // NameScreen::Show(Game's name, challenge)
    SetupScreen& n=s.setup;n.challenge=challenge;s.screens.name_12c09=1;
    const char* name=reinterpret_cast<const char*>(s.name);n.length=static_cast<std::int32_t>(std::strlen(name));
    if(!n.length){std::memcpy(n.name,"Enter name",11);n.named=0;}
    else {std::strncpy(n.name,name,16);n.name[16]=0;n.named=1;}
}
void frame_attack(void* c) {
    Session& s=self(c);dr_process_attack(&s.damage,&s.path,&s.animation,&s.overlay_alpha,s.dt,&s.attack_inputs,&s.process_hooks);
}

void link(Session& s) {
    void* c=&s;
    for(int i=0;i<10;++i)if(!s.classes[i].replacement_skills) {   // a record given without its replacement list: the session's (none)
        std::fill(s.class_replacements[i],s.class_replacements[i]+20,255);
        s.classes[i].replacement_skills=s.class_replacements[i];s.classes[i].replacement_skill_count=20;
    }
    s.match.stroke=&s.stroke;s.match.preview=&s.preview;
    s.resources.match=&s.match;
    s.path.match=&s.match;s.path.queue=s.tokens;
    s.refill.path=&s.path;
    s.generation.refill=&s.refill;s.generation.resources=&s.resources;
    s.damage.resources=&s.resources;
    s.end_of_turn.skills=&s.skills;s.end_of_turn.flags=&s.turn_flags;s.end_of_turn.rune=&s.rune;
    s.end_of_turn.counterattack=&s.animation.counterattack;s.end_of_turn.end=&s.end;s.end_of_turn.finish=&s.finish;
    s.end_of_turn.activated=s.activated;
    s.release=ReleaseState{&s.path,&s.generation,&s.resources,&s.turn_flags,&s.finish,&s.flights};
    s.scroll.classes=s.classes;s.scroll.difficulty=s.difficulty;
    s.frame_state=FrameState{&s.path,&s.preview,s.tokens,&s.extra,&s.animation,&s.damage,&s.finish,&s.touch};
    s.effects=BoardEffectsState{&s.path,&s.generation,&s.finish,&s.shatter};
    s.labels=DamageLabelState{&s.stroke.selection,&s.resources,&s.flights,s.extra.label_active};
    s.frame=GameFrame{&s.touch,&s.end,&s.screens,&s.stroke,&s.match,&s.path};
    s.skill_state=SkillState{&s.skills,&s.resources,&s.path,&s.generation,&s.turn_flags,&s.finish,&s.rune,&s.animation,&s.end};
    s.new_game=NewGameState{&s.match,&s.preview,&s.resources,&s.path,&s.generation,s.tokens,&s.turn_flags,&s.finish,&s.rune,&s.end,
                            &s.animation.counterattack,&s.damage,&s.player,s.classes,s.difficulty,&s.shatter,&s.extra};

    s.selection_hooks={c,selection_event};
    s.match_hooks={c,match_event};
    s.token_hooks={c,token_event};
    s.motion_hooks={c,motion_event,motion_target,choose_special};
    s.resource_hooks={c,resource_event};
    s.path_hooks={c,path_event,&s.match_hooks,&s.token_hooks};
    s.refill_hooks={c,refill_event};
    s.generation_hooks={c,generation_event};
    s.encounter_hooks={c,encounter_event,&s.refill_hooks};
    s.flare_hooks={c,flare_event};
    s.anim_hooks={c,anim_event,counterattack};
    s.absorb_hooks={c,absorb_event};
    s.shield_hooks={c,forward_event<SessionSource::AttackShield,AttackShieldEvent>};
    s.weaken_hooks={c,weaken_event};
    s.all_hooks={c,all_event,all_attack_skull,all_move};
    s.health_hooks={c,health_event};
    s.fade_hooks={c,forward_event<SessionSource::AttackFade,AttackFadeEvent>};
    s.process_hooks={&s.flare_hooks,&s.anim_hooks,&s.absorb_hooks,&s.shield_hooks,&s.weaken_hooks,&s.all_hooks,&s.health_hooks,&s.fade_hooks};
    s.vampire_hooks={c,vampire_event,nullptr};
    s.turn_hooks={c,turn_event,turn_match_tile,all_attack_skull,turn_check_end_game,all_move,turn_ability,
                  turn_swap,push_token,token_target,token_start};
    s.end_hooks={c,end_event,game_over};
    s.over_hooks={c,over_event,add_score};
    s.schedule_hooks={c,end_of_turn};
    s.release_hooks={c,release_event,release_check_end_game};
    s.input_hooks={&s.schedule_hooks,&s.selection_hooks,&s.release_hooks};
    s.effect_hooks={c,effect_event};
    s.part_hooks={c,part_event};
    s.label_hooks={c,label_event,label_check_end_game};
    s.frame_hooks={c,frame_event,frame_input,frame_effects,frame_falling,frame_tokens,frame_pools,
                   frame_flare_fade,frame_damage_label,frame_damage_labels,frame_attack};
    s.new_game_hooks={c,new_game_event,&s.generation_hooks};
    s.stats_targets=StatsTargets{&s.resources,&s.preview,&s.stroke,&s.path.battle,&s.attack_inputs,&s.end_of_turn.regen,&s.player};
    s.stats_hooks={c,stats_event};
    s.menu_hooks={c,menu_event};s.save_hooks={c,save_event,load_update_stats,&s.generation_hooks,&s.turn_hooks};
    s.cross_hooks={c,forward_event<SessionSource::Cross,CrossEvent>};
    s.skill_hooks={c,skill_event,skill_action,&s.match_hooks,&s.path_hooks};
}
}
extern "C" Session* dr_session_create(const SessionHost* host,std::int32_t difficulty) {
    auto* s=new Session;s->host=*host;s->difficulty=difficulty;dr_scores_init(&s->scores);
    for(int i=0;i<3;++i) {   // SimpleLabel::SimpleLabel, then Game::Start: colours 17, 18, 19 and duration 0.2
        SimpleLabelState& l=s->damage_labels[i];dr_label_construct(&l);dr_label_set_colour(&l,17+i);l.duration=0.2f;
    }
    for(int i=0;i<10;++i)dr_class_initialise(&s->classes[i],i,s->class_replacements[i]);   // Game::Start: the class roster
    s->tokens=dr_token_queue_create(&s->match);
    link(*s);return s;
}
extern "C" void dr_session_destroy(Session* s) {dr_token_queue_destroy(s->tokens);delete s;}
extern "C" SessionObjects dr_session_objects(Session* s) {
    return SessionObjects{&s->stroke,&s->preview,&s->match,&s->rune,s->tokens,&s->resources,&s->path,&s->refill,&s->generation,
        &s->damage,&s->animation,&s->overlay_alpha,&s->attack_inputs,&s->skills,&s->turn_flags,&s->finish,&s->end,s->activated,
        &s->end_of_turn,&s->flights,&s->release_inputs,s->classes,&s->scroll,&s->player,&s->extra,&s->shatter,&s->touch,&s->screens,
        &s->skill_input.pressed,&s->current_label_active,s->motions.data(),static_cast<std::uint32_t>(s->motions.size()),
        s->falling.data(),static_cast<std::uint32_t>(s->falling.size()),&s->skill_button,&s->skill_input,s->items,&s->menu,&s->menu_button,s->dimmed,
        s->save,s->name,&s->settings,&s->class_save,&s->scores,s->damage_labels,&s->setup,&s->game_menu,&s->stats_menu,
        &s->interface_buttons,&s->main_menu,&s->help};
}
extern "C" void dr_session_link(Session* s) {link(*s);}
// Game::SerialiseState now (the session runs it where the original does; IntroScreen::Process also calls it).
extern "C" void dr_session_save(Session* s) {save_state(*s);}
// Game::SerialiseClasses now (the session runs it at a game's end and a class scroll's level-up; the class screen's
// changes call it too).
extern "C" void dr_session_save_classes(Session* s) {const SaveSources src=save_sources(*s);dr_serialise_classes(&src,&s->class_save);}
// The platform's start-up: one stored high-score table back (ScoreScreen::DeserialiseState).
extern "C" bool dr_session_restore_scores(Session* s,std::int32_t type,const std::uint8_t* bytes,std::uint32_t length) {
    if(type<0 || type>5 || length>sizeof(s->scores.bytes))return false;
    std::copy(bytes,bytes+length,s->scores.bytes);dr_score_deserialise(&s->scores,type);return true;
}
// The platform's store loop (ScoreScreen::HaveScoresChanged / SerialiseChangedState): the next changed table into
// SessionObjects.scores->bytes (length scores->length); its type, -1 when none changed.
extern "C" std::int32_t dr_session_save_changed_scores(Session* s) {return dr_score_serialise_changed(&s->scores);}
// The platform's start-up: the stored class records back into Game+0x146d5 and Game::Start's DeserialiseClasses.
extern "C" bool dr_session_restore_classes(Session* s,const std::uint8_t* bytes,std::uint32_t length) {
    if(length>class_save_capacity)return false;
    std::copy(bytes,bytes+length,s->class_save.bytes);s->class_save.length_14ad8=static_cast<std::int32_t>(length);
    const SaveSources src=save_sources(*s);return dr_deserialise_classes(&src,&s->class_save);
}
// The platform's start-up: the stored save back into Game+0x13ecf and its length (stored data over 0x800 bytes is ignored).
extern "C" void dr_session_restore_save(Session* s,const std::uint8_t* bytes,std::uint32_t length) {
    if(length>save_capacity)return;
    std::copy(bytes,bytes+length,s->save);s->end.flag_146d0=static_cast<std::int32_t>(length);
}
extern "C" void dr_session_set_falling(Session* s,const std::int32_t* tiles,std::uint32_t count) {s->falling.assign(tiles,tiles+count);}
extern "C" void dr_session_set_motions(Session* s,const TokenMotion* motions,std::uint32_t count) {s->motions.assign(motions,motions+count);}
extern "C" void dr_session_new_game(Session* s,std::uint32_t time) {
    dr_init_new_game(&s->new_game,time,&s->new_game_hooks);follow_label_active(*s);
}
extern "C" void dr_session_set_mode(Session* s,std::int32_t mode) {
    const std::int32_t v=std::clamp(mode,0,1);s->settings.mode_changed_14aec=s->stroke.mode_14ae8!=v;s->stroke.mode_14ae8=v;
}
extern "C" void dr_session_set_difficulty(Session* s,std::int32_t difficulty) {
    const std::int32_t v=std::clamp(difficulty,0,3);s->settings.difficulty_changed_14ae4=s->match.spawn_enabled_14ae0!=v;
    s->match.spawn_enabled_14ae0=v;
}
extern "C" void dr_session_set_name(Session* s,const char* name) {set_name(*s,name);}
extern "C" void dr_session_setup_random_name(Session* s) {
    SetupScreen& n=s->setup;RandomState* r=&s->match.random;
    if(dr_random_int(r,0,1,0)==0) {
        const std::int32_t a=dr_random_int(r,0,49,0),b=dr_random_int(r,0,48,0);
        std::snprintf(n.name,sizeof n.name,"%s%s",name_starts[a],name_ends[b]);
    } else {
        const std::int32_t a=dr_random_int(r,0,49,0),b=dr_random_int(r,0,48,0),c=dr_random_int(r,0,49,0),d=dr_random_int(r,0,48,0);
        std::snprintf(n.name,sizeof n.name,"%s%s %s%s",name_starts[a],name_ends[b],name_starts[c],name_ends[d]);
    }
    n.length=static_cast<std::int32_t>(std::strlen(n.name));n.named=1;
}
extern "C" bool dr_session_setup_select_class(Session* s,std::int32_t type) {
    if(type<0 || type>9 || !s->classes[type].level)return false;
    dr_session_set_current_class(s,type);return true;
}
extern "C" bool dr_session_setup_mode(Session* s,std::int32_t mode) {
    if(!s->setup.challenge || mode<0 || mode>1)return false;
    dr_session_set_mode(s,mode);return true;
}
extern "C" bool dr_session_setup_difficulty(Session* s,std::int32_t difficulty) {
    if(s->setup.challenge || difficulty<0 || difficulty>3)return false;
    dr_session_set_difficulty(s,difficulty);return true;
}
extern "C" bool dr_session_setup_start(Session* s,std::uint32_t time) {
    if(!s->setup.named || s->setup.length<=0)return false;
    set_name(*s,s->setup.name);
    s->screens.intro_c3f0=1;          // IntroScreen::Initialise
    dr_session_new_game(s,time);
    s->screens.name_12c09=0;
    return true;
}
extern "C" void dr_session_intro_done(Session* s) {s->screens.intro_c3f0=0;save_state(*s);}
// The units read the current class record through views (SelectionState.character, MatchState.perks / class_type /
// class_level; the original reads the record itself): the old record first takes the views' values, then the views
// follow the new current record.
namespace {
// The class screen's edits: the current record takes the units' views first, the views follow it afterwards.
void record_from_views(Session& s) {
    ClassProfile& c=s.classes[s.scroll.current];const auto& sel=s.stroke.selection;
    c.race=sel.character.race;std::copy(s.match.perks,s.match.perks+4,c.perks);std::copy(sel.character.flaws,sel.character.flaws+4,c.flaws);
}
void views_from_record(Session& s) {
    const ClassProfile& c=s.classes[s.scroll.current];auto& sel=s.stroke.selection;
    sel.character.race=c.race;std::copy(c.perks,c.perks+4,s.match.perks);std::copy(c.flaws,c.flaws+4,sel.character.flaws);
    s.match.class_type=c.class_type;s.match.class_level=c.level;
}
template<class Edit> void edit_current(Session& s,Edit edit) {record_from_views(s);edit(s.classes[s.scroll.current]);views_from_record(s);}
}
extern "C" void dr_session_class_choices(Session* s,std::uint8_t perks[10],std::uint8_t flaws[10],std::uint8_t skills[20]) {
    record_from_views(*s);dr_class_choices(s->classes,s->scroll.current,perks,flaws,skills);
}
extern "C" bool dr_session_class_select(Session* s,std::int32_t type) {return dr_session_setup_select_class(s,type);}
// The setup screen's help button (NameScreen::ProcessInput: sound 0, then HelpMenu::QueueHelp of its five texts) and the
// class screen's (ClassScreen::Process, released on it: the shown tab's texts)
extern "C" void dr_session_setup_help(Session* s) {
    menu_sound(*s);
    for(std::int32_t t=100;t<105;++t)help_queue(*s,t);
}
extern "C" bool dr_session_class_help(Session* s,std::int32_t tab) {
    static const std::int32_t first[]={105,110,114,118,123};
    if(tab<0 || tab>3)return false;
    for(std::int32_t t=first[tab];t<first[tab+1];++t)help_queue(*s,t);
    return true;
}
extern "C" bool dr_session_class_set_race(Session* s,std::int32_t race) {
    record_from_views(*s);
    if(!dr_race_unlocked(s->classes,race) || !dr_class_can_choose_race(&s->classes[s->scroll.current]))return false;
    edit_current(*s,[race](ClassProfile& c){c.race=race;});return true;
}
extern "C" void dr_session_class_set_perk(Session* s,std::int32_t slot,std::int32_t perk) {
    edit_current(*s,[=](ClassProfile& c){dr_class_set_perk(&c,slot,perk);});
}
extern "C" void dr_session_class_set_flaw(Session* s,std::int32_t slot,std::int32_t flaw) {
    edit_current(*s,[=](ClassProfile& c){dr_class_set_flaw(&c,slot,flaw);});
}
extern "C" void dr_session_class_set_skill(Session* s,std::int32_t slot,std::int32_t skill) {
    edit_current(*s,[=](ClassProfile& c){dr_class_set_replacement(&c,slot,skill);});
}
extern "C" void dr_session_class_tab(Session* s) {dr_session_save_classes(s);}
extern "C" void dr_session_class_done(Session* s) {
    edit_current(*s,[](ClassProfile& c){dr_class_validate(&c);});
    dr_session_set_current_class(s,s->classes[s->scroll.current].class_type);
    dr_session_save_classes(s);
}
extern "C" void dr_session_set_current_class(Session* s,std::int32_t type) {
    auto& sel=s->stroke.selection;MatchState& m=s->match;
    ClassProfile& old=s->classes[s->scroll.current];
    old.race=sel.character.race;std::copy(m.perks,m.perks+4,old.perks);std::copy(sel.character.flaws,sel.character.flaws+4,old.flaws);
    s->scroll.current=static_cast<std::size_t>(dr_current_class(s->classes,type));
    const ClassProfile& c=s->classes[s->scroll.current];
    sel.character.race=c.race;std::copy(c.perks,c.perks+4,m.perks);std::copy(c.flaws,c.flaws+4,sel.character.flaws);
    m.class_type=c.class_type;m.class_level=c.level;
}
extern "C" void dr_session_start_game(Session* s,std::int32_t kind,std::uint32_t time) {
    s->stroke.record_14aed=kind==2;
    dr_session_new_game(s,time);
    if(kind==1)s->match.spawn_enabled_14ae0=0;
    s->screens.main_menu_c400=0;                     // MainMenu::SetActive(false)
    s->settings.help_13ec8=kind==1;                  // Game::SetHelpState
    s->finish.help_flags_102d0=kind==1?s->finish.help_flags_102d0|0x7fffffu:0u;   // HelpMenu::ResetHelp / ClearHelp
    show_setup(*s,kind==2);
    s->dt=0.0f;interface_process(*s,false);   // Interface::Process(0, false): with nothing open, ProcessHeartbeat (T040-M6)
}
// Game::DeserialiseState now: the saved game in SessionObjects.save over the current state (false: no 0xff header).
extern "C" bool dr_session_deserialise(Session* s) {const SaveSources src=save_sources(*s);return dr_deserialise_state(&src,s->save,&s->save_hooks);}
// Game::ContinueGame 0x165f4: with a saved game (end.flag_146d0), Game::InitNewGame, Game::DeserialiseState and
// Game::CalculateTilePositions (the main menu's fade and Interface::Process(0, false) are presentation).
extern "C" bool dr_session_continue_game(Session* s,std::uint32_t time) {
    if(!s->end.flag_146d0)return false;
    dr_session_new_game(s,time);
    const SaveSources src=save_sources(*s);dr_deserialise_state(&src,s->save,&s->save_hooks);
    dr_calculate_tile_positions(&s->stroke,&s->new_game_hooks);
    s->dt=0.0f;interface_process(*s,false);   // Interface::Process(0, false) (T040-M6: the heartbeat's help)
    return true;
}
extern "C" void dr_session_interface_process(Session* s,float dt,bool input_ready) {s->dt=dt;interface_process(*s,input_ready);}
extern "C" FrameRoute dr_session_frame(Session* s,float dt,std::int32_t touch_phase,Point touch) {
    s->touch.phase=touch_phase;s->touch.position=touch;s->dt=dt;s->input_route=-1;
    return dr_process_frame(&s->frame,dt,&s->frame_hooks);
}
extern "C" std::int32_t dr_session_input_route(const Session* s) {return s->input_route;}
