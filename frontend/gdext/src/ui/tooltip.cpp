#include "tooltip.hpp"
#include <algorithm>
#include <string>
namespace drui {
namespace {
constexpr Colour kWhite{255,255,255,255};
}
TooltipView::TooltipView(const Font* font):font_(font),title_(font) {
    for(int k=0;k<9;++k)quads_.set_quad_colour(k,255,255,255,0);
    // the frame's nine pieces (pixels of tiles.png): corners, edges and the middle
    const float pieces[9][4]={{498,498,13,13},{479,472,1,13},{380,415,15,13},{478,487,13,1},{145,399,1,1},
                              {380,430,15,1},{498,482,13,15},{483,470,1,15},{380,433,15,13}};
    for(int k=0;k<9;++k)quads_.set_quad(k,Point2{pieces[k][0],pieces[k][1]},Point2{pieces[k][2],pieces[k][3]});
    title_.scale=Point2{0.109999999f,0.109999999f};title_.space_scale=2.0f;
    title_.colour=Colour{255,255,0,0};title_.update_colour();
}
void TooltipView::set_size(float w,float h) {   // as UnlockMenu::SetSize: the corners, the edges between, the middle
    const float a=w*320.0f;const float b=a-13.0f;const float c=b-15.0f;const std::int32_t width=static_cast<std::int32_t>(c);
    const float d=h*320.0f;const float e=d-13.0f;const float f=e-15.0f;const std::int32_t height=static_cast<std::int32_t>(f);
    const float fw=static_cast<float>(width),fh=static_cast<float>(height);
    const float right=static_cast<float>(width+13),bottom=static_cast<float>(height+11);
    quads_.set_quad(0,0.0f,0.0f,13.0f,13.0f);quads_.set_quad(1,13.0f,0.0f,fw,13.0f);quads_.set_quad(2,right,0.0f,15.0f,13.0f);
    quads_.set_quad(3,0.0f,12.0f,13.0f,fh);quads_.set_quad(4,13.0f,12.0f,fw,fh);quads_.set_quad(5,right,12.0f,15.0f,fh);
    quads_.set_quad(6,0.0f,bottom,13.0f,15.0f);quads_.set_quad(7,13.0f,bottom,fw,15.0f);quads_.set_quad(8,right,bottom,15.0f,13.0f);
}
void TooltipView::add_label(const std::string& text,Colour colour) {
    if(static_cast<std::size_t>(count_)==lines_.size()) {
        lines_.emplace_back(font_);
        Label& l=lines_.back();l.space_scale=2.0f;l.scale=Point2{0.0900000036f,0.0900000036f};
        l.colour.a=0;l.update_colour();
    }
    Label& l=lines_[static_cast<std::size_t>(count_)];
    l.set_text(text.c_str());l.colour=colour;l.update_colour();
    ++count_;
}
// InitialiseLabels: a title (yellow, opaque) starts the text again; the text is cut into lines 0.85 wide at 0.09.
void TooltipView::initialise_labels(const Texts&,const char* title,const std::string& text,Colour colour) {
    if(title) {title_.set_text(title);title_.colour=Colour{255,255,0,255};title_.update_colour();}
    const std::vector<std::string> lines=split_lines(*font_,text,0.0900000036f,0.850000024f);
    if(title)count_=0;
    for(const auto& l:lines)add_label(l,colour);
}
void TooltipView::show(Point2 at,std::int32_t offset) {
    visible_=true;hiding_=false;
    const float ratio=static_cast<float>(font_->line_height-font_->base)/static_cast<float>(font_->line_height);
    const float spacing=ratio*0.109999999f;
    const float half=spacing*0.5f;
    const float x=half+0.0406249985f;const float y=spacing+0.0406249985f;
    title_.position=Point2{x,y};
    float widest=title_.width*title_.scale.x;
    for(std::int32_t i=0;i<count_;++i) {
        Label& l=lines_[static_cast<std::size_t>(i)];
        l.position.x=x;
        const float k=static_cast<float>(i+1)*spacing;l.position.y=y+k;
        const float w=l.width*l.scale.x;
        if(w>widest)widest=w;
    }
    const float pad=spacing+0.0874999985f;const float box_w=pad+widest;
    const float lines=spacing*static_cast<float>(count_);
    const float h1=half+lines;const float h2=h1+spacing;const float box_h=h2+0.0874999985f;
    if(at.y>1.0f) {   // above the point when low on the screen
        const float above=at.y-box_h;const float o=static_cast<float>(offset)/-320.0f;at_.y=above+o;
    } else {const float o=static_cast<float>(offset)/320.0f;at_.y=at.y+o;}
    float left=at.x-0.015625f;
    if(box_w+left>1.0f)left=1.0f-box_w;
    const float points=left*320.0f;
    at_.x=static_cast<float>(static_cast<std::int32_t>(points))/320.0f;
    set_size(box_w,box_h);
}
void TooltipView::show_enemy(const Texts& t,std::int32_t enemy,std::int32_t mortal,std::int32_t race,Point2 at) {
    const std::string& name=t.get("enemy.name",enemy);
    if(enemy!=0 && enemy==mortal) {   // the class's mortal enemy: red, with the race's weakness
        const Colour red{255,70,60,255};
        initialise_labels(t,printf_string(t.get("tooltip.mortal").c_str(),name.c_str()).c_str(),t.get("enemy.desc",enemy),kWhite);
        initialise_labels(t,nullptr,t.get("race.mortaldesc",race),red);
        title_.colour=red;title_.update_colour();
    } else initialise_labels(t,name.c_str(),t.get("enemy.desc",enemy),kWhite);
    show(at,25);
}
void TooltipView::show_skill(const Texts& t,std::int32_t skill,std::int32_t max,std::int32_t current,Point2 at) {
    initialise_labels(t,t.get("skill.name",skill).c_str(),t.get("skill.desc",skill),kWhite);
    if(max>0)add_label(printf_string(t.get("tooltip.cooldown").c_str(),current,max),kWhite);
    show(at,0);
}
void TooltipView::show_scroll(const Texts& t,std::int32_t skill,Point2 at) {
    const std::string& name=t.get("skill.name",skill);
    const std::string title=printf_string(t.get("tooltip.scroll").c_str(),name.c_str());
    initialise_labels(t,title.c_str(),printf_string(t.get("tooltip.scroll_text").c_str(),name.c_str(),t.get("skill.desc",skill).c_str()),kWhite);
    show(at,25);
}
void TooltipView::set_alpha(std::uint8_t a) {
    for(auto& v:quads_.v)v.colour[3]=a;
    title_.colour.a=a;title_.update_colour();
    for(std::int32_t i=0;i<count_;++i){Label& l=lines_[static_cast<std::size_t>(i)];l.colour.a=a;l.update_colour();}
}
void TooltipView::hide_instantly() {
    visible_=hiding_=false;
    for(int k=0;k<9;++k)quads_.set_quad_colour(k,255,255,255,0);
    title_.colour.a=0;title_.update_colour();
    for(std::int32_t i=0;i<count_;++i){Label& l=lines_[static_cast<std::size_t>(i)];l.colour.a=0;l.update_colour();}
}
void TooltipView::process(float dt) {   // in to 240, out to nothing (then hidden), 255 x 8 a second
    if(!visible_)return;
    const float alpha=static_cast<float>(quads_.v[0].colour[3]);
    const float step=dt*255.0f;
    std::int32_t a;
    if(hiding_) {const float d=step*-8.0f;a=static_cast<std::int32_t>(alpha+d);}
    else {const float d=step*8.0f;a=std::clamp(static_cast<std::int32_t>(alpha+d),0,240);}
    if(a<=0){visible_=hiding_=false;return;}
    set_alpha(static_cast<std::uint8_t>(a));
}
void TooltipView::render(GL& gl) const {
    gl.push();gl.translate(at_.x,at_.y);
    gl.bind_texture(Tiles);
    for(int k=0;k<9;++k)gl.draw(6,quads_.quad(k),4);
    title_.render(gl);
    for(std::int32_t i=0;i<count_;++i)lines_[static_cast<std::size_t>(i)].render(gl);
    gl.pop();
}
}
