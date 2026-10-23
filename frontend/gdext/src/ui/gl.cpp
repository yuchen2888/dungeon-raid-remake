#include "gl.hpp"
#include <cmath>
namespace drui {
GL::GL() {stack_.push_back(Matrix{1,0,0,1,0,0});}
void GL::clear() {draws_.clear();vertices_.clear();}
void GL::load_identity() {stack_.back()=Matrix{1,0,0,1,0,0};}
void GL::push() {stack_.push_back(stack_.back());}
void GL::pop() {if(stack_.size()>1)stack_.pop_back();}
// The same products, in the same order, as the emulator's recorder (original_frame.py, Python doubles).
void GL::multiply(const Matrix& n) {
    const Matrix m=stack_.back();
    stack_.back()=Matrix{m.a*n.a+m.c*n.b,m.b*n.a+m.d*n.b,m.a*n.c+m.c*n.d,m.b*n.c+m.d*n.d,m.a*n.e+m.c*n.f+m.e,m.b*n.e+m.d*n.f+m.f};
}
void GL::translate(float x,float y) {multiply(Matrix{1,0,0,1,static_cast<double>(x),static_cast<double>(y)});}
void GL::scale(float x,float y) {multiply(Matrix{static_cast<double>(x),0,0,static_cast<double>(y),0,0});}
void GL::rotate(float degrees,float z) {
    double angle=static_cast<double>(degrees)*(M_PI/180.0);
    if(z<0)angle=-angle;
    const double c=std::cos(angle),s=std::sin(angle);
    multiply(Matrix{c,s,-s,c,0,0});
}
void GL::draw(std::int32_t mode,const Vertex* v,std::uint32_t count) {
    const Matrix& m=stack_.back();
    draws_.push_back(Draw{textured_?texture_:0,mode,static_cast<std::uint8_t>(blend_),static_cast<std::uint32_t>(vertices_.size()),count,tag_});
    for(std::uint32_t i=0;i<count;++i) {
        const double x=v[i].x,y=v[i].y;
        DrawVertex d{m.a*x+m.c*y+m.e,m.b*x+m.d*y+m.f,v[i].u,v[i].v,{v[i].colour[0],v[i].colour[1],v[i].colour[2],v[i].colour[3]}};
        vertices_.push_back(d);
    }
}
}
