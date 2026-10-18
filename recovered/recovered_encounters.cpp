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
extern "C" void dr_tile_add_health(GenerationState* s,std::uint32_t i,std::int32_t amount,const EncounterHooks* h) {
    auto& c=s->refill->path->combat[i];
    c.health=static_cast<std::int32_t>(static_cast<std::uint32_t>(c.health)+static_cast<std::uint32_t>(amount));
    emit(h,EncounterEventKind::Text,i,0,0,1);
    if(c.health>s->tiles[i].max_health)s->tiles[i].max_health=c.health;
}
extern "C" void dr_process_vampires(GenerationState* s,const EncounterHooks* h) {
    auto& p=*s->refill->path;auto& board=p.match->stroke->selection;
    const int mortal=dr_mortal_enemy(board.character.race);
    for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
        const int i=y*6+x;const auto& rule=board.tiles[i].rule;
        if(rule.matched || rule.type!=1 || rule.enemy_type!=20)continue;
        if(mortal==20)dr_tile_add_health(s,i,attack(s,i),h);
        else {
            auto& c=p.combat[i];const int max=s->tiles[i].max_health;
            if(c.health>=max)continue;
            const int healed=static_cast<std::int32_t>(static_cast<std::uint32_t>(attack(s,i))+static_cast<std::uint32_t>(c.health));
            c.health=healed>max?max:healed;
            emit(h,EncounterEventKind::Text,i,0,0,1);
        }
        emit(h,EncounterEventKind::Label,i,26,attack(s,i),34,0x3f800000);
        emit(h,EncounterEventKind::Sound,-1,23);
    }
}
