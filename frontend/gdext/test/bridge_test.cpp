#include "dr_bridge.hpp"
#include "recovered_tokens.hpp"
#include <cstdio>
#include <map>
using namespace dungeonraid;
using drfront::Blob;
using drfront::Bridge;
// Headless check of the front end's bridge (T050-A): what the Godot layer does, without Godot. One "app run" is
// one Bridge (one session for all its games, as the original's one Game object); "disk" is a map the stored
// blobs go to. Run 1 plays a new game for 30 turns and quits; run 2 restores the disk, continues from the saved
// game at the same turn and plays it to the game-over screen, then a tutorial and a challenge game on the same
// session; run 3 restores again and finds no saved game but the class records and scores. Touches are the rules'
// own linking paths, ready skills are pressed now and then, menus are chosen and confirmed through menu buttons.
namespace {
std::map<std::string,std::vector<std::uint8_t>> disk;
struct Tally { int menus[3]{},skills=0,turns=0,writes=0; };
void store(Bridge& b,Tally& t) {
    for(auto& blob:b.take_changed()) {
        ++t.writes;
        if(blob.key=="game" && blob.bytes.empty())disk.erase("game");else disk[blob.key]=blob.bytes;
    }
}
void restore(Bridge& b) {   // Game::Start's order
    if(disk.count("classes"))b.restore({"classes",disk["classes"]});
    for(int i=0;i<6;++i) {const std::string k="scores"+std::to_string(i);if(disk.count(k))b.restore({k,disk[k]});}
    if(disk.count("game"))b.restore({"game",disk["game"]});
    if(disk.count("spawn"))b.restore({"spawn",disk["spawn"]});
}
std::uint32_t seed=7;
int next(int n) {seed=seed*1103515245u+12345u;return static_cast<int>((seed>>16)%static_cast<std::uint32_t>(n));}
// One turn: a path or a ready skill, then frames until the board is idle; true when the game-over screen shows.
bool play_turn(Bridge& b,Tally& t) {
    SessionObjects o=b.objects();
    struct Step { int phase; Point touch; int skill; };
    std::vector<Step> script;
    int ready=-1;
    for(int i=0;i<o.resources->skill_count;++i)if(o.resources->skill_current[i]==o.resources->skill_max[i])ready=i;
    const auto path=drfront::pick_path(o.stroke->selection,seed);
    if(ready>=0 && next(3)==0) {script={{1,drfront::skill_target(ready),ready},{2,drfront::skill_target(ready),ready}};++t.skills;}
    else if(!path.empty()) {
        for(int i:path)script.push_back({1,o.stroke->selection.tiles[i].geometry.center,-1});
        script.push_back({2,o.stroke->selection.tiles[path.back()].geometry.center,-1});
    }
    std::vector<std::pair<int,int>> menu_plan;bool menu_seen=false;
    for(int frame=0;frame<5000;++frame) {
        o=b.objects();int phase=0,skill=-1,button=-1;Point touch{0.5f,1.45f};
        if(frame<static_cast<int>(script.size()))phase=script[frame].phase,touch=script[frame].touch,skill=script[frame].skill;
        if(o.screens->menus[0]) {
            const MenuState& m=*o.menu;
            if(!menu_seen){menu_seen=true;++t.menus[m.type];}
            if(menu_plan.empty() && m.timer<0) {
                if(m.first==-1 || (m.type==0 && m.second==-1)) {const int c=m.first==14?15:14;menu_plan={{0,-1},{1,c},{2,c}};}
                else menu_plan={{0,-1},{1,7},{2,7}};
            }
            if(!menu_plan.empty()){phase=menu_plan.front().first;button=menu_plan.front().second;menu_plan.erase(menu_plan.begin());}
        } else menu_seen=false;
        const FrameRoute route=b.frame(1.0f/60,phase,touch,skill,button);store(b,t);
        o=b.objects();
        if(route==FrameRoute::Ended || o.end->game_over_screen)return true;
        if(frame>=static_cast<int>(script.size()) && o.path->input_ready && o.damage->phase==0 && !o.falling_count &&
           !dr_token_queue_counters(o.tokens)->pending && !o.screens->menus[0])break;
    }
    ++t.turns;return false;
}
int failures=0;
void check(bool ok,const char* what) {std::printf("%s %s\n",ok?"ok  ":"FAIL",what);failures+=!ok;}
// The main menu's new game through the setup screen (T040-M3) and the story screen, as a player would click it.
void begin(Bridge& b,int kind,std::uint32_t game_seed) {
    b.new_game(kind,game_seed);
    const SessionObjects o=b.objects();
    check(o.screens->name_12c09 && o.setup->challenge==(kind==2),"setup screen opens");
    b.setup_random_name();
    check(o.setup->named && o.setup->length>0,"setup: a random name");
    check(kind==2?b.setup_mode(0):b.setup_difficulty(1),"setup: difficulty or mode button");
    check(!b.setup_select_class(5),"setup: a locked class is refused");
    check(b.setup_start(game_seed+1u) && !o.screens->name_12c09 && o.screens->intro_c3f0,"setup: start opens the story screen");
    b.intro_done();
    check(!o.screens->intro_c3f0 && o.path->turn==0,"story screen closes, the game begins");
}
}
int main() {
    Tally t;int turn_saved=-1;
    {   // run 1: a new game, 30 turns, quit
        Bridge b;restore(b);
        check(!b.has_save(),"run 1: no saved game on an empty disk");
        begin(b,0,20261021u);
        bool over=false;for(int i=0;i<30 && !over;++i)over=play_turn(b,t);
        check(!over,"run 1: still playing after 30 turns");
        turn_saved=b.objects().path->turn;
        check(disk.count("game") && !disk["game"].empty(),"run 1: the saved game is on disk");
        std::printf("     run 1: turn %d, level %d, health %d/%d, %zu-byte save\n",turn_saved,b.objects().resources->level,
                    b.objects().resources->health,b.objects().resources->health_max,disk.count("game")?disk["game"].size():0);
    }
    {   // run 2: continue, play to the end, then a tutorial and a challenge game on the same session
        Bridge b;restore(b);
        check(b.has_save(),"run 2: Continue is offered");
        check(b.continue_game(1234u),"run 2: the saved game continues");
        check(b.objects().path->turn==turn_saved,"run 2: at the turn it was saved");
        bool over=false;int turns=0;
        while(!over && turns<600){over=play_turn(b,t);++turns;}
        check(over,"run 2: the game reaches the game-over screen");
        std::printf("     run 2: game over at turn %d, level %d, gold %d, skills %d\n",b.objects().path->turn,b.objects().resources->level,
                    b.objects().resources->gold,b.objects().resources->skill_count);
        check(!disk.count("game"),"run 2: the saved game is deleted at the end");
        check(!b.has_save(),"run 2: Continue is gone");
        bool scores=false;for(auto& e:disk)scores|=e.first.compare(0,6,"scores")==0;
        check(scores,"run 2: a high-score table is on disk");
        check(disk.count("classes")!=0,"run 2: the class records are on disk");
        for(int kind=1;kind<=2;++kind) {
            b.leave_game_over();
            begin(b,kind,99u+static_cast<std::uint32_t>(kind));
            check(!b.objects().end->game_over_screen && b.objects().path->turn==0,kind==1?"run 2: the tutorial starts fresh":"run 2: the challenge starts fresh");
            if(b.objects().path->turn!=0)std::printf("     new game at turn %d\n",b.objects().path->turn);
            over=false;turns=0;while(!over && turns<60){over=play_turn(b,t);++turns;}
            check(over || turns==60,"run 2: the game plays");
        }
    }
    {   // run 3: start-up again
        Bridge b;restore(b);
        const bool save=b.has_save();
        int count=0;for(int i=0;i<6;++i)count+=b.objects().scores->count[i];
        check(!save || disk.count("game"),"run 3: Continue only with a saved game on disk");
        check(count>0,"run 3: the high scores came back");
    }
    std::printf("turns %d, menus: level-up %d, shop %d, upgrade %d; skills pressed %d; blob writes %d\n",t.turns,t.menus[0],t.menus[1],
                t.menus[2],t.skills,t.writes);
    check(t.menus[0]>0 && t.menus[1]>0,"menus opened (level-up and shop)");
    check(t.skills>0,"skills pressed");
    std::printf("%s\n",failures?"bridge_test: FAILED":"bridge_test: passed");
    return failures?1:0;
}
