#include "gameover.hpp"
#include "setup.hpp"
#include "recovered_turn.hpp"
#include <cstring>
#include <string>
using namespace dungeonraid;
namespace drui {
namespace {
float clampf(float v,float lo,float hi) {if(v>=hi)return hi;return v<=lo?lo:v;}                    // 0x1b73c
float interpolate(float a,float b,float t) {const float x=a*t;const float y=(1.0f-t)*b;return x+y;}  // 0x1b800
std::uint8_t byte_of(float v) {return static_cast<std::uint8_t>(static_cast<std::int32_t>(v));}
void centre(Label& l) {const float w=l.scale.x*l.width;l.position.x=w*-0.5f+0.5f;}
void right_align(Label& l) {const float w=l.scale.x*l.width;l.position.x=0.850000024f-w;}
}
GameOverView::GameOverView(const Font* font):font_(font) {   // GameOverScreen::GameOverScreen 0x3143c
    black_.set_size(Point2{2.0f,2.0f});black_.position=Point2{0.5f,0.5f};
    tombstone_.set_size(Point2{0.278124988f,0.878125012f});tombstone_.position=Point2{0.501562476f,0.473437488f};
    tombstone_.set_alpha(0);tombstone_.set_uv(0.813476562f,0.66015625f,0.0869140625f,0.274414062f);tombstone_.rotation=-90.0f;
    title_.set_size(Point2{0.71875f,0.228125006f});title_.position=Point2{0.501562476f,0.473437488f};
    title_.set_uv(0.0712890625f,0.866210938f,0.224609375f,0.0712890625f);title_.set_alpha(0);
    for(int k=0;k<22;++k) {
        labels_.emplace_back(font_);
        Label& l=labels_.back();l.space_scale=2.0f;
        float extra=0.0f;
        if(k==0)l.scale=Point2{0.200000003f,0.200000003f};
        else {
            l.scale=Point2{0.150000006f,0.150000006f};
            if(k==1)extra=0.0175000001f;
            else if(k==2)extra=0.0350000001f;
            else if(k>=3 && k<=7)extra=0.0583333336f;
            else if(k==12)extra=0.198333323f;
            else extra=0.128333330f;
        }
        if(k<=12) {
            l.position.x=0.150000006f;
            const float y=static_cast<float>(k)*0.0700000003f+0.200000003f;l.position.y=y+extra;
        }
        if(k==10 || k==11) {   // the perks' and flaws' icons, right-aligned on their lines
            Quad* row=k==10?perks_:flaws_;
            for(int i=0;i<4;++i) {
                Quad& q=row[i];q.set_size(Point2{0.0612500012f,0.0612500012f});
                q.position.y=l.position.y-0.0306250006f;
                const float a=static_cast<float>(i)+0.5f;q.position.x=0.850000024f-a*0.0612500012f;
            }
        }
    }
    for(int i=0;i<36;++i) {   // (the glows' rotation: Rand(0, 360, stream 0) of the zeroed stream, 0)
        enemies_[i].set_size(Point2{0.0625f,0.0625f});glows_[i].set_size(Point2{0.09375f,0.09375f});
    }
}
void GameOverView::initialise(const Texts& t,const SessionObjects& o,bool win) {
    texts_=&t;win_=win;
    tombstone_.set_alpha(0);title_.set_alpha(0);
    black_.set_colour(win?Colour{64,226,0,0}:Colour{182,42,15,0});
    const bool crossings=o.stroke->record_14aed && o.stroke->mode_14ae8==1;
    const char* headings[]={"over.turn","over.level",crossings?"over.average":"over.xp",crossings?"over.max":"over.gold",
                            crossings?"over.pretzels":"over.upgrades","over.items","over.skills","over.perks","over.flaws",
                            "over.score"};
    for(int k=3;k<=12;++k)labels_[static_cast<std::size_t>(k)].set_text(t.get(headings[k-3]).c_str());
    const std::string name(reinterpret_cast<const char*>(o.name),strnlen(reinterpret_cast<const char*>(o.name),17));
    labels_[0].set_text(name.c_str());centre(labels_[0]);
    const ClassProfile& c=o.classes[o.scroll->current];
    labels_[1].set_text(printf_string(t.get("over.class").c_str(),c.level,t.get("race.name",c.race).c_str(),
                                      t.get("class.name",c.class_type).c_str()).c_str());
    centre(labels_[1]);
    if(!o.stroke->record_14aed || o.stroke->mode_14ae8==3)labels_[2].set_text(t.get("difficulty.name",o.match->spawn_enabled_14ae0).c_str());
    else labels_[2].set_text(t.get("mode.name",o.stroke->mode_14ae8).c_str());
    centre(labels_[2]);
    for(auto& l:labels_){l.colour.a=255;l.update_colour();}
    for(int k=13;k<=20;++k) {   // the numbers' first text, on their headings' lines
        Label& l=labels_[static_cast<std::size_t>(k)];
        l.set_text(t.get("over.zero").c_str());right_align(l);
        l.position.y=labels_[static_cast<std::size_t>(k==20?12:k-8)].position.y;
    }
    for(int i=0;i<4;++i){perks_[i].set_alpha(255);flaws_[i].set_alpha(255);}
    for(int i=0;i<36;++i){enemies_[i].set_alpha(255);glows_[i].set_alpha(255);}
}
void GameOverView::init_icons(const SessionObjects& o,SkillView* skills) {
    skills_=skills;
    // The equipped items' icons (Game::GetItem(type)) and the skills' on their lines, right to left, drawn at 0.4.
    const float item_y=labels_[8].position.y/0.400000006f;
    for(int k=0;k<5;++k) {
        for(int i=0;i<5;++i) {
            const ItemRecord& r=o.items[i];
            if(r.type!=k)continue;
            Icon& icon=items_[k];icon=Icon();icon.set_icon(r.icon%20,r.icon/20,1024,0);   // Item::Initialise 0x264a8
        }
        items_[k].position.y=item_y-0.153125003f;
        const float n=static_cast<float>(5-k);items_[k].position.x=n*-0.153125003f+2.125f;
    }
    const std::int32_t count=o.resources->skill_count;
    const float skill_y=labels_[9].position.y/0.400000006f;
    for(std::int32_t i=0;i<count && i<4;++i) {
        SkillView& s=skills[i];
        s.icon.position.y=skill_y-0.153125003f;
        const float n=static_cast<float>(count-i);s.icon.position.x=n*-0.153125003f+2.125f;
    }
    // The class's perks and flaws (the class record's, the unused slots 255 left out).
    const ClassProfile& c=o.classes[o.scroll->current];
    std::int32_t perks=0,flaws=0;
    for(int i=0;i<4;++i) {
        Point2 a,b;
        if(c.perks[i]!=255){icon_coords(0,c.perks[i],0,a,b);perks_[perks++].set_uv(texels(a),texels(b));}
    }
    for(int i=0;i<4;++i) {
        Point2 a,b;
        if(c.flaws[i]!=255){icon_coords(0,c.flaws[i]+10,0,a,b);flaws_[flaws++].set_uv(texels(a),texels(b));}
    }
    // The enemies on the board by type (Game::GetEnemyCount of 0..32), in rows of up to 11 centred under the score,
    // the class's mortal enemy under its glow.
    std::vector<std::int32_t> types;
    for(std::int32_t type=0;type<=32;++type) {
        for(const auto& tile:o.stroke->selection.tiles)if(tile.rule.type==1 && tile.rule.enemy_type==type)types.push_back(type);
    }
    const float h=enemies_[0].size.y;
    const std::int32_t mortal=dr_mortal_enemy(c.race);
    std::int32_t left=static_cast<std::int32_t>(types.size()),row=1,index=0;
    while(left>0) {
        const std::int32_t n=left<=10?left:11;
        const float half=static_cast<float>(n)*0.5f;const float start=half*-0.0625f+0.5f;
        const float down=static_cast<float>(row)*h;
        for(std::int32_t j=0;j<n && index<36;++j,++index) {
            Point2 a,b;enemy_uv(types[static_cast<std::size_t>(index)],a,b);
            Quad& e=enemies_[index];Quad& g=glows_[index];
            e.set_uv(a,b);
            const float y=down+labels_[12].position.y;
            const float across=static_cast<float>(j)+0.5f;const float x=across*h+start;
            e.position=Point2{x,y};g.position=Point2{x,y};
            const std::int32_t type=types[static_cast<std::size_t>(index)];
            if(type!=0 && type==mortal)g.set_uv(Point2{0.0009765625f,0.904296875f},Point2{0.052734375f,0.9609375f});
            else g.set_uv(0.0f,0.0f,0.0f,0.0f);
        }
        left-=n;++row;
    }
}
void GameOverView::show_value(const SessionObjects& o,std::int32_t line,float value) {
    Label& l=labels_[static_cast<std::size_t>(line==12?20:line+10)];
    if(o.stroke->record_14aed && o.stroke->mode_14ae8==1 && line==5) {   // the crossing average, in tenths
        const float tenths=static_cast<float>(static_cast<std::int32_t>(value))/10.0f;
        l.set_text(printf_string(texts_->get("over.tenths").c_str(),static_cast<double>(tenths)).c_str());
    } else l.set_text(printf_string(texts_->get("over.int").c_str(),static_cast<std::int32_t>(value)).c_str());
    right_align(l);
    l.position.y=labels_[static_cast<std::size_t>(line)].position.y;
}
void GameOverView::process(const SessionObjects& o,const GameOverTally& before,std::int32_t state,std::int32_t phase,
                           std::int32_t ended_line,std::int32_t ended_value,float dt,SkillView* skills) {
    const GameOverTally& g=*o.game_over;
    float wait=before.wait;
    if(state>1 && phase==1 && before.previous_phase==0)wait=0.0f;   // a tap
    if(wait>0.0f){const float left=wait-dt;if(left>0.0f)return;}    // still pausing: nothing else this frame
    Quad& panel=win_?title_:tombstone_;
    switch(state) {
    case 0:   // the coloured screen and the panel fade in (over 2 s, squared)
        if(o.screens->game_over_state_cc1c!=0){black_.set_alpha(255);panel.set_alpha(255);}
        else {
            const float p=g.progress;const std::uint8_t a=byte_of(interpolate(255.0f,0.0f,p*p));
            black_.set_alpha(a);panel.set_alpha(a);
        }
        break;
    case 1:   // then turns black (the title fading with it)
        if(o.screens->game_over_state_cc1c==2){init_icons(o,skills);black_.set_colour(Colour{0,0,0,255});}
        else {
            const float p=g.progress;
            const std::uint8_t r=byte_of(interpolate(0.0f,win_?64.0f:182.0f,p));
            const std::uint8_t gr=byte_of(interpolate(0.0f,win_?226.0f:42.0f,p));
            const std::uint8_t b=byte_of(interpolate(0.0f,win_?0.0f:15.0f,p));
            black_.set_colour(Colour{r,gr,b,255});
            if(win_) {
                const float a=p*-255.0f+255.0f;
                title_.set_alpha(static_cast<std::uint8_t>(static_cast<std::uint32_t>(a)));
            }
        }
        break;
    case 2: {   // a counted line's number as it counts (its end once the line is done: the session's GameOverLine)
        const std::int32_t line=g.line;
        if(line<3 || line>12 || (line>=8 && line<=11))break;
        show_value(o,line,line==ended_line?static_cast<float>(ended_value):g.value);
        break;
    }
    case 3:   // everything fades out over the high-score screen (the icons and texts three times faster)
        if(o.end->game_over_screen) {
            const float p=g.progress;
            const std::uint8_t a=byte_of(interpolate(0.0f,255.0f,p));
            const std::uint8_t b=byte_of(interpolate(0.0f,255.0f,clampf(p*3.0f,0.0f,1.0f)));
            for(auto& l:labels_){l.colour.a=b;l.update_colour();}
            for(auto& icon:items_)for(auto& v:icon.v)v.colour[3]=b;
            for(std::int32_t i=0;i<o.resources->skill_count && i<4 && skills_;++i)for(auto& v:skills_[i].icon.v)v.colour[3]=b;
            for(int i=0;i<4;++i){perks_[i].set_alpha(b);flaws_[i].set_alpha(b);}
            for(int i=0;i<36;++i){enemies_[i].set_alpha(b);glows_[i].set_alpha(b);}
            black_.set_alpha(a);
        }
        break;
    default: break;
    }
}
void GameOverView::render(GL& gl,const SessionObjects& o) const {
    gl.bind_texture(NoTexture);black_.render(gl);
    const std::int32_t state=o.screens->game_over_state_cc1c;
    if(state<=1) {
        gl.load_identity();gl.bind_texture(Tiles);
        (win_?title_:tombstone_).render(gl);
        return;
    }
    const GameOverTally& g=*o.game_over;
    const std::int32_t line=g.line;
    if(line<0 || line>21 || (line>12 && line<21))return;
    const auto label=[&](int k){labels_[static_cast<std::size_t>(k)].render(gl);};
    // The lines shown so far, the current one last: a line passed shows all its icons.
    if(line==21) {
        gl.bind_texture(Tiles);
        const std::int32_t n=state!=2?g.enemies:g.shown[4];
        for(std::int32_t i=0;i<n && i<36;++i){glows_[i].render(gl);enemies_[i].render(gl);}
    }
    if(line>=12){label(12);label(20);}
    if(line>=11) {
        const std::int32_t n=line>=12?g.flaws:g.shown[3];
        label(11);
        for(std::int32_t i=0;i<n && i<4;++i){gl.bind_texture(Menus);flaws_[i].render(gl);}
    }
    if(line>=10) {
        const std::int32_t n=line>=11?g.perks:g.shown[2];
        label(10);
        for(std::int32_t i=0;i<n && i<4;++i){gl.bind_texture(Menus);perks_[i].render(gl);}
    }
    const std::int32_t count=o.resources->skill_count;
    if(line>=9) {
        const std::int32_t n=line>=10?count:g.shown[1];
        label(9);
        if(count>0 && skills_) {
            gl.push();gl.scale(0.400000006f,0.400000006f);
            for(std::int32_t i=0;i<n;++i){gl.bind_texture(Tiles);skills_[count-1-i].render(gl,false);}
            gl.pop();
        }
    }
    if(line>=8) {
        const std::int32_t n=line>=9?5:g.shown[0];
        label(8);
        gl.bind_texture(Icons);
        gl.push();gl.scale(0.400000006f,0.400000006f);
        for(std::int32_t i=0;i<n && i<5;++i)items_[4-i].render(gl,nullptr);
        gl.pop();
    }
    for(int k=7;k>=3;--k)if(line>=k){label(k);label(k+10);}
    if(line>=2)label(2);
    if(line>=1)label(1);
    label(0);
}
}
