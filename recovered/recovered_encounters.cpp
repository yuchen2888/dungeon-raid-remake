#include "recovered_encounters.hpp"
#include <algorithm>
using namespace dungeonraid;
namespace {
void emit(const EncounterHooks* h,EncounterEventKind k,int i,int a=0,int b=0,int c=0,int d=0) {
    if(h && h->event) {const EncounterEvent e{k,i,a,b,c,d};h->event(h->context,&e);}
}
int attack(GenerationState* s,std::uint32_t i) {
    const auto& p=*s->refill->path;const auto& c=p.combat[i];
    const CharacterClassState character{p.match->stroke->selection.character.race};
    const GameContext game{&character};const TileState tile{c.attack,c.poison,&game};
    return dr_get_attack(&tile);
}
}
extern "C" void dr_stab(GenerationState* s,std::uint32_t i,const EncounterHooks* h) {
    emit(h,EncounterEventKind::Sound,-1,27);emit(h,EncounterEventKind::Sound,-1,17);
    emit(h,EncounterEventKind::Label,i,19,0,27,0x3f800000);
    auto& r=*s->resources;
    r.health=std::max(0,static_cast<int>(static_cast<std::uint32_t>(r.health)-static_cast<std::uint32_t>(attack(s,i))));
    if(r.ui_health!=r.health) {r.ui_health=r.health;emit(h,EncounterEventKind::HealthBar,-1,r.health);}
    emit(h,EncounterEventKind::PoisonPosition,-1);
    emit(h,EncounterEventKind::Label,-1,2,attack(s,i),11,0x3f000000);
    emit(h,EncounterEventKind::CheckEndGame,-1);
}
extern "C" void dr_jump_down(GenerationState* s,std::uint32_t i,const EncounterHooks* h) {
    auto& p=*s->refill->path;const auto rule=p.match->stroke->selection.tiles[i].rule;
    if(rule.y==5)return;
    dr_swap_tiles(s->refill,rule.x,5,rule.x,rule.y,h?h->refill:nullptr);
    emit(h,EncounterEventKind::Label,30+rule.x,37,0,45,0x3f800000);
    emit(h,EncounterEventKind::Flare,30+rule.x,1,-1);
    p.match->shake_progress_bd90=0;p.match->shake_scale_bd94=0x3f800000;
}
