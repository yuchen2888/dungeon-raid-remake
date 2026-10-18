#include "recovered_preview.hpp"
#include "recovered_rune.hpp"
#include "recovered_tokens.hpp"
#include "recovered_motion.hpp"
#include "recovered_path.hpp"
#include "recovered_encounters.hpp"
#include <algorithm>
#include <cstdio>
#include <vector>
using namespace dungeonraid;
// Headless source-only example. UI target coordinates are demonstration inputs.
struct Demo {
    StrokeState stroke{}; ResourcePreviewState preview{}; RuneState rune{1,0,0};
    MatchState match{}; ResourceState resources{}; PathState path{}; PathHooks path_hooks{}; TokenQueue* queue=nullptr;
    SelectionHooks selection_hooks{}; MatchHooks match_hooks{}; TokenHooks token_hooks{};
    MotionHooks motion_hooks{}; ResourceHooks resource_hooks{};
    RefillState refill{}; GenerationState generation{};
    RefillHooks refill_hooks{}; GenerationHooks generation_hooks{}; EncounterHooks encounter_hooks{};
    std::vector<int> moving;
    std::vector<TokenMotion> tokens; std::uint8_t menus[3]{};
    int gold_preview=0,match_requests=0,last_match=-1; bool needs_refill=false;
};
void path_event(void* context,const RoundEvent* e) {
    auto& d=*static_cast<Demo*>(context);
    if(e->kind==BattleEvent::MoveMatchedTiles) {
        d.needs_refill=true;dr_move_matched_tiles(&d.refill,&d.refill_hooks);
    }
}
void refill_event(void* context,RefillEventKind kind,int i,int j) {
    auto& d=*static_cast<Demo*>(context);
    if(kind==RefillEventKind::Swap)std::swap(d.generation.tiles[i],d.generation.tiles[j]);
    if(kind==RefillEventKind::AppendMoving)d.moving.push_back(i);
    if(kind==RefillEventKind::Randomise)dr_randomise_tile(&d.generation,i,&d.generation_hooks);
    if(kind==RefillEventKind::Stab)dr_stab(&d.generation,i,&d.encounter_hooks);
}
void generation_event(void* context,const GenerationEvent* e) {
    auto& d=*static_cast<Demo*>(context);
    if(e->kind==GenerationEventKind::JumpDown)dr_jump_down(&d.generation,e->tile,&d.encounter_hooks);
}
void encounter_event(void*,const EncounterEvent*) {} // Rendering/end-game boundary; no death in this fixture.
void resource_event(void* context,const ResourceEvent* e) {
    auto& d=*static_cast<Demo*>(context);
    if(e->kind==ResourceEventKind::Menu)d.menus[e->a]=1;
    if(e->kind==ResourceEventKind::GoldBar)std::printf("金币实际入账：%d\n",e->a);
}
void target(void*,int kind,int index,Point* out) {*out={.1f+index*.12f,kind==0?.08f:1.4f};}
int choose_special(void*,TokenMotion*) {return -1;} // Not exercised by coin demo.
void motion_event(void*,MotionEventKind,int) {} // Renderer boundary.
void token_event(void* context,const TokenEvent* e) {
    auto& d=*static_cast<Demo*>(context);
    if(e->kind==TokenEventKind::Allocate)d.tokens.emplace_back();
    if(e->kind==TokenEventKind::Initialise) {
        auto& t=d.tokens[e->index];t.scale={1,1};t.target_or_amount=-1;
        const Point* override=e->c>=0?&d.stroke.selection.tiles[e->c].geometry.center:nullptr;
        dr_initialise_token(&t,&d.match,e->a,e->b,override,e->d,&d.motion_hooks);
    }
}
void match_event(void* context,const MatchEvent* e) {
    auto& d=*static_cast<Demo*>(context);
    if(e->kind==MatchEventKind::Token)dr_enqueue_token(d.queue,e->tile,e->a,e->b!=0,e->c,&d.token_hooks);
}
void selection_event(void* context,SelectionEvent kind,int index,int value,int) {
    auto& d=*static_cast<Demo*>(context);
    if(kind==SelectionEvent::ResourceShadows)dr_preview_resources(&d.stroke,&d.preview,&d.selection_hooks);
    if(kind==SelectionEvent::GoldShadow)d.gold_preview=value;
    if(kind==SelectionEvent::ProcessRune)dr_process_rune(&d.stroke,&d.rune,value!=0,&d.selection_hooks);
    if(kind==SelectionEvent::RuneMatchTile) {
        ++d.match_requests;d.last_match=index;dr_match_tile(&d.match,index,value,&d.match_hooks);
    }
}
int main() {
    Demo d;d.selection_hooks={&d,selection_event};d.match_hooks={&d,match_event};
    d.token_hooks={&d,token_event};d.motion_hooks={&d,motion_event,target,choose_special};d.resource_hooks={&d,resource_event};
    d.match.stroke=&d.stroke;d.match.preview=&d.preview;d.resources.match=&d.match;
    d.resources.health=d.resources.health_max=30;
    for(auto& seed:d.match.random.seeds)seed=123456;
    for(auto& perk:d.match.perks)perk=255;
    d.queue=dr_token_queue_create(&d.match);d.path.match=&d.match;d.path.queue=d.queue;d.path.input_ready=1;
    d.path_hooks={&d,path_event,&d.match_hooks,&d.token_hooks};auto& s=d.stroke.selection;
    d.path.turn=1;d.refill.path=&d.path;d.generation.refill=&d.refill;d.generation.resources=&d.resources;
    d.generation.time_to_promotion=20;d.generation.promotion_enabled=1;
    d.refill_hooks={&d,refill_event};d.generation_hooks={&d,generation_event};d.encounter_hooks={&d,encounter_event,&d.refill_hooks};
    s.geometry.pitch=1.0f/6.0f;s.half_spacing=s.geometry.pitch/2;
    for(auto& flaw:s.character.flaws)flaw=255;
    d.preview.shield_value=1;
    for(int i=0;i<36;++i) {
        auto& t=s.tiles[i];t.rule.type=2;t.rule.special_type=3;t.rule.x=i%6;t.rule.y=i/6;
        t.geometry={{(i%6+.5f)*s.geometry.pitch,.246875f+(i/6+.5f)*s.geometry.pitch},.075f};
        t.resting_position=t.geometry.center;t.size=.15f;s.geometry.tiles[i]=t.geometry;
        d.refill.falling[i].speed=1;
    }
    std::puts("恢复源码独立演示：无原版二进制、无模拟器、无界面。\n范围：整条金币路径及符文圈内消除 → 原规则生成与下落补位 → 奖励移动和入账。");
    const int perimeter[]={0,1,2,8,14,13,12,6};
    for(int index:perimeter) {
        dr_reset_rune_preview(&d.rune);s.touch=s.tiles[index].geometry.center;dr_update_stroke(&d.stroke,&d.selection_hooks);
    }
    std::printf("圈选 %zu 格，圈内高亮 %u 格，金币预览 %d（尚未入账）\n",s.path_length,d.rune.highlight_count_164a0,d.gold_preview);
    if(s.path_length!=8 || d.rune.highlight_count_164a0!=1 || d.gold_preview!=18)return 1;
    dr_reset_rune_preview(&d.rune);const auto route=dr_prepare_release(&d.stroke,&d.selection_hooks);
    if(route!=ReleaseRoute::MatchPath || d.match_requests!=1 || d.last_match!=7 || !s.tiles[7].rule.matched)return 1;
    dr_commit_path(&d.path,s.path,s.path_length,nullptr,0,&d.path_hooks);
    int matched=0;for(const auto& tile:s.tiles)matched+=tile.rule.matched!=0;
    if(matched!=0 || d.generation.generated_count!=9 || !d.needs_refill || d.path.input_ready)return 1;
    auto counters=*dr_token_queue_counters(d.queue);
    std::printf("松手：周边 8 格与圈内 1 格均已消除，待处理奖励 %u，当前金币 %d\n",counters.pending,d.resources.gold);
    if(counters.pending!=9 || d.resources.gold!=0)return 1;
    int frames=0;
    while((counters.pending || !d.moving.empty()) && frames<180) {
        for(auto it=d.moving.begin();it!=d.moving.end();) {
            dr_process_falling_tile(&d.refill,*it,1.0f/60.0f);
            if(!d.refill.falling[*it].moving)it=d.moving.erase(it);else ++it;
        }
        if(!dr_process_reward_tokens(d.tokens.data(),&counters.pending,&d.resources,1.0f/60.0f,&d.motion_hooks,&d.resource_hooks,d.menus))return 1;
        ++frames;
    }
    dr_token_queue_restore(d.queue,&counters);
    if(counters.pending || !d.moving.empty() || d.resources.gold!=18)return 1;
    for(int i=0;i<36;++i) {
        const auto& t=s.tiles[i];if(t.rule.matched || t.rule.x!=i%6 || t.rule.y!=i/6 || t.geometry.center.y!=t.resting_position.y)return 1;
    }
    dr_process_reward_tokens(d.tokens.data(),&counters.pending,&d.resources,1.0f/60.0f,&d.motion_hooks,&d.resource_hooks,d.menus);
    if(d.resources.gold!=18)return 1;
    std::printf("经过 %d 帧，奖励到账且所有方块落定；金币 0 → 18，额外推进不重复入账。\n",frames);
    std::printf("棋盘恢复为 36 格，按原规则补入 %d 格，其中敌人 %d 格。\n",d.generation.generated_count,d.generation.generated_enemies);
    std::puts("此处停在敌人阶段之前；完整回合、下一回合输入与手机画面仍待接通。");
    dr_token_queue_destroy(d.queue);return 0;
}
