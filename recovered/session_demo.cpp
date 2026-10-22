#include "recovered_session.hpp"
#include "recovered_tokens.hpp"
#include <cstdio>
#include <cstdlib>
#include <vector>
using namespace dungeonraid;
// Headless source-only example: one native session plays whole games by itself -- no original instruction,
// no test harness. The embedding does what a renderer would: the board layout, the touch (the
// longest of a few random paths that follow the game's linking rule, or a ready skill's button), the menu buttons
// (options, then confirm) and the layout targets of flying tokens (demonstration constants). Each game runs until
// the game-over screen or a turn limit; the games start as the main menu's new game, tutorial and challenge in
// turn (dr_session_start_game, on the session's own class roster), through the setup screen (a random name, Start) and
// the story screen; the first game quits at turn 40 and continues
// from its save (dr_session_continue_game). DEMO_TRACE=1 prints every turn.
namespace {
struct Demo { long events=0; int menus[3]{},skills_used=0,continued=0; };
void event(void* c,SessionSource source,const void* e) {
    auto& d=*static_cast<Demo*>(c);++d.events;
    if(source==SessionSource::Skill && static_cast<const SkillEvent*>(e)->kind==SkillEventKind::UpdateSkills)++d.skills_used;
}
void target(void*,std::int32_t kind,std::int32_t index,Point* p) {*p=kind?Point{0.15f+0.2f*index,0.12f}:Point{0.2f*index,0.05f};}
void token_start(void*,std::int32_t,Point* p) {*p=Point{0.5f,0.5f};}
std::uint32_t seed=1;
int next(int n) {seed=seed*1103515245u+12345u;return static_cast<int>((seed>>16)%static_cast<std::uint32_t>(n));}
// The longest of a few random paths that follow the game's own rule (Tile::CanMatchType: dr_can_match, as
// UpdateDimming), from every start tile; none selectable: shorter than three.
std::vector<int> pick_path(const SelectionState& s) {
    std::vector<int> best;
    for(int start=0;start<36;++start)for(int tries=0;tries<4;++tries) {
        if(s.tiles[start].rule.flag_255)continue;
        std::vector<int> path{start};const RuleTile* rules[36]{&s.tiles[start].rule};
        while(path.size()<12) {
            std::vector<int> options;const int x=path.back()%6,y=path.back()/6;
            for(int ny=y-1;ny<=y+1;++ny)for(int nx=x-1;nx<=x+1;++nx) {
                const int n=ny*6+nx;
                if(nx<0||nx>5||ny<0||ny>5||n==path.back())continue;
                bool used=false;for(int p:path)used|=p==n;
                if(!used && !s.tiles[n].rule.flag_255 && dr_can_match(&s.tiles[n].rule,rules,path.size(),true))options.push_back(n);
            }
            if(options.empty())break;
            const int n=options[next(static_cast<int>(options.size()))];rules[path.size()]=&s.tiles[n].rule;path.push_back(n);
        }
        if(path.size()>best.size())best=path;
    }
    return best;
}
}
int main() {
    Demo demo;const SessionHost host{&demo,event,target,token_start};
    int ended=0,total_turns=0;long total_frames=0;
    for(int game=0;game<3;++game) {
        Session* s=dr_session_create(&host,1);SessionObjects o=dr_session_objects(s);
        auto& sel=o.stroke->selection;sel.geometry.pitch=1.0f/6;sel.half_spacing=1.0f/12;
        for(int k=0;k<4;++k){sel.character.flaws[k]=255;o.match->perks[k]=255;}
        const std::uint32_t seed=20261020u+static_cast<std::uint32_t>(game);
        dr_session_start_game(s,game,seed);
        // the setup screen: a random name, a difficulty (a challenge: the mode), Start, then the story screen's Continue
        dr_session_setup_random_name(s);
        if(game==2)dr_session_setup_mode(s,1);else dr_session_setup_difficulty(s,1);
        if(!dr_session_setup_start(s,seed)) {std::printf("game %d: the setup screen did not start\n",game);return 1;}
        dr_session_intro_done(s);
        o=dr_session_objects(s);std::printf("game %d: %s\n",game,reinterpret_cast<const char*>(o.name));
        int turns=0;long frames=0;bool over=false;
        while(!over && turns<400) {
            if(game==0 && turns==40) {   // quit and continue from the saved game (the end of the last turn saved it)
                o=dr_session_objects(s);const int before=o.resources->xp+o.resources->total_xp;
                if(dr_session_continue_game(s,777u)) {
                    o=dr_session_objects(s);++demo.continued;
                    std::printf("game 0: continued at turn %d from a %d-byte save (xp %d before, %d after)\n",o.path->turn,o.end->flag_146d0,
                                before,o.resources->xp+o.resources->total_xp);
                }
            }
            o=dr_session_objects(s);
            struct Step { int phase; Point touch; int button; };   // touch phase, position, skill button under it
            std::vector<Step> script;
            int ready=-1;
            for(int i=0;i<o.resources->skill_count;++i)if(o.resources->skill_current[i]==o.resources->skill_max[i])ready=i;
            const auto path=pick_path(o.stroke->selection);
            if(ready>=0 && next(3)==0)script={{1,Point{5,5},ready},{2,Point{5,5},ready}};   // a ready skill: press and release its button
            else if(path.size()>=3) {
                for(int i:path)script.push_back({1,o.stroke->selection.tiles[i].geometry.center,-1});
                script.push_back({2,o.stroke->selection.tiles[path.back()].geometry.center,-1});
            }
            std::vector<std::pair<int,int>> menu_plan;bool menu_seen=false;
            for(int frame=0;frame<5000;++frame) {
                o=dr_session_objects(s);int phase=0;Point touch{0.5f,0.9f};*o.menu_button=-1;*o.skill_button=-1;
                if(frame<static_cast<int>(script.size()))phase=script[frame].phase,touch=script[frame].touch,*o.skill_button=script[frame].button;
                if(o.screens->menus[0]) {   // the FoldoutMenu: after its animation, choose (two on the level-up menu), confirm
                    const MenuState& m=*o.menu;
                    if(!menu_seen){menu_seen=true;++demo.menus[m.type];}
                    if(menu_plan.empty() && m.timer<0) {
                        if(m.first==-1 || (m.type==0 && m.second==-1)) {
                            const int b=m.first==14?15:14;menu_plan={{0,-1},{1,b},{2,b}};
                        } else menu_plan={{0,-1},{1,7},{2,7}};
                    }
                    if(!menu_plan.empty()){phase=menu_plan.front().first;*o.menu_button=menu_plan.front().second;menu_plan.erase(menu_plan.begin());}
                } else menu_seen=false;
                const FrameRoute route=dr_session_frame(s,1.0f/60,phase,touch);++frames;
                o=dr_session_objects(s);
                if(route==FrameRoute::Ended || o.end->game_over_screen){over=true;break;}
                if(frame>=static_cast<int>(script.size()) && o.path->input_ready && o.damage->phase==0 && !o.falling_count &&
                   !dr_token_queue_counters(o.tokens)->pending && !o.screens->menus[0])break;
            }
            if(std::getenv("DEMO_TRACE")) {o=dr_session_objects(s);std::printf("turn %d path %zu type %d: xp %d gold %d up %d health %d level %d pending %u\n",turns,path.size(),
                path.empty()?-1:o.stroke->selection.tiles[path[0]].rule.type,o.resources->xp,o.resources->gold,o.resources->up,o.resources->health,o.resources->level,
                dr_token_queue_counters(o.tokens)->pending);}
            ++turns;
        }
        o=dr_session_objects(s);
        std::printf("game %d: %s after %d turns, %ld frames; level %d, health %d/%d, gold %d, skills %d\n",game,
                    over?"ended":"stopped",turns,frames,o.resources->level,o.resources->health,o.resources->health_max,
                    o.resources->gold,o.resources->skill_count);
        ended+=over;total_turns+=turns;total_frames+=frames;dr_session_destroy(s);
    }
    std::printf("%d games, %d ended, %d turns, %ld frames, %ld events; menus opened: level-up %d, shop %d, upgrade %d; skills used %d; continued %d\n",
                3,ended,total_turns,total_frames,demo.events,demo.menus[0],demo.menus[1],demo.menus[2],demo.skills_used,demo.continued);
    return ended>0 && demo.menus[0]>0 && demo.menus[1]>0 && demo.skills_used>0 && demo.continued>0 ? 0 : 1;
}
