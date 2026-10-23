#include "effects.hpp"
#include <cmath>
using namespace dungeonraid;
namespace drui {
namespace {
// cosf / sinf as the reference models them (double, rounded); Interpolate 0x1b800: a t + (1 - t) b.
float cosine(float a) {return static_cast<float>(std::cos(static_cast<double>(a)));}
float sine(float a) {return static_cast<float>(std::sin(static_cast<double>(a)));}
float interpolate(float a,float b,float t) {const float x=a*t;const float y=(1.0f-t)*b;return x+y;}
float rand(RandomState* r,float lo,float hi) {return dr_random_float(r,lo,hi,0);}
constexpr double pi_4=0.7853981633974483,pi3_4=2.356194490192345,pi5_4=3.9269908169872414,pi7_4=5.497787143782138,
                 two_pi=6.283185307179586;
// CastRayOntoSquare 0x21a44: where the ray at angle from centre leaves the square of half size half, with the
// texture coordinates there (u0..u1, v0..v1 across the square).
void cast_ray(float angle,float half,float u0,float u1,float v0,float v1,Point2 centre,Vertex& out) {
    const float c=cosine(angle),s=sine(angle);
    float x,y;
    if(std::fabs(c)>std::fabs(s)) {y=s*(half/std::fabs(c));x=c>=0.0f?half:-half;}
    else {x=c*(half/std::fabs(s));y=s>=0.0f?half:-half;}
    out.u=interpolate(u0,u1,(1.0f-x/half)*0.5f);
    out.v=interpolate(v0,v1,(1.0f-y/half)*0.5f);
    out.y=y+centre.y;out.x=centre.x+x;
}
}
void Particles::initialise(const Quad& tile,Point2 at,std::int32_t type,RandomState* random) {
    active=1;timer=0.0f;duration=0.300000012f;
    std::uint8_t r=255,g=255,b=255;
    if(type==0)from_tile(tile,random);
    else if(type>=1 && type<=3) {
        at_position(at,0.00999999978f,random);
        if(type==1){r=173;g=177;b=255;}
        else if(type==2){r=215;g=0;b=33;}
    }
    for(auto& x:v){x.colour[0]=r;x.colour[1]=g;x.colour[2]=b;x.colour[3]=255;}
}
// Ten shards around the point: three corners at angles k 0.2 pi + (0, 0.1 pi, 0.2 pi) from a random start, at a
// random distance size..2 size, the fourth at the centre; the velocity the middle corner's direction / size times
// Rand(0.1, 0.3), the speed Rand(-0.5, -3).
void Particles::at_position(Point2 at,float size,RandomState* random) {
    const float start=rand(random,0.0f,6.28318548f);
    const float twice=size+size;
    for(int k=0;k<10;++k) {
        Vertex* q=v+4*k;
        const float a0=start+static_cast<float>(k)*0.628318548f;
        const float a2=a0+0.628318548f,a1=a0+0.314159274f;
        float c=cosine(a0);q[0].x=c*rand(random,size,twice);
        float s=sine(a0);q[0].y=s*rand(random,size,twice);
        q[0].u=0.01953125f;q[0].v=0.0615234375f;
        c=cosine(a1);q[1].x=c*rand(random,size,twice);
        s=sine(a1);q[1].y=s*rand(random,size,twice);
        q[1].u=0.0244140625f;q[1].v=0.0595703125f;
        c=cosine(a2);q[2].x=c*rand(random,size,twice);
        s=sine(a2);
        q[3].u=0.0244140625f;q[2].u=0.029296875f;q[3].x=0.0f;q[3].y=0.0f;q[2].v=0.0615234375f;q[3].v=0.0673828125f;
        q[2].y=s*rand(random,size,twice);
        velocity[k]=Point2{q[1].x/size,q[1].y/size};
        const float m=rand(random,0.100000001f,0.300000012f);
        velocity[k].x=m*velocity[k].x;velocity[k].y=m*velocity[k].y;
        speed[k]=rand(random,-0.5f,-3.0f);
    }
    for(auto& x:v){x.x=x.x+at.x;x.y=x.y+at.y;}
}
// The tile's picture in ten wedges: a centre Rand(-size / 8, size / 8) from the tile's, the first edge at a random
// angle, each next one 0.2 pi on (Rand(-pi / 15, pi / 15)); a wedge whose edges pass a corner of the square takes
// that corner, else the middle of its edges. Each wedge flies along its middle direction times Rand(1, 2), its speed
// Rand(-3, -10).
void Particles::from_tile(const Quad& tile,RandomState* random) {
    const Point2 centre=tile.position;
    const float half=tile.size.x*0.5f;
    const float u0=tile.v[0].u,v0=tile.v[0].v,u1=tile.v[3].u,v1=tile.v[3].v;   // Quad::GetUV 0x1c6f0
    const float q=half*0.25f;
    float dx=rand(random,-q,q),dy=rand(random,-q,q);
    const float cu=interpolate(u0,u1,(1.0f-dx/half)*0.5f);
    const float cv=interpolate(v0,v1,(1.0f-dy/half)*0.5f);
    const float cx=dx+centre.x,cy=dy+centre.y;
    const float start=rand(random,0.0f,6.28318548f);
    cast_ray(start,half,u0,u1,v0,v1,centre,v[38]);
    v[0].x=v[38].x;v[0].y=v[38].y;v[0].u=v[38].u;v[0].v=v[38].v;
    float previous=start,sx=0.0f,sy=0.0f;   // sx / sy: the corner, kept as the original's stack slot and register
    for(int k=0;k<10;++k) {
        Vertex* w=v+4*k;
        const float jitter=rand(random,-0.209439516f,0.209439516f);
        const float next=(start+static_cast<float>(k+1)*0.628318548f)+jitter;
        float b=next,a=previous;
        if(static_cast<double>(next)>two_pi) {   // both ends of the edge pair come back by 2 pi (in double)
            b=static_cast<float>(static_cast<double>(next)-two_pi);
            a=static_cast<float>(static_cast<double>(previous)-two_pi);
        }
        const double A=a,B=b;
        const bool corner=(A<pi_4 && B>pi_4) || (A<pi3_4 && B>pi3_4) || (A<pi5_4 && B>pi5_4) || (A<pi7_4 && B>pi7_4);
        cast_ray(b,half,u0,u1,v0,v1,centre,w[2]);
        w[3].x=cx;w[3].y=cy;w[3].u=cu;w[3].v=cv;
        if(k){w[0].x=w[-2].x;w[0].y=w[-2].y;w[0].u=w[-2].u;w[0].v=w[-2].v;}
        if(corner) {
            const float side=static_cast<float>(A/pi_4);
            if(side<1.0f){sx=1.0f;sy=1.0f;}
            else if(side<3.0f){sx=-1.0f;sy=1.0f;}
            else if(side<5.0f){sx=-1.0f;sy=-1.0f;}
            else if(side<7.0f){sx=1.0f;sy=-1.0f;}
            w[1].x=centre.x+sx*half;w[1].y=centre.y+sy*half;
            w[1].u=interpolate(u0,u1,(1.0f-sx)*0.5f);
            w[1].v=interpolate(v0,v1,(1.0f-sy)*0.5f);
        } else {
            w[1].x=(w[0].x+w[2].x)*0.5f;w[1].y=(w[0].y+w[2].y)*0.5f;
            w[1].u=(w[0].u+w[2].u)*0.5f;w[1].v=(w[0].v+w[2].v)*0.5f;
        }
        const float middle=(a+b)*0.5f;
        velocity[k].x=cosine(middle);
        previous=next;
        velocity[k].y=sine(middle);
        const float m=rand(random,1.0f,2.0f);
        velocity[k].x=m*velocity[k].x;velocity[k].y=m*velocity[k].y;
        speed[k]=rand(random,-3.0f,-10.0f);
    }
}
void Particles::process(float dt) {
    timer=timer+dt;
    if(timer>duration){active=0;return;}
    const float t=timer/duration;
    const float f=(1.0f-t*t)*255.0f;
    const std::uint8_t alpha=static_cast<std::uint8_t>(f<=0.0f?0u:static_cast<std::uint32_t>(f));   // vcvt.u32, uxtb
    for(int k=0;k<10;++k) {
        Point2& d=velocity[k];
        const float x2=d.x*d.x,y2=d.y*d.y;
        const float length=std::sqrt(x2+y2);
        d.x=d.x/length;d.y=d.y/length;                 // GLfloat2::operator/= 0x217b8
        const float grown=length+dt*speed[k];
        d.x=d.x*grown;d.y=d.y*grown;
        for(int j=0;j<4;++j) {
            Vertex& x=v[4*k+j];
            x.x=x.x+dt*d.x;x.colour[3]=alpha;x.y=x.y+dt*d.y;
        }
    }
}
void Particles::render(GL& gl) const {
    for(int k=0;k<10;++k)gl.draw(6,v+4*k,4);
}
Particles& ParticlePool::next() {
    if(particles.size()<=static_cast<std::size_t>(count))particles.emplace_back();
    return particles[static_cast<std::size_t>(count)];
}
void ParticlePool::process(float dt) {
    if(count<=0)return;
    std::int32_t last=-1;
    for(std::int32_t i=0;i<count;++i) {
        Particles& p=particles[static_cast<std::size_t>(i)];
        if(!p.active)continue;
        p.process(dt);
        if(p.active)last=i;
    }
    count=last+1;
}
static_assert(sizeof(LabelVertex)==sizeof(Vertex),"a label vertex is the original's vertex");
void render_label(GL& gl,const SimpleLabelState& l) {
    gl.push();
    gl.translate(l.x,l.y);
    gl.scale(l.scale,l.scale);
    const Vertex* v=reinterpret_cast<const Vertex*>(l.vertices);
    for(std::int32_t i=0;i<l.count;++i)gl.draw(6,v+4*i,4);
    gl.pop();
}
SimpleLabelState& LabelPool::next() {
    if(labels.size()<=static_cast<std::size_t>(count)) {
        SimpleLabelState fresh{};dr_label_construct(&fresh);labels.push_back(fresh);
    }
    return labels[static_cast<std::size_t>(count)];
}
void LabelPool::process(float dt) {
    if(count<=0)return;
    std::int32_t last=-1;
    for(std::int32_t i=0;i<count;++i) {
        SimpleLabelState& l=labels[static_cast<std::size_t>(i)];
        if(!l.active)continue;
        dr_label_process(&l,dt);
        if(l.active)last=i;
    }
    count=last+1;
}
}
