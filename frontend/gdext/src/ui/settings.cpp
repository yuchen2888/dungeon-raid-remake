#include "settings.hpp"
namespace drui {
namespace {
// The page's places, in points of the 320-point-wide screen: the panel 40..280 x 140..338 (the game menu's pieces),
// the two language buttons and Back (the empty purple button of the menu button's "on" picture, 72 x 26, widened).
constexpr float kPanelX=40.0f, kPanelY=140.0f, kInnerW=212.0f, kInnerH=170.0f;
constexpr float kButtonW=90.0f, kButtonH=26.0f;
constexpr float kButtons[3][2]={{60.0f,222.0f},{170.0f,222.0f},{115.0f,282.0f}};   // English, 中文, Back
constexpr float kNameW=64.0f, kNameH=16.0f;   // a name in the LangNames picture: 128 x 32 of its 256 x 256 pixels
const std::string& text_or(const Texts& t,const char* key,const std::string& english) {
    const std::string& s=t.get(key);
    return s.empty()?english:s;
}
void place(Label& l,float centre_x,float y,float scale) {
    l.scale=Point2{scale,scale};
    l.position=Point2{centre_x-l.width*scale*0.5f,y};
}
}
SettingsView::SettingsView(const Font* menu_font):quads_(14),title_(menu_font),language_(menu_font),back_(menu_font) {
    const auto set=[&](int q,float x,float y,float u,float v,float w,float h,float sx,float sy) {
        quads_.set_quad(q,Point2{x,y},Point2{u,v},Point2{w,h},sx,sy);
    };
    const float x1=kPanelX+13.0f,x2=x1+kInnerW,y1=kPanelY+13.0f,y2=y1+kInnerH;
    set(0,kPanelX,kPanelY,498,498,13,13,1,1);   // the panel: as GameMenu::GameMenu's corners, edges and fill
    set(1,x1,kPanelY,479,472,1,13,kInnerW,1);
    set(2,x2,kPanelY,380,415,15,13,1,1);
    set(3,kPanelX,y1,478,487,13,1,1,kInnerH);
    set(4,x1,y1,145,399,1,1,kInnerW,kInnerH);
    set(5,x2,y1,380,430,15,1,1,kInnerH);
    set(6,kPanelX,y2,498,482,13,15,1,1);
    set(7,x1,y2,483,470,1,15,kInnerW,1);
    set(8,x2,y2,380,433,15,13,1,1);
    for(int b=0;b<3;++b)set(9+b,kButtons[b][0],kButtons[b][1],425,698,72,26,kButtonW/72.0f,1);
    for(int n=0;n<2;++n)   // the names, centred on their buttons (texture coordinates in 1024ths of the 256-pixel picture)
        set(12+n,kButtons[n][0]+(kButtonW-kNameW)*0.5f,kButtons[n][1]+(kButtonH-kNameH)*0.5f,0,128.0f*static_cast<float>(n),512,128,
            kNameW/512.0f,kNameH/128.0f);
    for(int q=0;q<14;++q)quads_.set_quad_colour(q,255,255,255,255);
    background_.set_size(Point2{2.0f,2.0f});background_.position=Point2{0.5f,0.5f};background_.set_colour(Colour{0,0,0,160});
    for(Label* l:{&title_,&language_,&back_}){l->colour=Colour{122,103,211,255};l->update_colour();}
    title_.colour=Colour{255,255,255,255};title_.update_colour();
}
void SettingsView::open(const Texts& t,std::int32_t language) {
    open_=true;previous_=1;language_index_=language;
    title_.set_text(text_or(t,"settings.title","Settings").c_str());
    language_.set_text(text_or(t,"settings.language","Language").c_str());
    back_.set_text(text_or(t,"settings.back","Back").c_str());
    place(title_,0.5f,(kPanelY+34.0f)/320.0f,0.09f);
    place(language_,0.5f,(kPanelY+64.0f)/320.0f,0.08f);
    place(back_,(kButtons[2][0]+kButtonW*0.5f)/320.0f,(kButtons[2][1]+kButtonH*0.5f+5.0f)/320.0f,0.07f);   // (+5: the menu font's middle sits above its line)
    for(int n=0;n<2;++n) {   // the shown language's button bright, the other dimmer
        const std::uint8_t c=n==language?255:150;
        quads_.set_quad_colour(9+n,c,c,c,255);quads_.set_quad_colour(12+n,c,c,c,255);
    }
}
std::int32_t SettingsView::touch(std::int32_t phase,Point2 p) {
    const bool began=phase==1 && previous_==0;
    previous_=phase==2?0:phase;
    if(!open_ || !began)return -1;
    const float x=p.x*320.0f,y=p.y*320.0f;
    for(int b=0;b<3;++b) {
        if(x>kButtons[b][0] && x<kButtons[b][0]+kButtonW && y>kButtons[b][1] && y<kButtons[b][1]+kButtonH)return b==2?Back:b;
    }
    return -1;
}
void SettingsView::render(GL& gl) const {
    if(!open_)return;
    gl.push();gl.load_identity();
    gl.bind_texture(NoTexture);background_.render(gl);
    gl.bind_texture(Tiles);
    for(int q=0;q<12;++q)gl.draw(6,quads_.quad(q),4);
    gl.bind_texture(LangNames);
    for(int q=12;q<14;++q)gl.draw(6,quads_.quad(q),4);
    title_.render(gl);language_.render(gl);back_.render(gl);
    gl.pop();
}
}
