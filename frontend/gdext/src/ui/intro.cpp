#include "intro.hpp"
using namespace dungeonraid;
namespace drui {
namespace {
float interpolate(float a,float b,float t) {const float x=a*t;const float y=(1.0f-t)*b;return x+y;}   // 0x1b800
}
IntroView::IntroView(const Font* font):font_(font),begin_(font) {   // IntroScreen::IntroScreen 0x2dbb8
    black_.set_size(Point2{2.0f,2.0f});black_.position=Point2{0.5f,0.5f};
}
void IntroView::initialise(const Texts& t,std::int32_t story) {
    black_.set_colour(Colour{0,0,0,0});
    begin_.colour=Colour{255,255,0,0};begin_.update_colour();
    begin_.scale=Point2{0.129999995f,0.129999995f};begin_.set_text(t.get("intro.begin").c_str());
    const float wb=begin_.width*begin_.scale.x;const float x=1.0f-wb;begin_.position.x=x*0.5f;begin_.position.y=1.42999995f;
    previous_=1;fade_=0.0f;closing_=false;
    // The lines' spacing from the font's line height and base (Game+0x1228 / 0x122c).
    const float ratio=static_cast<float>(font_->line_height-font_->base)/static_cast<float>(font_->line_height);
    const float spacing=ratio*0.119999997f*1.10000002f;
    const std::string text=t.get("story."+std::to_string(story));
    const char* s=text.c_str();
    // The story cut at spaces into lines no wider than 7.92 (0.95 of the screen at scale 0.12), each centred.
    count_=0;
    float width=0.0f,at_space=0.0f;
    std::int32_t i=0,start=0,space=0;
    for(;;) {
        const char c=s[i];
        bool emit=false;
        if(c==' '){space=i;at_space=width;}
        else if(c==0){space=i;at_space=width;emit=true;}
        if(!emit) {
            const float half=font_->size(c).x*0.5f;
            const float add=half+font_->advance(c,2.0f);
            width=width+add;
            emit=width>7.91666651f;
        }
        if(emit) {
            if(static_cast<std::size_t>(count_)==lines_.size()) {
                lines_.emplace_back(font_);
                Label& l=lines_.back();l.space_scale=2.0f;l.scale=Point2{0.119999997f,0.119999997f};
            }
            Label& l=lines_[static_cast<std::size_t>(count_)];
            const float a=at_space*-0.119999997f;const float b=a+1.0f;l.position.x=b*0.5f;
            const float k=static_cast<float>(count_+1);const float y=k*spacing;l.position.y=y+0.219999999f;
            l.set_text(s+start,space-start);
            ++count_;
            start=space+1;i=space;width=0.0f;
        }
        if(s[i]==0)break;
        ++i;
    }
    for(std::int32_t k=0;k<count_;++k){Label& l=lines_[static_cast<std::size_t>(k)];l.colour.a=0;l.update_colour();}
}
void IntroView::set_alpha(std::uint8_t a) {
    black_.set_alpha(a);
    begin_.colour.a=a;begin_.update_colour();
    for(std::int32_t k=0;k<count_;++k){Label& l=lines_[static_cast<std::size_t>(k)];l.colour.a=a;l.update_colour();}
}
bool IntroView::process(const SessionObjects& o,float dt) {
    const TouchState& touch=*o.touch;
    const bool fading_in=!closing_ && fade_<1.0f;
    if(!fading_in && fade_==1.0f && touch.phase==1 && previous_==0 && touch.position.y>1.32999992f &&
       touch.position.x>0.25f && touch.position.x<0.75f) {   // Begin
        begin_.colour=Colour{180,180,0,255};begin_.update_colour();
        sounds.push_back(18);
        closing_=true;fade_=0.0f;
    }
    previous_=touch.phase;
    if(!closing_ && !fading_in)return false;
    fade_=fade_+dt;
    if(fade_>=1.0f) {
        fade_=1.0f;
        if(closing_){closing_=false;return true;}
    }
    const float v=fading_in?interpolate(255.0f,0.0f,fade_):interpolate(0.0f,255.0f,fade_);
    set_alpha(static_cast<std::uint8_t>(static_cast<std::int32_t>(v)));
    return false;
}
void IntroView::render(GL& gl) const {
    gl.bind_texture(NoTexture);
    black_.render(gl);
    for(std::int32_t k=0;k<count_;++k)lines_[static_cast<std::size_t>(k)].render(gl);
    begin_.render(gl);
}
}
