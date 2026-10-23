#include "setup.hpp"
using namespace dungeonraid;
namespace drui {
namespace {
float interpolate(float a,float b,float t) {const float x=a*t;const float y=(1.0f-t)*b;return x+y;}   // 0x1b800
constexpr Colour kButton{150,150,255,255};
constexpr Colour kChosen{75,75,127,255};   // (150, 150, 255, 255) / 2
constexpr float kEdge=0.00937500037f;
}
ModeView::ModeView(const Font* font,const Font* menu_font):font_(font),menu_font_(menu_font) {   // 0x1137dc
    black_.set_size(Point2{1.0f,1.5f});black_.position=Point2{0.5f,0.75f};black_.set_colour(Colour{0,0,0,255});
    done_.add_quad(Point2{104.0f,1.0f},Point2{193.0f,27.0f},2,-1.0f);   // Back, in the bottom-right corner
    {
        const Point2 s=done_.size();
        const float a=1.0f-s.x;const float x=a-kEdge;
        const float b=1.5f-s.y;const float y=b-kEdge;
        done_.set_position(Point2{x,y});
    }
    const float height=done_.position.y-kEdge;   // the panels' backing reaches down to Back
    back_.set_size(Point2{1.0f,height});back_.position=Point2{0.5f,height*0.5f};back_.set_colour(Colour{45,45,75,255});
    make_panel(heading_,true,0.96875f,0.268750012f,0.015625f,0.015625f);
    const Point2 uv0[2]={Point2{399.0f,378.0f},Point2{409.0f,324.0f}},uv1[2]={Point2{511.0f,431.0f},Point2{511.0f,377.0f}};
    for(int k=0;k<2;++k) {   // the two modes' buttons with their pictures
        const float a=heading_.position.x+0.015625f;const float b=static_cast<float>(k)*0.4765625f;const float x=a+b;
        const float c=heading_.position.y+0.0718749985f;const float y=c+0.015625f;
        make_button(buttons_[k],0.4609375f,0.165625006f,x,y);
        icons_[k].add_quad(uv0[k],uv1[k],2,-1.0f);icons_[k].align_with(buttons_[k]);
    }
    {
        const Point2 hs=heading_.size();
        const float a=heading_.position.y+hs.y;const float y=a+0.03125f;
        make_panel(intro_panel_,false,0.96875f,hs.y,0.015625f,y);
    }
    picture_.add_quad(Point2{77.0f,225.0f},Point2{152.0f,301.0f},2,-1.0f);
    picture_.align_with(intro_panel_);
    {
        const float a=picture_.position.y+intro_panel_.position.x;const float x=a-intro_panel_.position.y;
        picture_.set_position(Point2{x,picture_.position.y});
    }
    {
        const float a=intro_panel_.position.y+intro_panel_.size().y;const float y=a+0.03125f;
        make_panel(scoring_,true,0.96875f,0.3125f,0.015625f,y);
    }
    {
        const float a=scoring_.position.y+scoring_.size().y;
        const float b=height-a;const float c=b-0.03125f;const float h=c-0.015625f;
        const float d=scoring_.position.y+scoring_.size().y;const float y=d+0.03125f;
        make_panel(rules_,true,0.96875f,h,0.015625f,y);
    }
}
void ModeView::initialise(const Texts& t) {   // 0x112a8c
    texts_=&t;
    make_heading_label(heading_,heading_label_,menu_font_,t.get("mode.heading"));
    make_heading_label(scoring_,scoring_label_,menu_font_,t.get("mode.scoring"));
    make_heading_label(rules_,rules_label_,menu_font_,t.get("mode.rules"));
}
void ModeView::set_alpha(std::uint8_t a) {   // 0x112ad8
    black_.set_alpha(a);back_.set_alpha(a);done_.set_alpha(a);heading_.set_alpha(a);
    heading_label_.colour.a=a;heading_label_.update_colour();
    buttons_[0].set_alpha(a);icons_[0].set_alpha(a);buttons_[1].set_alpha(a);icons_[1].set_alpha(a);
    intro_panel_.set_alpha(a);picture_.set_alpha(a);
    for(std::int32_t k=0;k<intro_count_;++k){Label& l=intro_[static_cast<std::size_t>(k)];l.colour.a=a;l.update_colour();}
    scoring_.set_alpha(a);scoring_label_.colour.a=a;scoring_label_.update_colour();
    for(std::int32_t k=0;k<scoring_count_;++k){Label& l=scoring_lines_[static_cast<std::size_t>(k)];l.colour.a=a;l.update_colour();}
    rules_.set_alpha(a);rules_label_.colour.a=a;rules_label_.update_colour();
    for(std::int32_t k=0;k<rules_count_;++k){Label& l=rules_lines_[static_cast<std::size_t>(k)];l.colour.a=a;l.update_colour();}
}
void ModeView::show() {   // 0x112bec
    open_=true;closing_=false;timer_=0.300000012f;previous_=1;pressed_=false;
    set_alpha(0);
}
void ModeView::add_label(const std::string& text,const QuadStrip& panel,std::vector<Label>& lines,std::int32_t& count,
                         float indent) {   // AddLabel 0x112e28
    if(static_cast<std::size_t>(count)>=lines.size()) {
        lines.emplace_back();
        Label& b=lines.back();b.font=font_;b.space_scale=2.0f;b.scale=Point2{0.100000001f,0.100000001f};
    }
    Label& l=lines[static_cast<std::size_t>(count)];
    l.set_text(text.c_str());
    const float a=panel.position.x+0.015625f;l.position.x=a+indent;
    const float k=static_cast<float>(count+1);const float b=k*0.0540000014f;const float c=panel.position.y+b;
    l.position.y=c+(indent>0.0f?0.015625f:0.0718749985f);
    ++count;
}
void ModeView::show_mode(std::int32_t mode) {   // ShowMode 0x112f84
    intro_count_=0;scoring_count_=0;rules_count_=0;
    const float indent=picture_.position.x+picture_.size().x;
    if(mode==0)picture_.set_uv(Point2{77.0f,225.0f},Point2{152.0f,301.0f});
    else picture_.set_uv(Point2{1.0f,225.0f},Point2{76.0f,301.0f});
    const std::string m=std::to_string(mode);
    for(int k=0;k<4;++k)add_label(texts_->get("mode.intro."+m,k),intro_panel_,intro_,intro_count_,indent);
    for(int k=0;k<4;++k)add_label(texts_->get("mode.score."+m,k),scoring_,scoring_lines_,scoring_count_,0.0f);
    for(int k=0;k<6;++k)add_label(texts_->get("mode.special."+m,k),rules_,rules_lines_,rules_count_,0.0f);
}
void ModeView::update_mode(const SessionObjects& o) {   // UpdateMode 0x113730
    if(!open_ || o.stroke->mode_14ae8==shown_)return;
    shown_=o.stroke->mode_14ae8;
    const std::uint8_t a=black_.v[0].colour[3];
    show_mode(shown_);
    for(int k=0;k<2;++k)buttons_[k].set_colour(k==shown_?kChosen:kButton);
    set_alpha(a);
}
std::int32_t ModeView::process(const SessionObjects& o,float dt) {   // Process 0x112c0c
    if(timer_>0.0f) {   // the fades
        timer_=timer_-dt;
        if(!(timer_>0.0f)) {
            timer_=0.0f;
            if(closing_){open_=false;return -1;}
        }
        const float t=timer_/0.300000012f;
        const float v=closing_?interpolate(255.0f,0.0f,t):interpolate(0.0f,255.0f,t);
        set_alpha(static_cast<std::uint8_t>(static_cast<std::int32_t>(v)));
        return -1;
    }
    const TouchState& touch=*o.touch;
    if(touch.phase==1 && previous_==0) {   // a touch starts: Back pressed, or a mode chosen (sound 0, Game::SetMode)
        previous_=1;
        if(done_.contains(touch.position)){pressed_=true;done_.set_alpha(150);if(sounds)sounds->push_back(0);return -1;}
        for(int k=0;k<2;++k)if(buttons_[k].contains(touch.position))return k;   // (its click: dr_session_setup_mode's)
        return -1;
    }
    if(previous_==1 && touch.phase==0) {   // it ended: let go on Back, the screen fades out
        previous_=0;
        if(pressed_) {
            if(done_.contains(touch.position)){closing_=true;timer_=0.300000012f;}
            done_.set_alpha(255);pressed_=false;
        }
    }
    return -1;
}
void ModeView::render(GL& gl) const {   // Render 0x112d3c
    gl.bind_texture(NoTexture);
    black_.render(gl);back_.render(gl);
    gl.bind_texture(Menus);
    done_.render(gl);heading_.render(gl);
    buttons_[0].render(gl);icons_[0].render(gl);buttons_[1].render(gl);icons_[1].render(gl);
    intro_panel_.render(gl);picture_.render(gl);scoring_.render(gl);rules_.render(gl);
    heading_label_.render(gl);scoring_label_.render(gl);rules_label_.render(gl);
    for(std::int32_t k=0;k<intro_count_;++k)intro_[static_cast<std::size_t>(k)].render(gl);
    for(std::int32_t k=0;k<scoring_count_;++k)scoring_lines_[static_cast<std::size_t>(k)].render(gl);
    for(std::int32_t k=0;k<rules_count_;++k)rules_lines_[static_cast<std::size_t>(k)].render(gl);
}
}
