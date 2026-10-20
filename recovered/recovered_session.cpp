#include "recovered_session.hpp"
#include "recovered_preview.hpp"
#include "recovered_rune.hpp"
#include "recovered_stroke.hpp"
#include "recovered_tokens.hpp"
#include "recovered_path.hpp"
#include <algorithm>
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
    std::int32_t input_target=-1;
    std::uint8_t current_label_active=0;
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
};
}
namespace {
Session& self(void* c) {return *static_cast<Session*>(c);}
void forward(Session& s,SessionSource source,const void* e) {if(s.host.event)s.host.event(s.host.context,source,e);}
template<SessionSource source,class Event> void forward_event(void* c,const Event* e) {forward(self(c),source,e);}

// Game::AddFlare: every unit's Flare event is one call (dr_add_flare: rotation from stream 0, count + 1).
void add_flare(Session& s) {dr_add_flare(&s.animation.flare_count,&s.match.random);}
// Game::AddParticles / Game::AddSimpleLabel: their random draws on stream 0 (dr_add_particles / dr_add_simple_label).
void particles(Session& s,std::int32_t type) {dr_add_particles(&s.match.random,type);}
void label(Session& s,std::int32_t type) {dr_add_simple_label(&s.match.random,type);}
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
    if(kind==SelectionEvent::ResourceShadows)dr_preview_resources(&s.stroke,&s.preview,&s.selection_hooks);
    else if(kind==SelectionEvent::ProcessRune)dr_process_rune(&s.stroke,&s.rune,a!=0,&s.selection_hooks);
    else if(kind==SelectionEvent::RuneMatchTile)dr_match_tile(&s.match,static_cast<std::uint32_t>(index),a,&s.match_hooks);
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
std::int32_t choose_special(void* c,TokenMotion* t) {Session& s=self(c);return s.host.choose_special(s.host.context,t);}
// The resource and encounter units call Game::Healing and Game::CheckEndGame (their result is not used there).
void resource_event(void* c,const ResourceEvent* e) {
    Session& s=self(c);forward(s,SessionSource::Resource,e);
    if(e->kind==ResourceEventKind::Healing)dr_healing(&s.resources,&s.resource_hooks);
    else if(e->kind==ResourceEventKind::CheckEndGame)check_end_game(s);
    else if(e->kind==ResourceEventKind::Label)label(s,e->a);
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
    default:break;
    }
}
void turn_match_tile(void* c,std::int32_t tile,std::int32_t reward) {
    Session& s=self(c);dr_match_tile(&s.match,static_cast<std::uint32_t>(tile),reward,&s.match_hooks);
}
bool turn_check_end_game(void* c) {return check_end_game(self(c));}
void turn_ability(void* c,std::int32_t kind,std::int32_t tile) {
    // Game::DestroyUpgrade needs the item model (not yet recovered): reported to the embedding.
    const SessionSmallEvent e{kind,tile,0,0};forward(self(c),SessionSource::Ability,&e);
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
void add_score(void* c,const ScoreEntry* e) {forward(self(c),SessionSource::Score,e);}
void over_event(void* c,const TurnEvent* e) {
    Session& s=self(c);forward(s,SessionSource::GameOver,e);
    // GameOverScreen::Initialise (0x307f8): the screen shows (Game+0xcac4 = 1, 0x30898) in its state 0
    // (Game+0xcc1c = 0, 0x30868); the rest of it is presentation.
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
    case ReleaseEventKind::MatchTiles: {   // Game::MatchTiles: the path without its fake tiles
        std::uint8_t excluded[36];std::size_t n=0;
        for(std::uint8_t i=0;i<36;++i)if(sel.fake[i])excluded[n++]=i;
        dr_commit_path(&s.path,sel.path,sel.path_length,excluded,n,&s.path_hooks);break;
    }
    case ReleaseEventKind::MatchTile:dr_match_tile(&s.match,static_cast<std::uint32_t>(e->tile),e->a,&s.match_hooks);break;
    case ReleaseEventKind::MoveMatchedTiles:move_matched_tiles(s);break;
    default:break;
    }
}
bool release_check_end_game(void* c) {return check_end_game(self(c));}
// Frame steps
void step_input(Session& s) {
    s.stroke.selection.touch=s.touch.position;
    s.gate_inputs=InputGateInputs{static_cast<std::uint32_t>(s.falling.size()),static_cast<std::int32_t>(dr_token_queue_counters(s.tokens)->pending),
                                  s.animation.flare_count,s.touch.phase,s.input_target};
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
    s.label_hooks={c,forward_event<SessionSource::Label,LabelEvent>,label_check_end_game};
    s.frame_hooks={c,forward_event<SessionSource::GameFrame,GameFrameEvent>,frame_input,frame_effects,frame_falling,frame_tokens,frame_pools,
                   frame_flare_fade,frame_damage_label,frame_damage_labels,frame_attack};
    s.new_game_hooks={c,forward_event<SessionSource::NewGame,NewGameEvent>,&s.generation_hooks};
}
}
extern "C" Session* dr_session_create(const SessionHost* host,std::int32_t difficulty) {
    auto* s=new Session;s->host=*host;s->difficulty=difficulty;
    s->tokens=dr_token_queue_create(&s->match);
    link(*s);return s;
}
extern "C" void dr_session_destroy(Session* s) {dr_token_queue_destroy(s->tokens);delete s;}
extern "C" SessionObjects dr_session_objects(Session* s) {
    return SessionObjects{&s->stroke,&s->preview,&s->match,&s->rune,s->tokens,&s->resources,&s->path,&s->refill,&s->generation,
        &s->damage,&s->animation,&s->overlay_alpha,&s->attack_inputs,&s->skills,&s->turn_flags,&s->finish,&s->end,s->activated,
        &s->end_of_turn,&s->flights,&s->release_inputs,s->classes,&s->scroll,&s->player,&s->extra,&s->shatter,&s->touch,&s->screens,
        &s->input_target,&s->current_label_active,s->motions.data(),static_cast<std::uint32_t>(s->motions.size()),
        s->falling.data(),static_cast<std::uint32_t>(s->falling.size())};
}
extern "C" void dr_session_link(Session* s) {link(*s);}
extern "C" void dr_session_set_falling(Session* s,const std::int32_t* tiles,std::uint32_t count) {s->falling.assign(tiles,tiles+count);}
extern "C" void dr_session_set_motions(Session* s,const TokenMotion* motions,std::uint32_t count) {s->motions.assign(motions,motions+count);}
extern "C" void dr_session_new_game(Session* s,std::uint32_t time) {dr_init_new_game(&s->new_game,time,&s->new_game_hooks);}
extern "C" FrameRoute dr_session_frame(Session* s,float dt,std::int32_t touch_phase,Point touch) {
    s->touch.phase=touch_phase;s->touch.position=touch;s->dt=dt;s->input_route=-1;
    return dr_process_frame(&s->frame,dt,&s->frame_hooks);
}
extern "C" std::int32_t dr_session_input_route(const Session* s) {return s->input_route;}
