#include "ios_png.hpp"
#include <cstdlib>
#include <cstring>
#include <zlib.h>
namespace drfront {
namespace {
std::uint32_t be32(const std::uint8_t* p) {
    return (std::uint32_t(p[0])<<24)|(std::uint32_t(p[1])<<16)|(std::uint32_t(p[2])<<8)|p[3];
}
int paeth(int a,int b,int c) {
    int p=a+b-c, pa=std::abs(p-a), pb=std::abs(p-b), pc=std::abs(p-c);
    return pa<=pb&&pa<=pc?a:(pb<=pc?b:c);
}
}

IosPicture decode_ios_png(const std::uint8_t* data,std::size_t size) {
    IosPicture out;
    static const std::uint8_t signature[8]={0x89,'P','N','G','\r','\n',0x1a,'\n'};
    if(size<8||std::memcmp(data,signature,8)!=0)return out;
    std::uint32_t w=0,h=0;
    bool cgbi=false;
    std::vector<std::uint8_t> idat;
    for(std::size_t i=8;i+12<=size;) {
        std::uint32_t n=be32(data+i);
        if(n>size-i-12)return out;
        const std::uint8_t* type=data+i+4;
        const std::uint8_t* body=data+i+8;
        if(std::memcmp(type,"CgBI",4)==0)cgbi=true;
        else if(std::memcmp(type,"IHDR",4)==0) {
            if(n<13||body[8]!=8||body[9]!=6)return out;   // (8 bits, RGBA: all the original's pictures)
            w=be32(body);
            h=be32(body+4);
        } else if(std::memcmp(type,"IDAT",4)==0)idat.insert(idat.end(),body,body+n);
        else if(std::memcmp(type,"IEND",4)==0)break;
        i+=12+n;
    }
    if(!cgbi||w==0||h==0||w>8192||h>8192)return out;
    const std::size_t stride=std::size_t(w)*4;
    std::vector<std::uint8_t> raw((stride+1)*h);
    z_stream z{};
    if(inflateInit2(&z,-MAX_WBITS)!=Z_OK)return out;   // raw deflate: CgBI drops zlib's header and check
    z.next_in=idat.data();
    z.avail_in=uInt(idat.size());
    z.next_out=raw.data();
    z.avail_out=uInt(raw.size());
    int r=inflate(&z,Z_FINISH);
    inflateEnd(&z);
    if((r!=Z_STREAM_END&&r!=Z_OK)||z.avail_out!=0)return out;
    std::vector<std::uint8_t> px(stride*h);
    for(std::uint32_t y=0;y<h;++y) {
        const std::uint8_t* in=raw.data()+y*(stride+1);
        std::uint8_t filter=in[0];
        ++in;
        std::uint8_t* line=px.data()+y*stride;
        const std::uint8_t* prev=y?line-stride:nullptr;
        for(std::size_t x=0;x<stride;++x) {
            int a=x>=4?line[x-4]:0, b=prev?prev[x]:0, c=(prev&&x>=4)?prev[x-4]:0, v=in[x];
            switch(filter) {
            case 1: v+=a; break;
            case 2: v+=b; break;
            case 3: v+=(a+b)>>1; break;
            case 4: v+=paeth(a,b,c); break;
            default: break;
            }
            line[x]=std::uint8_t(v);
        }
    }
    for(std::size_t i=0;i<px.size();i+=4) {   // BGRA, premultiplied -> RGBA, straight
        int b=px[i], g=px[i+1], r2=px[i+2], alpha=px[i+3];
        auto straight=[alpha](int c) {return alpha?std::uint8_t(c*255/alpha>255?255:c*255/alpha):std::uint8_t(0);};
        px[i]=straight(r2);
        px[i+1]=straight(g);
        px[i+2]=straight(b);
    }
    out.width=w;
    out.height=h;
    out.rgba=std::move(px);
    return out;
}
}
