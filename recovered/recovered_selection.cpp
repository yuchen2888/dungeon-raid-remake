#include "recovered_selection.hpp"
#include <cmath>
#include <cstring>
using namespace dungeonraid;
namespace {
std::int32_t bits(float value) {
    std::int32_t result; std::memcpy(&result,&value,sizeof(result));return result;
}
std::int32_t add(std::int32_t a,std::int32_t b) {
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)+static_cast<std::uint32_t>(b));
}
std::int32_t mul(std::int32_t a,std::int32_t b) {
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)*static_cast<std::uint32_t>(b));
}
void emit(const SelectionHooks* hooks,SelectionEvent kind,std::int32_t tile=-1,
          std::int32_t a=0,std::int32_t b=0) {
    if(hooks && hooks->event) hooks->event(hooks->context,kind,tile,a,b);
}
void reset_size(SelectionState* s,std::uint8_t index,const SelectionHooks* hooks) {
    emit(hooks,SelectionEvent::SetSize,index,bits(s->tiles[index].size),bits(s->tiles[index].size));
    s->tiles[index].selected=0;
}
void account(SelectionState* s,std::uint8_t index) {
    const auto& tile=s->tiles[index];const auto& rule=tile.rule;
    if(rule.type==4 && !tile.broken) {
        const auto weapon=mul(s->weapon_damage,tile.magic_sword?5:1);
        s->current_damage=add(s->current_damage,mul(weapon,s->double_damage?2:1));
    } else if(rule.type==1 && !s->skull_counted && !(rule.enemy_type==32 && rule.enemy_state)) {
        auto amount=add(s->base_damage,s->bonus_base_damage);
        if(dr_mortal_enemy(s->character.race)==8) {
            for(const auto& other:s->tiles) if(other.rule.type==1 && other.rule.enemy_type==8) {
                amount/=2;break;
            }
        }
        s->current_damage=add(s->current_damage,amount);s->skull_counted=1;
    }
    if(tile.flaming && !tile.self_flame)
        s->current_flame_damage=add(s->current_flame_damage,tile.flame_damage);
    if(rule.type==1 && rule.enemy_type==2) s->spiky_enemy_attacked=1;
}
}
extern "C" void dr_select_tile(SelectionTile* tile,std::int32_t index,const SelectionHooks* hooks) {
    // Tile::Select, original VA 0x1aa3c. Quad::SetSize is the rendering boundary.
    const auto size=bits(tile->size*0.9f);
    emit(hooks,SelectionEvent::SetSize,index,size,size);tile->selected=1;
}
extern "C" void dr_process_tile_selection(SelectionState* s,const SelectionHooks* hooks) {
    // Game::ProcessTileSelection, original VA 0xfb6c. Storage uses native
    // indices instead of 32-bit list nodes; rendering/audio remain hooks.
    // Inputs describe a valid board and an existing, non-repeating path.
    for(;;) {
        if(!s->path_length) return;
        const auto last=s->path[s->path_length-1];
        const auto* hit=dr_tile_at(&s->geometry,&s->touch);
        if(hit && hit==&s->geometry.tiles[last]) return;
        emit(hooks,SelectionEvent::HideTooltip);
        const auto top=s->geometry.vertical_offset+0.246875f;
        if(s->touch.y<top || s->touch.y>top+1.0f) {
            // Preserve the original fixed cancellation band, even when the
            // board has a nonzero vertical offset.
            if(s->touch.y>=0.146875f && s->touch.y<=1.3468750715255737f) return;
            for(std::uint8_t x=0;x<6;++x) for(std::uint8_t y=0;y<6;++y)
                emit(hooks,SelectionEvent::Undim,y*6+x);
            for(std::size_t i=0;i<s->path_length;++i) reset_size(s,s->path[i],hooks);
            s->current_leech=0;s->path_length=0;
            for(auto& value:s->fake) value=0;
            s->current_damage=0;
            if(!s->flame_label_moving) s->current_flame_damage=0;
            if(!s->spike_label_moving) s->current_spike_damage=0;
            emit(hooks,SelectionEvent::HealthShadow,-1,-1);
            emit(hooks,SelectionEvent::XPShadow,-1,-1);
            emit(hooks,SelectionEvent::UPShadow,-1,-1);
            emit(hooks,SelectionEvent::GoldShadow,-1,-1);
            emit(hooks,SelectionEvent::CrossVisibility);return;
        }
        const auto& tail=s->tiles[last];
        float dx=s->touch.x-tail.resting_position.x;
        float dy=s->touch.y-tail.resting_position.y;
        const float length=std::sqrt(dx*dx+dy*dy);
        const float limit=tail.size*1.2f;
        if(length>limit) {dx=(dx/length)*limit;dy=(dy/length)*limit;}
        const int sx=dx < -s->half_spacing ? -1 : (dx > s->half_spacing ? 1 : 0);
        const int sy=dy < -s->half_spacing ? -1 : (dy > s->half_spacing ? 1 : 0);
        const int x=tail.rule.x+sx,y=tail.rule.y+sy;
        if(x<0 || x>5 || y<0 || y>5) return;
        const auto next=static_cast<std::uint8_t>(y*6+x);
        const Point point{tail.geometry.center.x+dx,tail.geometry.center.y+dy};
        if(!dr_is_selected(&s->tiles[next].geometry,&point)) return;
        std::size_t found=s->path_length;
        for(std::size_t i=0;i<s->path_length;++i) if(s->path[i]==next) {found=i;break;}
        const bool backtrack=found<s->path_length;
        if(backtrack) {
            for(std::size_t i=found+1;i<s->path_length;++i) {
                const auto index=s->path[i];reset_size(s,index,hooks);
                s->tiles[index].cross_visibility=0;s->fake[index]=0;
            }
            s->path_length=found+1;
        } else {
            const RuleTile* path[36];
            for(std::size_t i=0;i<s->path_length;++i) path[i]=&s->tiles[s->path[i]].rule;
            if(!dr_can_match(&s->tiles[next].rule,path,s->path_length,false)) return;
            if(s->tiles[next].rule.flag_255 && s->tiles[next].rule.type!=1) return;
        }
        const auto next_type=s->tiles[next].rule.type;
        const auto& predecessor=s->tiles[s->path[s->path_length-1]].rule;
        const bool fake=predecessor.type==4 && predecessor.flag_231 && next_type!=4 && next_type!=1;
        if(!fake) emit(hooks,SelectionEvent::TileSound,next);
        if(!backtrack) {
            dr_select_tile(&s->tiles[next],next,hooks);
            s->path[s->path_length++]=next;
            if(fake) s->fake[next]=1;else account(s,next);
        } else if(s->current_damage>0 || s->current_flame_damage>0) {
            s->current_damage=s->current_flame_damage=0;
            s->skull_counted=s->spiky_enemy_attacked=0;
            for(std::size_t i=0;i<s->path_length;++i)
                if(!s->fake[s->path[i]]) account(s,s->path[i]);
        }
        const float fraction=static_cast<float>(s->leech)/100.0f;
        s->current_leech=static_cast<std::int32_t>(static_cast<float>(s->current_damage)*fraction);
        s->current_spike_damage=s->spiky_enemy_attacked?s->current_damage:0;
        if(s->current_damage>0) emit(hooks,SelectionEvent::CrossVisibility);
        if(s->path_length>1) emit(hooks,SelectionEvent::Arrow);
        // Original recurses until the current touch cannot extend the path.
        // This loop preserves its event order without consuming native stack.
    }
}
extern "C" void dr_update_dimming(const SelectionState* s,std::uint8_t dimmed[36]) {
    const RuleTile* path[36];
    for(std::size_t i=0;i<s->path_length;++i) path[i]=&s->tiles[s->path[i]].rule;
    for(int i=0;i<36;++i) dimmed[i]=!dr_can_match(&s->tiles[i].rule,path,s->path_length,true);
}
