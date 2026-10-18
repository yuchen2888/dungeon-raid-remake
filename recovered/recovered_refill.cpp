#include "recovered_refill.hpp"
#include <utility>
using namespace dungeonraid;
extern "C" void dr_position_tile(RefillState* s,std::uint32_t i,int x,int y,bool target) {
    auto& board=s->path->match->stroke->selection;
    if(target) {
        s->falling[i].target=board.tiles[y*6+x].resting_position;
        s->falling[i].moving=1;
    } else if(y>=0) {
        board.tiles[i].geometry.center=board.tiles[y*6+x].resting_position;
    } else {
        auto& p=board.tiles[i].geometry.center;
        // Literal bit patterns 0x3e7ccccd and 0x3b4ccccd respectively.
        p.y=(board.geometry.vertical_offset+.246875f)+board.geometry.pitch*(float(y)+.5f);
        p.x=board.geometry.pitch*(float(x)+.5f)+.003125f;
    }
}
extern "C" void dr_process_falling_tile(RefillState* s,std::uint32_t i,float dt) {
    auto& f=s->falling[i];auto& p=s->path->match->stroke->selection.tiles[i].geometry.center;
    f.speed+=dt*f.acceleration;p.y+=dt*f.speed;
    if(!(p.y<f.target.y)) {p.y=f.target.y;f.moving=0;f.speed=1.f;}
}
extern "C" void dr_process_falling_list(RefillState* s,std::int32_t* indices,std::uint32_t* count,float dt) {
    std::uint32_t kept=0;
    for(std::uint32_t j=0;j<*count;++j) {
        const int i=indices[j];dr_process_falling_tile(s,i,dt);
        if(s->falling[i].moving)indices[kept++]=i;
    }
    *count=kept;
}
static void emit(const RefillHooks* h,RefillEventKind kind,int i,int other=0) {
    if(h && h->event)h->event(h->context,kind,i,other);
}
static void swap_storage(RefillState* s,int source,int i,const RefillHooks* h) {
    auto& p=*s->path;auto& m=*p.match;auto& b=m.stroke->selection;
    const auto a=b.tiles[source].resting_position,z=b.tiles[i].resting_position;
    std::swap(b.tiles[source],b.tiles[i]);
    b.tiles[source].resting_position=a;b.tiles[i].resting_position=z;
    std::swap(p.combat[source],p.combat[i]);
    std::swap(m.preview->potions[source],m.preview->potions[i]);
    std::swap(m.flag_25d[source],m.flag_25d[i]);
    std::swap(s->falling[source],s->falling[i]);
    emit(h,RefillEventKind::Swap,source,i);
}
extern "C" void dr_swap_tiles(RefillState* s,int x1,int y1,int x2,int y2,const RefillHooks* h) {
    const int a=y1*6+x1,b=y2*6+x2;auto& tiles=s->path->match->stroke->selection.tiles;
    dr_position_tile(s,b,x1,y1,false);dr_position_tile(s,a,x2,y2,false);
    dr_position_tile(s,b,x1,y1,true);dr_position_tile(s,a,x2,y2,true);
    tiles[b].rule.x=x1;tiles[b].rule.y=y1;tiles[a].rule.x=x2;tiles[a].rule.y=y2;
    swap_storage(s,b,a,h);
}
extern "C" void dr_move_matched_tiles(RefillState* s,const RefillHooks* h) {
    auto& p=*s->path;auto& m=*p.match;auto& b=m.stroke->selection;
    bool stab[36]{};
    for(int x=0;x<6;++x) {
        int spawn_row=0;
        for(int y=5;y>=0;--y) {
            const int i=y*6+x;if(!b.tiles[i].rule.matched)continue;
            int row=y-1;while(row>=0 && b.tiles[row*6+x].rule.matched)--row;
            if(row>=0) {
                const int source=row*6+x;
                dr_position_tile(s,source,x,y,true);s->falling[source].acceleration=float(y+1)*.8f;
                b.tiles[source].rule.x=x;b.tiles[source].rule.y=y;
                b.tiles[i].rule.x=x;b.tiles[i].rule.y=row;
                // resting_position belongs to Game's fixed coordinate table,
                // unlike the actual Tile fields that std::swap exchanged.
                swap_storage(s,source,i,h);
                emit(h,RefillEventKind::AppendMoving,i);
                if(b.tiles[i].rule.type==1 && b.tiles[i].rule.enemy_type==31)stab[i]=true;
            } else {
                dr_position_tile(s,i,x,--spawn_row,false);dr_position_tile(s,i,x,y,true);
                s->falling[i].acceleration=float(y+1)*.8f;
                emit(h,RefillEventKind::AppendMoving,i);
                b.tiles[i].rule.matched=0;p.combat[i].attack_flag=1;
                emit(h,RefillEventKind::Randomise,i);
            }
        }
    }
    for(int i=0;i<36;++i)if(stab[i])emit(h,RefillEventKind::Stab,i);
}
