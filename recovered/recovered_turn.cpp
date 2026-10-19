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
