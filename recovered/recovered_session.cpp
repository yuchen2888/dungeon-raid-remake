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
    default:break;
    }
}
// A token request becomes a flying token in its slot (Token::InitialiseFromTile).
void token_event(void* c,const TokenEvent* e) {
    Session& s=self(c);forward(s,SessionSource::Token,e);
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
}
void menu_event(void* c,const MenuEvent* e) {
    Session& s=self(c);forward(s,SessionSource::Menu,e);
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
    default:break;
    }
}
void skill_action(void* c,SkillAction action,std::int32_t a,std::int32_t b) {
    Session& s=self(c);dr_skill_action(&s.skill_state,action,a,b,&s.skill_hooks,&s.generation_hooks);
}
// Interface::Process: with an in-game menu open the menu runs (the renderer's); otherwise, with input ready,
// Interface::ProcessInput's skill buttons.
void frame_event(void* c,const GameFrameEvent* e) {
    Session& s=self(c);forward(s,SessionSource::GameFrame,e);
    if(e->kind!=GameFrameEventKind::InterfaceProcess)return;
    const auto& m=s.screens.menus;
    if(m[0]) {   // the shop and upgrade menus end in Game::UpdateStats
        const MenuSources src=menu_sources(s);dr_menu_process(&s.menu,&src,s.dt,s.touch.phase,s.menu_button,&s.menu_hooks);sync_chances(s);return;
    }
    if(m[1] || m[2] || !e->a)return;
    dr_skill_input(&s.skill_state,&s.skill_input,s.touch.phase,s.skill_button,&s.skill_hooks,&s.generation_hooks);
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
    if(e->kind==FrameEventKind::ProcessInput)step_input(s);   // the stroke cancelled by help 8 (touch phase 3)
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
    s.effect_hooks={c,forward_event<SessionSource::BoardEffect,BoardEffectEvent>};
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
        s->save,s->name,&s->settings,&s->class_save,&s->scores,s->damage_labels,&s->setup};
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
    return true;
}
extern "C" FrameRoute dr_session_frame(Session* s,float dt,std::int32_t touch_phase,Point touch) {
    s->touch.phase=touch_phase;s->touch.position=touch;s->dt=dt;s->input_route=-1;
    return dr_process_frame(&s->frame,dt,&s->frame_hooks);
}
extern "C" std::int32_t dr_session_input_route(const Session* s) {return s->input_route;}
