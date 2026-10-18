#include "recovered_preview.hpp"
#include "recovered_rune.hpp"
#include <cstdio>
using namespace dungeonraid;
// Headless integration example, not a game. No original binary or emulator.
struct Demo {
    StrokeState stroke{};
    ResourcePreviewState preview{};
    RuneState rune{1,0,0};
    SelectionHooks hooks{};
    int gold=0, match_requests=0, last_match=-1;
};
void event(void* context,SelectionEvent kind,std::int32_t index,std::int32_t value,std::int32_t) {
    auto& d=*static_cast<Demo*>(context);
    if(kind==SelectionEvent::ResourceShadows)dr_preview_resources(&d.stroke,&d.preview,&d.hooks);
    if(kind==SelectionEvent::GoldShadow)d.gold=value;
    if(kind==SelectionEvent::ProcessRune)dr_process_rune(&d.stroke,&d.rune,value!=0,&d.hooks);
    if(kind==SelectionEvent::RuneMatchTile) {
        ++d.match_requests;d.last_match=index; // Actual MatchTile is still unresolved.
        std::printf("rune_match_request tile=%d reward_type=%d (not executed)\n",index,value);
    }
}
int main() {
    Demo d;d.hooks={&d,event};auto& s=d.stroke.selection;
    s.geometry.pitch=1.0f/6.0f;s.half_spacing=s.geometry.pitch/2;
    for(auto& flaw:s.character.flaws)flaw=255;
    d.preview.shield_value=1;
    for(int i=0;i<36;++i) {
        auto& t=s.tiles[i];t.rule.type=2;t.rule.x=i%6;t.rule.y=i/6;
        t.geometry={{(i%6+.5f)*s.geometry.pitch,.246875f+(i/6+.5f)*s.geometry.pitch},.075f};
        t.resting_position=t.geometry.center;t.size=.15f;s.geometry.tiles[i]=t.geometry;
    }
    std::puts("Source-only stroke/rune/preview example; actual MatchTile and turn effects are unresolved.");
    for(int i=0;i<3;++i) {
        dr_reset_rune_preview(&d.rune);
        s.touch=s.tiles[i].geometry.center;dr_update_stroke(&d.stroke,&d.hooks);
        std::printf("touch=%d path=%zu gold_preview=%d\n",i,s.path_length,d.gold);
    }
    const auto route=dr_release_route(&s);
    std::printf("release_route=%d (1=MatchPath; not executed)\n",static_cast<int>(route));
    if(s.path_length!=3 || route!=ReleaseRoute::MatchPath || d.gold!=6)return 1;
    dr_cancel_stroke(&d.stroke,&d.hooks);
    std::printf("cancel path=%zu gold_preview=%d (-1=hidden)\n",s.path_length,d.gold);
    if(s.path_length!=0 || d.gold!=-1)return 1;
    const int perimeter[]={0,1,2,8,14,13,12,6};
    for(int index:perimeter) {
        dr_reset_rune_preview(&d.rune);s.touch=s.tiles[index].geometry.center;
        dr_update_stroke(&d.stroke,&d.hooks);
    }
    std::printf("closed_path=%zu inside_highlights=%u gold_preview=%d\n",s.path_length,d.rune.highlight_count_164a0,d.gold);
    if(s.path_length!=8 || d.rune.highlight_count_164a0!=1 || d.gold!=18)return 1;
    dr_reset_rune_preview(&d.rune);
    const auto prepared=dr_prepare_release(&d.stroke,&d.hooks);
    if(prepared!=ReleaseRoute::MatchPath || d.match_requests!=1 || d.last_match!=7)return 1;
    for(const auto& tile:s.tiles)if(tile.selected)return 1;
    std::puts("release prefix passed; path settlement and resource grants have NOT run.");
    return 0;
}
