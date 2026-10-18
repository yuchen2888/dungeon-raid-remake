#include "recovered_rune.hpp"
#include <cstdlib>
using namespace dungeonraid;
namespace {
void emit(const SelectionHooks* h,SelectionEvent event,int index,int a,int b=0) {
    if(h && h->event)h->event(h->context,event,index,a,b);
}
}
extern "C" void dr_reset_rune_preview(RuneState* rune) {rune->highlight_count_164a0=0;}
extern "C" void dr_process_rune(StrokeState* state,RuneState* rune,bool commit,
                                 const SelectionHooks* hooks) {
    auto& s=state->selection;
    if(!rune->enabled_16491)return;
    if(s.path_length<=3) {rune->highlight_count_164a0=0;return;}
    const auto& first=s.tiles[s.path[0]].rule;
    const auto& last=s.tiles[s.path[s.path_length-1]].rule;
    if(std::abs(first.x-last.x)>1 || std::abs(first.y-last.y)>1)return;
    std::uint32_t matched=0;
    // Original scans interior rows, x=0..4. x=5 is only the right-hand boundary.
    for(int y=1;y<5;++y) {
        bool inside=false;
        for(int x=0;x<5;++x) {
            const int index=y*6+x;auto& t=s.tiles[index];
            if(t.selected) {
                int px=-1,py=-1,nx=-1,ny=-1;bool found=false;
                for(std::size_t i=0;i<s.path_length;++i) {
                    const auto& v=s.tiles[s.path[i]].rule;
                    if(found) {nx=v.x;ny=v.y;break;}
                    if(v.x==x && v.y==y)found=true;
                    else {px=v.x;py=v.y;}
                }
                if(px<0) {const auto& v=s.tiles[s.path[s.path_length-1]].rule;px=v.x;py=v.y;}
                else if(nx<0) {const auto& v=s.tiles[s.path[0]].rule;nx=v.x;ny=v.y;}
                if(ny==y && py==y && nx!=x && px!=x)continue;
                if(ny>=y && py>=y)continue;
                if(ny<y && py<y)continue;
                inside=!inside;
                continue;
            }
            if(!inside)continue;
            bool right_boundary=false;
            for(int right=x+1;right<=5;++right)
                if(s.tiles[y*6+right].selected) {right_boundary=true;break;}
            if(!right_boundary)break;
            const int type=t.rule.type>5?5:t.rule.type;
            auto& count=state->resource_counts_164b0[type];
            count=static_cast<std::int32_t>(static_cast<std::uint32_t>(count)+1);
            if(commit) {
                if(t.rule.type==1 && t.rule.enemy_type!=0)continue;
                ++matched;
                emit(hooks,SelectionEvent::RuneMatchTile,index,5);
            } else {
                if(rune->highlight_count_164a0>=rune->allocated_highlights) {
                    emit(hooks,SelectionEvent::RuneAllocateHighlight,-1,static_cast<int>(rune->allocated_highlights));
                    ++rune->allocated_highlights;
                }
                emit(hooks,SelectionEvent::RuneHighlight,index,static_cast<int>(rune->highlight_count_164a0));
                ++rune->highlight_count_164a0;
            }
        }
    }
    if(commit && matched>0) {
        std::uint32_t fake=0;for(auto v:s.fake)if(v)++fake;
        const auto effective=static_cast<std::uint32_t>(s.path_length)-fake;
        if(matched>effective)emit(hooks,SelectionEvent::RuneAchievement,-1,58,100);
    }
}
