#include "recovered_stroke.hpp"
#include <cstring>
using namespace dungeonraid;
namespace {
std::int32_t bits(float value) {
    std::int32_t result; std::memcpy(&result,&value,sizeof(result)); return result;
}
std::int32_t add(std::int32_t a,std::int32_t b) {
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)+static_cast<std::uint32_t>(b));
}
std::int32_t mul(std::int32_t a,std::int32_t b) {
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)*static_cast<std::uint32_t>(b));
}
void emit(const SelectionHooks* h,SelectionEvent kind,std::int32_t index=-1,
          std::int32_t a=0,std::int32_t b=0) {
    if(h && h->event) h->event(h->context,kind,index,a,b);
}
void clear_counts(StrokeState* state) {
    for(auto& value:state->resource_counts_164b0) value=0;
}
}
extern "C" void dr_begin_stroke(StrokeState* state,const SelectionHooks* hooks) {
    // ProcessInput empty-path branch, 0x16e28..0x16ff2, with out-of-line blocks
    // 0x170ca..0x170dc. Calls preserve original order and mutation boundaries.
    auto* s=&state->selection;
    if(s->path_length) return; // Native caller guard; outside original branch.
    s->current_damage=0;
    s->spiky_enemy_attacked=0;
    const auto* hit=dr_tile_at(&s->geometry,&s->touch);
    if(hit) {
        const auto index=static_cast<std::uint8_t>(hit-s->geometry.tiles);
        auto& tile=s->tiles[index];
        if(!tile.rule.flag_255 || tile.rule.type==1) {
            s->skull_counted=0;
            if(tile.rule.type==1) {
                if(!(tile.rule.enemy_type==32 && tile.rule.enemy_state!=0)) {
                    auto amount=add(s->base_damage,s->bonus_base_damage);
                    if(dr_mortal_enemy(s->character.race)==8) {
                        for(const auto& other:s->tiles) {
                            if(other.rule.type==1 && other.rule.enemy_type==8) {amount/=2;break;}
                        }
                    }
                    s->current_damage=amount;
                    s->skull_counted=1;
                    if(tile.rule.enemy_type!=0) {
                        emit(hooks,SelectionEvent::EnemyTooltip,index,tile.rule.enemy_type);
                        if(tile.rule.enemy_type==2) s->spiky_enemy_attacked=1;
                    }
                }
            } else if(tile.rule.type==4 && !tile.broken) {
                s->current_damage=mul(mul(s->weapon_damage,tile.magic_sword?5:1),s->double_damage?2:1);
            }
            if(tile.flaming && !tile.self_flame) s->current_flame_damage=tile.flame_damage;
            dr_select_tile(&tile,index,hooks);
            s->path[s->path_length++]=index;
            emit(hooks,SelectionEvent::CrossVisibility);
            emit(hooks,SelectionEvent::UpdateDimming);
            emit(hooks,SelectionEvent::TileSound,index);
        }
    }
    clear_counts(state);
    emit(hooks,SelectionEvent::ResourceShadows);
    const float fraction=static_cast<float>(s->leech)/100.0f;
    s->current_leech=static_cast<std::int32_t>(static_cast<float>(s->current_damage)*fraction);
    s->current_spike_damage=s->spiky_enemy_attacked?s->current_damage:0;
}
extern "C" void dr_update_stroke(StrokeState* state,const SelectionHooks* hooks) {
    auto* s=&state->selection;
    if(!s->path_length) {dr_begin_stroke(state,hooks);return;}
    // Existing-path branch 0x16ff4..0x17072.
    const auto* hit=dr_tile_at(&s->geometry,&s->touch);
    if(hit==&s->geometry.tiles[s->path[s->path_length-1]]) {
        emit(hooks,SelectionEvent::ProcessRune,-1,0);return;
    }
    clear_counts(state);
    dr_process_tile_selection(s,hooks);
    emit(hooks,SelectionEvent::ProcessRune,-1,0);
    emit(hooks,SelectionEvent::ResourceShadows);
    emit(hooks,SelectionEvent::UpdateDimming);
    if(state->record_14aed && state->mode_14ae8==1)
        emit(hooks,SelectionEvent::ProcessPretzels);
}
extern "C" void dr_cancel_stroke(StrokeState* state,const SelectionHooks* hooks) {
    // Phase 3 path: 0x17082/0x1675a..0x16818, then 0x16d88..0x16e0e.
    auto* s=&state->selection;
    for(std::uint8_t x=0;x<6;++x) for(std::uint8_t y=0;y<6;++y)
        emit(hooks,SelectionEvent::Undim,y*6+x);
    for(std::size_t i=0;i<s->path_length;++i) {
        const auto index=s->path[i];auto& tile=s->tiles[index];
        emit(hooks,SelectionEvent::SetSize,index,bits(tile.size),bits(tile.size));
        tile.selected=0;
    }
    s->current_leech=0;
    emit(hooks,SelectionEvent::HealthShadow,-1,-1);
    emit(hooks,SelectionEvent::XPShadow,-1,-1);
    emit(hooks,SelectionEvent::UPShadow,-1,-1);
    emit(hooks,SelectionEvent::GoldShadow,-1,-1);
    s->path_length=0;
    for(auto& value:s->fake)value=0;
    s->current_damage=0;
    if(!s->flame_label_moving)s->current_flame_damage=0;
    if(!s->spike_label_moving)s->current_spike_damage=0;
    emit(hooks,SelectionEvent::CrossVisibility);
}
extern "C" ReleaseRoute dr_release_route(const SelectionState* s) {
    // 0x16890..0x168a2 and 0x16bf4..0x16c18. ProcessRune(true) precedes
    // this decision in the original; it is intentionally not faked here.
    std::size_t fake=0;
    for(const auto value:s->fake)if(value)++fake;
    if(s->path_length-fake>2)return ReleaseRoute::MatchPath;
    if(s->path_length==1) {
        const auto& tile=s->tiles[s->path[0]];
        if(tile.rule.type==6 && tile.rule.special_type==1)return ReleaseRoute::ClassScroll;
    }
    return ReleaseRoute::ClearOnly;
}
extern "C" ReleaseRoute dr_prepare_release(StrokeState* state,const SelectionHooks* hooks) {
    auto& s=state->selection;
    for(std::uint8_t x=0;x<6;++x)for(std::uint8_t y=0;y<6;++y)
        emit(hooks,SelectionEvent::Undim,y*6+x);
    emit(hooks,SelectionEvent::ProcessRune,-1,1);
    for(std::size_t i=0;i<s.path_length;++i) {
        const auto index=s.path[i];auto& tile=s.tiles[index];
        emit(hooks,SelectionEvent::SetSize,index,bits(tile.size),bits(tile.size));
        tile.selected=0;
    }
    return dr_release_route(&s);
}
