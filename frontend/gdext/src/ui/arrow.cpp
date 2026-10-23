#include "arrow.hpp"
#include <cmath>
#include <cstring>
namespace drui {
namespace {
float bits(std::uint32_t b) {float f;std::memcpy(&f,&b,4);return f;}   // a literal of the original, exactly
// GLfloat2::Normalise 0x1b508.
void normalise(Point2& p) {const float a=p.x*p.x,b=p.y*p.y;const float len=std::sqrt(a+b);p.x=p.x/len;p.y=p.y/len;}
// A component of a snapped direction (0x1d9ec..): above 0.1 it is 1, then below -0.1 it is -1.
float snap(float c) {if(c>0.100000001f)c=1.0f;if(c<-0.100000001f)c=-1.0f;return c;}
std::uint8_t alpha_of(std::int32_t k,std::size_t n) {   // 100 at the start up to 200 at the head (vcvt.u32.f32, uxtb)
    const float r=static_cast<float>(k)/static_cast<float>(static_cast<std::uint32_t>(n));
    const float a=r*100.0f+100.0f;
    return static_cast<std::uint8_t>(a<=0.0f?0u:static_cast<std::uint32_t>(a));
}
constexpr float half=0.0140624996f;   // half the line's width
}
void ArrowView::set_colour(std::uint32_t r,std::uint32_t g,std::uint32_t b) {
    for(auto& p:v){p.colour[0]=static_cast<std::uint8_t>(r);p.colour[1]=static_cast<std::uint8_t>(g);p.colour[2]=static_cast<std::uint8_t>(b);}
}
void ArrowView::add(Point2 p,std::uint8_t alpha,float u,float w) {
    if(count>=288)return;
    Vertex& d=v[count++];d.x=p.x;d.y=p.y;d.colour[3]=alpha;d.u=u;d.v=w;
}
void ArrowView::render(GL& gl) const {
    gl.load_identity();
    for(std::int32_t i=0;i<count/4;++i)gl.draw(6,v+4*i,4);
}
// Arrow::Update 0x1d868, block by block: every path tile gets a type (0 start, 1 straight, 2 / 3 / 4 corners of
// 90 / 45 / 135 degrees, 5 the head) and a sideways vector nn (half the width; for corners the mitre of the bisector);
// each tile finishes the previous run's quad with two vertices and opens the next with two, with the corner's or
// cap's quad between. The vertices' alpha grows from 100 to 200 along the path.
void ArrowView::update(const dungeonraid::SelectionState& s) {
    count=0;
    const std::size_t n=s.path_length;
    if(n<=1)return;
    const dungeonraid::SelectionTile* prev=nullptr;
    std::int32_t k=1;
    for(std::size_t i=0;i<n;++i) {
        const dungeonraid::SelectionTile* cur=&s.tiles[s.path[i]];
        const dungeonraid::SelectionTile* next=i+1<n?&s.tiles[s.path[i+1]]:nullptr;
        const std::uint8_t alpha=alpha_of(k,n);
        const Point2 P=cur->geometry.center;
        Point2 nn{0,0};
        int type=0;bool flip=false;
        if(!prev || !next) {
            Point2 d;
            if(prev) {d.y=P.y-prev->geometry.center.y;d.x=P.x-prev->geometry.center.x;}
            else {d.y=next->geometry.center.y-P.y;d.x=next->geometry.center.x-P.x;}
            normalise(d);
            const float y=d.y*half;nn.x=-y;nn.y=d.x*half;
            type=next?0:5;
        } else {
            Point2 a{P.x-prev->geometry.center.x,P.y-prev->geometry.center.y};normalise(a);
            Point2 b{next->geometry.center.x-P.x,next->geometry.center.y-P.y};normalise(b);
            Point2 m;m.y=a.y+b.y;m.x=a.x+b.x;normalise(m);
            const float my=m.y*half;nn.x=-my;nn.y=m.x*half;
            const float ax=snap(a.x),bx=snap(b.x),ay=snap(a.y),by=snap(b.y);
            float factor=1.0f;
            if(ax==bx && ay==by) type=1;
            else if(ax==by && ay==-bx) {type=2;flip=true;factor=bits(0x3fb504f3);}
            else if(ax==-by && bx==ay) {type=2;flip=ax==by && ay==-bx;factor=bits(0x3fb504f3);}   // (0x1db06: vmrs, then the IT)
            else if(ax==bx || by==ay) {
                type=3;factor=bits(0x3f8a8bd4);
                if(ax==0.0f)flip=ay!=bx;
                else if(ay==0.0f)flip=ax==by;
                else if(ax!=ay)flip=by==0.0f;
                else flip=bx==0.0f;
            } else {
                type=4;factor=bits(0x40273d75);
                if(ax==0.0f)flip=bx!=ay;
                else if(ay==0.0f)flip=ax==by;
                else if(ax==ay)flip=bx!=0.0f;
                else flip=by!=0.0f;
            }
            if(type!=1){nn.x=nn.x*factor;nn.y=nn.y*factor;}
        }
        const Point2 from=prev?prev->geometry.center:P,to=next?next->geometry.center:P;
        switch(type) {
        case 0: {   // the start cap (0x1e2de), then the run's first side
            Point2 d{to.x-P.x,to.y-P.y};normalise(d);
            const float dx=d.x*half,dy=d.y*half;
            const float by=P.y-dy,bx=P.x-dx;
            add(Point2{bx-nn.x,by-nn.y},alpha,0.293945312f,0.35546875f);
            add(Point2{bx+nn.x,by+nn.y},alpha,0.293945312f,0.362304688f);
            add(Point2{P.x+nn.x,P.y+nn.y},alpha,0.297851562f,0.362304688f);
            add(Point2{P.x-nn.x,P.y-nn.y},alpha,0.297851562f,0.35546875f);
            add(Point2{P.x-nn.x,P.y-nn.y},alpha,0.263671875f,0.362304688f);
            add(Point2{P.x+nn.x,P.y+nn.y},alpha,0.263671875f,0.35546875f);
            break;
        }
        case 1:   // straight (0x1e27e, 0x1e3f6)
            add(Point2{P.x+nn.x,P.y+nn.y},alpha,0.263671875f,0.35546875f);
            add(Point2{P.x-nn.x,P.y-nn.y},alpha,0.263671875f,0.362304688f);
            add(Point2{P.x-nn.x,P.y-nn.y},alpha,0.263671875f,0.362304688f);
            add(Point2{P.x+nn.x,P.y+nn.y},alpha,0.263671875f,0.35546875f);
            break;
        case 5: {   // the end of the run and the head (0x1e27e, 0x1e454)
            add(Point2{P.x+nn.x,P.y+nn.y},alpha,0.263671875f,0.35546875f);
            add(Point2{P.x-nn.x,P.y-nn.y},alpha,0.263671875f,0.362304688f);
            const float len=std::sqrt(nn.x*nn.x+nn.y*nn.y);
            const float scale=0.0250000004f/len+1.0f;
            const float hx=nn.x*scale,hy=scale*nn.y;
            add(Point2{P.x-hx,P.y-hy},alpha,0.299804688f,0.356445312f);
            add(P,alpha,0.309082031f,0.356445312f);
            add(Point2{P.x+hx,P.y+hy},alpha,0.318359375f,0.356445312f);
            add(Point2{P.x+hy,P.y-hx},alpha,0.309082031f,0.366210938f);
            break;
        }
        case 2: {   // 90 degrees (0x1de7c)
            Point2 f{P.x-from.x,P.y-from.y};normalise(f);
            const float fx=f.x*half,fy=f.y*half;
            Point2 e{to.x-P.x,to.y-P.y};normalise(e);
            const float ex=e.x*half,ey=e.y*half;
            const float sy=P.y-fy,sx=P.x-fx;
            const Point2 c{sx+ex,sy+ey},d{sx-ex,sy-ey};
            const float mx=flip?-nn.x:nn.x,my=flip?-nn.y:nn.y;
            const Point2 a{P.x+mx,P.y+my};
            const float ty=P.y+ey;const float tx=P.x+ex;
            const Point2 b{tx+fx,ty+fy};
            if(flip) {
                add(c,alpha,0.263671875f,0.35546875f);add(d,alpha,0.263671875f,0.362304688f);
                add(c,alpha,0.267578125f,0.362304688f);add(d,alpha,0.267578125f,0.35546875f);
                add(a,alpha,0.274414062f,0.35546875f);add(b,alpha,0.274414062f,0.362304688f);
                add(b,alpha,0.263671875f,0.362304688f);add(c,alpha,0.263671875f,0.35546875f);
            } else {
                add(d,alpha,0.263671875f,0.35546875f);add(c,alpha,0.263671875f,0.362304688f);
                add(c,alpha,0.267578125f,0.362304688f);add(d,alpha,0.267578125f,0.35546875f);
                add(a,alpha,0.274414062f,0.35546875f);add(b,alpha,0.274414062f,0.362304688f);
                add(c,alpha,0.263671875f,0.362304688f);add(b,alpha,0.263671875f,0.35546875f);
            }
            break;
        }
        case 3: case 4: {   // 45 (0x1dc56) and 135 degrees (0x1dff2): mitred joins of the two runs
            const float m=bits(type==3?0x3bbedea1u:0x3d0b0f07u);   // the literals at 0x1dc28 / 0x1e168
            Point2 b{P.x-from.x,P.y-from.y};normalise(b);
            const float b1x=b.x*m,b2=-(b.y*half),b1y=b.y*m,b3=b.x*half;
            Point2 a{to.x-P.x,to.y-P.y};normalise(a);
            const float a1x=a.x*m,a1y=a.y*m,a2=-(a.y*half),a3=a.x*half;
            const float sy=P.y-b1y,sx=P.x-b1x;
            const float fy=P.y+a1y;const float fx0=P.x+a1x;
            if(!flip) {
                const Point2 d{sx-b2,sy-b3},c{sx+b2,sy+b3},e{nn.x+P.x,nn.y+P.y},f{a2+fx0,a3+fy};
                if(type==3) {
                    add(c,alpha,0.263671875f,0.35546875f);add(d,alpha,0.263671875f,0.362304688f);
                    add(d,alpha,0.263671875f,0.37109375f);add(c,alpha,0.263671875f,0.364257812f);
                    add(e,alpha,0.266601562f,0.364257812f);add(f,alpha,0.268554688f,0.3671875f);
                } else {
                    add(c,alpha,0.263671875f,0.35546875f);add(d,alpha,0.263671875f,0.362304688f);
                    add(d,alpha,0.276367188f,0.362304688f);add(c,alpha,0.28125f,0.357421875f);
                    add(e,alpha,0.291992188f,0.369140625f);add(f,alpha,0.276367188f,0.369140625f);
                }
                add(d,alpha,0.263671875f,0.362304688f);add(f,alpha,0.263671875f,0.35546875f);
            } else {
                const Point2 d{b2+sx,b3+sy},c{sx-b2,sy-b3},e{P.x-nn.x,P.y-nn.y},f{fx0-a2,fy-a3};
                if(type==3) {
                    add(d,alpha,0.263671875f,0.35546875f);add(c,alpha,0.263671875f,0.362304688f);
                    add(d,alpha,0.263671875f,0.37109375f);add(c,alpha,0.263671875f,0.364257812f);
                    add(e,alpha,0.266601562f,0.364257812f);add(f,alpha,0.268554688f,0.3671875f);
                } else {
                    add(d,alpha,0.263671875f,0.35546875f);add(c,alpha,0.263671875f,0.362304688f);
                    add(d,alpha,0.276367188f,0.362304688f);add(c,alpha,0.28125f,0.357421875f);
                    add(e,alpha,0.291992188f,0.369140625f);add(f,alpha,0.276367188f,0.369140625f);
                }
                add(f,alpha,0.263671875f,0.362304688f);add(d,alpha,0.263671875f,0.35546875f);
            }
            break;
        }
        }
        prev=cur;++k;
    }
}
}
