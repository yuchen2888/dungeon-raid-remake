#include "recovered_turn.hpp"
#include <cstring>
#include <cstdlib>
using namespace dungeonraid;
namespace {
void emit(const TurnHooks* h,TurnEventKind kind,int tile,int a=0,int b=0,int c=0,int d=0) {
    if(h && h->event) { const TurnEvent e{kind,tile,a,b,c,d};h->event(h->context,&e); }
}
}
extern "C" void dr_mimic_defence(PathState* p,std::uint32_t tile,const TurnHooks* h) {
    p->combat[tile].defence=p->match->preview->armour_current;
    emit(h,TurnEventKind::Text,tile,0,1,0);
    emit(h,TurnEventKind::Label,tile,20,0,28,0x3f800000);
    emit(h,TurnEventKind::Sound,-1,23);
}
extern "C" void dr_resurrect(MatchState* m,std::uint32_t tile,const TurnHooks* h) {
    emit(h,TurnEventKind::Sound,-1,22);
    emit(h,TurnEventKind::Sound,-1,14);
    emit(h,TurnEventKind::Flare,tile,1,static_cast<std::int32_t>(0xff00ffffu));   // RGBA 255,255,0,255
    emit(h,TurnEventKind::Label,tile,38,0,46,0x3f800000);
    m->shake_scale_bd94=0x3f800000;m->shake_progress_bd90=0;
}
extern "C" void dr_process_cripples(PathState* p,const TurnHooks* h) {
    const auto& board=p->match->stroke->selection;
    if(board.character.race!=7)return;
    for(int y=0;y<6;++y)for(int x=0;x<6;++x) {
        const int i=y*6+x;const auto& rule=board.tiles[i].rule;
        if(rule.type!=1 || rule.enemy_type!=0 || rule.matched)continue;
        if(p->combat[i].health>=p->combat[i].defence)continue;
        h->match_tile(h->context,i,5);
        emit(h,TurnEventKind::Label,i,36,0,44,0x3f800000);
        emit(h,TurnEventKind::Achievement,-1,53,0x40000000);
    }
}
namespace {
struct FreezeBridge {
    const TurnHooks* h;std::int32_t tile;
    static std::int32_t random(void*,std::int32_t,std::int32_t,std::int32_t) {return 0;}   // never used by SetFreezeVisibility
    static void forward(void* context,BattleEvent kind,std::int32_t a,std::int32_t,std::int32_t,std::int32_t) {
        auto* b=static_cast<FreezeBridge*>(context);
        if(kind==BattleEvent::Freeze)emit(b->h,TurnEventKind::Freeze,b->tile,a);
    }
};
// Original Tile::SetFreezeVisibility through the recovered dr_set_freeze on a BattleTile view.
void set_freeze(PathState* p,int i,bool visible,const TurnHooks* h) {
    auto& t=p->match->stroke->selection.tiles[i];auto& c=p->combat[i];
    BattleTile view{};view.frozen=t.rule.flag_255;view.freeze_overlay_visible=c.overlay;view.flag_256=t.flaming;
    FreezeBridge bridge{h,i};const BattleHooks hooks{&bridge,FreezeBridge::random,FreezeBridge::forward};
    dr_set_freeze(&view,visible,&hooks);
    t.rule.flag_255=view.frozen;c.overlay=view.freeze_overlay_visible;t.flaming=view.flag_256;
}
}
extern "C" void dr_set_flame_visibility(PathState* p,std::uint32_t tile,bool on,std::int32_t damage,bool self_flame,const TurnHooks* h) {
    auto& t=p->match->stroke->selection.tiles[tile];auto& c=p->combat[tile];
    if(on) {
        if(t.flaming)damage=static_cast<std::int32_t>(static_cast<std::uint32_t>(damage)+static_cast<std::uint32_t>(t.flame_damage));
        t.self_flame=self_flame;t.rule.flag_255=0;t.flame_damage=damage;c.overlay=1;t.flaming=1;
        emit(h,TurnEventKind::FlameOverlay,tile);
    } else {
        c.overlay=0;t.flaming=0;t.self_flame=self_flame;
    }
}
extern "C" void dr_end_turn_burn_freeze(PathState* p,const TurnHooks* h) {
    auto& board=p->match->stroke->selection;
    bool sounded=false;
    for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
        const int i=y*6+x;auto& t=board.tiles[i];auto& c=p->combat[i];
        if(t.rule.flag_255) {
            emit(h,TurnEventKind::FlareRest,i,1,static_cast<std::int32_t>(0xffffe664u));   // RGBA 100,230,255,255
            set_freeze(p,i,false,h);
            if(!sounded) {emit(h,TurnEventKind::Sound,-1,22);sounded=true;}
        } else if(t.flaming) {
            emit(h,TurnEventKind::FlareRest,i,1,static_cast<std::int32_t>(0xff0a96f0u));   // RGBA 240,150,10,255
            const int type=t.rule.type;
            if(type==1) {
                emit(h,TurnEventKind::LabelRest,i,9,t.flame_damage,18,0x3f800000);
                const auto rest=static_cast<std::int32_t>(static_cast<std::uint32_t>(c.health)-static_cast<std::uint32_t>(t.flame_damage));
                if(rest>0) {
                    c.health=rest;emit(h,TurnEventKind::Text,i,0,0,type);emit(h,TurnEventKind::Particles,i,2);
                } else {
                    c.health=0;emit(h,TurnEventKind::Text,i,0,0,type);
                    h->attack_skull(h->context,i,0,false);
                    if(board.character.race==8)emit(h,TurnEventKind::Achievement,-1,54,0x40000000);
                }
            }
            dr_set_flame_visibility(p,i,false,0,false,h);
        }
    }
}
extern "C" void dr_end_turn_poison_enemies(PathState* p,const TurnHooks* h) {
    auto& board=p->match->stroke->selection;
    for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
        const int i=y*6+x;const int type=board.tiles[i].rule.type;
        if(type!=1)continue;
        auto& c=p->combat[i];
        TileState view{c.attack,c.poison,nullptr};
        const std::int32_t poison=dr_get_poison(&view);c.poison=view.poison;
        if(!poison)continue;
        emit(h,TurnEventKind::LabelRest,i,7,poison,15,0x3f800000);
        const auto rest=static_cast<std::int32_t>(static_cast<std::uint32_t>(c.health)-static_cast<std::uint32_t>(poison));
        if(rest>0) {c.health=rest;emit(h,TurnEventKind::Text,i,0,0,type);emit(h,TurnEventKind::Particles,i,2);}
        else {
            h->match_tile(h->context,i,5);
            if(board.character.race==1)emit(h,TurnEventKind::Achievement,-1,47,0x40000000);
        }
    }
}
extern "C" bool dr_end_turn_finish(ResourceState* r,PathState* p,GenerationState* g,EndGameState* e,
    TurnFinishFlags* f,const TurnHooks* h) {
    r->guard_164a6=r->guard_164a4;r->guard_164a4=e->revive_second;e->revive_second=0;
    if(h->check_end_game(h->context))return true;
    h->move_matched_tiles(h->context);
    for(auto& c:p->combat)c.attack_flag=0;
    g->one_health=f->next_one_health_14af7;f->next_one_health_14af7=0;
    g->force_coins=f->next_force_coins_14af8;f->next_force_coins_14af8=0;
    g->filter_enabled=0;g->filter_swords=0;
    const auto left=static_cast<std::int32_t>(static_cast<std::uint32_t>(g->time_to_promotion)-1u);
    g->time_to_promotion=left<0?0:left;
    const auto& stroke=*p->match->stroke;const auto& board=stroke.selection;
    constexpr std::int32_t help_size=0x3da9999a;
    // Each column shows the help for its first (topmost) matching enemy.
    if(f->help_flags_102d0&0x8000u)
        for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
            const int i=y*6+x;
            if(board.tiles[i].rule.type==1) {emit(h,TurnEventKind::Help,i,15,help_size,help_size);break;}
        }
    if(f->help_flags_102d0&0x200000u)
        for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
            const int i=y*6+x;const auto& rule=board.tiles[i].rule;
            if(rule.type==1 && rule.enemy_type!=0) {emit(h,TurnEventKind::Help,i,21,help_size,help_size);break;}
        }
    f->flag_1554c=0;
    e->victory=stroke.record_14aed && stroke.mode_14ae8==0 && p->turn==100;
    if(h->check_end_game(h->context))return true;
    emit(h,TurnEventKind::SerialiseState,-1);
    return false;
}
namespace {
void reset_attack_timers(MatchState& m) {m.shake_progress_bd90=0;m.shake_scale_bd94=0x3f800000;}
}
extern "C" void dr_run_away_enemy(PathState* p,std::uint32_t tile,const TurnHooks* h) {
    emit(h,TurnEventKind::Flare,static_cast<int>(tile),1,static_cast<std::int32_t>(0xff00ffffu));   // RGBA 255,255,0,255
    emit(h,TurnEventKind::Sound,-1,35);
    h->match_tile(h->context,static_cast<std::int32_t>(tile),7);
    h->move_matched_tiles(h->context);
    for(auto& c:p->combat)c.attack_flag=0;
    reset_attack_timers(*p->match);
}
extern "C" void dr_explode_enemy(ResourceState* r,PathState* p,std::uint32_t tile,const TurnHooks* h) {
    auto& m=*p->match;
    for(int i=0;i<5;++i)m.matched_counts[i]=0;
    m.sound_13ec4=0;
    h->match_tile(h->context,static_cast<std::int32_t>(tile),7);
    emit(h,TurnEventKind::FlareTarget,-1,1,static_cast<std::int32_t>(0xff0000ffu));   // RGBA 255,0,0,255
    const std::int32_t half=r->health/2;
    r->health=half>0?half:1;
    if(r->health!=r->ui_health) {r->ui_health=r->health;emit(h,TurnEventKind::HealthBar,-1,r->health);}
    reset_attack_timers(m);
}
extern "C" void dr_teleport_enemy(PathState* p,GenerationState* g,const TurnHooks* h) {
    auto& board=p->match->stroke->selection;
    for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
        const int i=y*6+x;auto& rule=board.tiles[i].rule;
        if(rule.matched)continue;
        rule.matched=1;
        emit(h,TurnEventKind::FlareRest,i,1,static_cast<std::int32_t>(0xffff6400u));   // RGBA 0,100,255,255
    }
    const bool swords=dr_mortal_enemy(board.character.race)==19;
    g->filter_swords=swords;g->filter_enabled=1;
    reset_attack_timers(*p->match);
    if(swords)emit(h,TurnEventKind::Achievement,-1,38,0x42c80000);
    emit(h,TurnEventKind::Sound,-1,21);
}
namespace {
std::int32_t attack_of(const PathState* p,std::uint32_t i) {
    const auto& c=p->combat[i];
    const CharacterClassState character{p->match->stroke->selection.character.race};
    const GameContext game{&character};const TileState view{c.attack,c.poison,&game};
    return dr_get_attack(&view);
}
}
extern "C" void dr_lower_skulls(PathState* p,std::uint32_t tile,const TurnHooks* h) {
    const auto& board=p->match->stroke->selection;const auto& self=board.tiles[tile].rule;
    for(int x=0;x<6;++x)for(int y=4;y>=0;--y) {
        const int i=y*6+x,below=i+6;
        if(board.tiles[i].rule.type!=1 || board.tiles[below].rule.type==1)continue;
        if(x==self.x && y==self.y)continue;
        h->match_tile(h->context,below,7);
        emit(h,TurnEventKind::FlareRest,below,1,static_cast<std::int32_t>(0xff143c73u));   // RGBA 115,60,20,255
        break;
    }
    emit(h,TurnEventKind::Label,static_cast<int>(tile),23,0,31,0x3f800000);
    emit(h,TurnEventKind::Sound,-1,5);
    reset_attack_timers(*p->match);
}
extern "C" void dr_flee_up(PathState* p,std::uint32_t tile,const TurnHooks* h) {
    const auto& rule=p->match->stroke->selection.tiles[tile].rule;
    const int x=rule.x,y=rule.y;
    emit(h,TurnEventKind::LabelRest,y*6+x,37,0,45,0x3f800000);
    if(y==0) {
        h->match_tile(h->context,static_cast<std::int32_t>(tile),7);
        emit(h,TurnEventKind::FlareRest,x,1,-1);   // white
        return;
    }
    h->swap_tiles(h->context,x,y-1,x,y);
    emit(h,TurnEventKind::FlareRest,y*6+x,1,-1);
    emit(h,TurnEventKind::FlareRest,(y-1)*6+x,1,-1);
    emit(h,TurnEventKind::Sound,-1,35);
    reset_attack_timers(*p->match);
}
extern "C" void dr_ignite_tiles(PathState* p,std::uint32_t tile,const TurnHooks* h) {
    const auto& board=p->match->stroke->selection;const auto& self=board.tiles[tile].rule;
    const int cx=self.x,cy=self.y;
    for(int dx=-1;dx<=1;++dx)for(int dy=-1;dy<=1;++dy) {
        if(!dx && !dy)continue;
        const int x=cx+dx,y=cy+dy;
        if(static_cast<unsigned>(x)>5u || y<0 || y>5)continue;
        const int i=y*6+x;const auto& rule=board.tiles[i].rule;
        if(rule.matched || (rule.type==1 && rule.enemy_type==7))continue;
        emit(h,TurnEventKind::FlareRest,i,1,static_cast<std::int32_t>(0xff0a96f0u));   // RGBA 240,150,10,255
        dr_set_flame_visibility(p,static_cast<std::uint32_t>(i),true,attack_of(p,tile),false,h);
    }
    reset_attack_timers(*p->match);
}
extern "C" void dr_stab_attack(ResourceState* r,PathState* p,std::uint32_t tile,const TurnHooks* h) {
    const auto& board=p->match->stroke->selection;const auto& self=board.tiles[tile].rule;
    if(dr_mortal_enemy(board.character.race)==16 && self.y!=5) {
        const int below=(self.y+1)*6+self.x;const auto& rule=board.tiles[below].rule;
        if(!(rule.type==1 && rule.enemy_type!=0))h->match_tile(h->context,below,7);
        return;
    }
    if(self.y!=5)return;
    emit(h,TurnEventKind::Sound,-1,27);
    emit(h,TurnEventKind::Sound,-1,17);
    emit(h,TurnEventKind::Label,static_cast<int>(tile),19,0,27,0x3f800000);
    const auto damage=static_cast<std::uint32_t>(attack_of(p,tile))<<1;
    const auto rest=static_cast<std::int32_t>(static_cast<std::uint32_t>(r->health)-damage);
    r->health=rest<0?0:rest;
    if(r->health!=r->ui_health) {r->ui_health=r->health;emit(h,TurnEventKind::HealthBar,-1,r->health);}
    emit(h,TurnEventKind::LabelPoison,-1,2,static_cast<std::int32_t>(static_cast<std::uint32_t>(attack_of(p,tile))<<1),11,0x3f000000);
}
extern "C" void dr_convert_sword_to_skull(GenerationState* g,std::uint32_t tile,const TurnHooks* h,const GenerationHooks* gh) {
    PathState* p=g->refill->path;auto& m=*p->match;const auto& board=m.stroke->selection;
    auto swords=[&] {int n=0;for(const auto& t:board.tiles)if(t.rule.type==4)++n;return n;};
    int pick=dr_random_int(&m.random,0,swords()-1,5);
    if(swords()>0) {
        emit(h,TurnEventKind::Label,static_cast<int>(tile),18,0,26,0x3f800000);
        emit(h,TurnEventKind::Sound,-1,14);
    }
    for(int x=0;x<6 && pick>=0;++x)for(int y=0;y<6;++y) {
        const int i=y*6+x;
        if(board.tiles[i].rule.type!=4)continue;
        if(pick) {--pick;continue;}
        dr_set_tile_type(g,static_cast<std::uint32_t>(i),1,p->turn,m.spawn_enabled_14ae0,gh);
        if(g->one_health) {p->combat[i].health=1;emit(h,TurnEventKind::Text,i,0,0,1);}
        emit(h,TurnEventKind::FlareRest,i,1,static_cast<std::int32_t>(0xff0a96f0u));   // RGBA 240,150,10,255
        emit(h,TurnEventKind::LabelRest,i,18,0,26,0x3f800000);
        pick=-1;break;
    }
    reset_attack_timers(m);
}
namespace {
bool normal_potion(const PotionFlags& f) {return !f.flag_234 && !f.flag_232 && !f.flag_233;}
std::int32_t float_bits(float f) {std::int32_t i;std::memcpy(&i,&f,4);return i;}
}
extern "C" void dr_make_acid_potion(GenerationState* g,std::uint32_t tile,const TurnHooks* h,const GenerationHooks* gh) {
    PathState* p=g->refill->path;auto& m=*p->match;const auto& board=m.stroke->selection;
    auto normal=[&](int i) {return board.tiles[i].rule.type==0 && normal_potion(m.preview->potions[i]);};
    auto potions=[&] {int n=0;for(int i=0;i<36;++i)if(normal(i))++n;return n;};
    int pick=dr_random_int(&m.random,0,potions()-1,5);
    if(potions()>0) {
        emit(h,TurnEventKind::Label,static_cast<int>(tile),14,0,23,0x3f800000);
        emit(h,TurnEventKind::Sound,-1,24);
    }
    for(int x=0;x<6 && pick>=0;++x)for(int y=0;y<6;++y) {
        const int i=y*6+x;
        if(!normal(i))continue;
        if(pick) {--pick;continue;}
        // Tile::MakeAcidPotion 0x3d7b8
        constexpr float cell=.0517578125f;
        const float u=static_cast<float>(g->tiles[i].variant)*cell;
        const float v=static_cast<float>(board.tiles[i].rule.type)*cell+.552734375f;
        if(gh && gh->event) {
            const GenerationEvent e{GenerationEventKind::UV,i,float_bits(u),float_bits(v),float_bits(cell),float_bits(cell)};
            gh->event(gh->context,&e);
        }
        m.preview->potions[i].flag_233=1;
        emit(h,TurnEventKind::FlareRest,i,1,static_cast<std::int32_t>(0xff00ff00u));   // RGBA 0,255,0,255
        pick=-1;break;
    }
    reset_attack_timers(m);
}
extern "C" void dr_freeze_tiles(PathState* p,std::uint32_t tile,const TurnHooks* h) {
    auto& m=*p->match;const auto& board=m.stroke->selection;
    bool candidate[36]={};
    for(int i=0;i<36;++i) {
        const auto& rule=board.tiles[i].rule;
        candidate[i]=!rule.matched && !(rule.type==1 && rule.enemy_type!=0) && !rule.flag_255;
    }
    for(int round=0;round<2;++round) {
        int n=0;for(bool b:candidate)n+=b;
        if(!n)break;
        int pick=dr_random_int(&m.random,0,n-1,5);
        for(int i=0;i<36;++i) {
            if(!candidate[i])continue;
            if(pick) {--pick;continue;}
            set_freeze(p,i,true,h);
            emit(h,TurnEventKind::Flare,i,1,static_cast<std::int32_t>(0xffffe664u));   // RGBA 100,230,255,255
            candidate[i]=false;break;
        }
    }
    emit(h,TurnEventKind::Label,static_cast<int>(tile),17,0,25,0x3f800000);
    emit(h,TurnEventKind::Sound,-1,20);
    reset_attack_timers(m);
}
extern "C" void dr_break_random_shield_sword(GenerationState* g,std::uint32_t tile,const TurnHooks* h,const GenerationHooks* gh) {
    PathState* p=g->refill->path;auto& m=*p->match;const auto& board=m.stroke->selection;
    bool candidate[36]={};int n=0;
    for(int i=0;i<36;++i) {
        const auto& t=board.tiles[i];
        if(t.rule.matched || t.broken)continue;
        candidate[i]=(t.rule.type==4 && !t.rule.flag_231) || t.rule.type==3;
        n+=candidate[i];
    }
    if(!n)return;
    int pick=dr_random_int(&m.random,0,n-1,5);
    for(int i=0;i<36;++i) {
        if(!candidate[i])continue;
        if(pick) {--pick;continue;}
        dr_make_broken(g,static_cast<std::uint32_t>(i),gh);
        emit(h,TurnEventKind::Flare,i,1,-1);   // white
        break;
    }
    emit(h,TurnEventKind::Label,static_cast<int>(tile),22,0,30,0x3f800000);
    emit(h,TurnEventKind::Sound,-1,16);
    reset_attack_timers(m);
}
extern "C" void dr_convert_random_tiles(GenerationState* g,std::uint32_t tile,const TurnHooks* h,const GenerationHooks* gh) {
    PathState* p=g->refill->path;auto& m=*p->match;const auto& board=m.stroke->selection;
    bool candidate[36]={};
    for(int i=0;i<36;++i) {
        const auto& rule=board.tiles[i].rule;
        candidate[i]=!rule.matched && !(rule.type==1 && rule.enemy_type!=0);
    }
    for(int round=0;round<2;++round) {
        int n=0;for(bool b:candidate)n+=b;
        if(!n)break;
        int pick=dr_random_int(&m.random,0,n-1,5);
        for(int i=0;i<36;++i) {
            if(!candidate[i])continue;
            if(pick) {--pick;continue;}
            dr_randomise_tile(g,static_cast<std::uint32_t>(i),gh);
            emit(h,TurnEventKind::Flare,i,1,static_cast<std::int32_t>(0xff00ffffu));   // RGBA 255,255,0,255
            candidate[i]=false;break;
        }
    }
    emit(h,TurnEventKind::Label,static_cast<int>(tile),21,0,29,0x3f800000);
    emit(h,TurnEventKind::Sound,-1,24);
    reset_attack_timers(m);
}
extern "C" void dr_jump_enemy(PathState* p,std::uint32_t tile,const TurnHooks* h) {
    auto& m=*p->match;const auto& board=m.stroke->selection;
    const int sx=board.tiles[tile].rule.x,sy=board.tiles[tile].rule.y;
    bool candidate[36]={};int n=0;
    for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
        const int i=y*6+x;const auto& rule=board.tiles[i].rule;
        candidate[i]=!rule.matched && !(rule.type==1 && rule.enemy_type!=0) && !(x==sx && y==sy);
        n+=candidate[i];
    }
    if(!n)return;
    int pick=dr_random_int(&m.random,0,n-1,5);
    int tx=0,ty=0;
    for(int i=0;i<36;++i) {
        if(!candidate[i])continue;
        if(pick) {--pick;continue;}
        tx=board.tiles[i].rule.x;ty=board.tiles[i].rule.y;break;
    }
    h->swap_tiles(h->context,tx,ty,sx,sy);
    h->match_tile(h->context,sy*6+sx,7);
    emit(h,TurnEventKind::FlareRest,sy*6+sx,1,-1);   // white
    emit(h,TurnEventKind::FlareRest,ty*6+tx,1,-1);
    emit(h,TurnEventKind::LabelRest,ty*6+tx,15,0,24,0x3f800000);
    emit(h,TurnEventKind::Sound,-1,35);
    reset_attack_timers(m);
}
namespace {
// Shared body of AttractSkulls and AttractShieldsSwords.
void attract(PathState* p,std::uint32_t tile,const TurnHooks* h,bool shields,std::int32_t colour,
    int label,int label_colour,int sound) {
    auto& m=*p->match;const auto& board=m.stroke->selection;
    const auto target=[&](int i) {
        const int type=board.tiles[i].rule.type;return shields?(type==3 || type==4):type==1;
    };
    const int sx=board.tiles[tile].rule.x,sy=board.tiles[tile].rule.y;
    bool far[36]={},near[36]={};int nfar=0,nnear=0;
    for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
        const int i=y*6+x;
        if(board.tiles[i].rule.matched || !target(i))continue;
        if(std::abs(x-sx)>1 || std::abs(y-sy)>1) {far[i]=true;++nfar;}
    }
    if(!nfar)return;
    for(int x=sx-1;x<=sx+1;++x)for(int y=sy-1;y<=sy+1;++y) {
        if(x==sx && y==sy)continue;
        if(static_cast<unsigned>(x)>5u || y<0 || y>5)continue;
        const int i=y*6+x;
        if(board.tiles[i].rule.matched || target(i))continue;
        near[i]=true;++nnear;
    }
    if(!nnear)return;
    const auto nth=[](const bool* set,int n) {for(int i=0;i<36;++i)if(set[i] && n--==0)return i;return -1;};
    while(nfar && nnear) {
        const int a=nth(far,dr_random_int(&m.random,0,nfar-1,5));
        const int b=nth(near,dr_random_int(&m.random,0,nnear-1,5));
        const int ax=board.tiles[a].rule.x,ay=board.tiles[a].rule.y,bx=board.tiles[b].rule.x,by=board.tiles[b].rule.y;
        h->swap_tiles(h->context,ax,ay,bx,by);
        emit(h,TurnEventKind::FlareRest,by*6+bx,1,colour);
        emit(h,TurnEventKind::FlareRest,ay*6+ax,1,colour);
        far[a]=false;--nfar;near[b]=false;--nnear;
    }
    emit(h,TurnEventKind::Label,static_cast<int>(tile),label,0,label_colour,0x3f800000);
    emit(h,TurnEventKind::Sound,-1,sound);
    reset_attack_timers(m);
}
}
extern "C" void dr_attract_skulls(PathState* p,std::uint32_t tile,const TurnHooks* h) {
    attract(p,tile,h,false,static_cast<std::int32_t>(0xff00ffffu),24,32,14);   // RGBA 255,255,0,255
}
extern "C" void dr_attract_shields_swords(PathState* p,std::uint32_t tile,const TurnHooks* h) {
    attract(p,tile,h,true,-1,25,33,23);   // white
}
extern "C" void dr_heal_or_bless(GenerationState* g,std::uint32_t tile,const TurnHooks* h) {
    PathState* p=g->refill->path;auto& m=*p->match;const auto& board=m.stroke->selection;
    const int sx=board.tiles[tile].rule.x,sy=board.tiles[tile].rule.y;
    bool candidate[36]={};int n=0;bool heal=true;
    for(int pass=0;pass<2 && !n;++pass) {
        heal=pass==0;
        for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
            if(x==sx && y==sy)continue;
            const int i=y*6+x;const auto& rule=board.tiles[i].rule;
            if(rule.matched || rule.type!=1)continue;
            if(heal && p->combat[i].health>=g->tiles[i].max_health)continue;
            candidate[i]=true;++n;
        }
    }
    if(!n)return;
    emit(h,TurnEventKind::Sound,-1,36);
    // Game::HealOrBless(std::set<Tile*>&, bool heal, int count) with count 2
    for(int count=2;count>0 && n>0;--count) {
        int pick=dr_random_int(&m.random,0,n-1,5);
        for(int i=0;i<36;++i) {
            if(!candidate[i])continue;
            if(pick) {--pick;continue;}
            auto& c=p->combat[i];
            if(heal) {
                c.health=g->tiles[i].max_health;
                emit(h,TurnEventKind::Text,i,0,0,1);
                emit(h,TurnEventKind::Label,i,12,0,21,0x3f800000);
            } else {
                c.attack=static_cast<std::int32_t>(static_cast<std::uint32_t>(c.attack)+1u);
                emit(h,TurnEventKind::Text,i,1,0,0);
                emit(h,TurnEventKind::Label,i,11,0,20,0x3f800000);
            }
            emit(h,TurnEventKind::Flare,i,1,static_cast<std::int32_t>(0xffff6464u));   // RGBA 100,100,255,255
            candidate[i]=false;--n;break;
        }
    }
    reset_attack_timers(m);
}
extern "C" void dr_activate_ability(PathState* p,GenerationState* g,std::uint8_t* activated,std::uint32_t tile,
    const TurnHooks* h,const GenerationHooks* gh) {
    if(activated[tile])return;
    activated[tile]=1;
    auto& rule=p->match->stroke->selection.tiles[tile].rule;
    const auto index=static_cast<std::int32_t>(tile);
    auto generation=[gh,index](GenerationEventKind kind) {
        if(gh && gh->event) { const GenerationEvent e{kind,index,0,0,0,0};gh->event(gh->context,&e); }
    };
    auto count_down=[&] {
        rule.enemy_state=static_cast<std::int32_t>(static_cast<std::uint32_t>(rule.enemy_state)-1u);
        generation(GenerationEventKind::Countdown);
        return rule.enemy_state==0;
    };
    const auto type=rule.enemy_type;
    switch(type) {
    case 3:
        if(count_down())dr_run_away_enemy(p,tile,h);
        break;
    case 10:
        if(count_down())dr_explode_enemy(g->resources,p,tile,h);
        break;
    case 19:
        if(count_down())dr_teleport_enemy(p,g,h);
        break;
    case 7: dr_ignite_tiles(p,tile,h);break;
    case 11: dr_convert_sword_to_skull(g,tile,h,gh);break;
    case 16: dr_stab_attack(g->resources,p,tile,h);break;
    case 23: dr_lower_skulls(p,tile,h);break;
    case 31: dr_flee_up(p,tile,h);break;
    case 6: dr_make_acid_potion(g,tile,h,gh);break;
    case 8: dr_freeze_tiles(p,tile,h);break;
    case 22: dr_break_random_shield_sword(g,tile,h,gh);break;
    case 18: dr_convert_random_tiles(g,tile,h,gh);break;
    case 14: dr_jump_enemy(p,tile,h);break;
    case 24: dr_attract_skulls(p,tile,h);break;
    case 25: dr_attract_shields_swords(p,tile,h);break;
    case 4: dr_heal_or_bless(g,tile,h);break;
    case 13: case 26:
        h->ability(h->context,type,index);   // not yet recovered
        break;
    case 17:
        dr_mimic_defence(p,tile,h);
        break;
    case 28:
        rule.enemy_state=static_cast<std::int32_t>(static_cast<std::uint32_t>(rule.enemy_state)-1u);
        if(rule.enemy_state==0) {h->ability(h->context,type,index);rule.enemy_state=5;}   // Game::DestroyUpgrade
        generation(GenerationEventKind::Countdown);
        break;
    case 32:
        if(rule.enemy_state==0)break;
        if(p->combat[tile].flag_25e) {p->combat[tile].flag_25e=0;break;}
        rule.enemy_state=0;
        dr_generate_stats(g,tile,p->turn,p->match->spawn_enabled_14ae0,gh);
        generation(GenerationEventKind::EnemyUV);
        dr_update_generated_values(g,tile,gh);
        dr_resurrect(p->match,tile,h);
        break;
    default:
        break;
    }
}
extern "C" void dr_end_turn_abilities(PathState* p,GenerationState* g,std::uint8_t* activated,
    const TurnHooks* h,const GenerationHooks* gh) {
    for(int i=0;i<36;++i)activated[i]=0;
    dr_process_cripples(p,h);
    const auto& board=p->match->stroke->selection;
    for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
        const int i=y*6+x;const auto& rule=board.tiles[i].rule;
        if(rule.type==1 && rule.enemy_type!=0)dr_activate_ability(p,g,activated,static_cast<std::uint32_t>(i),h,gh);
    }
}
extern "C" bool dr_end_turn_regen_poison(ResourceState* r,std::int32_t regen,const TurnHooks* h) {
    if(regen>0) {
        const auto ceiling=static_cast<std::int32_t>(static_cast<std::uint32_t>(r->health_max)+static_cast<std::uint32_t>(r->health_bonus));
        if(ceiling>r->health) {
            emit(h,TurnEventKind::Sound,-1,4);
            const auto healed=static_cast<std::int32_t>(static_cast<std::uint32_t>(r->health)+static_cast<std::uint32_t>(regen));
            r->health=ceiling<healed?ceiling:healed;
            if(r->health!=r->ui_health) {r->ui_health=r->health;emit(h,TurnEventKind::HealthBar,-1,r->health);}
            emit(h,TurnEventKind::LabelTarget,-1,3,regen,13,0x3f800000);
        }
    }
    if(r->poison>0) {
        emit(h,TurnEventKind::Sound,-1,29);
        r->health=static_cast<std::int32_t>(static_cast<std::uint32_t>(r->health)-static_cast<std::uint32_t>(r->poison));
        if(r->health<0) {r->health=0;emit(h,TurnEventKind::Achievement,-1,36,0x42c80000);}
        if(r->health!=r->ui_health) {r->ui_health=r->health;emit(h,TurnEventKind::HealthBar,-1,r->health);}
        emit(h,TurnEventKind::LabelPoison,-1,7,r->poison,15,0x3f800000);
        if(h->check_end_game(h->context))return true;
    }
    return false;
}
extern "C" bool dr_check_end_game(ResourceState* r,EndGameState* e,const EndGameHooks* h) {
    auto emit=[h](TurnEventKind kind,int tile,int a=0,int b=0,int c=0,int d=0) {
        if(h && h->event) { const TurnEvent ev{kind,tile,a,b,c,d};h->event(h->context,&ev); }
    };
    if(e->game_over_screen)return true;
    const auto& stroke=*r->match->stroke;const auto& board=stroke.selection;
    if(e->victory && stroke.record_14aed && stroke.mode_14ae8==0) {
        emit(TurnEventKind::Achievement,-1,76,0x42c80000);
        h->game_over(h->context,true);return true;
    }
    if(r->health>0)return false;
    if(board.character.race!=0) {
        const int mortal=dr_mortal_enemy(board.character.race);
        RuleTile tiles[36];for(int i=0;i<36;++i)tiles[i]=board.tiles[i].rule;
        const RuleGame view{0,board.character,tiles};
        if(dr_enemy_count(&view,mortal)>0)emit(TurnEventKind::Achievement,-1,40,0x42c80000);
    }
    if(r->guard_164a4) {
        r->guard_164a4=0;e->revive_second=0;
        r->health=static_cast<std::int32_t>(static_cast<std::uint32_t>(r->health_max)+static_cast<std::uint32_t>(r->health_bonus));
        if(r->health!=r->ui_health) {r->ui_health=r->health;emit(TurnEventKind::HealthBar,-1,r->health);}
        emit(TurnEventKind::Sound,-1,19);
        emit(TurnEventKind::LabelPoison,-1,28,0,36,0x3f800000);
        emit(TurnEventKind::Achievement,-1,61,0x42c80000);
        return false;
    }
    h->game_over(h->context,false);return true;
}
namespace {
std::int32_t record_quarter(const ResourceState* r,std::int32_t total) {
    const auto& stroke=*r->match->stroke;
    return stroke.record_14aed && stroke.mode_14ae8==0?total/4:total;
}
std::int32_t sum(std::int32_t a,std::int32_t b) {
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)+static_cast<std::uint32_t>(b));
}
}
extern "C" std::int32_t dr_total_gold(const ResourceState* r) {return record_quarter(r,sum(r->gold,r->total_gold));}
extern "C" std::int32_t dr_total_up(const ResourceState* r) {return record_quarter(r,sum(r->up,r->total_up));}
extern "C" std::int32_t dr_total_xp(const ResourceState* r) {return record_quarter(r,sum(r->xp,r->total_xp));}
extern "C" std::int32_t dr_get_score(const ResourceState* r,const PathState* p,const SkillSlots* skills,bool victory) {
    const auto& stroke=*r->match->stroke;
    if(stroke.record_14aed) {
        if(stroke.mode_14ae8==1)return p->total;
        if(stroke.mode_14ae8==0) {
            const auto total=sum(sum(dr_total_gold(r),dr_total_xp(r)),dr_total_up(r));
            return victory?static_cast<std::int32_t>(static_cast<std::uint32_t>(total)<<1):total;
        }
    }
    auto total=sum(sum(sum(dr_total_gold(r),dr_total_xp(r)),dr_total_up(r)),p->turn);
    for(int i=0;i<r->skill_count;++i)total=sum(total,static_cast<std::int32_t>(static_cast<std::uint32_t>(skills->level[i])*100u));
    return total;
}
extern "C" void dr_game_over(ResourceState* r,PathState* p,ClassProfile* cls,const SkillSlots* skills,EndGameState* e,bool win,const GameOverHooks* h) {
    auto emit=[h](std::int32_t kind,int a=0,int b=0,int c=0,int d=0) {
        if(h && h->event) { const TurnEvent ev{static_cast<TurnEventKind>(kind),-1,a,b,c,d};h->event(h->context,&ev); }
    };
    cls->games_played+=1;
    cls->enemies_killed+=static_cast<std::uint32_t>(p->battle.kill_count_165b4);
    const auto& stroke=*r->match->stroke;const bool victory=e->victory;
    if(!stroke.record_14aed) {
        const ScoreEntry entry{0,p->turn,dr_total_xp(r),dr_total_gold(r),dr_total_up(r),dr_get_score(r,p,skills,victory),r->match->spawn_enabled_14ae0};
        h->add_score(h->context,&entry);
        std::uint32_t* best=entry.mode==1?&cls->normal_score:entry.mode==2?&cls->hard_score:entry.mode==3?&cls->harder_score:nullptr;
        if(best) {
            const auto score=static_cast<std::uint32_t>(dr_get_score(r,p,skills,victory));
            if(score>*best)*best=score;
        }
    } else if(stroke.mode_14ae8==1) {
        const ScoreEntry entry{1,p->turn,p->crossing_average,p->crossing_best,p->crossing_samples,dr_get_score(r,p,skills,victory),1};
        h->add_score(h->context,&entry);
    } else if(stroke.mode_14ae8==0) {
        const ScoreEntry entry{1,p->turn,dr_total_xp(r),dr_total_gold(r),dr_total_up(r),dr_get_score(r,p,skills,victory),0};
        h->add_score(h->context,&entry);
    }
    std::int32_t ids[4]={-1,-1,-1,-1};
    for(int i=0;i<4 && i<r->skill_count;++i)ids[i]=skills->id[i];
    emit(static_cast<std::int32_t>(EndGameEventKind::SetSkills),ids[0],ids[1],ids[2],ids[3]);
    emit(static_cast<std::int32_t>(EndGameEventKind::SerialiseClasses));
    emit(static_cast<std::int32_t>(EndGameEventKind::GameOverScreen),win);
    e->flag_146d0=0;e->flag_146d4=1;e->flag_15546=1;
    emit(static_cast<std::int32_t>(TurnEventKind::Achievement),67,0x42c80000);
}
extern "C" bool dr_end_turn_begin(ResourceState* r,PathState* p,SkillSlots* skills,TurnFlags* f,RuneState* rune,
    std::uint8_t* counterattack,const TurnHooks* h) {
    p->turn=static_cast<std::int32_t>(static_cast<std::uint32_t>(p->turn)+1u);
    if(h->check_end_game(h->context))return true;
    auto& m=*r->match;const auto& board=m.stroke->selection;
    for(int i=0;i<r->skill_count;++i) {
        RuleTile tiles[36];for(int j=0;j<36;++j)tiles[j]=board.tiles[j].rule;
        const RuleGame view{0,board.character,tiles};
        if(dr_enemy_count(&view,15)==0) {
            if(r->skill_current[i]==static_cast<std::int32_t>(static_cast<std::uint32_t>(r->skill_max[i])-1u))emit(h,TurnEventKind::Sound,-1,10);
            const auto next=static_cast<std::int32_t>(static_cast<std::uint32_t>(r->skill_current[i])+1u);
            r->skill_current[i]=next<=r->skill_max[i]?next:r->skill_max[i];
        }
        skills->active[i]=0;   // Skill::Deactivate
    }
    emit(h,TurnEventKind::UpdateSkills,-1);
    f->b15561=0;f->b15562=0;
    for(auto& b:f->b165b8)b=0;
    if(rune->enabled_16491 && !f->arrow_hold_16492) {
        emit(h,TurnEventKind::ArrowColour,-1,50,255,50);
        rune->enabled_16491=f->arrow_hold_16492;
    }
    f->arrow_hold_16492=0;
    f->prev_164a7=f->next_164a8;f->next_164a8=0;
    m.stroke->selection.double_damage=f->next_be78[0];
    m.preview->double_upgrade=f->next_be78[1];m.preview->double_healing=f->next_be78[2];m.preview->double_gold=f->next_be78[3];
    for(auto& b:f->next_be78)b=0;
    *counterattack=0;
    p->battle.grant_coin_on_attack=f->next_coin_bfbc;f->next_coin_bfbc=0;
    for(int i=0;i<5;++i)m.matched_counts[i]=0;
    m.shake_progress_bd90=0;m.shake_scale_bd94=0x3f800000;
    return false;
}
extern "C" void dr_end_of_turn(ResourceState* r,PathState* p,GenerationState* g,EndOfTurnState* s,
    const TurnHooks* h,const GenerationHooks* gh) {
    if(dr_end_turn_begin(r,p,s->skills,s->flags,s->rune,s->counterattack,h))return;
    dr_end_turn_burn_freeze(p,h);
    if(dr_end_turn_regen_poison(r,s->regen,h))return;
    dr_end_turn_poison_enemies(p,h);
    dr_end_turn_abilities(p,g,s->activated,h,gh);
    dr_end_turn_finish(r,p,g,s->end,s->finish,h);
}
