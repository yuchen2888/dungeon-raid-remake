#include "screens.hpp"
#include "recovered_scores.hpp"
#include <cmath>
using namespace dungeonraid;
namespace drui {
namespace {
float interpolate(float a,float b,float t) {const float x=a*t;const float y=(1.0f-t)*b;return x+y;}   // 0x1b800
Point2 texels(float x,float y) {return Point2{x/1024.0f,y/1024.0f};}   // GLfloat2::operator/(1024)
Point2 points(float x,float y) {return Point2{x/320.0f,y/320.0f};}     // GLfloat2::operator/(320)
// HSVtoRGB 0x1baa0 (in fact hue, saturation, lightness), branch for branch: red's first test is in double precision and
// blue's last tests red's hue (and then sets green too) as the original does.
Colour hsv_to_rgb(float h,float s,float l) {
    float q;
    if(l<0.5f){const float k=s+1.0f;q=l*k;}
    else {const float sum=s+l;const float sl=s*l;q=sum-sl;}
    const float twice=l+l;const float p=twice-q;
    const float third=0.333333343f;
    float tr=h+third;if(tr>1.0f)tr=tr-1.0f;
    float tb=h-third;if(tb<0.0f)tb=tb+1.0f;
    const float qp=q-p;
    float r,g,b;
    if(static_cast<double>(tr)*6.0<1.0){const float x=qp*6.0f;const float y=x*tr;r=y+p;}
    else if(tr+tr<1.0f)r=q;
    else if(!(tr*3.0f<2.0f))r=p;
    else {const float d=0.666666687f-tr;const float x=qp*d;const float y=x*6.0f;r=y+p;}
    if(h*6.0f<1.0f){const float x=qp*6.0f;const float y=h*x;g=y+p;}
    else if(h+h<1.0f)g=q;
    else if(!(h*3.0f<2.0f))g=p;
    else {const float d=0.666666687f-h;const float x=qp*d;const float y=x*6.0f;g=y+p;}
    if(tb*6.0f<1.0f){const float x=qp*6.0f;const float y=x*tb;b=y+p;}
    else if(tb+tb<1.0f)b=q;
    else if(!(tr*3.0f<2.0f)){g=p;b=p;}
    else {const float d=0.666666687f-tb;const float x=qp*d;const float y=x*6.0f;b=y+p;}
    const auto byte=[](float v){return static_cast<std::uint8_t>(static_cast<std::int32_t>(v*256.0f));};
    return Colour{byte(r),byte(g),byte(b),255};
}
bool has_save(const SessionObjects& o) {return static_cast<std::int32_t>(o.end->flag_146d0)>0;}
bool has_scores(const SessionObjects& o) {return dr_score_count(o.scores)>0;}
}
// MainMenu::MainMenu 0x2ec84 (frontend/tools/trace_function.py '__ZN8MainMenuC2EP4Game').
MainMenuView::MainMenuView() {
    background_.set_uv(0.5f,0.5f,0.3125f,0.46875f);background_.scale=Point2{1.0f,1.5f};
    title_.set_uv(0.5f,0.97265625f,0.130859375f,0.02734375f);
    title_.position=Point2{0.790624976f,1.45624995f};title_.scale=Point2{0.418749988f,0.0874999985f};title_.set_alpha(255);
    more_games_.set_uv(0.817382812f,0.961914062f,0.181640625f,0.037109375f);
    more_games_.position=Point2{0.709375024f,1.44062495f};more_games_.scale=Point2{0.581250012f,0.118749999f};
    more_games_.set_alpha(0);
    stop_cycling();
    struct Button { float x,y,u0,v0,u1,v1,w,h; };
    const Button b[8]={{0.207812503f,0.353125006f,833,513,964,552,131,39},{0.228125006f,0.524999976f,833,553,977,592,144,39},
                       {0.224999994f,0.618749976f,881,472,1023,511,142,39},{0.203125f,0.712499976f,833,593,961,633,128,40},
                       {0.154687494f,0.864062488f,833,634,930,675,97,41},{0,0,0,0,0,0,0,0},
                       {0.228125006f,0.951562524f,1,984,145,1023,144,39},{0.262499988f,1.08906245f,147,983,313,1023,166,40}};
    for(int k=0;k<8;++k) {
        if(k==5)continue;   // the sound switch: SetSoundState (Game::Game turns the sound on)
        Quad& q=buttons_[k];
        q.position=Point2{b[k].x,b[k].y};
        q.set_uv(texels(b[k].u0,b[k].v0),texels(b[k].u1,b[k].v1));
        q.scale=points(b[k].w,b[k].h);
        q.set_alpha(0);
    }
    buttons_[5].set_alpha(0);buttons_[5].rotation=-90.0f;
    darken_.set_size(Point2{2.0f,2.0f});darken_.position=Point2{0.5f,0.5f};darken_.set_colour(Colour{0,0,0,0});
    box_.position=Point2{0.5f,0.5f};box_.set_uv(texels(2,710),texels(494,1022));box_.set_size(points(246,156));box_.set_alpha(0);
    yes_.position=Point2{0.741999984f,0.647000015f};yes_.set_uv(texels(2,626),texels(100,670));yes_.set_size(points(49,22));
    yes_.set_colour(Colour{100,100,100,255});
    no_.position=Point2{0.246999994f,0.647000015f};no_.set_uv(texels(2,672),texels(82,708));no_.set_size(points(40,18));
    no_.set_colour(Colour{100,100,100,255});
}
void MainMenuView::set_sound_state(bool on) {
    Quad& q=buttons_[5];
    if(on){q.position=Point2{0.798437476f,1.3125f};q.set_uv(texels(923,676),texels(963,815));q.scale=Point2{0.434374988f,0.125f};}
    else {q.position=Point2{0.785937488f,1.3125f};q.set_uv(texels(983,513),texels(1023,660));q.scale=Point2{0.459374994f,0.125f};}
}
void MainMenuView::update_more_games_colour() {
    Colour c=hsv_to_rgb(hue_,0.899999976f,0.600000024f);
    c.a=more_games_.v[0].colour[3];
    more_games_.set_colour(c);
}
void MainMenuView::start_cycling() {hue_=0.200000003f;update_more_games_colour();cycling_=true;}
void MainMenuView::stop_cycling() {hue_=0.200000003f;update_more_games_colour();cycling_=false;}
void MainMenuView::button_acted(const SessionObjects& o,std::int32_t button,float dt) {
    if(!(button==0 || (button>=1 && button<=3 && !has_save(o))))return;
    start_cycling();
    const float x=dt*0.5f;const float h=hue_+x;
    hue_=std::fmod(h,1.0f);
    update_more_games_colour();
}
void MainMenuView::set_buttons(std::uint8_t a,std::uint8_t dim,bool save,bool scores) {
    for(int k=0;k<8;++k)buttons_[k].set_alpha((k==0 && !save) || (k==4 && !scores)?dim:a);
}
void MainMenuView::show(const SessionObjects& o) {
    const bool save=has_save(o),scores=has_scores(o);
    background_.set_alpha(255);
    for(auto& q:buttons_)q.set_alpha(255);
    more_games_.set_alpha(255);
    if(!save)buttons_[0].set_alpha(128);
    if(!scores)buttons_[4].set_alpha(128);
}
void MainMenuView::fade_in() {
    background_.set_alpha(0);
    for(auto& q:buttons_)q.set_alpha(0);
    more_games_.set_alpha(0);
}
void MainMenuView::process(const SessionObjects& o,float dt) {
    const MainMenuScreen& m=*o.main_menu;
    const bool save=has_save(o),scores=has_scores(o);
    const auto fade=[&](std::int32_t a) {   // the background, the buttons (unavailable ones at half) and "more games"
        const auto full=static_cast<std::uint8_t>(a);
        background_.set_alpha(full);
        set_buttons(full,static_cast<std::uint8_t>(a/2),save,scores);
        more_games_.set_alpha(full);
    };
    if(m.timer>0.0f) {   // FadeIn (0.5 s) / FadeOut (0.3 s)
        float t=m.timer-dt;
        if(t<0.0f)t=0.0f;
        if(m.fading){const float x=t+t;fade(static_cast<std::int32_t>(interpolate(0.0f,255.0f,x)));}
        else {const float x=t/0.300000012f;fade(static_cast<std::int32_t>(interpolate(255.0f,0.0f,x)));}
        return;
    }
    const std::int32_t phase=o.touch->phase,button=*o.menu_button;
    if(m.confirm) {
        float t=m.confirm_timer-dt;
        if(t<0.0f) {
            t=0.0f;
            if(m.closing) {   // closed: a yes starts its game (StartCyclingGamesColour)
                darken_.set_alpha(0);box_.set_alpha(0);yes_.set_alpha(0);no_.set_alpha(0);
                if(m.chosen)start_cycling();
                return;
            }
        }
        const float x=t/0.300000012f;
        const auto a=static_cast<std::int32_t>(m.closing?interpolate(255.0f,0.0f,x):interpolate(0.0f,255.0f,x));
        darken_.set_alpha(static_cast<std::uint8_t>(a/2));
        box_.set_alpha(static_cast<std::uint8_t>(a));yes_.set_alpha(static_cast<std::uint8_t>(a));no_.set_alpha(static_cast<std::uint8_t>(a));
        return;
    }
    if(m.splash) {   // the title fades out, the buttons and "more games" in
        const float f=static_cast<float>(m.splash)+dt*-500.0f;
        std::int32_t a=static_cast<std::int32_t>(f);if(a<0)a=0;
        const auto title=static_cast<std::uint8_t>(a);
        title_.set_alpha(title);
        const auto rest=static_cast<std::uint8_t>(~title);
        more_games_.set_alpha(rest);
        set_buttons(rest,static_cast<std::uint8_t>((255-a)/2),save,scores);
        return;
    }
    if(phase==1 && m.previous_phase==0) {
        if(button==8)return;   // Game::ShowMoreGames (the session's MoreGames event stops the cycle)
        if(m.bonus && button==9)return;
        if(button>=0 && button<8 && !(button==0 && !save) && !(button==4 && !scores))buttons_[button].set_alpha(128);
    } else if(phase==0) {
        for(auto& q:buttons_)q.set_alpha(255);
        if(!save)buttons_[0].set_alpha(128);
        if(!scores)buttons_[4].set_alpha(128);
    }
    if(cycling_) {
        const float x=dt*0.5f;const float h=hue_+x;
        hue_=std::fmod(h,1.0f);
        update_more_games_colour();
    }
}
std::int32_t MainMenuView::button_at(const SessionObjects& o,Point2 p) const {
    const MainMenuScreen& m=*o.main_menu;
    if(m.confirm) {
        if(yes_.contains(p))return 10;
        if(no_.contains(p))return 11;
        return -1;
    }
    if(more_games_.contains(p))return 8;
    if(m.bonus && buttons_[7].contains(p))return 9;
    for(int k=0;k<8;++k)if(buttons_[k].contains(p))return k;
    return -1;
}
void MainMenuView::render(GL& gl,const SessionObjects& o) const {
    const MainMenuScreen& m=*o.main_menu;
    gl.bind_texture(Tiles);
    background_.render(gl);title_.render(gl);more_games_.render(gl);
    for(int k=0;k<7;++k)buttons_[k].render(gl);
    if(m.bonus)buttons_[7].render(gl);
    if(!m.confirm)return;
    gl.bind_texture(NoTexture);
    darken_.render(gl);
    gl.bind_texture(Menus);
    box_.render(gl);
    if(m.closing)(m.chosen?yes_:no_).render(gl);
}
}
