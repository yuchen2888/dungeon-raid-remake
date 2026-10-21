#include "recovered_labels.hpp"
using namespace dungeonraid;
namespace {
// CreateTypeDefinition 0x22374: each type's glyph (atlas u0, v0, u1, v1; scale 1); types 5 and 10 take plural_glyph when
// the number is above 1.
constexpr LabelGlyph type_glyphs[42]={
    {425,23,471,36},{425,93,474,113},{425,93,474,113},{425,129,499,142},{444,157,484,170},{425,171,459,184},{425,115,471,128},
    {425,115,471,128},{466,143,504,156},{425,558,465,571},{425,171,459,184},{425,513,460,526},{461,513,493,526},{457,527,493,540},
    {425,527,456,540},{463,541,498,556},{425,558,465,571},{466,558,508,571},{425,541,462,554},{462,572,494,585},{462,586,502,599},
    {425,628,483,641},{425,656,481,669},{462,614,507,627},{425,670,470,683},{425,684,479,697},{462,600,505,613},{425,642,479,655},
    {425,831,495,844},{425,845,476,858},{425,859,481,872},{425,873,473,886},{425,887,476,900},{425,901,469,914},{470,901,511,914},
    {425,915,487,928},{425,929,481,942},{425,943,453,956},{425,957,492,970},{771,425,1023,461},{513,351,817,387},{513,388,808,424}};
// The digit glyphs 0..9 (two GLfloat2 tables at 0x1eac64 / 0x1eacb4, set by a static initialiser).
constexpr LabelGlyph digit_glyphs[10]={
    {486,65,506,92},{472,1,488,28},{489,1,509,28},{425,37,445,64},{446,37,467,64},{468,37,488,64},{489,37,509,64},{425,65,444,92},
    {445,65,464,92},{465,65,485,92}};
constexpr LabelGlyph minus_glyph={475,93,488,101},type8_last_glyph={425,157,443,170};
constexpr LabelGlyph plural_glyph={425,143,465,156};   // types 5 and 10 with a number above 1
// SetColour 0x221c4: RGB of colours 0..49.
constexpr std::uint8_t colours[50][3]={
    {215,30,33},{15,219,0},{253,249,38},{166,168,255},{255,255,255},{255,255,255},{255,255,255},{255,255,255},{255,255,255},
    {255,255,255},{0,255,0},{255,0,0},{173,177,255},{215,30,33},{255,255,255},{169,76,202},{200,200,200},{215,30,33},{255,130,0},
    {255,255,255},{200,255,255},{200,255,255},{255,255,0},{0,255,0},{255,255,255},{100,255,255},{255,255,255},{255,255,255},
    {255,255,255},{255,255,0},{40,170,80},{130,120,30},{255,255,0},{180,180,180},{255,30,30},{230,0,110},{255,255,255},{255,30,30},
    {255,255,255},{255,255,255},{255,30,30},{255,255,255},{160,160,255},{255,255,255},{255,255,255},{255,255,255},{255,255,0},
    {255,255,0},{255,255,0},{255,255,0}};
bool in(std::int32_t type,std::uint32_t last,std::uint32_t mask) {
    return type>=0 && static_cast<std::uint32_t>(type)<=last && ((1u<<type)&mask);
}
bool number_first(std::int32_t type) {return in(type,27,0xc0006a6u);}   // the number before the type's glyph
bool number_after(std::int32_t type) {return in(type,29,0x20000118u);}  // ... after it
// SetDefinition 0x222f4.
void define(SimpleLabelState* l,const LabelGlyph& g,float scale) {l->glyphs[l->count]=g;l->glyph_scale[l->count]=scale;++l->count;}
// CreateNumberDefinition 0x22c34: a minus, then the digits from the ten-thousands without leading zeros (none for 0;
// numbers from 100000 would read past the original's digit tables: the digit is limited to 9 here).
void number_glyphs(SimpleLabelState* l,std::int32_t n) {
    if(n<0){define(l,minus_glyph,1.0f);n=-n;}
    bool started=false;std::int32_t divisor=10000;
    for(int i=0;;) {
        const std::int32_t d=n/divisor;
        if(d>0 || started){define(l,digit_glyphs[d>9?9:d],l->size);started=true;}
        const std::int32_t next=divisor/10;
        if(++i==5)break;
        n%=divisor;divisor=next;
    }
}
// SetVertex 0x22d04.
void vertex(SimpleLabelState* l,int k,float x,float y,float u,float v) {
    LabelVertex& w=l->vertices[k];
    w.x=(x+l->offset_x)/320.0f;w.y=(y+l->offset_y)/320.0f;w.u=u*0.0009765625f;w.v=v*0.0009765625f;
}
}
extern "C" void dr_label_construct(SimpleLabelState* l) {
    l->active=0;l->count=0;l->number=0;l->scale=1.0f;l->duration=1.0f;l->alpha=0xff;
}
extern "C" void dr_label_set_colour(SimpleLabelState* l,std::int32_t colour) {
    static constexpr std::uint8_t white[3]={255,255,255};
    const std::uint8_t* c=colour>=0 && colour<50?colours[colour]:white;
    for(auto& w:l->vertices){w.colour[0]=c[0];w.colour[1]=c[1];w.colour[2]=c[2];w.colour[3]=0xff;}
}
extern "C" void dr_label_regenerate(SimpleLabelState* l) {
    l->count=0;
    if(number_first(l->type))number_glyphs(l,l->number);
    if(l->count<=7 && l->type>=0 && l->type<42)   // CreateTypeDefinition
        define(l,(l->type==5 || l->type==10) && l->number>1?plural_glyph:type_glyphs[l->type],1.0f);
    if(number_after(l->type))number_glyphs(l,l->number);
    if(l->count<=7 && l->type==8)define(l,type8_last_glyph,1.0f);                      // CreateTypeDefinitionLast
    if(!l->count)return;
    for(int k=0;k<4*l->count;++k)l->vertices[k].colour[3]=0xff;
    float x=0.0f;   // centred: half the glyphs' width to the left
    for(int i=0;i<l->count;++i)x+=(l->glyphs[i].u1-l->glyphs[i].u0)*-0.5f*l->glyph_scale[i];
    for(int i=0;i<l->count;++i) {
        const LabelGlyph& g=l->glyphs[i];const float s=l->glyph_scale[i];
        l->offset_x=x-g.u0;
        l->offset_y=-(g.v0+(g.v1-g.v0)*s);
        if(i==0 && l->number<0)l->offset_y=l->offset_y-(g.v1-g.v0)*s;
        const float x1=g.u0+(g.u1-g.u0)*s,y1=g.v0+s*(g.v1-g.v0);
        vertex(l,4*i,g.u0,g.v0,g.u0,g.v0);vertex(l,4*i+1,x1,g.v0,g.u1,g.v0);
        vertex(l,4*i+2,x1,y1,g.u1,g.v1);vertex(l,4*i+3,g.u0,y1,g.u0,g.v1);
        x+=(g.u1-g.u0)*s;
    }
}
extern "C" void dr_label_initialise(SimpleLabelState* l,std::int32_t type,Point position,std::int32_t number,float scale,RandomState* random) {
    l->active=1;l->type=type;l->x=position.x;l->y=position.y;l->timer=0.0f;
    if(type==1 || type==8 || type==9 || type==10)l->speed=0.1f;
    else if(type==3)l->speed=0.08f;
    else l->speed=dr_random_float(random,0.1f,0.2f,0);
    l->number=number;l->scale=scale;
    l->size=in(type,29,0x2c0007b8u)?0.5f:1.0f;
    dr_label_regenerate(l);
}
extern "C" void dr_label_set_number(SimpleLabelState* l,std::int32_t number) {
    if(!number_first(l->type) && !number_after(l->type))return;
    if(l->number==number)return;
    l->number=number;dr_label_regenerate(l);
}
extern "C" void dr_label_set_position(SimpleLabelState* l,Point p) {l->x=p.x;l->y=p.y;}
extern "C" void dr_label_set_alpha(SimpleLabelState* l,std::uint8_t alpha) {for(auto& w:l->vertices)w.colour[3]=alpha;}
extern "C" void dr_label_process(SimpleLabelState* l,float dt) {
    l->timer=l->timer+dt;
    if(l->timer>=l->duration){l->active=0;return;}
    l->y=l->y-dt*l->speed;
    const float t=l->timer/l->duration;
    const auto a=static_cast<std::int32_t>((1.0f-t*t)*static_cast<float>(l->alpha));
    for(int k=0;k<4*l->count;++k)l->vertices[k].colour[3]=static_cast<std::uint8_t>(a);
}
