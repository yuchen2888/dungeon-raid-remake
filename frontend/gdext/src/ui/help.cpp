#include "help.hpp"
namespace drui {
namespace {
float interpolate(float a,float b,float t) {const float x=a*t;const float y=(1.0f-t)*b;return x+y;}   // 0x1b800
float clamp(float v,float lo,float hi) {if(v>=hi)return hi;return v<=lo?lo:v;}                            // 0x1b73c
}
HelpView::HelpView(const Font* font):font_(font),quads_(13) {
    for(int q=0;q<13;++q)quads_.set_quad_colour(q,255,255,255,240);
    const float pieces[11][4]={{495,249,16,15},{399,391,1,15},{380,391,17,15},{380,408,16,1},{383,402,1,1},{478,429,17,1},
                               {426,269,16,17},{399,407,1,17},{408,269,17,17},{399,391,1,15},{399,407,1,17}};
    for(int q=0;q<11;++q)quads_.set_quad(q,Point2{pieces[q][0],pieces[q][1]},Point2{pieces[q][2],pieces[q][3]});
}
void HelpView::set_size(float width,float height,float pointer,bool below) {
    const float points=width*320.0f;
    const std::int32_t w=static_cast<std::int32_t>((points-16.0f)-17.0f);
    const std::int32_t h=static_cast<std::int32_t>((height*320.0f-15.0f)-17.0f);
    const bool left=pointer<0.5f;
    const std::int32_t at=static_cast<std::int32_t>(points*pointer)-(left?6:20);   // the pointer's left edge
    const float right=static_cast<float>(w+16),bottom=static_cast<float>(h+15);
    const float fw=static_cast<float>(w),fh=static_cast<float>(h);
    quads_.set_quad(0,0.0f,0.0f,16.0f,15.0f);
    const Point2 far{1000.0f,1000.0f},none{0.0f,0.0f};
    if(below) {   // the pointer on the top edge, which it splits (1 left of it, 9 right)
        quads_.set_quad(1,16.0f,0.0f,static_cast<float>(at-16),15.0f);
        quads_.set_quad(2,right,0.0f,17.0f,15.0f);
        quads_.set_quad(3,0.0f,15.0f,16.0f,fh);
        quads_.set_quad(4,16.0f,15.0f,fw,fh);
        quads_.set_quad(5,right,15.0f,17.0f,fh);
        quads_.set_quad(6,0.0f,bottom,16.0f,17.0f);
        quads_.set_quad(7,16.0f,bottom,fw,17.0f);
        quads_.set_quad(8,right,bottom,17.0f,17.0f);
        quads_.set_quad(11,Point2{left?454.0f:483.0f,265.0f},Point2{28.0f,39.0f});
        const float x=static_cast<float>(at);
        quads_.set_quad(11,x,-24.0f,28.0f,39.0f);
        quads_.set_quad(9,Point2{399.0f,391.0f},Point2{1.0f,15.0f});
        quads_.set_quad(9,x+28.0f,0.0f,static_cast<float>(w+16-at)-28.0f,15.0f);
        quads_.set_quad(10,far,none,none,1.0f,1.0f);
        quads_.set_quad(12,far,none,none,1.0f,1.0f);
    } else {      // the pointer on the bottom edge (7 left of it, 10 right)
        quads_.set_quad(1,16.0f,0.0f,fw,15.0f);
        quads_.set_quad(2,right,0.0f,17.0f,15.0f);
        quads_.set_quad(3,0.0f,15.0f,16.0f,fh);
        quads_.set_quad(4,16.0f,15.0f,fw,fh);
        quads_.set_quad(5,right,15.0f,17.0f,fh);
        quads_.set_quad(6,0.0f,bottom,16.0f,17.0f);
        quads_.set_quad(7,16.0f,bottom,static_cast<float>(at-16),17.0f);
        quads_.set_quad(8,right,bottom,17.0f,17.0f);
        quads_.set_quad(12,Point2{left?454.0f:483.0f,305.0f},Point2{28.0f,41.0f});
        const float x=static_cast<float>(at);
        quads_.set_quad(12,x,bottom,28.0f,41.0f);
        quads_.set_quad(10,Point2{399.0f,407.0f},Point2{1.0f,17.0f});
        quads_.set_quad(10,x+28.0f,bottom,static_cast<float>(w+16-at)-28.0f,17.0f);
        quads_.set_quad(9,far,none,none,1.0f,1.0f);
        quads_.set_quad(11,far,none,none,1.0f,1.0f);
    }
}
void HelpView::show(const std::string& text,float x,float y,float up,float down) {
    width_=0.980000019f;
    // InitialiseLabels(text, 0.88): Font::SplitLines at scale 0.1 into the kept labels (new ones black, scale 0.1)
    const std::vector<std::string> lines=split_lines(*font_,text,0.100000001f,0.879999995f);
    count_=0;
    for(const std::string& line:lines) {
        if(static_cast<std::size_t>(count_)==labels_.size()) {
            Label l(font_);l.space_scale=2.0f;l.scale=Point2{0.100000001f,0.100000001f};l.colour=Colour{0,0,0,0};l.update_colour();
            labels_.push_back(l);
        }
        labels_[static_cast<std::size_t>(count_++)].set_text(line.c_str());
    }
    for(int q=0;q<13;++q)for(int k=0;k<4;++k)quads_.v[static_cast<std::size_t>(4*q+k)].colour[3]=0;
    for(std::int32_t i=0;i<count_;++i){Label& l=labels_[static_cast<std::size_t>(i)];l.colour.a=0;l.update_colour();}
    const bool below=y<0.75f;
    const float offset=below?down:-up;
    const float px=clamp(x,0.100000001f,0.899999976f);
    height_=(static_cast<float>(count_)*0.0500000007f+0.100000001f)+0.0299999993f;
    for(std::int32_t i=0;i<count_;++i)
        labels_[static_cast<std::size_t>(i)].position=Point2{0.0599999987f,static_cast<float>(i)*0.0500000007f+0.100000001f};
    at_.x=(1.0f-width_)*0.5f;
    const float lift=below?0.0625f:-0.0625f-height_;
    const float top=lift+(offset+y);
    at_.x=static_cast<float>(static_cast<std::int32_t>(at_.x*320.0f))/320.0f;
    at_.y=static_cast<float>(static_cast<std::int32_t>(top*320.0f))/320.0f;
    set_size(width_,height_,(px-at_.x)/width_,below);
}
void HelpView::set_alpha(std::uint8_t a) {
    for(auto& v:quads_.v)v.colour[3]=a;
    for(std::int32_t i=0;i<count_;++i){Label& l=labels_[static_cast<std::size_t>(i)];l.colour.a=a;l.update_colour();}
}
void HelpView::fade(float timer,bool closing,float dt) {
    if(!(timer>0.0f))return;
    float t=timer-dt;
    if(!(t>0.0f)) {
        if(closing)return;   // closed (the session shows a queued text next)
        t=0.0f;
    }
    const float r=t/0.200000003f;
    const float a=closing?interpolate(240.0f,0.0f,r):interpolate(0.0f,240.0f,r);
    set_alpha(static_cast<std::uint8_t>(static_cast<std::int32_t>(a)));
}
std::int32_t HelpView::button_at(Point2 p) const {
    if(!(p.x>at_.x))return -1;
    if(!(p.x<at_.x+width_))return -1;
    if(!(p.y>at_.y))return -1;
    return p.y<at_.y+height_?0:-1;
}
void HelpView::render(GL& gl) const {
    gl.push();
    gl.translate(at_.x,at_.y);
    gl.bind_texture(Tiles);
    for(int q=0;q<13;++q)gl.draw(6,quads_.quad(q),4);
    for(std::int32_t i=0;i<count_;++i)labels_[static_cast<std::size_t>(i)].render(gl);
    gl.pop();
}
}
