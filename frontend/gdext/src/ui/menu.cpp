#include "menu.hpp"
#include "recovered_turn.hpp"
#include <cstdio>
#include <cstdlib>
using namespace dungeonraid;
namespace drui {
namespace {
constexpr float kOption[4][2]={{18.0f,33.0f},{18.0f,90.0f},{18.0f,147.0f},{18.0f,204.0f}};   // 0x1ead04, set at start-up
bool record_mode(const SessionObjects& o,std::int32_t mode) {return o.stroke->record_14aed && o.stroke->mode_14ae8==mode;}
// ItemUpgrade::GetFloatPrecision 0x2d078 / GetFloatValue 0x2d090: a value in quarters, with 0, 1 or 2 decimals.
int precision(std::int32_t v) {return (v&3)==0?0:((v&1)?2:1);}
double quarters(std::int32_t v) {return static_cast<double>(static_cast<float>(v)*0.25f);}
Point2 points(float x,float y) {return Point2{x/320.0f,y/320.0f};}   // GLfloat2::operator/(320)
}
// ---- Menu ---------------------------------------------------------------------------------------------------------
void MenuQuads::set_vertex(int i,float x,float y,float u,float w) {
    Vertex& p=v[static_cast<std::size_t>(i)];
    p.x=x/320.0f;p.y=y/320.0f;p.u=u*0.0009765625f;p.v=w*0.0009765625f;
}
void MenuQuads::set_quad(int q,Point2 at,Point2 uv,Point2 size,float sx,float sy) {
    const float w=size.x*sx,h=size.y*sy;
    set_vertex(4*q,at.x,at.y,uv.x,uv.y);
    set_vertex(4*q+1,w+at.x,at.y,size.x+uv.x,uv.y);
    set_vertex(4*q+2,w+at.x,h+at.y,size.x+uv.x,size.y+uv.y);
    set_vertex(4*q+3,at.x,h+at.y,uv.x,size.y+uv.y);
}
void MenuQuads::set_quad_colour(int q,std::uint8_t r,std::uint8_t g,std::uint8_t b,std::uint8_t a) {
    for(int k=0;k<4;++k) {std::uint8_t* c=v[static_cast<std::size_t>(4*q+k)].colour;c[0]=r;c[1]=g;c[2]=b;c[3]=a;}
}
void MenuQuads::set_vertex_uv(int i,float u,float w) {
    Vertex& p=v[static_cast<std::size_t>(i)];p.u=u*0.0009765625f;p.v=w*0.0009765625f;
}
void MenuQuads::set_quad_uv(int q,Point2 uv,Point2 size) {
    set_vertex_uv(4*q,uv.x,uv.y);
    set_vertex_uv(4*q+1,uv.x+size.x,uv.y);
    set_vertex_uv(4*q+2,uv.x+size.x,uv.y+size.y);
    set_vertex_uv(4*q+3,uv.x,uv.y+size.y);
}
void MenuQuads::set_vertex_pos(int i,float x,float y) {Vertex& p=v[static_cast<std::size_t>(i)];p.x=x/320.0f;p.y=y/320.0f;}
void MenuQuads::set_quad_pos(int q,float x,float y) {
    const Vertex* p=quad(q);
    const float w=p[2].x-p[0].x,h=p[2].y-p[0].y;
    set_vertex_pos(4*q,x,y);
    const float right=x+w*320.0f;
    set_vertex_pos(4*q+1,right,y);
    const float bottom=y+h*320.0f;
    set_vertex_pos(4*q+2,right,bottom);
    set_vertex_pos(4*q+3,x,bottom);
}
void MenuQuads::set_quad(int q,Point2 uv,Point2 size) {
    set_vertex(4*q,0.0f,0.0f,uv.x,uv.y);
    set_vertex(4*q+1,size.x,0.0f,size.x+uv.x,uv.y);
    set_vertex(4*q+2,size.x,size.y,size.x+uv.x,size.y+uv.y);
    set_vertex(4*q+3,0.0f,size.y,uv.x,size.y+uv.y);
}
void MenuQuads::set_quad_size(int q,float w,float h) {
    const Vertex* p=quad(q);
    const float x=p[0].x*320.0f,y=p[0].y*320.0f;
    set_vertex_pos(4*q,x,y);
    const float right=x+w;
    set_vertex_pos(4*q+1,right,y);
    const float bottom=y+h;
    set_vertex_pos(4*q+2,right,bottom);
    set_vertex_pos(4*q+3,x,bottom);
}
void MenuQuads::set_quad(int q,float x,float y,float w,float h) {
    set_vertex_pos(4*q,x,y);
    const float right=x+w;
    set_vertex_pos(4*q+1,right,y);
    const float bottom=y+h;
    set_vertex_pos(4*q+2,right,bottom);
    set_vertex_pos(4*q+3,x,bottom);
}
// ---- Upgrade ------------------------------------------------------------------------------------------------------
Icon::Icon() {
    const float s=0.153125003f;
    const float xy[4][2]={{0.0f,0.0f},{s,0.0f},{0.0f,s},{s,s}};
    for(int k=0;k<4;++k){v[k].x=xy[k][0];v[k].y=xy[k][1];for(auto& c:v[k].colour)c=255;}
}
void Icon::set_icon(int column,int row,int texture_size,int x_offset) {
    const float size=static_cast<float>(texture_size);
    const float cell=50.0299988f/size,border=1.0f/size;
    const float u0=(cell*static_cast<float>(column)+border)+static_cast<float>(x_offset)/size;
    const float v0=border+cell*static_cast<float>(row);
    const float icon=49.0f/size;
    const float u1=u0+icon,v1=icon+v0;
    v[0].u=u0;v[2].u=u0;v[0].v=v0;v[1].v=v0;
    v[1].u=u1;v[3].u=u1;v[2].v=v1;v[3].v=v1;
}
void Icon::render(GL& gl,const Label* extras) const {
    gl.push();
    gl.translate(position.x,position.y);
    gl.draw(5,v,4);
    if(extras)extras->render(gl);
    gl.pop();
}
// ---- Skill --------------------------------------------------------------------------------------------------------
// Skill::Initialise(SkillType, Skill*) 0x2b2a0, its picture: icon, name, the level on the icon (scale 0.08, its right
// edge at 0.14375, 0.146875 down) and the cooldown line (old and new value for an upgrade, none for a one-time skill).
void SkillView::skill(const Texts& t,std::int32_t kind,std::int32_t lvl,std::int32_t max,const SkillRecord* existing) {
    type=kind;
    icon.set_icon(kind%10,kind/10,1024,512);
    name=t.get("skill.name",kind);
    level.set_text(printf_string(t.get("skill.level").c_str(),lvl).c_str());
    level.scale=Point2{0.0799999982f,0.0799999982f};
    level.position.y=0.146874994f;
    const float w=level.width*0.0799999982f;
    level.position.x=0.143749997f-w;
    if(max<0)stats[0].clear();
    else if(existing)stats[0]=printf_string(t.get("skill.cooldown_up").c_str(),existing->max,max);
    else stats[0]=printf_string(t.get("skill.cooldown").c_str(),max);
}
// Skill::Initialise(StatType) 0x2b434 and Skill::SetStatChance 0x2abc8, the texts: the stat's effect now and after,
// and the bonus chances (5 points more, up to 100%).
void SkillView::stat(const Texts& t,std::int32_t s,const SessionObjects& o) {
    type=s+40;
    icon.set_icon(type%10,type/10,1024,512);
    name=t.get("stat.name",s);
    lines=2;
    const std::int32_t* chance=o.match->bonus_chance;   // potion Game+0xbe20, XP be28, coin be18, shield be30
    const auto set_chance=[&](int line,const char* prefix,std::int32_t c) {
        if(c>99)stats[line]=printf_string(t.get("stat.chance_max").c_str(),t.get(prefix).c_str());
        else {const std::int32_t next=c+5;stats[line]=printf_string(t.get("stat.chance").c_str(),t.get(prefix).c_str(),c,next>100?100:next);}
    };
    const std::int32_t damage=o.stroke->selection.base_damage,shield=o.preview->shield_value;
    const std::int32_t health=o.resources->health_max,healing=o.preview->healing_value;
    const char* base=t.get("stat.base_dmg").c_str();const char* armour=t.get("stat.armour").c_str();
    const char* max_health=t.get("stat.max_health").c_str();
    switch(s) {
    case 0: stats[0]=printf_string(base,damage,damage+1);set_chance(1,"stat.chance_xp",chance[1]);break;
    case 1: stats[0]=printf_string(armour,shield,shield+1);set_chance(1,"stat.chance_shield",chance[3]);break;
    case 2:
        if(record_mode(o,1))stats[0].clear();else stats[0]=printf_string(max_health,health,health+5);
        set_chance(1,"stat.chance_potion",chance[0]);break;
    case 3: stats[0]=printf_string(t.get("stat.healing").c_str(),healing,healing+1);set_chance(1,"stat.chance_coin",chance[2]);break;
    case 4: lines=1;stats[0]=printf_string(base,damage,damage+2);break;
    case 5: lines=1;stats[0]=printf_string(armour,shield,shield+2);break;
    case 6: lines=1;stats[0]=printf_string(max_health,health,health+10);break;
    case 7:
        lines=4;
        set_chance(0,"stat.coin",chance[2]);set_chance(1,"stat.xp",chance[1]);
        set_chance(2,"stat.shield",chance[3]);set_chance(3,"stat.potion",chance[0]);break;
    default: break;
    }
}
// ---- Item ---------------------------------------------------------------------------------------------------------
// Item::Initialise(Item*) 0x2a584, the picture and texts of the session's item: icon (20 to a row of icons.png), name
// (prefix and name: GenerateName 0x263a0; a fixed prefix for a starting item), and MakeStats 0x28e30: each stat above 0 in
// the original's order ("3 def", "15 hp", ...), four on the first line, the rest on the second, ", " between.
void ItemView::item(const Texts& t,const ItemRecord& r) {
    type=r.type;
    icon.set_icon(r.icon%20,r.icon/20,1024,0);
    for(int k=0;k<20;++k)stats[k]=r.stats.upgrade[k];
    const std::string& prefix=r.prefix<0?t.get("item.novice"):t.get("item.prefix",r.prefix);
    const std::string* base=&t.get("empty");
    for(int i=0;;++i) {
        const std::string& range=t.get("item.range",i);
        if(range.empty())break;
        int lo=0,hi=0;std::sscanf(range.c_str(),"%d %d",&lo,&hi);
        if(r.icon>=lo && r.icon<hi) {base=&t.get("item.names."+std::to_string(i),r.name);break;}
    }
    name=printf_string(t.get("item.name").c_str(),prefix.c_str(),base->c_str());
    std::vector<std::string> parts;std::vector<int> kinds;
    for(int i=0;i<20;++i) {
        const std::string& k=t.get("item.stat",i);
        if(k.empty())continue;
        const int s=std::atoi(k.c_str());const std::int32_t v=stats[s];
        if(v<=0)continue;
        const char* format=t.get("item.format",s).c_str();
        if(s==5)parts.push_back(t.get("item.quick"));
        else if(s==6 || s==7 || s==13)parts.push_back(printf_string(format,precision(v),quarters(v)));
        else parts.push_back(printf_string(format,v));
        kinds.push_back(s);
    }
    for(int k=0;k<20;++k){line_of[k]=-1;from[k]=-1;to[k]=-1;}
    line[0].clear();line[1].clear();
    const std::string& comma=t.get("item.separator");
    for(std::size_t i=0;i<parts.size();++i) {
        std::string& l=line[i<=3?0:1];
        if(i!=0 && i!=4)l+=comma;
        const int s=kinds[i];
        line_of[s]=i<=3?0:1;
        from[s]=static_cast<std::int32_t>(l.size());
        l+=parts[i];
        to[s]=static_cast<std::int32_t>(l.size());
    }
}
// ---- ItemUpgrade --------------------------------------------------------------------------------------------------
// ItemUpgrade::Initialise 0x2da74 / InitStats 0x2d958: the icon (rows 5 and 6 of the skill icons), name, and the stat
// line: "label: amount", or "label: now >> after" when the item has the stat (WriteStatInt / Percent / Float).
void UpgradeView::upgrade(const Texts& t,std::int32_t kind,std::int32_t amount,const ItemView& item) {
    type=kind;
    icon.set_icon(kind%10,kind/10+5,1024,512);
    name=t.get("upgrade.name",kind);
    const std::string& label=t.get("upgrade.stat",kind);const std::string& how=t.get("upgrade.kind",kind);
    const std::int32_t now=kind>=0 && kind<20?item.stats[kind]:0;
    if(how=="float") {
        if(now>0) {
            const std::int32_t after=now+amount;
            stats=printf_string(t.get("upgrade.float_up").c_str(),label.c_str(),precision(now),quarters(now),precision(after),quarters(after));
        } else stats=printf_string(t.get("upgrade.float").c_str(),label.c_str(),precision(amount),quarters(amount));
    } else {
        const bool percent=how=="percent";
        if(now>0)stats=printf_string(t.get(percent?"upgrade.percent_up":"upgrade.int_up").c_str(),label.c_str(),now,now+amount);
        else stats=printf_string(t.get(percent?"upgrade.percent":"upgrade.int").c_str(),label.c_str(),amount);
    }
}
const std::string& UpgradeView::description(const Texts& t,const SessionObjects& o) const {
    if(record_mode(o,1) && type==19)return t.get("upgrade.potion_desc");
    return t.get("upgrade.desc",type);
}
// ---- Font::SplitLines ---------------------------------------------------------------------------------------------
std::vector<std::string> split_lines(const Font& font,const std::string& text,float scale,float width) {
    std::vector<std::string> out;
    const float limit=width/scale;
    const char* s=text.c_str();
    if(has_wide(s)) {   // (T050-D)
        for(const TextLine& l:wrap_wide(font,s,limit))out.emplace_back(s+l.start,l.end-l.start);
        return out;
    }
    std::size_t i=0,start=0,space=0;
    float w=0.0f;
    for(;;) {
        const char c=s[i];
        if(c==0){w=1000.0f;space=i;}
        else {
            if(c==' ')space=i;
            const float half=font.size(c).x*0.5f;
            const float add=half+font.advance(c,2.0f);
            w=w+add;
        }
        if(w>limit) {
            out.emplace_back(s+start,space-start);
            w=0.0f;i=space;start=space+1;
        }
        if(s[i]==0)break;
        ++i;
    }
    return out;
}
// ---- FoldoutMenu --------------------------------------------------------------------------------------------------
FoldoutView::FoldoutView(const Font* font):font_(font),quads_(31) {
    for(auto& s:options_)s=SkillView(font);
    scroll_=SkillView(font);
    for(int q=0;q<31;++q)quads_.set_quad_colour(q,255,255,255,255);
    const auto set=[&](int q,float x,float y,float u,float v,float w,float h,float sx,float sy) {
        quads_.set_quad(q,Point2{x,y},Point2{u,v},Point2{w,h},sx,sy);
    };
    set(0,0,0,498,498,13,13,1,1);       // the panel: corners, edges and fill
    set(1,13,0,479,472,1,13,284,1);
    set(2,0,13,478,487,13,1,1,249);
    set(3,0,262,498,482,13,15,1,1);
    set(4,13,262,483,470,1,15,284,1);
    set(5,13,13,145,399,1,1,284,249);
    set(6,0,262,109,383,91,52,1,1);     // the confirm button
    set(7,18,261,143,288,53,35,1,1);
    for(int s=0;s<2;++s) {              // the two selection bars
        set(8+3*s,309,380,309,380,3,55,1,1);set(9+3*s,313,380,313,380,1,55,271,1);set(10+3*s,315,380,315,380,3,55,1,1);
    }
    set(20,18,204,319,380,3,53,1,1);set(21,21,204,323,380,1,53,269,1);set(22,290,204,325,380,3,53,1,1);
    for(int k=0;k<4;++k)set(27+k,71,49.0f+57.0f*static_cast<float>(k),491,93,20,21,1,1);
    background_.set_size(Point2{2.0f,2.0f});background_.position=Point2{0.5f,0.5f};background_.set_colour(Colour{0,0,0,0});
}
const ItemView* FoldoutView::equipped_of(const std::vector<ItemView>& equipped,std::int32_t kind) const {
    for(const auto& e:equipped)if(e.type==kind)return &e;
    return nullptr;
}
void FoldoutView::add_label(std::int32_t option,const std::string& text) {
    ++lines_[option];
    if(labels_.size()==static_cast<std::size_t>(count_)){labels_.emplace_back(font_);labels_.back().space_scale=2.0f;}
    Label& l=labels_[static_cast<std::size_t>(count_)];
    l.set_text(text.c_str());
    const float s=lines_[option]<=1?0.109999999f:0.0900000036f;
    l.scale=Point2{s,s};
    ++count_;
}
void FoldoutView::open(const Texts& t,const SessionObjects& o,std::vector<ItemView>& equipped) {
    const MenuState& m=*o.menu;
    type=m.type;at_.x=1.0f;
    count_=0;for(auto& l:lines_)l=0;
    for(int k=0;k<4;++k)quads_.set_quad(14+k,Point2{kOption[k][0],kOption[k][1]},Point2{1,382},Point2{53,53},1,1);
    const auto at=[](int k,float dx) {return points(kOption[k][0]+dx,kOption[k][1]+2.0f);};
    if(type==0) {
        quads_.set_quad(18,Point2{15,3},Point2{1,266},Point2{121,29},1,1);
        quads_.set_quad(19,Point2{137,15},Point2{251,266},Point2{156,21},1,1);
        skill_options_=m.skill_options;
        const float width=((kOption[0][0]+53.0f)+5.0f)/-320.0f+0.984375f-0.0718749985f;
        for(int k=0;k<4;++k) {
            const SkillRecord& r=m.options[k];
            SkillView& v=options_[k];
            if(k<skill_options_) {
                SkillRecord existing{};const SkillRecord* e=nullptr;
                for(std::int32_t j=0;j<o.resources->skill_count;++j)
                    if(o.skills->id[j]==r.type){existing.type=r.type;existing.max=o.resources->skill_max[j];e=&existing;}
                v.skill(t,r.type,r.level,r.max,e);
                v.icon.position=at(k,2.0f);
                add_label(k,v.name);
                const auto lines=split_lines(*font_,t.get("skill.desc",r.type),0.0900000036f,width);
                for(const auto& line:lines)add_label(k,line);
                if(lines.size()<=1)add_label(k,t.get("empty"));
                add_label(k,v.stats[0]);
            } else {
                v.stat(t,r.type-40,o);
                v.icon.position=at(k,2.0f);
                add_label(k,v.name);
                for(std::int32_t j=0;j<v.lines;++j)add_label(k,v.stats[j]);
            }
        }
    } else if(type==1) {
        quads_.set_quad(18,Point2{15,3},Point2{1,296},Point2{141,29},1,1);
        quads_.set_quad(19,Point2{161,15},Point2{123,266},Point2{127,21},1,1);
        for(int k=0;k<3;++k) {
            items_[k].item(t,m.items[k]);
            items_[k].icon.position=at(k,2.0f);
            add_label(k,items_[k].name);add_label(k,items_[k].line[0]);add_label(k,items_[k].line[1]);
        }
        scroll_slot_=m.scroll_slot;
        if(scroll_slot_>=0) {
            const int s=scroll_slot_;
            quads_.set_quad(23,Point2{kOption[s][0]+54.0f,kOption[s][1]},Point2{1,382},Point2{53,53},1,1);
            scroll_.skill(t,m.scroll.type,m.scroll.level,m.scroll.max,nullptr);
            scroll_.icon.position=points((kOption[s][0]+54.0f)+2.0f,kOption[s][1]+2.0f);
        }
        slot_=at(3,2.0f);
        for(int k=0;k<3;++k)add_label(3,t.get("empty"));
    } else if(type==2) {
        quads_.set_quad(18,Point2{15,3},Point2{1,326},Point2{123,29},1,1);
        quads_.set_quad(19,Point2{139,15},Point2{1,360},Point2{159,21},1,1);
        for(int k=0;k<4;++k) {
            quads_.set_quad(23+k,Point2{kOption[k][0]+73.0f,kOption[k][1]},Point2{1,382},Point2{53,53},1,1);
            upgrade_items_[k]=m.upgrade_items[k];
            ItemView& item=equipped[static_cast<std::size_t>(upgrade_items_[k])];
            item.icon.position=at(k,2.0f);
            UpgradeView& u=upgrades_[k];
            u.upgrade(t,m.upgrade_type[k],m.upgrade_amount[k],item);
            u.icon.position=at(k,75.0f);
            add_label(k,u.name);add_label(k,u.description(t,o));add_label(k,u.stats);
        }
    }
    update_labels(o,equipped);
}
// UpdateLabels 0x23234: every option's labels beside its icon -- the title (scale 0.11) on the first row, the lines
// below (0.09, the font's line height apart); a skill's cooldown at the right edge; the lines after the second to the
// right of the two before. The shop's scroll lines shrink to fit; its fourth slot (what the chosen item replaces) is
// greyer; and a shop item's stats that differ from the equipped item's are green (better) or red (worse).
void FoldoutView::update_labels(const SessionObjects& o,const std::vector<ItemView>& equipped) {
    const std::int32_t lh=font_->line_height,base=font_->base;
    const float ratio=static_cast<float>(lh-base)/static_cast<float>(lh);
    const auto option_of=[&](std::int32_t i,std::int32_t& line) {
        std::int32_t r=i;
        for(int k=0;k<3;++k){if(r-lines_[k]<0){line=r;return k;}r-=lines_[k];}
        line=r;return 3;
    };
    float scroll_scale=0.0900000036f;
    if(type==1 && scroll_slot_>=0) {
        for(std::int32_t i=0;i<count_;++i) {
            std::int32_t line=0;const int k=option_of(i,line);
            if(k>scroll_slot_)break;
            if(k!=scroll_slot_ || line==0)continue;
            Label& l=labels_[static_cast<std::size_t>(i)];
            l.scale=Point2{0.0900000036f,0.0900000036f};
            const float x=((kOption[k][0]+53.0f)+5.0f)/320.0f;
            const float left=x+0.168750003f;
            const float w=l.width*l.scale.x;
            const float avail=(0.984375f-left)-0.0718749985f;
            if(w>avail) {const float s=(avail*0.0900000036f)/w;if(s<scroll_scale)scroll_scale=s;}
        }
    }
    const float top=ratio*0.109999999f;
    float widest=0.0f;
    for(std::int32_t i=0;i<count_;++i) {
        std::int32_t line=0;const int k=option_of(i,line);
        Label& l=labels_[static_cast<std::size_t>(i)];
        if(line==0)widest=0.0f;
        else if(static_cast<std::uint32_t>(line-1)<=1u) {const float w=l.width*l.scale.x;if(w>widest)widest=w;}
        const float scale=scroll_slot_==k?scroll_scale:0.0900000036f;
        float x=((kOption[k][0]+53.0f)+5.0f)/320.0f;
        std::int32_t row=line;
        float step;
        if(line>2 && type==0 && k<skill_options_) {   // a skill's cooldown, right-aligned on the title's row
            row=0;
            l.scale=Point2{0.0720000044f,0.0720000044f};
            const float w=l.width*l.scale.x;
            x=0.912500024f-w;
            step=scale*ratio;
        } else if(line>2) {
            step=scale*ratio;
            row=line-2;
            const float half=step*0.5f;
            x=x+(half+widest);
        } else step=scale*ratio;
        if(type==2)x=x+0.228125006f;
        else if(type==1 && scroll_slot_==k) {
            x=x+0.168750003f;
            if(row>0)l.scale=Point2{scale,scale};
        }
        l.position.x=x;
        const float y=kOption[k][1]/320.0f+top;
        l.position.y=step*static_cast<float>(row)+y;
        const bool replaced=type==1 && k==3;
        const std::uint8_t c=row==0?(replaced?0xaa:0xff):(replaced?0x78:0xc8);
        l.colour=Colour{c,c,c,255};l.update_colour();
        if(row<=0 || type!=1)continue;
        const ItemView* a=nullptr;const ItemView* b=nullptr;   // a: whose stats and places, b: compared with
        if(k<=2){a=&items_[k];b=equipped_of(equipped,a->type);}
        else if(o.menu->first>=0){b=&items_[o.menu->first-14];a=equipped_of(equipped,b->type);}
        if(!a || !b)continue;
        for(int s=0;s<20;++s) {
            if(a->stats[s]==b->stats[s] || a->line_of[s]+1!=row)continue;
            const Colour sub=a->stats[s]>b->stats[s]?Colour{0,255,0,255}:Colour{255,0,0,255};
            l.set_sub_colour(static_cast<std::uint32_t>(a->from[s]),static_cast<std::uint32_t>(a->to[s]),sub);
        }
    }
}
void FoldoutView::process(const SessionObjects& o,float dt) {
    const MenuState& m=*o.menu;
    const float timer=m.timer;
    if(timer<0.0f)return;
    float r=timer/0.300000012f;
    if(!m.opening)r=1.0f-r;
    const float a=r*180.0f;
    background_.set_colour(Colour{0,0,0,static_cast<std::uint8_t>(a<=0.0f?0u:static_cast<std::uint32_t>(a))});
    const float next=timer+dt;
    if(!(next<0.300000012f)) {
        if(m.opening)at_.x=0.0718749985f;
        else if(type==0) {   // closing: Game::SetSkill on the first, then the second choice
            exchanges.clear();
            for(const std::int32_t b:{m.first,m.second})
                if(b>=14 && b<=17 && options_[b-14].type>=0 && options_[b-14].type<40)exchanges.push_back(b-14);
        }
        return;
    }
    const float t=next/0.300000012f;
    const auto interpolate=[](float p,float q,float s) {const float x=p*s;const float y=(1.0f-s)*q;return x+y;};
    at_.x=m.opening?interpolate(0.0718749985f,1.0f,t):interpolate(1.0f,0.0718749985f,t);
}
void FoldoutView::highlight(const Texts& t,const SessionObjects& o,std::vector<ItemView>& equipped,std::int32_t button,
                            std::int32_t selection,bool on) {
    const Point2 frame=on?Point2{55,382}:Point2{1,382};
    quads_.set_quad_uv(button,frame,Point2{53,53});
    if(type==2)quads_.set_quad_uv(button+9,frame,Point2{53,53});
    else if(type==1 && button-14==scroll_slot_)quads_.set_quad_uv(23,frame,Point2{53,53});
    if(!on)return;
    const float y=quads_.quad(button)[0].y*320.0f-1.0f;
    quads_.set_quad_pos(8+3*selection,17.0f,y);
    quads_.set_quad_pos(9+3*selection,20.0f,y);
    quads_.set_quad_pos(10+3*selection,291.0f,y);
    if(type!=1 || button<14 || button>16)return;
    const ItemView* e=equipped_of(equipped,items_[button-14].type);
    if(!e)return;
    labels_[static_cast<std::size_t>(count_-3)].set_text(printf_string(t.get("menu.replaces").c_str(),e->name.c_str()).c_str());
    labels_[static_cast<std::size_t>(count_-2)].set_text(e->line[0].c_str());
    labels_[static_cast<std::size_t>(count_-1)].set_text(e->line[1].c_str());
    update_labels(o,equipped);
}
void FoldoutView::confirm(bool pressed) {
    const std::uint8_t c=pressed?200:255;
    quads_.set_quad_colour(7,c,c,c,255);
}
std::int32_t FoldoutView::button_at(const SessionObjects& o,Point2 p) const {
    (void)o;
    const auto in_quad=[&](int q) {
        const Vertex* v=quads_.quad(q);
        if(!(p.x>at_.x+v[0].x) || !(p.x<at_.x+v[2].x))return false;
        if(!(p.y>v[0].y+at_.y))return false;
        return at_.y+v[2].y>p.y;
    };
    const auto in_button=[&](int q) {
        const Vertex* v=quads_.quad(q);
        if(!(p.x>v[0].x+at_.x) || !(p.y>v[0].y+at_.y))return false;
        return at_.y+v[2].y>p.y;
    };
    if(in_quad(7))return 7;
    for(int b=14;b<=17;++b) {
        if(b==17 && type==1)continue;
        if(in_button(b))return b;
    }
    return -1;
}
// Render 0x246a8: the darkened screen; the panel at its slide position: its quads (the confirm button when it can be
// pressed, the selection bars when chosen, the fourth option frame not in the shop, the shop's and the upgrade menu's
// own pieces); the options' icons (items from icons.png; the item a chosen shop item replaces in the fourth slot); the
// labels (the shop's last three only with a choice).
void FoldoutView::render(GL& gl,const SessionObjects& o,std::vector<ItemView>& equipped) const {
    const MenuState& m=*o.menu;
    gl.bind_texture(NoTexture);
    background_.render(gl);
    gl.push();
    gl.translate(at_.x,at_.y);
    gl.bind_texture(Tiles);
    for(int k=0;k<31;++k) {
        if(!m.confirm_ready && (k==6 || k==7))continue;
        if(k>7 && m.first<0 && k<=10)continue;
        if(k>10 && m.second<0 && k<=13)continue;
        if(k==17 && type==1)continue;
        if(k>=20 && k<=22 && type!=1)continue;
        if(k>22 && type!=2 && !(type==1 && scroll_slot_>=0))continue;
        if(k>23 && type!=2)continue;
        gl.draw(6,quads_.quad(k),4);
    }
    if(type==1) {
        gl.bind_texture(Icons);
        for(const auto& item:items_)item.icon.render(gl,nullptr);
        if(m.first>=0) {
            const ItemView* e=equipped_of(equipped,items_[m.first-14].type);
            if(e) {
                ItemView& eq=equipped[static_cast<std::size_t>(e-equipped.data())];
                eq.icon.position=slot_;eq.icon.render(gl,nullptr);
            }
        }
        if(scroll_slot_>=0){gl.bind_texture(Tiles);scroll_.render(gl,false);}
    } else if(type==0) {
        for(const auto& s:options_){gl.bind_texture(Tiles);s.render(gl,true);}
    } else if(type==2) {
        gl.bind_texture(Icons);
        for(int k=0;k<4;++k)equipped[static_cast<std::size_t>(upgrade_items_[k])].icon.render(gl,nullptr);
        gl.bind_texture(Tiles);
        for(const auto& u:upgrades_)u.icon.render(gl,nullptr);
    }
    for(std::int32_t i=0;i<count_;++i) {
        if(type==1 && m.first<0 && i>=count_-3)continue;
        labels_[static_cast<std::size_t>(i)].render(gl);
    }
    gl.pop();
}
}
// ---- GameMenu -----------------------------------------------------------------------------------------------------
namespace drui {
namespace {
float interpolate(float a,float b,float t) {const float x=a*t;const float y=(1.0f-t)*b;return x+y;}   // 0x1b800
}
GameMenuView::GameMenuView():quads_(21) {
    const auto set=[&](int q,float x,float y,float u,float v,float w,float h,float sx,float sy) {
        quads_.set_quad(q,Point2{x,y},Point2{u,v},Point2{w,h},sx,sy);
    };
    set(0,98,105,498,498,13,13,1,1);    // the panel: corners, edges and fill
    set(1,111,105,479,472,1,13,99,1);
    set(2,210,105,380,415,15,13,1,1);
    set(3,98,118,478,487,13,1,1,216);
    set(4,111,118,145,399,1,1,99,216);
    set(5,210,118,380,430,15,1,1,216);
    set(6,98,334,498,482,13,15,1,1);
    set(7,111,334,483,470,1,15,99,1);
    set(8,210,334,380,433,15,13,1,1);
    set(9,116,123,329,364,89,26,1,1);   // the buttons: close, sound, help, clock, attack dimming, high frame rate, quit
    set(10,116,157,422,347,89,26,1,1);
    set(11,116,185,422,374,89,26,1,1);
    set(12,116,213,647,997,89,26,1,1);
    set(13,116,241,737,997,89,26,1,1);
    set(14,116,269,388,997,89,26,1,1);
    set(15,116,303,422,401,89,26,1,1);
    for(int k=0;k<5;++k)set(16+k,121,162.0f+28.0f*static_cast<float>(k),405,411,16,16,1,1);   // the switches' marks
    background_.set_size(Point2{2.0f,2.0f});background_.position=Point2{0.5f,0.5f};background_.set_colour(Colour{0,0,0,0});
}
void GameMenuView::show() {
    background_.set_alpha(0);
    for(int q=0;q<21;++q)quads_.set_quad_colour(q,255,255,255,0);
}
void GameMenuView::fade(const OverlayMenu& m) {
    const float t=m.timer/0.200000003f;
    const float bg=m.closing?interpolate(180.0f,0.0f,t):interpolate(0.0f,180.0f,t);
    background_.set_alpha(static_cast<std::uint8_t>(static_cast<std::uint32_t>(bg)));
    const float a=m.closing?interpolate(255.0f,0.0f,t):interpolate(0.0f,255.0f,t);
    const auto alpha=static_cast<std::uint8_t>(static_cast<std::int32_t>(a));
    for(int q=0;q<21;++q)quads_.set_quad_colour(q,255,255,255,alpha);
}
void GameMenuView::press(std::int32_t button,bool on) {quads_.set_quad_colour(button,255,255,255,on?150:255);}
std::int32_t GameMenuView::button_at(Point2 p) const {
    for(int b=9;b<=15;++b) {
        const Vertex* v=quads_.quad(b);
        if(p.x>v[0].x && p.x<v[2].x && p.y>v[0].y && v[2].y>p.y)return b;
    }
    return -1;
}
void GameMenuView::render(GL& gl,const SaveSettings& s) {
    const std::uint8_t on[5]={s.sound_13ec6,s.help_13ec8,s.clock_13ec9,s.dimming_13eca,s.framerate_13ecb};
    for(int k=0;k<5;++k)quads_.set_quad_uv(16+k,Point2{405.0f,on[k]?394.0f:411.0f},Point2{16.0f,16.0f});
    gl.push();
    gl.bind_texture(NoTexture);
    background_.render(gl);
    gl.bind_texture(Tiles);
    for(int q=0;q<21;++q)gl.draw(6,quads_.quad(q),4);
    gl.pop();
}
}
// ---- StatsMenu ----------------------------------------------------------------------------------------------------
namespace drui {
namespace {
// Item::MakeStatLabels 0x26600: the item's name, then a line for each stat above 0 (the order of item.line.*).
std::int32_t make_stat_labels(const Texts& t,const ItemView& item,std::vector<Label>& lines) {
    lines[0].set_text(item.name.c_str());
    std::int32_t n=1;
    for(int i=0;;++i) {
        const std::string& k=t.get("item.line",i);
        if(k.empty())break;
        const int s=std::atoi(k.c_str());const std::int32_t v=item.stats[s];
        if(v<=0)continue;
        const char* format=t.get("item.long",s).c_str();
        const std::string text=s==5?std::string(format):(s==6 || s==7 || s==13)?printf_string(format,precision(v),quarters(v))
                                                                               :printf_string(format,v);
        lines[static_cast<std::size_t>(n++)].set_text(text.c_str());
    }
    return n;
}
// The tab of each item type (StatsMenu::Show: GetButtonPosition 0x3284c of tab 10 + ...) and its reverse (Process).
constexpr std::int32_t kItemTab[5]={12,10,11,13,14};
}
StatsMenuView::StatsMenuView(const Font* font):font_(font),quads_(16),lines_(15,Label(font)) {
    for(auto& l:names_)l=Label(font);
    for(auto& l:values_)l=Label(font);
    difficulty_=Label(font);score_=Label(font);
    background_.set_size(Point2{2.0f,2.0f});background_.position=Point2{0.5f,0.5f};background_.set_colour(Colour{0,0,0,180});
    set_menu_height(203);
    quads_.set_quad(9,Point2{23.0f,height_+58.0f},Point2{18.0f,383.0f},Point2{0.5f,0.5f},1.0f,1.0f);   // the page's backing
    for(int k=0;k<6;++k)                // the tabs: the items, then the class
        quads_.set_quad(10+k,Point2{k%2?80.0f:23.0f,63.0f+57.0f*static_cast<float>(k/2)},Point2{1.0f,382.0f},
                        Point2{53.0f,53.0f},1.0f,1.0f);
    // QuadStrip::AddQuad(CharacterClass::GetDummyIconCoords: (-51, 0)..(0, 51), policy 2, -1) on a 512 texture:
    // SetUV, then UpdateSize (the picture's size in points) and SetPosition ((80, 177) / 320, centred by half a size).
    strip_.set_uv(Point2{-51.0f/512.0f,0.0f/512.0f},Point2{0.0f/512.0f,51.0f/512.0f});
    {
        const float du=strip_.v[3].u-strip_.v[0].u,dv=strip_.v[3].v-strip_.v[0].v;
        const float w=du*512.0f,h=dv*512.0f;
        strip_.set_size(Point2{w/320.0f,h/320.0f});
    }
    strip_at_=Point2{80.0f/320.0f,177.0f/320.0f};
    strip_.position=Point2{strip_.size.x/2.0f+strip_at_.x,strip_.size.y/2.0f+strip_at_.y};
    float y=height_+58.0f;y=y/320.0f;   // the page's lines below the panel's rows
    for(std::size_t k=0;k<lines_.size();++k) {
        y=y+(k==0?0.0599999987f:0.0500000007f);
        Label& l=lines_[k];
        l.position=Point2{0.0874999985f,y};
        const float s=k==0?0.109999999f:0.0900000036f;l.scale=Point2{s,s};l.space_scale=2.0f;
    }
    const float bottom=height_+58.0f-5.0f;const float score_y=bottom/320.0f;
    difficulty_.position=Point2{0.0718749985f,score_y-0.0379999988f};
    score_.position=Point2{0.0718749985f,score_y};
    for(Label* l:{&difficulty_,&score_}) {
        l->scale=Point2{0.0869999975f,0.0869999975f};l->space_scale=2.0f;l->colour.a=0;l->update_colour();
    }
    // CreateLabels: from the right of tab 11, a row each, headings (0, 1, 4, 7, 10, 13, 15) larger and further apart
    const Vertex& corner=quads_.quad(11)[1];
    float row_y=corner.y-0.00200000009f;
    const float heading_x=corner.x+0.015625f,row_x=heading_x+0.03125f;
    for(int k=0;k<17;++k) {
        const bool heading=k<=1 || k==4 || k==7 || k==10 || k==13 || k==15;
        row_y=row_y+(heading?0.0379999988f:0.0340000018f);
        const float s=heading?0.0869999975f:0.0790000036f;
        for(Label* l:{&names_[k],&values_[k]}) {
            l->position=Point2{heading?heading_x:row_x,row_y};l->scale=Point2{s,s};l->space_scale=2.0f;
            l->colour.a=0;l->update_colour();
        }
    }
}
void StatsMenuView::set_menu_height(std::int32_t height) {
    height_=static_cast<float>(height);
    const float bottom=height_+58.0f;
    const auto set=[&](int q,float x,float y,float u,float v,float w,float h,float sx,float sy) {
        quads_.set_quad(q,Point2{x,y},Point2{u,v},Point2{w,h},sx,sy);
    };
    set(0,5,45,498,498,13,13,1,1);
    set(1,18,45,479,472,1,13,284,1);
    set(2,302,45,380,415,15,13,1,1);
    set(3,5,58,478,487,13,1,1,height_);
    set(4,18,58,145,399,1,1,284,height_);
    set(5,302,58,380,430,15,1,1,height_);
    set(6,5,bottom,498,482,13,15,1,1);
    set(7,18,bottom,483,470,1,15,284,1);
    set(8,302,bottom,380,433,15,13,1,1);
}
void StatsMenuView::set_label_value(std::int32_t row,std::int32_t base,std::int32_t bonus,bool percent,const Texts& t) {
    const std::int32_t sum=base+bonus;
    const std::string text=percent?printf_string(t.get("stats.percent").c_str(),sum>100?100:sum)
                                  :printf_string(t.get("stats.int").c_str(),sum);
    const bool green=bonus>0 && (!percent || base<=99);
    Label& l=values_[row];
    l.set_text(text.c_str());
    l.position.x=right_-l.width*l.scale.x;
    l.colour=green?Colour{0,255,0,0}:Colour{255,255,255,0};
    l.update_colour();
}
void StatsMenuView::show(const Texts& t,const SessionObjects& o,std::vector<ItemView>& equipped) {
    count_=0;
    set_menu_height(203);
    set_alpha(0,equipped);
    for(auto& l:lines_){l.colour.a=0;l.update_colour();}
    if(names_[0].text.empty())for(int k=0;k<17;++k)names_[k].set_text(t.get("stats.row",k).c_str());
    const auto& sel=o.stroke->selection;const auto& pre=*o.preview;const auto& res=*o.resources;
    const std::int32_t* base=o.extra->base_bde8;const PlayerStats& p=*o.player;const std::int32_t* chance=o.match->bonus_chance;
    set_label_value(0,res.level,0,false,t);
    set_label_value(1,base[0],p.base_bdec,false,t);
    set_label_value(2,sel.base_damage,sel.bonus_base_damage,false,t);
    set_label_value(3,chance[1],p.chance_be2c,true,t);
    set_label_value(4,base[1],p.base_bdf4,false,t);
    set_label_value(5,pre.shield_value,pre.shield_bonus,false,t);
    set_label_value(6,chance[3],p.chance_be34,true,t);
    set_label_value(7,base[2],p.base_bdfc,false,t);
    set_label_value(8,res.health_max,res.health_bonus,false,t);
    set_label_value(9,chance[0],p.chance_be24,true,t);
    set_label_value(10,base[3],p.base_be04,false,t);
    set_label_value(11,pre.healing_value,pre.healing_bonus,false,t);
    set_label_value(12,chance[2],p.chance_be1c,true,t);
    set_label_value(13,sel.weapon_damage,0,false,t);
    set_label_value(14,50,o.path->battle.armour_break_chance-50,true,t);
    set_label_value(15,pre.armour_max,0,false,t);
    const std::int32_t loss=o.attack_inputs->armour_loss_chance;
    set_label_value(16,50,50-(loss>100?100:loss),true,t);
    const auto& stroke=*o.stroke;
    if(!stroke.record_14aed || stroke.mode_14ae8==3)
        difficulty_.set_text(printf_string(t.get("stats.difficulty").c_str(),t.get("difficulty.name",o.match->spawn_enabled_14ae0).c_str()).c_str());
    else difficulty_.set_text(t.get("mode.name",stroke.mode_14ae8).c_str());
    score_.set_text(printf_string(t.get("stats.score").c_str(),dr_get_score(o.resources,o.path,o.skills,o.end->victory!=0)).c_str());
    for(int type=0;type<5;++type) {   // Game::GetItem(type)'s icon on its tab, GetButtonPosition: the corner + 0.00625
        const Vertex& v=quads_.quad(kItemTab[type])[0];
        equipped[static_cast<std::size_t>(type)].icon.position=Point2{v.x+0.00625000009f,v.y+0.00625000009f};
    }
    for(int q=10;q<16;++q)quads_.set_quad_uv(q,Point2{1.0f,382.0f},Point2{53.0f,53.0f});
    const ClassProfile& c=o.classes[o.scroll->current];   // CharacterClass::GetIconCoords(class, -1): row 0 at 70
    const float u0=static_cast<float>(51*c.class_type),u1=static_cast<float>(51*(c.class_type+1));
    strip_.set_uv(Point2{u0/512.0f,70.0f/512.0f},Point2{u1/512.0f,121.0f/512.0f});
}
void StatsMenuView::set_alpha(std::uint8_t a,std::vector<ItemView>& equipped) {
    background_.set_alpha(a);   // (Show: 0; the fade sets the background on its own)
    strip_.set_alpha(a);
    for(int q=0;q<16;++q)quads_.set_quad_colour(q,255,255,255,a);
    for(auto& item:equipped)for(auto& v:item.icon.v)v.colour[3]=a;
}
void StatsMenuView::fade(const OverlayMenu& m,std::vector<ItemView>& equipped) {
    if(m.closing && !(m.timer>0.0f)) {   // closed: Game::GetItem(0..4)'s icons opaque again
        for(auto& item:equipped)for(auto& v:item.icon.v)v.colour[3]=255;
        return;
    }
    const float t=m.timer/0.200000003f;
    const auto interpolate=[](float a,float b,float s) {const float x=a*s;const float y=(1.0f-s)*b;return x+y;};
    const float bg=m.closing?interpolate(180.0f,0.0f,t):interpolate(0.0f,180.0f,t);
    background_.set_alpha(static_cast<std::uint8_t>(static_cast<std::uint32_t>(bg)));
    const float af=m.closing?interpolate(255.0f,0.0f,t):interpolate(0.0f,255.0f,t);
    const auto a=static_cast<std::uint8_t>(static_cast<std::int32_t>(af));
    for(int q=0;q<16;++q)quads_.set_quad_colour(q,255,255,255,a);
    for(int k=0;k<17;++k) {
        names_[k].colour.a=a;names_[k].update_colour();
        values_[k].colour.a=a;values_[k].update_colour();
    }
    difficulty_.colour.a=a;difficulty_.update_colour();
    score_.colour.a=a;score_.update_colour();
    for(auto& item:equipped)for(auto& v:item.icon.v)v.colour[3]=a;
    for(auto& l:lines_){l.colour.a=a;l.update_colour();}
    strip_.set_alpha(a);
}
void StatsMenuView::tab(const Texts& t,const SessionObjects& o,const std::vector<ItemView>& equipped,std::int32_t tab,
                        std::int32_t previous) {
    if(previous>=0)quads_.set_quad_uv(previous,Point2{1.0f,382.0f},Point2{53.0f,53.0f});
    quads_.set_quad_uv(tab,Point2{55.0f,382.0f},Point2{53.0f,53.0f});
    if(tab==15) {   // the race and class, the race's bonus (cut to 0.8 at 0.09), the perks and the flaws
        const ClassProfile& c=o.classes[o.scroll->current];
        lines_[0].set_text(printf_string(t.get("stats.race_class").c_str(),t.get("race.name",c.race).c_str(),
                                         t.get("class.name",c.class_type).c_str()).c_str());
        const std::vector<std::string> split=split_lines(*font_,t.get("race.bonus",c.race),0.0900000036f,0.800000012f);
        std::size_t n=0;
        for(;n<split.size();++n)lines_[n+1].set_text(split[n].c_str());
        std::size_t at=n+1;
        for(int k=0;k<4;++k)if(c.perks[k]!=255 && at<lines_.size())lines_[at++].set_text(t.get("perk.desc",c.perks[k]).c_str());
        for(int k=0;k<4;++k)if(c.flaws[k]!=255 && at<lines_.size())lines_[at++].set_text(t.get("flaw.desc",c.flaws[k]).c_str());
        count_=static_cast<std::int32_t>(at);
    } else {
        std::int32_t type=0;
        for(int k=0;k<5;++k)if(kItemTab[k]==tab)type=k;
        count_=make_stat_labels(t,equipped[static_cast<std::size_t>(type)],lines_);
    }
    const float lines=static_cast<float>(count_-1);
    const float page=((lines*0.0500000007f)*320.0f+19.1999989f)+5.0f;
    const float height=(page+203.0f)+5.0f;
    set_menu_height(static_cast<std::int32_t>(height));
    quads_.set_quad_size(9,274.0f,page);
}
std::int32_t StatsMenuView::button_at(Point2 p) const {
    const Point2 a{5.0f/320.0f,45.0f/320.0f};
    const float bottom=(height_+58.0f)+13.0f;
    const Point2 b{317.0f/320.0f,bottom/320.0f};
    if(p.x<a.x || p.x>b.x || p.y<a.y || p.y>b.y)return -1;
    for(int q=10;q<16;++q) {
        const Vertex* v=quads_.quad(q);
        if(p.x>v[0].x && p.x<v[2].x && p.y>v[0].y && v[2].y>p.y)return q;
    }
    return 0;
}
void StatsMenuView::render(GL& gl,const std::vector<ItemView>& equipped) const {
    gl.push();
    gl.bind_texture(NoTexture);
    background_.render(gl);
    gl.bind_texture(Tiles);
    for(int q=0;q<16;++q) {
        if(q==9 && count_<=0)continue;
        gl.draw(6,quads_.quad(q),4);
    }
    gl.pop();
    gl.bind_texture(Menus);
    strip_.render(gl);
    gl.bind_texture(Icons);
    for(const auto& item:equipped)item.icon.render(gl,nullptr);
    for(int k=0;k<17;++k){names_[k].render(gl);values_[k].render(gl);}
    difficulty_.render(gl);score_.render(gl);
    for(std::int32_t i=0;i<count_;++i)lines_[static_cast<std::size_t>(i)].render(gl);
}
}
