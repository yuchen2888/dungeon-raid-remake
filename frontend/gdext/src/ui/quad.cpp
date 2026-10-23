#include "quad.hpp"
#include <cstring>
namespace drui {
// Quad::Quad 0x1c508: vertices at +-0.5, white, texture coordinates 0..1; position (0.5, 0.75), size and scale 1.
Quad::Quad() {
    const float c[4][4]={{-0.5f,-0.5f,0.0f,0.0f},{0.5f,-0.5f,1.0f,0.0f},{-0.5f,0.5f,0.0f,1.0f},{0.5f,0.5f,1.0f,1.0f}};
    for(int i=0;i<4;++i)v[i]=Vertex{c[i][0],c[i][1],{255,255,255,255},c[i][2],c[i][3]};
}
// Quad::SetUV(GLfloat2, GLfloat2) 0x1c5b8.
void Quad::set_uv(Point2 tl,Point2 br) {
    v[0].u=tl.x;v[0].v=tl.y;v[1].u=br.x;v[1].v=tl.y;v[2].u=tl.x;v[2].v=br.y;v[3].u=br.x;v[3].v=br.y;
}
// Quad::SetUV(float, float, float, float) 0x213a4: x, y, width, height.
void Quad::set_uv(float x,float y,float w,float h) {const float x1=x+w,y1=y+h;set_uv(Point2{x,y},Point2{x1,y1});}
// Quad::SetSize 0x1c5dc: the vertices at +-half the size (the offset is lost).
void Quad::set_size(Point2 s) {
    size=s;
    const float hw=s.x*0.5f,hh=s.y*0.5f;
    v[0].x=-hw;v[0].y=-hh;v[1].x=hw;v[1].y=-hh;v[2].x=-hw;v[2].y=hh;v[3].x=hw;v[3].y=hh;
}
// Quad::SetOffset 0x1c624: every vertex moves by o.
void Quad::set_offset(Point2 o) {for(auto& p:v){p.x=p.x+o.x;p.y=p.y+o.y;}}
void Quad::set_colour(Colour c) {for(auto& p:v){p.colour[0]=c.r;p.colour[1]=c.g;p.colour[2]=c.b;p.colour[3]=c.a;}}
void Quad::set_alpha(std::uint8_t a) {for(auto& p:v)p.colour[3]=a;}
// Quad::CopyFrom 0x1c6a4 / operator= 0x18d08: vertices, position, size, scale, rotation.
void Quad::copy_from(const Quad& q) {*this=q;}
// Quad::ContainsPoint 0x1c724: inside the scaled corners (top-left, bottom-right) around the position.
bool Quad::contains(Point2 p) const {
    const float left=scale.x*v[0].x+position.x,right=scale.x*v[3].x+position.x;
    if(!(p.x>=left) || !(p.x<=right))return false;   // the conditions as branched (unordered: outside)
    const float top=scale.y*v[0].y+position.y,bottom=scale.y*v[3].y+position.y;
    if(!(p.y>=top))return false;
    return bottom>=p.y;
}
// Quad::Render 0x1c7a0: translate, scale, rotate about z, one triangle strip.
void Quad::render(GL& gl) const {
    gl.push();gl.translate(position.x,position.y);gl.scale(scale.x,scale.y);gl.rotate(rotation,1.0f);
    gl.draw(5,v,4);
    gl.pop();
}
}
