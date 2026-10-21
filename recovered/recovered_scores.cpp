#include "recovered_scores.hpp"
#include <algorithm>
using namespace dungeonraid;
extern "C" void dr_scores_init(ScoreBoard* b) {
    b->last_type=b->last_pos=-1;
    for(int t=0;t<6;++t){b->count[t]=0;b->changed[t]=0;}
}
extern "C" void dr_score_add(ScoreBoard* b,const char* name,std::int32_t turn,std::int32_t a,std::int32_t bb,std::int32_t c,
                             std::int32_t score,std::int32_t type) {
    if(b->last_type>=0 && b->last_type!=type)b->changed[b->last_type]=1;
    b->changed[type]=1;b->last_type=type;
    ScoreRecord* table=b->scores[type];
    std::int32_t pos=0;
    while(pos<b->count[type] && table[pos].score>=score)++pos;
    if(pos==10)pos=9;
    b->last_pos=pos;
    for(std::int32_t k=std::min(b->count[type],9);k>pos;--k)table[k]=table[k-1];
    ScoreRecord& r=table[pos];
    for(int k=0;k<20;++k){r.name[k]=name[k];if(!name[k])break;}   // strcpy (names are at most 16 characters)
    r.turn=turn;r.a=a;r.b=bb;r.c=c;r.score=score;
    for(auto& s:r.skills)s=-1;
    b->count[type]=std::min(b->count[type]+1,10);
}
extern "C" void dr_score_set_skills(ScoreBoard* b,std::int32_t s0,std::int32_t s1,std::int32_t s2,std::int32_t s3) {
    if(b->last_type<0 || b->last_pos<0)return;   // after AddScore only (the original would write outside the tables)
    ScoreRecord& r=b->scores[b->last_type][b->last_pos];
    r.skills[0]=s0;r.skills[1]=s1;r.skills[2]=s2;r.skills[3]=s3;
}
extern "C" std::int32_t dr_score_count(const ScoreBoard* b) {
    std::int32_t n=0;for(int t=0;t<6;++t)n+=b->count[t];return n;
}
extern "C" bool dr_scores_changed(const ScoreBoard* b) {
    for(int t=0;t<6;++t)if(b->changed[t])return true;
    return false;
}
extern "C" void dr_score_serialise(ScoreBoard* b,std::int32_t type) {
    std::uint8_t* p=b->bytes;
    auto word=[&](std::int32_t v){for(int i=0;i<4;++i)*p++=static_cast<std::uint8_t>(static_cast<std::uint32_t>(v)>>(8*i));};
    *p++=static_cast<std::uint8_t>(b->count[type]);
    *p++=static_cast<std::uint8_t>(type==b->last_type?b->last_pos:-1);
    for(std::int32_t i=0;i<b->count[type];++i) {
        const ScoreRecord& r=b->scores[type][i];
        word(r.turn);word(r.a);word(r.b);word(r.c);word(r.score);
        for(std::int32_t s:r.skills)*p++=static_cast<std::uint8_t>(s);
        for(int k=0;k<17;++k){*p++=static_cast<std::uint8_t>(r.name[k]);if(!r.name[k])break;}
    }
    b->length=static_cast<std::int32_t>(p-b->bytes);b->changed[type]=0;b->serialised_type=type;
}
extern "C" std::int32_t dr_score_serialise_changed(ScoreBoard* b) {
    for(int t=0;t<6;++t)if(b->changed[t]){dr_score_serialise(b,t);return t;}
    return -1;
}
extern "C" void dr_score_deserialise(ScoreBoard* b,std::int32_t type) {
    const std::uint8_t* p=b->bytes;
    auto word=[&]{std::uint32_t v=0;for(int i=0;i<4;++i)v|=static_cast<std::uint32_t>(*p++)<<(8*i);return static_cast<std::int32_t>(v);};
    b->count[type]=std::clamp<std::int32_t>(p[0],0,10);
    if(p[1]!=0xff){b->last_pos=p[1];b->last_type=type;}
    p+=2;
    for(std::int32_t i=0;i<b->count[type];++i) {
        ScoreRecord& r=b->scores[type][i];
        r.turn=word();r.a=word();r.b=word();r.c=word();r.score=word();
        for(auto& s:r.skills){const std::int32_t v=*p++;s=v==0xff?-1:std::clamp(v,0,39);}
        for(int k=0;k<17;++k){r.name[k]=static_cast<char>(*p++);if(!r.name[k])break;}
    }
    b->changed[type]=0;
}
