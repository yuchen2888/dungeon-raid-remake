#include "presenter.hpp"
#include "recovered_random.hpp"
#include "recovered_tokens.hpp"
#include <cmath>
#include <cstdio>
#include <algorithm>
#include <cstring>
#include <utility>
using namespace dungeonraid;
namespace drui {
namespace {
constexpr float cell=0.0517578125f;   // one tile picture in tiles.png (53 / 1024)
float f32(std::int32_t bits) {float f;std::memcpy(&f,&bits,4);return f;}
Colour colour_of(std::int32_t rgba) {
    Colour c;std::memcpy(&c,&rgba,4);return c;
}
// Tile::GetAttack 0x3d21c on the session's combat tile, with the race the rule units use (selection.character).
std::int32_t tile_attack(const SessionObjects& o,int i) {
    const PathCombatTile& c=o.path->combat[i];
    const CharacterClassState character{o.stroke->selection.character.race};
    const GameContext game{&character};const TileState t{c.attack,c.poison,&game};
    return dr_get_attack(&t);
}
}
// Tile::Tile 0x3e088: the cross and the glow get their pictures and sizes; no labels yet.
TileView::TileView() {
    cross.set_uv(Point2{0.157226562f,0.323242188f},Point2{0.203125f,0.372070312f});
    cross.set_size(Point2{0.146874994f,0.15625f});
    glow.set_uv(Point2{0.0009765625f,0.904296875f},Point2{0.052734375f,0.9609375f});
    glow.set_size(Point2{0.248437509f,0.267187476f});
}
bool Presenter::load(const std::string& assets,const std::string& language) {
    bool ok=font.load(assets+"/font.fnt",FontTexture);
    ok=menu_font.load(assets+"/fontMenu.fnt",FontMenu) && ok;
    menu_font.use_small_caps(0.75f);menu_font.spacing=-0.225f;
    ok=score_font.load(assets+"/fontScore.fnt",FontScore) && ok;
    score_font.use_small_caps(0.75f);score_font.spacing=-0.05f;
    iface.set_fonts(&font,&score_font);iface.set_texts(texts);
    ok=texts.load(assets+"/texts.txt") && ok;
    if(!language.empty()) {   // (T050-D)
        language_index=language.size()>=3 && language.compare(language.size()-3,3,"/zh")==0?1:0;
        ok=texts.load(language+"/texts.txt") && ok;
        ok=font.load_wide(language+"/font.fnt",WideFont) && ok;
        ok=menu_font.load_wide(language+"/fontMenu.fnt",WideMenu) && ok;
        ok=score_font.load_wide(language+"/fontScore.fnt",WideScore) && ok;
    }
    setup.initialise(texts);   // NameScreen::Initialise (Game::Start, once the fonts are made)
    scores.initialise(texts);  // ScoreScreen::Initialise
    return ok;
}
// Tile::InitialiseLabels 0x3e358 (once per tile): four labels in the game's font (Game+0x1c), scaled 0.08 (the
// countdown 0.13), defence pale blue, health red, placed from the font's line height and base.
void Presenter::initialise_labels(int i) {
    TileView& t=tiles[i];
    if(t.labels)return;
    t.labels=true;
    t.attack=Label(&font);t.defence=Label(&font);t.health=Label(&font);t.countdown=Label(&font);
    t.attack.scale=t.defence.scale=t.health.scale=Point2{0.08f,0.08f};
    t.countdown.scale=Point2{0.13f,0.13f};
    t.defence.colour=Colour{173,177,255,255};t.defence.update_colour();
    t.health.colour=Colour{255,70,60,255};t.health.update_colour();
    const float k=static_cast<float>(font.line_height-font.base)/static_cast<float>(font.line_height);
    const float a=k*0.08f;
    const float attack_y=a-0.082812503f;
    t.attack.position.y=attack_y;
    t.defence.position.y=a+attack_y;
    const float h=k/2.5999999f;
    t.health.position.y=h*-0.0799999982f+0.082812503f;
    t.countdown.position.y=k*0.0533333309f+attack_y;
    t.countdown.position.x=0.0f;
}
// Tile::UpdateText 0x3da78: the chosen numbers rewritten, right-aligned at 0.0752841 (1s nudged right by 0.005).
void Presenter::update_text(const SessionObjects& o,int i,bool attack,bool defence,bool health) {
    TileView& t=tiles[i];const PathCombatTile& c=o.path->combat[i];char text[32];
    if(attack) {
        std::snprintf(text,sizeof text,"%d",tile_attack(o,i));t.attack.set_text(text);
        const float nudge=c.attack==1?0.00499999989f:0.0f;
        const float x=0.0752840936f-t.attack.width*t.attack.scale.x;
        t.attack.position.x=x-nudge;
    }
    if(defence) {
        std::snprintf(text,sizeof text,"%d",c.defence);t.defence.set_text(text);
        const float nudge=c.defence==1?0.00499999989f:0.0f;
        const float x=0.0752840936f-t.defence.width*t.defence.scale.x;
        t.defence.position.x=x-nudge;
    }
    if(health) {
        std::snprintf(text,sizeof text,"%d",c.health);t.health.set_text(text);
        t.health.position.x=0.0752840936f-t.health.width*t.health.scale.x;
    }
}
// Tile::UpdateCountdown 0x3d9ec: the enemy state centred on the label offset (enemy 28: 0.009375 to the left).
void Presenter::update_countdown(const SessionObjects& o,int i) {
    TileView& t=tiles[i];char text[32];
    std::snprintf(text,sizeof text,"%d",o.stroke->selection.tiles[i].rule.enemy_state);t.countdown.set_text(text);
    const float w=t.countdown.width*t.countdown.scale.x;
    float x=w*-0.5f+o.generation->tiles[i].label_offset;
    if(o.stroke->selection.tiles[i].rule.enemy_type==28)x=x-0.00937500037f;
    t.countdown.position.x=x;
}
// Tile::UpdateEnemyUV 0x3ef64: the picture of the enemy type (Tile::GetEnemyUV 0x3d2c4: eight a row from v 0.65625;
// an active resurrecting enemy (32) has its own), the countdown's colour for enemies 3 / 19 (black) and 10 / 28
// (yellow), and the glow of the class's mortal enemy: Tile+0x224 (GeneratedTile.flag_224) and its spin speed
// Rand(30, 45, stream 0) -- the session's, drawn after the event, so the speed from a copy of the stream here.
void Presenter::update_enemy_uv(const SessionObjects& o,int i) {
    TileView& t=tiles[i];const RuleTile& r=o.stroke->selection.tiles[i].rule;const std::int32_t e=r.enemy_type;
    if(e==0) {
        const float u=static_cast<float>(o.generation->tiles[i].variant)*cell,v=static_cast<float>(r.type)*cell;
        t.quad.set_uv(u,v,cell,cell);
    } else if(e==32 && r.enemy_state) {
        t.quad.set_uv(0.655273438f,0.448242188f,cell,cell);
    } else {
        const std::int32_t k=e-1;
        const float u=static_cast<float>(k%8)*cell;
        const float row=static_cast<float>(k/8)*cell;
        const Point2 tl{u,row+0.65625f};
        t.quad.set_uv(tl,Point2{tl.x+cell,tl.y+cell});
    }
    if(e==19 || e==3) {t.countdown.colour=Colour{0,0,0,255};t.countdown.update_colour();}
    else if(e==28 || e==10) {t.countdown.colour=Colour{255,255,0,255};t.countdown.update_colour();}
    if(e && e==dr_mortal_enemy(o.classes[o.scroll->current].race)) {
        RandomState r=o.match->random;t.glow_speed=dr_random_float(&r,30.0f,45.0f,0);
    }
}
// Tile::Dim 0x3e5f0 / Undim 0x3e670: alpha 150 (undimmed 255; a burning overlay 200), the skull's labels too.
void Presenter::dim(const SessionObjects& o,int i) {
    TileView& t=tiles[i];
    t.quad.set_alpha(150);t.overlay.set_alpha(150);t.glow.set_alpha(150);
    if(o.stroke->selection.tiles[i].rule.type==1 && t.labels)
        for(Label* l:{&t.attack,&t.defence,&t.health,&t.countdown}){l->colour.a=150;l->update_colour();}
}
void Presenter::undim(const SessionObjects& o,int i) {
    TileView& t=tiles[i];
    t.quad.set_alpha(255);t.glow.set_alpha(255);
    t.overlay.set_alpha(o.stroke->selection.tiles[i].flaming?200:255);
    if(o.stroke->selection.tiles[i].rule.type==1 && t.labels)
        for(Label* l:{&t.attack,&t.defence,&t.health,&t.countdown}){l->colour.a=255;l->update_colour();}
}
// Tile::SetFreezeVisibility 0x3d934 (the flags are the session's): the ice picture on the overlay.
void Presenter::freeze(int i,bool on) {
    if(!on)return;
    Quad& q=tiles[i].overlay;
    q.set_uv(Point2{0.321289062f,0.389648438f},Point2{0.370117188f,0.435546875f});
    q.set_size(Point2{0.15625f,0.146874994f});q.set_alpha(255);
}
// Tile::SetFlameVisibility 0x3d89c (the flags and damage are the session's): the flame picture, alpha 200.
void Presenter::flame(int i,bool on) {
    if(!on)return;
    Quad& q=tiles[i].overlay;
    q.set_uv(Point2{0.415039062f,0.55859375f},Point2{0.450195312f,0.603515625f});
    q.set_size(Point2{0.112499997f,0.143749997f});q.set_alpha(200);
}
// Token::InitialiseFromTile 0x21448, its picture: a copy of the tile (Quad::CopyFrom), white; an XP reward is the
// orb, a reward of another type than the tile is that type's picture (Tile::GetTileUV 0x3d480: its RandI(0, 7, stream 0)
// the session draws after the event, so the same number from a copy of the stream here).
void Presenter::token_picture(const SessionObjects& o,const SessionSmallEvent& e) {
    if(token_slot<0 || static_cast<std::size_t>(token_slot)>=tokens.size())return;
    Quad& q=tokens[static_cast<std::size_t>(token_slot)];
    switch(static_cast<MotionEventKind>(e.kind)) {
    case MotionEventKind::CopyTile: if(e.index>=0 && e.index<36)q.copy_from(tiles[e.index].quad);break;
    case MotionEventKind::WhiteColour: q.set_colour(Colour{255,255,255,255});break;
    case MotionEventKind::XPVisual:
        q.set_uv(Point2{0.4140625f,0.0009765625f},Point2{0.452148438f,0.0224609375f});
        q.set_size(Point2{0.121875003f,0.0718749985f});
        break;
    case MotionEventKind::TileVisual: {
        RandomState r=o.match->random;
        const float x=static_cast<float>(dr_random_int(&r,0,7,0))*cell,y=static_cast<float>(e.index)*cell;
        q.set_uv(Point2{x,y},Point2{x+cell,y+cell});
        break;
    }
    default: break;
    }
}
Presenter::Presenter() {
    dr_label_construct(&current);
    for(auto& l:attack_labels)dr_label_construct(&l);
    game_start(nullptr);
}
// Game::Start 0xb916..0xbbce, the presentation it sets up for every game.
void Presenter::game_start(const SessionObjects* o) {
    dr_label_set_colour(&current,10);current.duration=0.2f;
    Quad& red=attack_bar[0];
    red.set_size(Point2{0.778124988f,0.075000003f});red.position=Point2{0.5f,0.529999971f};red.set_colour(Colour{255,0,0,255});
    red.set_uv(Point2{0.192382812f,0.280273438f},Point2{0.435546875f,0.303710938f});
    Quad& yellow=attack_bar[1];
    yellow.set_size(Point2{0.574999988f,0.075000003f});yellow.position=Point2{0.5f,0.529999971f};
    yellow.set_colour(Colour{255,255,0,255});
    yellow.set_uv(Point2{0.262695312f,0.3046875f},Point2{0.442382812f,0.328125f});yellow.set_alpha(0);
    const float label_y=o?o->animation->label_y:0.667500019f;   // Game+0xbd54, set to 0.6675 just before
    RandomState unused{};   // types 2 and 7 draw nothing (SimpleLabel::Initialise)
    dr_label_set_colour(&attack_labels[0],11);attack_labels[0].duration=0.2f;
    dr_label_initialise(&attack_labels[0],2,Point2{0.5f,label_y},0,1.0f,&unused);
    dr_label_set_colour(&attack_labels[1],15);attack_labels[1].duration=0.2f;
    dr_label_initialise(&attack_labels[1],7,Point2{0.5f,label_y+0.0500000007f},0,1.0f,&unused);
    overlay.set_size(Point2{2.0f,2.0f});overlay.position=Point2{0.5f,0.5f};overlay.set_colour(Colour{0,0,0,120});
    for(auto& q:shield_chunk)q.set_size(Point2{0.0343750007f,0.0625f});
    shield_chunk[0].set_uv(Point2{0.4765625f,0.450195312f},Point2{0.487304688f,0.469726562f});
    shield_chunk[1].set_uv(Point2{0.48828125f,0.450195312f},Point2{0.499023438f,0.469726562f});
}
// Game::AddSimpleLabel(SimpleLabelType, GLfloat2 const&, int, int, float) 0xae2c (the tile overload 0xb130 is type 0,
// number 0, scale 1 at the tile): Initialise, then SetColour. Initialise draws its Rand(0.1, 0.2) on stream 0 for
// most types; the session draws the same right after the event (dr_add_simple_label), so the label draws from a
// copy of the stream as it is now.
void Presenter::add_label(const SessionObjects& o,std::int32_t type,Point2 at,std::int32_t number,std::int32_t colour,float scale) {
    SimpleLabelState& l=labels.next();
    RandomState random=o.match->random;
    dr_label_initialise(&l,type,at,number,scale,&random);
    dr_label_set_colour(&l,colour);
    ++labels.count;
}
// Game::AddFlare 0x9f94 in the entry the session's flare count names (it counts the flare after this event): the
// type's star of tiles.png, scale 0.08, the position, rotation Rand(0, 360) on stream 0 (from a copy of the stream:
// the session draws it next, dr_add_flare), the colour.
void Presenter::add_flare(const SessionObjects& o,std::int32_t type,Point2 at,std::int32_t colour) {
    const std::int32_t n=o.animation->flare_count;
    if(n<0)return;
    if(flares.size()<=static_cast<std::size_t>(n))flares.resize(static_cast<std::size_t>(n)+1);
    Quad& q=flares[static_cast<std::size_t>(n)];
    if(type==0)q.set_uv(Point2{0.466796875f,0.426757812f},Point2{0.489257812f,0.44921875f});
    else if(type==1)q.set_uv(Point2{0.204101562f,0.313476562f},Point2{0.26171875f,0.372070312f});
    q.scale=Point2{0.0799999982f,0.0799999982f};
    q.position=at;
    RandomState random=o.match->random;
    q.rotation=dr_random_float(&random,0.0f,360.0f,0);
    q.set_colour(colour_of(colour));
}
// Tile::GetAttackLabelPosition 0x3e2c0 (GetDefenceLabelPosition 0x3e274, GetHealthLabelPosition 0x3e30c): the
// middle of the label's text at its place on the tile, 0.015 up.
Point2 Presenter::label_position(const SessionObjects& o,std::int32_t tile,const Label& l) const {
    const Point2 c=o.stroke->selection.tiles[tile].geometry.center;
    const float x=l.width*l.scale.x*0.5f+l.position.x;
    return Point2{c.x+x,c.y+(l.position.y-0.0149999997f)};
}
// Game::AddParticles 0xa914: Particles::InitialiseFromTile(tile, type) in the next pool entry (its Rand calls from a
// copy of the stream, as add_label's).
void Presenter::add_particles(const SessionObjects& o,std::int32_t tile,std::int32_t type) {
    if(tile<0 || tile>35)return;
    const TileView& t=tiles[tile];
    Quad q=t.quad;q.position=o.stroke->selection.tiles[tile].geometry.center;
    Point2 at{};
    if(type==1)at=label_position(o,tile,t.defence);
    else if(type==2)at=label_position(o,tile,t.health);
    else if(type==3)at=label_position(o,tile,t.attack);
    RandomState random=o.match->random;
    particles.next().initialise(q,at,type,&random);
    ++particles.count;
}
// Game::UpdateCrossVisibility 0xaa24, a cross label: SetColour, then Initialise(type, the tile's position less
// (0.0109375, 0.0171875), 0, 1) (its Rand drawn as add_label's).
void Presenter::add_cross_label(const SessionObjects& o,std::int32_t type,std::int32_t tile,std::int32_t colour) {
    if(tile<0 || tile>35)return;
    SimpleLabelState& l=cross_labels.next();
    dr_label_set_colour(&l,colour);
    const Point2 c=o.stroke->selection.tiles[tile].geometry.center;
    RandomState random=o.match->random;
    dr_label_initialise(&l,type,Point2{c.x-0.0109374998f,c.y-0.0171875004f},0,1.0f,&random);
    ++cross_labels.count;
}
// Game::Process 0x17622: the current-damage label's Process / Initialise(type 1, scale 1) / SetPosition / SetNumber;
// the session reads its active byte back (current_label_active).
void Presenter::current_label(const SessionObjects& o,const FrameEvent& e) {
    switch(e.kind) {
    case FrameEventKind::Process: dr_label_process(&current,f32(e.a));break;
    case FrameEventKind::Initialise: {
        RandomState random=o.match->random;
        dr_label_initialise(&current,e.a,Point2{e.x,e.y},e.b,1.0f,&random);
        break;
    }
    case FrameEventKind::Position: dr_label_set_position(&current,Point2{e.x,e.y});break;
    case FrameEventKind::Number: dr_label_set_number(&current,e.a);break;
    default: return;
    }
    *o.current_label_active=current.active;
}
// After the session's Interface::Process: what its menus and buttons did, seen from what changed (GameMenu::Show at the
// menu button's release; GameMenu::Process's fade while its timer ran, else a button pressed or let go; Interface's
// menu and stats buttons touched (alpha 150) or released (255)), then Interface::Process's own part.
void Presenter::finish_game_over(const SessionObjects& o) {
    GameOverBefore& b=game_over_before;
    if(!b.due)return;
    b.due=false;
    game_over.process(o,b.tally,b.state,b.phase,b.ended_line,b.ended_value,dt,skills);
}
void Presenter::finish_frame(const SessionObjects& o) {finish_interface(o);finish_game_over(o);finish_scores(o);finish_unlock(o);}
void Presenter::finish_unlock(const SessionObjects& o) {   // UnlockMenu::Process: everything at the session's alpha
    if(!unlock_due)return;
    unlock_due=false;
    if(o.screens->unlock_165a0)unlock.set_alpha(o.unlock->alpha);
}
void Presenter::finish_scores(const SessionObjects& o) {
    ScoresBefore& b=scores_before;
    if(!b.due)return;
    b.due=false;
    if(b.shown)scores.show(o,true);
    else if(!b.open && o.screens->score_ef6c)scores.show(o,false);   // the main menu's High scores
    else if(b.routed)scores.process(o,b.pages);
}
void Presenter::finish_interface(const SessionObjects& o) {
    if(!interface_due)return;
    interface_due=false;
    const MenusBefore& was=menus_before;
    const OverlayMenu& gm=*o.game_menu;
    if(!was.open[1] && o.screens->menus[1])game_menu.show();
    else if(was.open[1]) {
        if(was.game.timer>0.0f)game_menu.fade(gm);
        else if(was.game.pressed<0 && gm.pressed>=0)game_menu.press(gm.pressed,true);
        else if(was.game.pressed>=0 && gm.pressed<0)game_menu.press(was.game.pressed,false);
    }
    const OverlayMenu& sm=*o.stats_menu;
    if(!was.open[2] && o.screens->menus[2]) {   // StatsMenu::Show, on the equipped items (Game::GetItem by type)
        equipped.resize(5);
        for(int i=0;i<5;++i)equipped[static_cast<std::size_t>(i)].item(texts,o.items[i]);
        stats_menu.show(texts,o,equipped);
    } else if(was.open[2]) {
        if(was.stats.timer>0.0f)stats_menu.fade(sm,equipped);
        else if(sm.pressed!=was.stats.pressed && sm.pressed>=10)stats_menu.tab(texts,o,equipped,sm.pressed,was.stats.pressed);
    }
    const InterfaceButtons& now=*o.interface_buttons;
    if(!was.buttons.menu_pressed && now.menu_pressed)iface.q(0xbd4).set_alpha(150);
    else if(was.buttons.menu_pressed && !now.menu_pressed)iface.q(0xbd4).set_alpha(255);
    if(!was.buttons.stats_pressed && now.stats_pressed)iface.q(0xc44).set_alpha(150);
    else if(was.buttons.stats_pressed && !now.stats_pressed)iface.q(0xc44).set_alpha(255);
    iface.process(o,interface_dt,was.heartbeat);
    tooltip.process(interface_dt);   // Interface::Process 0x20cce, after the heartbeat
}
// Interface::ShowMenu -> FoldoutMenu::Initialise: the menu's picture on the options the session chose.
void Presenter::open_menu(const SessionObjects& o) {
    menu_pending=false;
    equipped.resize(5);
    for(int i=0;i<5;++i)equipped[static_cast<std::size_t>(i)].item(texts,o.items[i]);
    foldout.open(texts,o,equipped);
}
std::int32_t Presenter::menu_button_at(const SessionObjects& o,Point2 touch) const {
    if(o.screens->help_102a4)return help.button_at(touch);   // the help bubble pauses everything else
    if(o.screens->main_menu_c400 && !o.screens->score_ef6c && !o.screens->name_12c09)return main_menu.button_at(o,touch);
    if(o.screens->score_ef6c)return scores.button_at(touch);
    if(o.screens->menus[0])return foldout.button_at(o,touch);
    if(o.screens->menus[1])return game_menu.button_at(touch);
    if(o.screens->menus[2])return stats_menu.button_at(touch);
    return -1;
}
std::int32_t Presenter::skill_button_at(const SessionObjects& o,Point2 touch) const {
    for(std::size_t k=0;k<4;++k)
        if(o.skills && iface.q(0x690+k*0x70).contains(touch))return static_cast<std::int32_t>(k);
    if(iface.q(0xbd4).contains(touch))return 4;
    if(iface.q(0xc44).contains(touch))return 5;
    return -1;
}
// HelpMenu::Show for the session's text: a topic (0..22) where the game points (19 / 20: Interface::UpdateSkills, at the
// skill slot, Interface+0x690 + 0x70 slot), or a screen's text (100..: QueueHelp, at the screen's place).
void Presenter::show_help(const SessionObjects& o,std::int32_t text) {
    const HelpPopup& h=*o.help;
    Point2 at=h.at;
    if(h.skill_slot>=0 && h.skill_slot<4)at=iface.q(0x690+static_cast<std::size_t>(h.skill_slot)*0x70).position;
    float width=h.width,height=h.height;
    if(text>=100 && text<=104)at=setup.help_place(text);   // the setup screen's Help (QueueHelp at its panels)
    if(text>=105 && text<=122){const HelpPlace p=setup.class_help_place(text);at=p.at;width=p.size;height=p.size;}   // the class screen's
    const std::string& words=text<100?texts.get("help.topic",text):texts.get("help.screen",text);
    help.show(words,at.x,at.y,width,height);
}
void Presenter::set_clock(const SessionObjects& o,const char* text) {
    iface.set_clock_state(o.settings->clock_13ec9!=0);
    iface.set_clock_string(text);
}
// Game::Process 0x174dc..0x17570: the Particles and SimpleLabel pools, between the tokens and the flares' fade.
void Presenter::process_pools() {
    particles.process(dt);
    labels.process(dt);
}
namespace {
Point2 centre(const SessionObjects& o,std::int32_t i) {return o.stroke->selection.tiles[i].geometry.center;}
Point2 resting(const SessionObjects& o,std::int32_t i) {return o.stroke->selection.tiles[i].resting_position;}
constexpr Point2 poison_position{0.853124976f,1.38437498f};   // Interface::GetPoisonPosition 0x20028
// Tile::GetEyePosition 0x3e6dc: the tile's position plus the eye's offset for its picture variant (the tables
// 0x1eadd8 / 0x1eae18, filled by a static initialiser: read from the running original).
constexpr float eyes[2][8][2]={
    {{-0.0562499985f,0.00937500037f},{-0.0562499985f,0.00625000009f},{-0.0562499985f,0.00625000009f},{-0.0562499985f,0.00937500037f},
     {-0.0562499985f,0.00937500037f},{-0.0531250015f,0.00625000009f},{-0.0531250015f,0.0125000002f},{-0.0500000007f,0.00625000009f}},
    {{0.0218749996f,0.00625000009f},{0.0218749996f,0.00937500037f},{0.0218749996f,0.00937500037f},{0.0218749996f,0.00312500005f},
     {0.0187500007f,0.00937500037f},{0.0218749996f,0.00625000009f},{0.0218749996f,0.00312500005f},{0.0218749996f,0.00625000009f}}};
Point2 eye(const SessionObjects& o,std::int32_t tile,std::int32_t which) {
    const std::int32_t v=o.generation->tiles[tile].variant;
    const Point2 c=o.stroke->selection.tiles[tile].geometry.center;
    if(which<0 || which>1 || v<0 || v>7)return c;
    return Point2{eyes[which][v][0]+c.x,eyes[which][v][1]+c.y};
}
bool tile_ok(std::int32_t i) {return i>=0 && i<36;}
}
// The effects every unit asks for by event: SimpleLabels (their position as the original call passes it), and the
// frame's pool step. Called for every event before its other presentation.
void Presenter::effect_event(const SessionObjects& o,SessionSource source,const void* p) {
    if(source==SessionSource::GameFrame && static_cast<const GameFrameEvent*>(p)->kind==GameFrameEventKind::UpdateTime) {
        finish_interface(o);   // the last frame's, when it was not drawn
        finish_game_over(o);
        finish_scores(o);
        finish_unlock(o);
        ScoresBefore& sb=scores_before;   // ScoreScreen::Show / Process: seen after the session's (finish_scores)
        sb.due=true;sb.open=o.screens->score_ef6c!=0;sb.routed=false;sb.shown=false;sb.pages=*o.scores_screen;
        return;
    }
    if(source==SessionSource::GameFrame && static_cast<const GameFrameEvent*>(p)->kind==GameFrameEventKind::Pools)process_pools();
    if(source==SessionSource::GameFrame && static_cast<const GameFrameEvent*>(p)->kind==GameFrameEventKind::InterfaceProcess) {
        if(o.screens->menus[0]) {   // Interface::Process: FoldoutMenu::Process, before the session's
            if(menu_pending)open_menu(o);
            foldout.process(o,dt);
        }
        MenusBefore& was=menus_before;   // the other menus: seen after the session's (finish_interface)
        std::copy(o.screens->menus,o.screens->menus+3,was.open);
        was.game=*o.game_menu;was.stats=*o.stats_menu;was.buttons=*o.interface_buttons;was.heartbeat=*o.heartbeat;
    }
    switch(source) {
    case SessionSource::Match: {
        const auto& e=*static_cast<const MatchEvent*>(p);
        if(e.kind==MatchEventKind::Label && tile_ok(e.tile))add_label(o,0,centre(o,e.tile),0,e.a,1.0f);
        else if(e.kind==MatchEventKind::Particles)add_particles(o,e.tile,e.a);
        else if(e.kind==MatchEventKind::Flare && tile_ok(e.tile))add_flare(o,e.a,resting(o,e.tile),e.b);
        break;
    }
    case SessionSource::Resource: {
        const auto& e=*static_cast<const ResourceEvent*>(p);
        if(e.kind==ResourceEventKind::Menu)menu_pending=true;   // the session opens it after this event
        else if(e.kind==ResourceEventKind::Target)label_target=iface.target(e.a);
        else if(e.kind==ResourceEventKind::Label)add_label(o,e.a,label_target,e.b,e.c,f32(e.d));
        break;
    }
    case SessionSource::Path: {   // Game::AttackSkull's poison label at the tile; MatchTiles' crossing labels (no tile)
        const auto& e=*static_cast<const RoundEvent*>(p);   // at its static (0.5, 0.5) (0x1e7960, set on first use)
        if(e.kind==BattleEvent::Label && tile_ok(e.tile_index))add_label(o,e.a,centre(o,e.tile_index),e.b,e.c,f32(e.d));
        else if(e.kind==BattleEvent::Label && e.tile_index<0)add_label(o,e.a,Point2{0.5f,0.5f},e.b,e.c,f32(e.d));
        else if(e.kind==BattleEvent::Particles)add_particles(o,e.tile_index,e.a);
        else if(e.kind==BattleEvent::Flare && tile_ok(e.tile_index))add_flare(o,e.a,centre(o,e.tile_index),e.b);
        break;
    }
    case SessionSource::Encounter: case SessionSource::Vampires: {
        const auto& e=*static_cast<const EncounterEvent*>(p);
        if(e.kind==EncounterEventKind::Flare && tile_ok(e.tile))add_flare(o,e.a,resting(o,e.tile),e.b);   // Game::JumpDown
        if(e.kind!=EncounterEventKind::Label)break;
        if(e.tile<0)add_label(o,e.a,poison_position,e.b,e.c,f32(e.d));
        else if(tile_ok(e.tile))add_label(o,e.a,centre(o,e.tile),e.b,e.c,f32(e.d));
        break;
    }
    case SessionSource::Turn: case SessionSource::EndGame: {
        const auto& e=*static_cast<const TurnEvent*>(p);
        if(e.kind==TurnEventKind::LabelTarget)add_label(o,e.a,iface.target(0),e.b,e.c,f32(e.d));
        else if(e.kind==TurnEventKind::LabelPoison)add_label(o,e.a,poison_position,e.b,e.c,f32(e.d));
        else if(e.kind==TurnEventKind::Label && tile_ok(e.tile))add_label(o,e.a,centre(o,e.tile),e.b,e.c,f32(e.d));
        else if(e.kind==TurnEventKind::LabelRest && tile_ok(e.tile))add_label(o,e.a,resting(o,e.tile),e.b,e.c,f32(e.d));
        else if(e.kind==TurnEventKind::Particles)add_particles(o,e.tile,e.a);
        else if(e.kind==TurnEventKind::Flare && tile_ok(e.tile))add_flare(o,e.a,centre(o,e.tile),e.b);
        else if(e.kind==TurnEventKind::FlareRest && tile_ok(e.tile))add_flare(o,e.a,resting(o,e.tile),e.b);
        else if(e.kind==TurnEventKind::FlareTarget)add_flare(o,e.a,iface.target(e.c),e.b);
        break;
    }
    case SessionSource::Release: {
        const auto& e=*static_cast<const ReleaseEvent*>(p);
        if(e.kind==ReleaseEventKind::Label)add_label(o,e.a,Point2{e.x,e.y},e.b,e.c,f32(e.d));
        else if(e.kind==ReleaseEventKind::CrossVisibility)cross_labels.count=0;
        break;
    }
    case SessionSource::Stats: {
        const auto& e=*static_cast<const StatsEvent*>(p);
        if(e.kind==StatsEventKind::Label && tile_ok(e.tile))add_label(o,e.a,centre(o,e.tile),e.b,e.c,f32(e.d));
        break;
    }
    case SessionSource::Skill: {
        const auto& e=*static_cast<const SkillEvent*>(p);
        if(e.kind==SkillEventKind::Menu)menu_pending=true;   // Game::Upgrade (skill 10): the upgrade menu
        else if(e.kind==SkillEventKind::PositionSkill && e.a>=0 && e.a<3) {   // Game::RemoveSkill: the objects move up
            std::swap(skills[e.a],skills[e.a+1]);
            skills[e.a].icon.position=InterfaceView::skill_position(e.a);
        }
        else if(e.kind==SkillEventKind::Label && tile_ok(e.b))add_label(o,e.a,resting(o,e.b),e.c,e.d,0.5f);
        else if(e.kind==SkillEventKind::Particles)add_particles(o,e.b,e.a);
        else if(e.kind==SkillEventKind::Flare && tile_ok(e.b))add_flare(o,e.a,resting(o,e.b),e.c);
        break;
    }
    case SessionSource::AttackHealth: {   // the damage at the attack label (type 2), enemy 9's at the poison one (7)
        const auto& e=*static_cast<const AttackHealthEvent*>(p);
        if(e.kind==AttackHealthEventKind::Label) {
            const SimpleLabelState& at=attack_labels[e.a==7?1:0];
            add_label(o,e.a,Point2{at.x,at.y},e.b,e.c,f32(e.d));
        }
        break;
    }
    case SessionSource::AttackAbsorb: {
        const auto& e=*static_cast<const AttackAbsorbEvent*>(p);
        if(e.kind==AttackAbsorbEventKind::Label)add_label(o,e.a,Point2{attack_labels[1].x,attack_labels[1].y},e.b,e.c,f32(e.d));
        else if(e.kind==AttackAbsorbEventKind::DamageNumber)dr_label_set_number(&attack_labels[0],e.a);
        break;
    }
    case SessionSource::AttackWeaken: {   // at Tile::GetAttackLabelPosition 0x3e2c0
        const auto& e=*static_cast<const AttackWeakenEvent*>(p);
        if(!tile_ok(e.tile))break;
        if(e.kind==AttackWeakenEventKind::Label)add_label(o,e.a,label_position(o,e.tile,tiles[e.tile].attack),e.b,e.c,f32(e.d));
        else if(e.kind==AttackWeakenEventKind::Particles)add_particles(o,e.tile,e.a);
        break;
    }
    case SessionSource::AttackAll: {   // ProcessAttack's damage to all at the tile, DoCounterattack's at its resting place
        const auto& e=*static_cast<const AttackAllEvent*>(p);
        if(e.kind==AttackAllEventKind::Label && tile_ok(e.tile))
            add_label(o,e.a,e.a==2?resting(o,e.tile):centre(o,e.tile),e.b,e.c,f32(e.d));
        break;
    }
    case SessionSource::AttackAnim: {
        const auto& e=*static_cast<const AttackAnimEvent*>(p);
        if(e.kind==AttackAnimEventKind::LabelPosition && (e.a==0 || e.a==1)) {
            dr_label_set_position(&attack_labels[e.a],Point2{f32(e.b),f32(e.c)});
        }
        else if(e.kind==AttackAnimEventKind::LabelNumber && (e.a==0 || e.a==1))dr_label_set_number(&attack_labels[e.a],e.b);
        else if(e.kind==AttackAnimEventKind::LabelAlpha && (e.a==0 || e.a==1))
            dr_label_set_alpha(&attack_labels[e.a],static_cast<std::uint8_t>(e.b));
        else if(e.kind==AttackAnimEventKind::SetAlpha && (e.a==1 || e.a==2))attack_bar[e.a-1].set_alpha(static_cast<std::uint8_t>(e.b));
        else if(e.kind==AttackAnimEventKind::FlareAlpha && e.a>=0 && static_cast<std::size_t>(e.a)<flares.size())
            flares[static_cast<std::size_t>(e.a)].set_alpha(static_cast<std::uint8_t>(e.b));
        else if(e.kind==AttackAnimEventKind::FlareScale && e.a>=0 && static_cast<std::size_t>(e.a)<flares.size())
            flares[static_cast<std::size_t>(e.a)].scale=Point2{f32(e.b),f32(e.b)};
        else if(e.kind==AttackAnimEventKind::AddLabel)add_label(o,e.a,Point2{attack_labels[0].x,attack_labels[0].y},e.b,e.c,0.5f);
        break;
    }
    case SessionSource::Selection: {
        const auto& e=*static_cast<const SessionSmallEvent*>(p);
        if(static_cast<SelectionEvent>(e.kind)==SelectionEvent::CrossVisibility)cross_labels.count=0;
        break;
    }
    case SessionSource::AttackFade: {   // the phase-7 fade: a=quad (0 the overlay, the session's alpha; 1, 2 the bars)
        const auto& e=*static_cast<const AttackFadeEvent*>(p);
        if(e.kind==AttackFadeEventKind::SetAlpha && (e.a==1 || e.a==2))attack_bar[e.a-1].set_alpha(static_cast<std::uint8_t>(e.b));
        break;
    }
    case SessionSource::BoardEffect: {
        const auto& e=*static_cast<const BoardEffectEvent*>(p);
        if(e.kind==BoardEffectEventKind::ShatterInitialise) {   // Game::InialiseShieldShatter 0x9810
            shield_chunk[0].position=Point2{0.485937506f,1.29375005f};shield_chunk[0].set_alpha(255);shield_chunk[0].rotation=0.0f;
            shield_chunk[1].position=Point2{0.5078125f,1.29375005f};shield_chunk[1].set_alpha(255);shield_chunk[1].rotation=0.0f;
        } else if(e.kind==BoardEffectEventKind::ShieldChunk && (e.a==0 || e.a==1)) {   // Game::ProcessShieldChunk 0x96a8
            Quad& q=shield_chunk[e.a];
            const float direction=e.a==0?-1.0f:1.0f;
            const Point2 target=e.a==0?Point2{0.485937506f,1.29375005f}:Point2{0.5078125f,1.29375005f};
            const float t=o.shatter->progress;
            const float d=0.300000012f-t;
            q.position.y=(0.0399999991f-d*d)*-0.200000003f+target.y;
            q.position.x=t*0.0799999982f*direction+target.x;
            q.rotation=direction*t*90.0f;
            const float a=(1.0f-static_cast<float>(std::pow(static_cast<double>(t),3.0)))*255.0f;
            q.set_alpha(static_cast<std::uint8_t>(a<=0.0f?0u:static_cast<std::uint32_t>(a)));
        }
        break;
    }
    case SessionSource::Save: {   // Skill::Deserialise: the equipped skill's icon, name and level, then its place
        const auto& e=*static_cast<const SessionSmallEvent*>(p);
        const auto kind=static_cast<SaveEventKind>(e.kind);
        if(kind==SaveEventKind::SkillIcon && e.a>=0 && e.a<4)
            skills[e.a].skill(texts,o.skills->id[e.a],o.skills->level[e.a],o.resources->skill_max[e.a],nullptr);
        else if(kind==SaveEventKind::PositionSkill && e.a>=0 && e.a<4)skills[e.a].icon.position=InterfaceView::skill_position(e.a);
        break;
    }
    case SessionSource::Cross: {
        const auto& e=*static_cast<const CrossEvent*>(p);
        if(e.kind==CrossEventKind::Label)add_cross_label(o,e.a,e.b,e.c);
        break;
    }
    case SessionSource::Menu: {
        const auto& e=*static_cast<const MenuEvent*>(p);
        if(e.kind==MenuEventKind::PositionSkill && e.a>=0 && e.a<4) {   // Game::SetSkill exchanged an option in
            if(!foldout.exchanges.empty()) {
                std::swap(skills[e.a],foldout.option(foldout.exchanges.front()));
                foldout.exchanges.erase(foldout.exchanges.begin());
            }
            skills[e.a].icon.position=InterfaceView::skill_position(e.a);
        } else if(e.kind==MenuEventKind::Highlight)foldout.highlight(texts,o,equipped,e.a,e.b,e.c!=0);
        else if(e.kind==MenuEventKind::Confirm)foldout.confirm(e.a!=0);
        break;
    }
    case SessionSource::Frame: {
        const auto& e=*static_cast<const FrameEvent*>(p);
        if(e.kind==FrameEventKind::FlareAlpha) {   // the flares' fade: alpha and size (quad +0x64 / +0x68)
            if(e.a>=0 && static_cast<std::size_t>(e.a)<flares.size()) {
                Quad& q=flares[static_cast<std::size_t>(e.a)];q.set_alpha(static_cast<std::uint8_t>(e.b));q.scale=Point2{f32(e.c),f32(e.c)};
            }
        } else current_label(o,e);
        break;
    }
    case SessionSource::AttackFlare: {   // InitialiseFlares: a flare at each eye of an attacking enemy
        const auto& e=*static_cast<const AttackFlareEvent*>(p);
        if(e.kind==AttackFlareEventKind::Flare && tile_ok(e.tile))add_flare(o,e.b,eye(o,e.tile,e.a),e.c);
        break;
    }
    default: break;
    }
}
void Presenter::event(const SessionObjects& o,SessionSource source,const void* p) {
    effect_event(o,source,p);
    switch(source) {
    case SessionSource::NewGame: {
        const auto& e=*static_cast<const NewGameEvent*>(p);
        switch(e.kind) {
        case NewGameEventKind::SetSize: tiles[e.tile].quad.set_size(Point2{f32(e.a),f32(e.b)});break;
        case NewGameEventKind::Labels: initialise_labels(e.tile);break;
        case NewGameEventKind::SkullValue: iface.update_skull_value(o);break;
        case NewGameEventKind::HealthBar: iface.update_health_bar(o,0x70,e.a);break;
        case NewGameEventKind::XPBar: iface.update_xp_bar(0xe0,e.a);break;
        case NewGameEventKind::UPBar: iface.update_up_bar(o,0x150,e.a);break;
        case NewGameEventKind::GoldBar: iface.update_gold_bar(0x1c0,e.a);break;
        case NewGameEventKind::InterfaceReset: iface.reset();tooltip.hide_instantly();game_start(&o);break;
        default: break;
        }
        break;
    }
    case SessionSource::Resource: {
        const auto& e=*static_cast<const ResourceEvent*>(p);
        switch(e.kind) {
        case ResourceEventKind::HealthBar: iface.update_health_bar(o,0x70,e.a);break;
        case ResourceEventKind::XPBar: iface.update_xp_bar(0xe0,e.a);break;
        case ResourceEventKind::UPBar: iface.update_up_bar(o,0x150,e.a);break;
        case ResourceEventKind::GoldBar: iface.update_gold_bar(0x1c0,e.a);break;
        case ResourceEventKind::Shield: iface.update_shield_value(o);break;
        case ResourceEventKind::Poison: iface.set_poison(e.a);break;
        case ResourceEventKind::Skills: iface.update_skills(o);break;
        case ResourceEventKind::Shadow:   // a: the reward (0 health, 1 XP, 2 gold, 3 shield)
            if(e.a==0)iface.set_health_shadow(o,e.b);else if(e.a==1)iface.set_xp_shadow(o,e.b);
            else if(e.a==2)iface.set_gold_shadow(o,e.b);else if(e.a==3)iface.set_up_shadow(o,e.b);
            break;
        default: break;
        }
        break;
    }
    case SessionSource::Stats: {
        const auto& e=*static_cast<const StatsEvent*>(p);
        switch(e.kind) {
        case StatsEventKind::HealthBar: iface.update_health_bar(o,0x70,e.a);break;
        case StatsEventKind::SwordValue: iface.update_sword_value(o);break;
        case StatsEventKind::SkullValue: iface.update_skull_value(o);break;
        case StatsEventKind::ShieldValue: iface.update_shield_value(o);break;
        case StatsEventKind::UpdateSkills: iface.update_skills(o);break;
        default: break;
        }
        break;
    }
    case SessionSource::Menu: {
        const auto& e=*static_cast<const MenuEvent*>(p);
        if(e.kind==MenuEventKind::HealthBar)iface.update_health_bar(o,0x70,e.a);
        else if(e.kind==MenuEventKind::SkullValue)iface.update_skull_value(o);
        else if(e.kind==MenuEventKind::UpdateSkills)iface.update_skills(o);
        else if(e.kind==MenuEventKind::TooltipHide)tooltip.hide();
        else if(e.kind==MenuEventKind::ScrollTooltip && o.menu->scroll_slot>=0 && o.menu->scroll_slot<4) {
            // FoldoutMenu::ProcessInput: by the scroll's option (its corner + (54, 26) points), the menu's place added
            const float x=18.0f+54.0f;const float y=static_cast<float>(33+57*o.menu->scroll_slot)+26.0f;
            const Point2 off{x/320.0f,y/320.0f};const Point2 m=foldout.at();
            tooltip.show_scroll(texts,e.a,Point2{m.x+off.x,m.y+off.y});
        }
        break;
    }
    case SessionSource::AttackHealth: {
        const auto& e=*static_cast<const AttackHealthEvent*>(p);
        if(e.kind==AttackHealthEventKind::HealthBar)iface.update_health_bar(o,0x70,e.a);
        break;
    }
    case SessionSource::AttackShield: {
        const auto& e=*static_cast<const AttackShieldEvent*>(p);
        if(e.kind==AttackShieldEventKind::ShieldValue)iface.update_shield_value(o);
        break;
    }
    case SessionSource::AttackFlare: {
        const auto& e=*static_cast<const AttackFlareEvent*>(p);
        if(e.kind==AttackFlareEventKind::Shadow) {   // a: 0 health, 1 XP, 2 UP, 3 gold
            if(e.a==0)iface.set_health_shadow(o,e.b);else if(e.a==1)iface.set_xp_shadow(o,e.b);
            else if(e.a==2)iface.set_up_shadow(o,e.b);else if(e.a==3)iface.set_gold_shadow(o,e.b);
        }
        break;
    }
    case SessionSource::Interface: {   // Game::SetClockState -> Interface::SetClockState (the game menu's clock switch)
        const auto& e=*static_cast<const SessionSmallEvent*>(p);
        if(e.kind==static_cast<std::int32_t>(InterfaceEventKind::Setting) && e.index==12)iface.set_clock_state(e.a!=0);
        else if(e.kind==static_cast<std::int32_t>(InterfaceEventKind::Help))show_help(o,e.index);
        else if(e.kind==static_cast<std::int32_t>(InterfaceEventKind::Setting) && e.index==10)main_menu.set_sound_state(e.a!=0);
        else if(e.kind==static_cast<std::int32_t>(InterfaceEventKind::MainMenu))main_menu.fade_in();   // MainMenu::FadeIn
        else if(e.kind==static_cast<std::int32_t>(InterfaceEventKind::MainMenuShow))main_menu.show(o);   // MainMenu::Show
        else if(e.kind==static_cast<std::int32_t>(InterfaceEventKind::MoreGames))main_menu.stop_cycling();   // ShowMoreGames
        else if(e.kind==static_cast<std::int32_t>(InterfaceEventKind::Dashboard))settings.open(texts,language_index);   // (T050-D)
        else if(e.kind==static_cast<std::int32_t>(InterfaceEventKind::MainMenuButton))main_menu.button_acted(o,e.index,dt);
        else if(e.kind==static_cast<std::int32_t>(InterfaceEventKind::GameOverLine)) {   // shown by finish_game_over
            game_over_before.ended_line=e.index;game_over_before.ended_value=e.a;
        }
        else if(e.kind==static_cast<std::int32_t>(InterfaceEventKind::ScorePageTurn))scores.turn_page(o,e.a);   // SetScorePage
        break;
    }
    case SessionSource::GameFrame: {
        const auto& e=*static_cast<const GameFrameEvent*>(p);
        // Interface::Process 0x20c64 runs its menus and input first (the session does that after this event), then
        // the heartbeat and the skill highlights: those run when the frame is drawn.
        if(e.kind==GameFrameEventKind::InterfaceProcess){interface_due=true;interface_dt=dt;}
        // Game::Process with the help bubble open runs HelpMenu::Process only (the session's step follows this event)
        else if(e.kind==GameFrameEventKind::Screen && e.a==static_cast<std::int32_t>(FrameRoute::Help))
            help.fade(o.help->timer,o.help->closing!=0,dt);
        else if(e.kind==GameFrameEventKind::Screen && e.a==static_cast<std::int32_t>(FrameRoute::MainMenu))
            main_menu.process(o,dt);   // MainMenu::Process's picture, before the session's step
        else if(e.kind==GameFrameEventKind::Screen && e.a==static_cast<std::int32_t>(FrameRoute::Name) && setup.open()) {
            setup.process(o,dt);       // NameScreen::Process (the session runs the screen's rules by call)
            for(const std::int32_t s:setup.sounds)queue_sound(s);
            setup.sounds.clear();
        }
        else if(e.kind==GameFrameEventKind::Screen && e.a==static_cast<std::int32_t>(FrameRoute::Intro)) {
            intro_ended=intro.process(o,dt) || intro_ended;   // IntroScreen::Process (the session has no step)
            for(const std::int32_t s:intro.sounds)queue_sound(s);
            intro.sounds.clear();
        }
        else if(e.kind==GameFrameEventKind::Screen && e.a==static_cast<std::int32_t>(FrameRoute::Score))scores_before.routed=true;
        else if(e.kind==GameFrameEventKind::Screen && e.a==static_cast<std::int32_t>(FrameRoute::Unlock))unlock_due=true;
        else if(e.kind==GameFrameEventKind::ScoreShow)scores_before.shown=true;   // Show(..., true) from the game-over screen
        else if(e.kind==GameFrameEventKind::Screen && e.a==static_cast<std::int32_t>(FrameRoute::GameOver)) {
            GameOverBefore& b=game_over_before;   // GameOverScreen::Process: seen after the session's (finish_game_over)
            b.due=true;b.tally=*o.game_over;b.state=o.screens->game_over_state_cc1c;b.phase=o.touch->phase;b.ended_line=-1;
        }
        break;
    }
    case SessionSource::Generation: {
        const auto& e=*static_cast<const GenerationEvent*>(p);
        if(e.tile<0 || e.tile>35)break;
        switch(e.kind) {
        case GenerationEventKind::UV: tiles[e.tile].quad.set_uv(f32(e.a),f32(e.b),f32(e.c),f32(e.d));break;
        case GenerationEventKind::Colour: tiles[e.tile].quad.set_colour(colour_of(e.a));break;
        case GenerationEventKind::Text: update_text(o,e.tile,e.a!=0,e.b!=0,e.c!=0);break;
        case GenerationEventKind::Countdown: update_countdown(o,e.tile);break;
        case GenerationEventKind::EnemyUV: update_enemy_uv(o,e.tile);break;
        default: break;
        }
        break;
    }
    case SessionSource::Selection: {
        const auto& e=*static_cast<const SessionSmallEvent*>(p);
        switch(static_cast<SelectionEvent>(e.kind)) {
        case SelectionEvent::SetSize: tiles[e.index].quad.set_size(Point2{f32(e.a),f32(e.b)});break;
        case SelectionEvent::HealthShadow: iface.set_health_shadow(o,e.a);break;   // the amount is a (index -1)
        case SelectionEvent::XPShadow: iface.set_xp_shadow(o,e.a);break;
        case SelectionEvent::UPShadow: iface.set_up_shadow(o,e.a);break;
        case SelectionEvent::GoldShadow: iface.set_gold_shadow(o,e.a);break;
        case SelectionEvent::Undim: undim(o,e.index);break;
        case SelectionEvent::Arrow: arrow.update(o.stroke->selection);break;   // Arrow::Update over the path
        case SelectionEvent::HideTooltip: tooltip.hide();break;
        case SelectionEvent::EnemyTooltip:   // Game::ProcessInput: a stroke begun on an enemy, at the tile
            if(tile_ok(e.index)) {
                const std::int32_t race=o.classes[o.scroll->current].race;
                tooltip.show_enemy(texts,e.a,dr_mortal_enemy(race),race,centre(o,e.index));
            }
            break;
        case SelectionEvent::UpdateDimming: {   // Game::UpdateDimming 0x9c78 on the path as it is now
            std::uint8_t dimmed[36];dr_update_dimming(&o.stroke->selection,dimmed);
            for(int i=0;i<36;++i){if(dimmed[i])dim(o,i);else undim(o,i);}
            break;
        }
        default: break;
        }
        break;
    }
    case SessionSource::Refill: {
        const auto& e=*static_cast<const SessionSmallEvent*>(p);
        if(static_cast<RefillEventKind>(e.kind)==RefillEventKind::Swap)std::swap(tiles[e.index],tiles[e.a]);
        break;
    }
    case SessionSource::BoardEffect: {
        const auto& e=*static_cast<const BoardEffectEvent*>(p);
        if(e.tile<0 || e.tile>35)break;
        if(e.kind==BoardEffectEventKind::Spin) {
            Quad& g=tiles[e.tile].glow;const float turn=f32(e.a)*tiles[e.tile].glow_speed;g.rotation=g.rotation+turn;
        } else if(e.kind==BoardEffectEventKind::Colour) {
            for(auto& v:tiles[e.tile].quad.v){v.colour[0]=static_cast<std::uint8_t>(e.a);v.colour[1]=static_cast<std::uint8_t>(e.b);v.colour[2]=static_cast<std::uint8_t>(e.c);}
        } else if(e.kind==BoardEffectEventKind::Text)update_text(o,e.tile,e.a!=0,e.b!=0,e.c!=0);
        break;
    }
    case SessionSource::GameOver: {   // GameOverScreen::Initialise(win), as the session opens the screen
        const auto& e=*static_cast<const TurnEvent*>(p);
        if(static_cast<std::int32_t>(e.kind)==static_cast<std::int32_t>(EndGameEventKind::GameOverScreen)) {
            game_over.initialise(texts,o,e.a!=0);
            queue_sound(e.a!=0?12:33);   // (Initialise's last call)
        }
        break;
    }
    case SessionSource::Turn: {
        const auto& e=*static_cast<const TurnEvent*>(p);
        if(e.kind==TurnEventKind::HealthBar)iface.update_health_bar(o,0x70,e.a);
        else if(e.kind==TurnEventKind::ArrowColour)arrow.set_colour(static_cast<std::uint32_t>(e.a),static_cast<std::uint32_t>(e.b),static_cast<std::uint32_t>(e.c));
        else if(e.kind==TurnEventKind::UpdateSkills)iface.update_skills(o);
        else if(e.kind==TurnEventKind::GoldBar)iface.update_gold_bar(0x1c0,e.a);
        if(e.tile<0 || e.tile>35)break;
        if(e.kind==TurnEventKind::Text)update_text(o,e.tile,e.a!=0,e.b!=0,e.c!=0);
        else if(e.kind==TurnEventKind::Freeze)freeze(e.tile,e.a!=0);
        else if(e.kind==TurnEventKind::FlameOverlay)flame(e.tile,true);   // (a burning elite's flames, and a loaded game's)
        break;
    }
    case SessionSource::Encounter: {
        const auto& e=*static_cast<const EncounterEvent*>(p);
        if(e.kind==EncounterEventKind::Text && e.tile>=0 && e.tile<36)update_text(o,e.tile,e.a!=0,e.b!=0,e.c!=0);
        break;
    }
    case SessionSource::AttackWeaken: {
        const auto& e=*static_cast<const AttackWeakenEvent*>(p);
        if(e.kind==AttackWeakenEventKind::Text && e.tile>=0 && e.tile<36)update_text(o,e.tile,e.a!=0,e.b!=0,e.c!=0);
        break;
    }
    case SessionSource::Release: {
        const auto& e=*static_cast<const ReleaseEvent*>(p);
        if(e.kind==ReleaseEventKind::Text && e.tile>=0 && e.tile<36)update_text(o,e.tile,e.a!=0,e.b!=0,e.c!=0);
        else if(e.kind==ReleaseEventKind::UnlockMenu)unlock.show(texts,e.a,e.b);   // UnlockMenu::Show(ClassType, level)
        break;
    }
    case SessionSource::Path: {
        const auto& e=*static_cast<const RoundEvent*>(p);
        if(e.tile_index<0 || e.tile_index>35)break;
        if(e.kind==BattleEvent::UpdateText)update_text(o,e.tile_index,e.a!=0,e.b!=0,e.c!=0);
        else if(e.kind==BattleEvent::UpdateEnemyUV)update_enemy_uv(o,e.tile_index);
        else if(e.kind==BattleEvent::Freeze)freeze(e.tile_index,true);
        break;
    }
    case SessionSource::Skill: {
        const auto& e=*static_cast<const SkillEvent*>(p);
        if(e.kind==SkillEventKind::UpdateSkills){iface.update_skills(o);break;}
        if(e.kind==SkillEventKind::Tooltip && e.d>=0 && e.d<4) {   // Interface::ProcessInput: by the pressed button
            // (the buttons' centres, a table 0x1eac44 a static initialiser fills: read from the running original)
            constexpr float centres[4]={0.1015625f,0.285937488f,0.470312506f,0.654687524f};
            const Point2 at{centres[e.d]+-0.0828125030f,0.228125006f};
            tooltip.show_skill(texts,e.a,e.b,e.c,at);break;
        }
        if(e.kind==SkillEventKind::ButtonColour && e.a>=0 && e.a<4) {   // the pressed button's fill (Interface+0x850)
            iface.q(0x850+static_cast<std::size_t>(e.a)*0x70).set_colour(colour_of(e.b));break;
        }
        if(e.kind==SkillEventKind::TooltipHide){tooltip.hide();break;}
        if(e.kind==SkillEventKind::ArrowColour){arrow.set_colour(static_cast<std::uint32_t>(e.a),static_cast<std::uint32_t>(e.b),static_cast<std::uint32_t>(e.c));break;}
        if(e.b<0 || e.b>35)break;
        if(e.kind==SkillEventKind::Text)update_text(o,e.b,e.a!=0,e.c!=0,e.d!=0);
        else if(e.kind==SkillEventKind::Freeze)freeze(e.b,true);
        else if(e.kind==SkillEventKind::FlameVisibility)flame(e.b,true);
        else if(e.kind==SkillEventKind::EnemyUV)update_enemy_uv(o,e.b);
        break;
    }
    case SessionSource::Token: {   // Game::AddToken: a new slot is a new Token (Token::Token(Interface*): a Quad)
        const auto& e=*static_cast<const TokenEvent*>(p);
        if(e.kind==TokenEventKind::Allocate)tokens.emplace_back();
        else if(e.kind==TokenEventKind::Initialise && e.index>=0) {
            token_slot=e.index;
            if(tokens.size()<=static_cast<std::size_t>(e.index))tokens.resize(static_cast<std::size_t>(e.index)+1);
        }
        break;
    }
    case SessionSource::Motion: token_picture(o,*static_cast<const SessionSmallEvent*>(p));break;
    case SessionSource::Save: {   // Game::DeserialiseState's interface updates (a: the value)
        const auto& e=*static_cast<const SessionSmallEvent*>(p);
        switch(static_cast<SaveEventKind>(e.kind)) {
        case SaveEventKind::Freeze: if(e.a>=0 && e.a<36)freeze(e.a,true);break;
        case SaveEventKind::Skull: iface.update_skull_value(o);break;
        case SaveEventKind::HealthCeiling: case SaveEventKind::Health: iface.update_health_bar(o,0x70,o.resources->ui_health);break;
        case SaveEventKind::ArmourMax: case SaveEventKind::Armour: iface.update_shield_value(o);break;
        case SaveEventKind::XP: iface.update_xp_bar(0xe0,e.a);break;
        case SaveEventKind::UP: iface.update_up_bar(o,0x150,e.a);break;
        case SaveEventKind::Gold: iface.update_gold_bar(0x1c0,e.a);break;
        case SaveEventKind::Poison: iface.set_poison(e.a);break;
        case SaveEventKind::UpdateSkills: iface.update_skills(o);break;
        default: break;
        }
        break;
    }
    default: break;
    }
}
// Tile::Render 0x3dc98: a skull moves by its label offset; the mortal glow first; the tile's quad at its centre.
void Presenter::render_tile(const SessionObjects& o,int i) {
    TileView& t=tiles[i];const SelectionTile& s=o.stroke->selection.tiles[i];const GeneratedTile& g=o.generation->tiles[i];
    t.quad.position=s.geometry.center;
    if(s.rule.type!=1){t.quad.render(gl);return;}
    gl.push();
    if(!(s.rule.enemy_type==32 && s.rule.enemy_state))gl.translate(g.label_offset,0.0f);
    if(g.flag_224){t.glow.position=t.quad.position;t.glow.render(gl);}
    t.quad.render(gl);
    gl.pop();
}
// Tile::RenderText 0x3f5dc: a skull's three numbers at its centre, and its countdown when the enemy has one.
void Presenter::render_text(const SessionObjects& o,int i) {
    TileView& t=tiles[i];const SelectionTile& s=o.stroke->selection.tiles[i];
    if(s.rule.type!=1 || (s.rule.enemy_type==32 && s.rule.enemy_state) || !t.labels)return;
    gl.push();gl.translate(s.geometry.center.x,s.geometry.center.y);
    t.attack.render(gl);t.defence.render(gl);t.health.render(gl);
    if(s.rule.enemy_type!=32 && s.rule.enemy_state>0)t.countdown.render(gl);
    gl.pop();
}
// Tile::RenderOverlay 0x3e650 / RenderCross 0x3e720 at the tile's centre.
void Presenter::render_overlays(const SessionObjects& o,int i) {
    TileView& t=tiles[i];const SelectionTile& s=o.stroke->selection.tiles[i];
    if(o.path->combat[i].overlay){t.overlay.position=s.geometry.center;t.overlay.render(gl);}
    if(s.cross_visibility){t.cross.position=s.geometry.center;t.cross.render(gl);}
}
// Game::Render 0xd1cc, the game screen (so far: the board; the rest of the frame is the next step).
// MainMenu::Render (MainMenu::Show: the session's MainMenuShow event).
void Presenter::render_main_menu(const SessionObjects& o) {
    main_menu.set_sound_state(o.settings->sound_13ec6!=0);
    gl.set_tag(MainMenuTag);main_menu.render(gl,o);gl.set_tag(GameTag);
}
// Game::Render 0xd1cc: the high-score screen alone (over the main menu while it fades), or the setup screen over the main
// menu (the story over both), or the game with everything over it.
void Presenter::render(const SessionObjects& o) {
    finish_frame(o);
    gl.clear();gl.load_identity();
    const FrameScreens& screens=*o.screens;
    if(screens.score_ef6c) {   // 0xd1f0: the main menu under the fade, the high scores, the game-over screen over them
        if(o.scores_screen->timer>0.0f)render_main_menu(o);
        gl.set_tag(ScoreTag);scores.render(gl,o);gl.set_tag(GameTag);
        setup_was_open=false;
        if(o.end->game_over_screen){gl.set_tag(GameOverTag);game_over.render(gl,o);gl.set_tag(GameTag);}   // 0xd6c6
        return;
    }
    if(screens.name_12c09) {   // 0xd228 (Game+0xc3f1, the story closing, hides the main menu and the setup screen)
        if(!setup_was_open)setup.show(texts,o);   // NameScreen::Show, as the session opened it
        if(!intro.closing()) {
            render_main_menu(o);
            gl.set_tag(NameTag);setup.render(gl,o);gl.set_tag(GameTag);
        }
        if(screens.intro_c3f0){gl.set_tag(IntroTag);intro.render(gl);gl.set_tag(GameTag);}
        setup_was_open=true;
        if(screens.unlock_165a0){gl.set_tag(UnlockTag);unlock.render(gl);gl.set_tag(GameTag);}   // 0xd27e
        if(screens.help_102a4){gl.set_tag(HelpTag);help.render(gl);gl.set_tag(GameTag);}
        return;
    }
    gl.bind_texture(Tiles);
    for(int i=0;i<36;++i)render_tile(o,i);
    gl.bind_texture(FontTexture);
    for(int i=0;i<36;++i)render_text(o,i);
    gl.bind_texture(Tiles);
    for(int i=0;i<36;++i)render_overlays(o,i);
    if(static_cast<std::uint32_t>(o.damage->phase-1)<=6u) {   // Game::Render 0xd378: phases 1..7
        gl.bind_texture(NoTexture);
        if(o.settings->dimming_13eca){overlay.set_alpha(*o.overlay_alpha);overlay.render(gl);}
    }
    gl.bind_texture(Tiles);
    iface.render(gl,o,skills);
    if(o.animation->flare_count>0) {
        gl.bind_texture(Tiles);
        for(std::int32_t i=0;i<o.animation->flare_count && static_cast<std::size_t>(i)<flares.size();++i)flares[static_cast<std::size_t>(i)].render(gl);
    }
    if(static_cast<std::uint32_t>(o.damage->phase-3)<=4u) {   // Game::Render 0xd3f0: phases 3..7
        gl.bind_texture(Tiles);
        attack_bar[0].render(gl);attack_bar[1].render(gl);
        if(o.damage->phase<=6 && !o.animation->counterattack) {
            // their scale (SimpleLabel+0x33c: Game+0xbd38 / 0x15520) is the session's (damage_label_alpha /
            // poison_label_alpha: the labels shrink to the bar)
            attack_labels[0].scale=o.animation->damage_label_alpha;attack_labels[1].scale=o.animation->poison_label_alpha;
            render_label(gl,attack_labels[0]);
            if(o.damage->enemy9_damage>0)render_label(gl,attack_labels[1]);
        }
    }
    if(o.stroke->selection.path_length>1){gl.bind_texture(Tiles);arrow.render(gl);}
    // The pending tokens that still fly, each a Quad::Render at the session's position and scale.
    const std::uint32_t pending=dr_token_queue_counters(o.tokens)->pending;
    if(pending>0) {
        gl.load_identity();gl.bind_texture(Tiles);
        for(std::uint32_t i=0;i<pending;++i) {
            if(i>=o.motion_count || i>=tokens.size() || !o.motions[i].active)continue;
            Quad& q=tokens[i];q.position=o.motions[i].position;q.scale=o.motions[i].scale;q.render(gl);
        }
    }
    if(particles.count>0) {
        gl.load_identity();gl.bind_texture(Tiles);
        for(std::int32_t i=0;i<particles.count;++i) {
            const Particles& q=particles.particles[static_cast<std::size_t>(i)];
            if(q.active)q.render(gl);
        }
    }
    const auto label_pass=[&](const LabelPool& pool,bool active_only) {
        if(pool.count<=0)return;
        gl.load_identity();gl.bind_texture(Tiles);
        for(std::int32_t i=0;i<pool.count;++i) {
            const SimpleLabelState& l=pool.labels[static_cast<std::size_t>(i)];
            if(!active_only || l.active)render_label(gl,l);
        }
    };
    label_pass(cross_labels,false);
    label_pass(labels,true);
    if(o.shatter->active) {   // Game::Render 0xd56c
        gl.load_identity();gl.bind_texture(Tiles);
        shield_chunk[0].render(gl);shield_chunk[1].render(gl);
    }
    const auto single=[&](const SimpleLabelState& l) {gl.load_identity();gl.bind_texture(Tiles);render_label(gl,l);};
    const SelectionState& sel=o.stroke->selection;
    if(sel.current_damage>0 || current.active)single(current);
    if(sel.current_leech>0)single(o.damage_labels[0]);
    if(sel.current_flame_damage>0)single(o.damage_labels[1]);
    if(sel.current_spike_damage>0)single(o.damage_labels[2]);
    if(screens.menus[0] || screens.menus[1] || screens.menus[2]) {   // Interface::RenderMenu 0x1eba8
        gl.load_identity();gl.bind_texture(Tiles);
        if(screens.menus[0]) {
            if(menu_pending)open_menu(o);
            foldout.render(gl,o,equipped);
        } else if(screens.menus[1])game_menu.render(gl,*o.settings);
        else stats_menu.render(gl,equipped);
    }
    if(tooltip.visible())tooltip.render(gl);   // Interface::RenderTooltip 0x1eb90
    // 0xd65e: the main menu over the game while it or the story is open, the setup screen under the story (both hidden
    // while the story closes, Game+0xc3f1), then the story.
    const bool menu_shown=screens.main_menu_c400 || screens.intro_c3f0;
    if(menu_shown) {
        if(!intro.closing()) {
            render_main_menu(o);
            if(screens.intro_c3f0){gl.set_tag(NameTag);setup.render(gl,o);gl.set_tag(GameTag);}
        }
        if(screens.intro_c3f0){gl.set_tag(IntroTag);intro.render(gl);gl.set_tag(GameTag);}
    }
    setup_was_open=false;
    if(screens.unlock_165a0){gl.set_tag(UnlockTag);unlock.render(gl);gl.set_tag(GameTag);}   // Game::Render 0xd6b6
    if(screens.help_102a4){gl.set_tag(HelpTag);help.render(gl);gl.set_tag(GameTag);}   // Game::Render 0xd6ba
    if(o.end->game_over_screen){gl.set_tag(GameOverTag);game_over.render(gl,o);gl.set_tag(GameTag);}
    if(settings.is_open() && screens.main_menu_c400)settings.render(gl);   // (T050-D, over the main menu)
}
}
