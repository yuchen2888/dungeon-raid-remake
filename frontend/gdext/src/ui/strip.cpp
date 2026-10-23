#include "strip.hpp"
namespace drui {
Point2 QuadStrip::picture(const Quad& q) const {
    const float dv=q.v[3].v-q.v[0].v;
    const float size=static_cast<float>(texture_size);
    const float du=q.v[3].u-q.v[0].u;
    const float w=du*size,h=dv*size;
    return Point2{w/320.0f,h/320.0f};
}
void QuadStrip::add_quad(Point2 uv0,Point2 uv1,std::int32_t policy,float extent) {
    quads.emplace_back();policies.push_back(policy);extents.push_back(extent);rows.push_back(row);
    const float size=static_cast<float>(texture_size);
    quads.back().set_uv(Point2{uv0.x/size,uv0.y/size},Point2{uv1.x/size,uv1.y/size});
    update_size();
}
void QuadStrip::add_quad() {
    quads.emplace_back();policies.push_back(3);extents.push_back(-1.0f);rows.push_back(row);
    quads.back().set_uv(0.0f,0.0f,0.0f,0.0f);
    update_size();
}
Point2 QuadStrip::fixed_size(std::int32_t r,std::int32_t c) const {
    float x=0.0f,y=0.0f;
    std::int32_t column=-1;
    for(std::size_t i=0;i<quads.size();++i) {
        if(i==0 || rows[i]==rows[i-1])column+=1;else column=0;
        if(r>=0 && rows[i]!=r && c>=0 && c!=column)continue;
        const Point2 p=picture(quads[i]);
        float h=p.y;
        const std::int32_t policy=policies[i];
        if(c==-1 && r==-1) {
            y=h;
            if(policy!=2 && policy!=0)continue;
        } else {
            if(policy==2 || policy==1) {
                const float e=extents[i];
                h=e>=0.0f?y+e:h+y;
                y=h;
                if(policy!=2)continue;
            } else if(policy!=0)continue;
        }
        x=x+p.x;
    }
    return Point2{x,y};
}
void QuadStrip::update_size() {
    std::int32_t column=-1;
    for(std::size_t i=0;i<quads.size();++i) {
        if(i>0 && rows[i]!=rows[i-1])column=0;else column+=1;
        const Point2 taken=fixed_size(rows[i],column);
        const float rest_x=fixed.x-taken.x,rest_y=fixed.y-taken.y;
        const Point2 p=picture(quads[i]);
        float extent=extents[i];
        if(extent<0.0f)extent=p.y;
        switch(policies[i]) {
        case 0: quads[i].set_size(Point2{p.x,rest_y});break;
        case 1: quads[i].set_size(Point2{rest_x,extent});break;
        case 2: quads[i].set_size(Point2{p.x,extent});break;
        case 3: quads[i].set_size(Point2{rest_x,rest_y});break;
        default: break;
        }
    }
    set_position(position);
}
Point2 QuadStrip::size() const {return has_fixed?fixed:fixed_size(-1,-1);}
Point2 QuadStrip::middle() const {
    const Point2 s=size();const Point2 h{s.x/2.0f,s.y/2.0f};
    return Point2{position.x+h.x,position.y+h.y};
}
void QuadStrip::set_position(Point2 p) {
    position=p;
    float x=p.x,y=p.y;
    for(std::size_t i=0;i<quads.size();++i) {
        Quad& q=quads[i];
        const Point2 h{q.size.x/2.0f,q.size.y/2.0f};
        q.position=Point2{x+h.x,y+h.y};
        if(i+1<quads.size() && rows[i]!=rows[i+1]){x=position.x;y=y+q.size.y;}
        else x=x+q.size.x;
    }
}
void QuadStrip::set_position_centre(Point2 p) {
    const Point2 s=size();const Point2 h{s.x/2.0f,s.y/2.0f};
    set_position(Point2{p.x-h.x,p.y-h.y});
}
void QuadStrip::align_with(const QuadStrip& other) {
    const Point2 a=other.size(),b=size();
    const Point2 d{a.x-b.x,a.y-b.y};const Point2 h{d.x/2.0f,d.y/2.0f};
    set_position(Point2{other.position.x+h.x,other.position.y+h.y});
}
void QuadStrip::set_uv(Point2 uv0,Point2 uv1) {
    const float size=static_cast<float>(texture_size);
    quads.back().set_uv(Point2{uv0.x/size,uv0.y/size},Point2{uv1.x/size,uv1.y/size});
}
void QuadStrip::set_colour(Colour c) {for(auto& q:quads)q.set_colour(c);}
void QuadStrip::set_alpha(std::uint8_t a) {for(auto& q:quads)q.set_alpha(a);}
void QuadStrip::mirror() {
    for(auto& q:quads) {
        const float u0=q.v[0].u,v0=q.v[0].v,u1=q.v[3].u,v1=q.v[3].v;
        q.set_uv(Point2{u1,v0},Point2{u0,v1});
    }
}
bool QuadStrip::contains(Point2 p) const {
    for(const auto& q:quads)if(q.contains(p))return true;
    return false;
}
void QuadStrip::render(GL& gl) const {for(const auto& q:quads)q.render(gl);}
}
