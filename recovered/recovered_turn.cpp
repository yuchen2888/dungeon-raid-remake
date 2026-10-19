#include "recovered_turn.hpp"
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
