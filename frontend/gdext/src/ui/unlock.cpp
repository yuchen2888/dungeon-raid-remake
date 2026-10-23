#include "unlock.hpp"
#include "setup.hpp"
#include <string>
using namespace dungeonraid;
namespace drui {
UnlockView::UnlockView(const Font* font):font_(font),title_(font) {
    for(int k=0;k<9;++k)quads_.set_quad_colour(k,255,255,255,0);
    // the frame's nine pieces (pixels of tiles.png): corners, edges and the middle
    const float pieces[9][4]={{498,1010,13,13},{479,984,1,13},{380,927,15,13},{478,999,13,1},{621,633,1,1},
                              {380,942,15,1},{498,994,13,15},{483,982,1,15},{380,945,15,13}};
    for(int k=0;k<9;++k)quads_.set_quad(k,Point2{pieces[k][0],pieces[k][1]},Point2{pieces[k][2],pieces[k][3]});
    title_.scale=Point2{0.119999997f,0.119999997f};title_.colour=Colour{255,255,0,0};title_.update_colour();
    title_.space_scale=2.0f;
    icon_.set_alpha(0);
}
void UnlockView::set_size(float w,float h) {
    const float a=w*320.0f;const float b=a-13.0f;const float c=b-15.0f;const std::int32_t width=static_cast<std::int32_t>(c);
    const float d=h*320.0f;const float e=d-13.0f;const float f=e-15.0f;const std::int32_t height=static_cast<std::int32_t>(f);
    const float fw=static_cast<float>(width),fh=static_cast<float>(height);
    const float right=static_cast<float>(width+13),bottom=static_cast<float>(height+11);
    quads_.set_quad(0,0.0f,0.0f,13.0f,13.0f);quads_.set_quad(1,13.0f,0.0f,fw,13.0f);quads_.set_quad(2,right,0.0f,15.0f,13.0f);
    quads_.set_quad(3,0.0f,12.0f,13.0f,fh);quads_.set_quad(4,13.0f,12.0f,fw,fh);quads_.set_quad(5,right,12.0f,15.0f,fh);
    quads_.set_quad(6,0.0f,bottom,13.0f,15.0f);quads_.set_quad(7,13.0f,bottom,fw,15.0f);quads_.set_quad(8,right,bottom,15.0f,13.0f);
}
void UnlockView::initialise_labels(const char* text) {   // cut at spaces into lines no wider than 6 (0.6 at scale 0.1)
    count_=0;
    float width=0.0f;
    std::int32_t i=0,start=0,space=0;
    for(;;) {
        const char c=text[i];
        bool emit=false;
        if(c==' ')space=i;
        else if(c==0){space=i;emit=true;}
        if(!emit) {
            const float half=font_->size(c).x*0.5f;
            const float add=half+font_->advance(c,2.0f);
            width=width+add;
            emit=width>6.0f;
        }
        if(emit) {
            if(static_cast<std::size_t>(count_)==lines_.size()) {
                lines_.emplace_back(font_);
                Label& l=lines_.back();l.space_scale=2.0f;l.scale=Point2{0.100000001f,0.100000001f};
                l.colour.a=0;l.update_colour();
            }
            lines_[static_cast<std::size_t>(count_)].set_text(text+start,space-start);
            ++count_;
            start=space+1;i=space;width=0.0f;
        }
        if(text[i]==0)break;
        ++i;
    }
}
void UnlockView::show(const char* title,const char* text) {
    const float ratio=static_cast<float>(font_->line_height-font_->base)/static_cast<float>(font_->line_height);
    const float gap=ratio*0.119999997f;
    const float spacing=ratio*0.120000005f;
    const float half=spacing*0.5f;
    title_.set_text(title);
    initialise_labels(text);
    Point2 u0,u1;skill_uvs(30,u0,u1);   // Upgrade::GetIconUVs(0, 3, 1024, 512): an icon's height
    const float span=u1.y-u0.y;const float pixels=span*1024.0f;const float icon=pixels/320.0f;
    const float top=gap+0.0406249985f;
    float widest=title_.width*title_.scale.x;
    const float below=top+spacing;
    const float x=half+0.0406249985f;
    const float first=below+icon;
    for(std::int32_t i=0;i<count_;++i) {
        Label& l=lines_[static_cast<std::size_t>(i)];
        l.position.x=x;
        const float k=static_cast<float>(i)*spacing;l.position.y=k+first;
        const float w=l.width*l.scale.x;
        if(w>widest)widest=w;
    }
    const float pad=spacing+0.0874999985f;const float box_w=pad+widest;
    title_.position.y=top;
    {
        const float middle=box_w*0.5f;const float w=title_.width*title_.scale.x;const float off=w*-0.5f;
        title_.position.x=middle+off;
    }
    icon_.set_uv(u0,u1);
    icon_.position.x=box_w*0.5f;
    {
        const float m=first+top;const float n=spacing*-0.5f;const float o=m+n;icon_.position.y=o*0.5f;
    }
    icon_.scale=Point2{icon,icon};
    const float lines=static_cast<float>(count_)*spacing;
    const float h1=half+lines;const float h2=h1+gap;const float h3=h2+icon;const float box_h=h3+0.0874999985f;
    {
        const float y=box_h*-0.5f;at_.y=y+0.75f;
        const float l=box_w*-0.5f;float left=l+0.5f;
        const float right=box_w+left;
        if(right>1.0f)left=1.0f-box_w;
        const float points=left*320.0f;
        at_.x=static_cast<float>(static_cast<std::int32_t>(points))/320.0f;
    }
    set_size(box_w,box_h);
}
void UnlockView::show(const Texts& t,std::int32_t type,std::int32_t level) {
    const std::string& name=t.get("class.name",type);
    if(level>1) {
        const std::string title=printf_string(t.get("unlock.level_title").c_str(),name.c_str());
        const std::string text=printf_string(t.get("unlock.level_text").c_str(),name.c_str(),level);
        show(title.c_str(),text.c_str());
    } else {
        const std::string title=printf_string(t.get("unlock.class_title").c_str(),name.c_str());
        show(title.c_str(),t.get("class.unlock",type).c_str());
    }
    Point2 a,b;icon_coords(0,type,-1,a,b);icon_.set_uv(texels(a),texels(b));   // CharacterClass::GetIconCoords(ClassType)
    texture_=Menus;
}
void UnlockView::set_alpha(std::uint8_t a) {
    for(auto& v:quads_.v)v.colour[3]=a;
    title_.colour.a=a;title_.update_colour();
    for(std::int32_t i=0;i<count_;++i){Label& l=lines_[static_cast<std::size_t>(i)];l.colour.a=a;l.update_colour();}
    icon_.set_alpha(a);
}
void UnlockView::render(GL& gl) const {
    gl.push();gl.translate(at_.x,at_.y);
    gl.bind_texture(Tiles);
    for(int k=0;k<9;++k)gl.draw(6,quads_.quad(k),4);
    gl.bind_texture(texture_);icon_.render(gl);
    title_.render(gl);
    for(std::int32_t i=0;i<count_;++i)lines_[static_cast<std::size_t>(i)].render(gl);
    gl.pop();
}
}
