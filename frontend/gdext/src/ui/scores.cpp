#include "scores.hpp"
#include "setup.hpp"
#include <cstring>
#include <string>
using namespace dungeonraid;
namespace drui {
namespace {
constexpr float kBand=0.0375000015f;   // ScoreScreen::MakePanel's heading band
constexpr Colour kText{122,103,211,255};
float interpolate(float a,float b,float t) {const float x=a*t;const float y=(1.0f-t)*b;return x+y;}  // 0x1b800
std::uint8_t byte_of(float v) {return static_cast<std::uint8_t>(static_cast<std::int32_t>(v));}
Colour divided(Colour c,float f) {   // GLcolour4::operator/ 0x36c78 (the alpha kept)
    const auto d=[f](std::uint8_t v){const float x=static_cast<float>(v)/f;return static_cast<std::uint8_t>(static_cast<std::uint32_t>(x));};
    return Colour{d(c.r),d(c.g),d(c.b),c.a};
}
// The scores in a table (ScoreScreen+0xf00 + 4 x table). The pages beside the first and the last read the words
// either side of the counts (the last record's last skill, the latest score's table) as the original does.
std::int32_t count_of(const SessionObjects& o,std::int32_t table) {
    const ScoreBoard& s=*o.scores;
    if(table<0)return s.scores[5][9].skills[3];
    if(table>5)return s.last_type;
    return s.count[table];
}
// ScoreScreen::SetLabelText 0x34bd0: right-aligned at x
void label_text(Label& l,const char* text,float x) {l.set_text(text);l.position.x=x-l.width*l.scale.x;}
}
ScoreView::ScoreView(const Font* font,const Font* menu_font,const Font* score_font)
    :font_(font),menu_font_(menu_font),score_font_(score_font) {
    black_.set_size(Point2{1.0f,1.5f});black_.position=Point2{0.5f,0.75f};black_.set_colour(Colour{0,0,0,255});
    back_.add_quad(Point2{104.0f,1.0f},Point2{193.0f,27.0f},2,-1.0f);
    {
        const Point2 size=back_.size();
        const float x=1.0f-size.x;const float y=1.5f-size.y;
        back_.set_position(Point2{x-0.00937500037f,y-0.00937500037f});
    }
    const float h=back_.position.y-0.00937500037f;
    backing_.set_size(Point2{1.0f,h});backing_.position=Point2{0.5f,h*0.5f};backing_.set_colour(Colour{45,45,75,255});
    banner_.set_size(Point2{0.134375006f,0.753125012f});banner_.position=Point2{0.5f,0.0799999982f};
    banner_.set_colour(kText);banner_.set_uv(0.95703125f,0.661132812f,0.0419921875f,0.235351562f);banner_.rotation=-90.0f;
    for(auto& p:pages_)create_page(p);
}
void ScoreView::create_page(Page& p) {
    for(int r=0;r<10;++r) {
        const float a=back_.position.y-0.00937500037f;const float b=a-0.00937500037f;const float base=b+0.00625000009f;
        const float k=static_cast<float>(10-r);const float y=base+k*-0.10625f;
        make_panel(p.ranks[r],false,0.100000001f,0.100000001f,0.00937500037f,y,kBand);
        QuadStrip& row=p.rows[r];
        make_panel(row,true,0.87499994f,0.100000001f,0.115625001f,y,kBand);
        for(int i=0;i<4;++i) {
            Quad& q=p.skills[r][i];
            Point2 u0,u1;skill_uvs(0,u0,u1);q.set_uv(u0,u1);
            q.scale=Point2{0.0500000007f,0.0500000007f};
            const Point2 size=row.size();
            const float top=row.position.y+0.0250000004f;q.position.y=top+0.00312500005f;
            const float right=row.position.x+size.x;
            const float step=static_cast<float>(i)*-0.0500000007f;
            const float x=right+step;const float x2=x-0.0250000004f;q.position.x=x2-0.00625000009f;
        }
    }
    const float y0=p.rows[0].position.y-0.100000001f;const float y=y0-0.0718749985f;
    make_button(p.left,0.100000001f,0.100000001f,0.00937500037f,y);
    const float x1=p.left.position.x+p.left.size().x;
    make_panel(p.title,false,0.768749952f,0.100000001f,x1+0.00625000009f,y,kBand);
    const float x2=p.title.position.x+p.title.size().x;
    make_button(p.right,0.100000001f,0.100000001f,x2+0.00625000009f,y);
    p.left_arrow.add_quad(Point2{302.0f,1.0f},Point2{329.0f,30.0f},2,-1.0f);
    p.left_arrow.align_with(p.left);p.left_arrow.mirror();p.left_arrow.set_colour(kText);
    p.right_arrow.add_quad(Point2{302.0f,1.0f},Point2{329.0f,30.0f},2,-1.0f);
    p.right_arrow.align_with(p.right);p.right_arrow.set_colour(kText);
    Label& t=p.title_label;
    t.font=menu_font_;t.scale=Point2{0.0712499991f,0.0712499991f};t.space_scale=2.0f;t.colour=kText;t.update_colour();
    const float bottom=p.title.position.y+p.title.size().y;t.position.y=bottom-0.03125f;
}
void ScoreView::initialise(const Texts& t) {
    texts_=&t;
    for(auto& p:pages_) {
        const QuadStrip& first=p.rows[0];
        for(int j=0;j<5;++j) {   // the headings over the rows (the values' are InitialisePage's)
            Label& h=p.headings[j];
            h.font=menu_font_;h.scale=Point2{0.0593749993f,0.0593749993f};h.space_scale=2.0f;
            h.position.y=first.position.y-0.015625f;
            h.colour=kText;h.update_colour();
            if(j==0) {h.set_text(t.get("scores.turns").c_str());h.position.x=first.position.x;}
            else if(j==4) {
                h.set_text(t.get("scores.score").c_str());
                const float right=first.position.x+first.size().x;const float x=right-0.00625000009f;
                h.position.x=x-h.width*h.scale.x;
            }
        }
        for(int r=0;r<10;++r) {
            const QuadStrip& rank=p.ranks[r];const QuadStrip& row=p.rows[r];
            for(int j=0;j<7;++j) {
                Label& l=p.lines[r][j];
                l.font=font_;l.space_scale=2.0f;
                if(j==0) {   // the rank, centred in its box
                    l.font=score_font_;l.scale=Point2{0.131249994f,0.131249994f};
                    l.set_text(printf_string(t.get("scores.rank").c_str(),r+1).c_str());
                    const Point2 size=rank.size();
                    const float half=size.x*0.5f;const float middle=rank.position.x+half;
                    const float w=l.width*l.scale.x;const float x=middle+w*-0.5f;
                    l.position.x=x-0.00312500005f;
                    const float bottom=rank.position.y+rank.size().y;l.position.y=bottom-0.0281249993f;
                } else if(j==1) {   // the name, at the top of the row
                    l.scale=Point2{0.100000001f,0.100000001f};
                    const float top=row.position.y+0.0531250015f;
                    l.position.x=row.position.x+0.0125000002f;l.position.y=top-0.00625000009f;
                } else {   // the numbers, at its bottom
                    l.scale=Point2{0.0900000036f,0.0900000036f};
                    const float bottom=row.position.y+row.size().y;l.position.y=bottom-0.00937500037f;
                }
            }
        }
    }
}
void ScoreView::initialise_page(const SessionObjects& o,std::int32_t k) {
    const std::int32_t table=o.scores_screen->page-1+k;
    if(static_cast<std::uint32_t>(table)>5u)return;
    const Texts& t=*texts_;
    Page& p=page(k);
    Label& title=p.title_label;
    title.set_text((table<=3?t.get("difficulty.name",table):t.get("mode.name",table-4)).c_str());
    {
        const float half=p.title.size().x*0.5f;const float middle=p.title.position.x+half;
        const float w=title.width*title.scale.x;title.position.x=middle+w*-0.5f;
    }
    const Colour button{150,150,255,255};
    p.left.set_colour(table==0?divided(button,2.0f):button);
    p.right.set_colour(table==5?divided(button,2.0f):button);
    const std::int32_t n=count_of(o,table);
    if(table==5) {
        label_text(p.headings[1],t.get("scores.avg").c_str(),0.400000006f);
        label_text(p.headings[2],t.get("scores.max").c_str(),0.590000033f);
        label_text(p.headings[3],t.get("scores.total").c_str(),0.779999971f);
    } else {
        label_text(p.headings[1],t.get("scores.xp").c_str(),0.400000006f);
        label_text(p.headings[2],t.get("scores.gp").c_str(),0.590000033f);
        label_text(p.headings[3],t.get("scores.up").c_str(),0.779999971f);
    }
    // ScoreScreen::SetLabelNumber 0x34c04: a number (in tenths with a divisor), right-aligned at x or left at it
    const auto number=[&t](Label& l,std::int32_t value,float x,bool left,std::int32_t divisor) {
        if(divisor==0)l.set_text(printf_string(t.get("scores.int").c_str(),value).c_str());
        else {
            const float v=static_cast<float>(value)/static_cast<float>(divisor);
            l.set_text(printf_string(t.get("scores.tenths").c_str(),static_cast<double>(v)).c_str());
        }
        const float w=left?0.0f:l.width*l.scale.x;l.position.x=x-w;
    };
    for(int r=0;r<10;++r) {
        p.ranks[r].set_alpha(n>r?255:128);p.rows[r].set_alpha(n>r?255:128);
        if(n<=r)continue;
        const ScoreRecord& e=o.scores->scores[table][r];
        Label* line=p.lines[r];
        line[1].set_text(std::string(e.name,strnlen(e.name,sizeof e.name)).c_str());
        number(line[2],e.turn,line[1].position.x,true,0);
        number(line[3],e.a,0.400000006f,false,table==5?10:0);
        number(line[4],e.b,0.590000033f,false,0);
        number(line[5],e.c,0.779999971f,false,0);
        const float right=p.rows[r].position.x+p.rows[r].size().x;
        number(line[6],e.score,right-0.0125000002f,false,0);
        const bool latest=o.scores->last_type==table && o.scores->last_pos==r;
        for(int j=0;j<7;++j){line[j].colour=latest?Colour{255,255,0,255}:Colour{255,255,255,255};line[j].update_colour();}
        for(int i=0;i<4;++i) {
            Point2 a{0.0f,0.0f},b{0.0f,0.0f};
            if(e.skills[i]!=-1)skill_uvs(e.skills[i],a,b);
            p.skills[r][i].set_uv(a,b);
        }
    }
}
void ScoreView::set_alpha(const SessionObjects& o,std::uint8_t a) {
    black_.set_alpha(a);backing_.set_alpha(a);banner_.set_alpha(a);back_.set_alpha(a);
    for(std::int32_t k=0;k<3;++k) {
        Page& p=page(k);
        const std::int32_t n=count_of(o,o.scores_screen->page+k-1);
        for(int r=0;r<10;++r) {
            const std::uint8_t dim=n<=r?static_cast<std::uint8_t>(a>>1):a;
            p.ranks[r].set_alpha(dim);p.rows[r].set_alpha(dim);
            for(auto& l:p.lines[r]){l.colour.a=a;l.update_colour();}
            for(auto& q:p.skills[r])q.set_alpha(a);
        }
        p.left.set_alpha(a);p.left_arrow.set_alpha(a);p.title.set_alpha(a);p.right.set_alpha(a);p.right_arrow.set_alpha(a);
        p.title_label.colour.a=a;p.title_label.update_colour();
        for(auto& h:p.headings){h.colour.a=a;h.update_colour();}
    }
}
void ScoreView::show(const SessionObjects& o,bool from_game) {
    initialise_page(o,0);initialise_page(o,1);initialise_page(o,2);
    set_alpha(o,from_game?255:0);
}
void ScoreView::process(const SessionObjects& o,const ScorePages& before) {
    const ScorePages& p=*o.scores_screen;
    if(before.timer>0.0f) {   // the 0.3 s fades (closed when the fade-out ends)
        if(p.timer>0.0f) {
            const float f=p.timer/0.300000012f;
            set_alpha(o,byte_of(before.closing?interpolate(255.0f,0.0f,f):interpolate(0.0f,255.0f,f)));
        } else if(!before.closing)set_alpha(o,byte_of(interpolate(0.0f,255.0f,0.0f)));
        return;
    }
    if(before.sliding)return;   // sliding (into place: turn_page)
    // a button pressed (alpha 150) or let go
    if(!before.back && p.back)back_.set_alpha(150);
    else if(!before.left && p.left)page(1).left.set_alpha(150);
    else if(!before.right && p.right)page(1).right.set_alpha(150);
    if(before.back && !p.back)back_.set_alpha(255);
    else if(before.left && !p.left)page(1).left.set_alpha(255);
    else if(before.right && !p.right)page(1).right.set_alpha(255);
}
void ScoreView::turn_page(const SessionObjects& o,std::int32_t direction) {
    const float d=static_cast<float>(direction);
    if(d>0.5f) {
        const std::int32_t a=slot_[0],b=slot_[1],c=slot_[2];slot_[0]=c;slot_[1]=a;slot_[2]=b;
        initialise_page(o,0);
    } else if(d<-0.5f) {
        const std::int32_t a=slot_[0],b=slot_[1],c=slot_[2];slot_[0]=b;slot_[1]=c;slot_[2]=a;
        initialise_page(o,2);
    }
}
std::int32_t ScoreView::button_at(Point2 touch) const {
    std::int32_t b=0;
    const Page& shown=page(1);
    if(back_.contains(touch))b=1;
    else if(shown.left.contains(touch))b=2;
    else if(shown.right.contains(touch))b=3;
    const Page& first=page(0);   // ScoreScreen::Process: the rows of the page object before (all are laid out alike)
    const QuadStrip& last=first.rows[9];
    if(touch.y>first.rows[0].position.y && touch.y<last.position.y+last.size().y)b|=16;
    return b;
}
void ScoreView::render_page(GL& gl,const SessionObjects& o,std::int32_t k) const {
    const Page& p=page(k);
    const std::int32_t at=o.scores_screen->page+k;
    gl.bind_texture(Menus);
    for(int r=0;r<10;++r){p.ranks[r].render(gl);p.rows[r].render(gl);}
    p.left.render(gl);p.title.render(gl);p.right.render(gl);
    if(at>1)p.left_arrow.render(gl);
    if(at<=5)p.right_arrow.render(gl);
    p.title_label.render(gl);
    const std::int32_t n=count_of(o,at-1);
    for(std::int32_t r=0;r<n && r<10;++r)for(const auto& l:p.lines[r])l.render(gl);
    gl.bind_texture(Tiles);
    for(std::int32_t r=0;r<n && r<10;++r)for(const auto& q:p.skills[r])q.render(gl);
    for(const auto& h:p.headings)h.render(gl);
}
void ScoreView::render(GL& gl,const SessionObjects& o) const {
    gl.bind_texture(NoTexture);black_.render(gl);backing_.render(gl);
    gl.bind_texture(Tiles);banner_.render(gl);
    gl.bind_texture(Menus);back_.render(gl);
    const float drag=o.scores_screen->drag;
    gl.push();gl.translate(drag,0.0f);render_page(gl,o,1);gl.pop();
    if(drag>0.00937500037f){gl.push();gl.translate(drag-1.0f,0.0f);render_page(gl,o,0);gl.pop();}
    else if(drag<-0.00937500037f){gl.push();gl.translate(drag+1.0f,0.0f);render_page(gl,o,2);gl.pop();}
}
}
