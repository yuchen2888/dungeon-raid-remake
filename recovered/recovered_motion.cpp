#include "recovered_motion.hpp"
#include <cmath>
using namespace dungeonraid;
namespace {
float length(Point p) {return std::sqrt(p.x*p.x+p.y*p.y);}
void emit(const MotionHooks* h,MotionEventKind k,int i=0) {if(h->event)h->event(h->context,k,i);}
Point target(const MotionHooks* h,int kind,int i) {Point p;h->target(h->context,kind,i,&p);return p;}
}
extern "C" void dr_initialise_token(TokenMotion* t,MatchState* m,std::uint32_t tile,
    int reward,const Point* position,int incoming,const MotionHooks* h) {
    const auto& source=m->stroke->selection.tiles[tile];const auto& potion=m->preview->potions[tile];
    emit(h,MotionEventKind::CopyTile,static_cast<int>(tile));t->position=source.geometry.center;
    emit(h,MotionEventKind::WhiteColour);t->active=1;t->reward_type=reward;t->linked_tile=-1;
    if(position)t->position=*position;
    t->token_type=0;
    if(source.rule.type==0) {
        if(potion.flag_232) {
            t->token_type=1;t->target_or_amount=h->choose_special(h->context,t);
            if(t->target_or_amount<0) {t->active=0;return;}
        } else if(potion.flag_233)t->token_type=2;
    } else if(incoming==3)t->token_type=3;
    t->direction.x=dr_random_float(&m->random,-.1f,.1f,0);
    t->direction.y=dr_random_float(&m->random,-.1f,.1f,0);
    if(t->direction.x==0 && t->direction.y==0)t->direction.x=.1f;
    else {
        const float distance=length(t->direction);
        t->direction.x=(t->direction.x/distance)*.1f;
        t->direction.y=(t->direction.y/distance)*.1f;
    }
    t->speed=dr_random_float(&m->random,6.0f,7.0f,0);t->progress=0;
    t->acceleration=dr_random_float(&m->random,1.0f,1.35f,0);
    const Point destination=target(h,0,t->token_type==3?0:reward);
    t->initial_distance=length({destination.x-t->position.x,destination.y-t->position.y});
    if(reward==1 && incoming!=3) {
        emit(h,MotionEventKind::XPVisual);
        t->speed=dr_random_float(&m->random,4.0f,6.0f,0);
    } else if(reward!=source.rule.type) {   // Tile::GetTileUV 0x3d480: the picture, RandI(0, 7, stream 0) (T040-N3)
        emit(h,MotionEventKind::TileVisual,reward);(void)dr_random_int(&m->random,0,7,0);
    }
}
extern "C" void dr_process_token(TokenMotion* t,const StrokeState* s,float dt,const MotionHooks* h) {
    Point destination;
    if(t->linked_tile>=0)destination=s->selection.tiles[t->linked_tile].geometry.center;
    else destination=target(h,t->token_type==1?1:0,t->token_type==1?t->target_or_amount:(t->token_type==3?0:t->reward_type));
    Point delta{destination.x-t->position.x,destination.y-t->position.y};
    const float distance=length(delta);delta.x=delta.x/distance;delta.y=delta.y/distance;
    t->progress=t->progress+dt*t->acceleration;
    float step;
    if(t->progress>1.0f) {
        step=(t->progress*t->speed)*dt;delta.x=delta.x*step;delta.y=delta.y*step;
    } else {
        step=dt*t->speed;const float remaining=1.0f-t->progress;
        delta.x=t->progress*(step*delta.x)+(step*t->direction.x)*remaining;
        delta.y=t->progress*(step*delta.y)+(step*t->direction.y)*remaining;
    }
    if(step>distance) {t->active=0;return;}
    t->position.x=t->position.x+delta.x;t->position.y=t->position.y+delta.y;
    const float ratio=distance/t->initial_distance;
    const float scale=ratio>=1.0f?1.0f:(.2f>=ratio?.2f:ratio);
    t->scale={scale,scale};
}
extern "C" bool dr_process_reward_tokens(TokenMotion* tokens,std::uint32_t* pending,
    ResourceState* r,float dt,const MotionHooks* motion,const ResourceHooks* resources,
    const std::uint8_t menus[3]) {
    if(*pending==0)return true;
    std::uint32_t last=0;
    for(std::uint32_t i=0;i<*pending;++i) {
        auto& t=tokens[i];if(!t.active)continue;
        dr_process_token(&t,r->match->stroke,dt,motion);
        if(t.active) {last=i+1;continue;}
        if(t.linked_tile<0) {
            dr_add_resource(r,t.reward_type,t.token_type,t.target_or_amount,resources);
            if(menus[0] || menus[1] || menus[2] || r->health==0)return false;
        } else if(resources && resources->event) {
            const ResourceEvent event{ResourceEventKind::Sound,2,0,0,0};
            resources->event(resources->context,&event);
        }
    }
    *pending=last;return true;
}
extern "C" void dr_token_set_target_tile(TokenMotion* t,const StrokeState* s,std::int32_t tile) {
    t->linked_tile=tile;
    if(tile<0)return;
    const Point centre=s->selection.tiles[tile].geometry.center;
    const float dx=centre.x-t->position.x,dy=centre.y-t->position.y;
    t->initial_distance=std::sqrt(dx*dx+dy*dy);
}
