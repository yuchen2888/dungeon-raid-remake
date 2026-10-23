#pragma once
#include "quad.hpp"
#include "recovered_labels.hpp"
#include "recovered_random.hpp"
#include <vector>
namespace drui {
// SimpleLabel::Render 0x23004: the label's glyphs (four vertices each, a fan) at its position and scale. The
// SimpleLabel itself is the recovered one (recovered_labels: Initialise, SetColour, Process, RegenerateLabel).
void render_label(GL& gl,const dungeonraid::SimpleLabelState& l);
// The original Particles (0x3a4 bytes): ten pieces, each a fan of four vertices (+0x4), flying with a velocity
// (+0x324) whose length changes by a speed per second (+0x374), fading over the duration (timer +0x39c, duration
// +0x3a0). Type 0 breaks the tile's picture into ten wedges around a random point (InitialiseFromTile(Tile*)
// 0x21b24); types 1..3 are ten small shards at the tile's defence / health / attack label (InitialiseAtPosition
// 0x217ec), pale blue, red and white. Their Rand calls are on stream 0, drawn here from the stream given (a copy
// of the session's, which draws the same: dr_add_particles).
struct Particles {
    std::uint8_t active=0;
    Vertex v[40]{};
    Point2 velocity[10]{};
    float speed[10]{};
    float timer=0.0f, duration=0.0f;
    // Particles::InitialiseFromTile(Tile*, ParticleType) 0x21f68: tile is the tile's quad at the tile's position;
    // at is the label position for types 1..3.
    void initialise(const Quad& tile,Point2 at,std::int32_t type,dungeonraid::RandomState* random);
    void process(float dt);              // Particles::Process 0x22028
    void render(GL& gl) const;           // Particles::Render 0x22140
private:
    void at_position(Point2 at,float size,dungeonraid::RandomState* random);
    void from_tile(const Quad& tile,dungeonraid::RandomState* random);
};
struct ParticlePool {   // Game+0xb530 (in use Game+0xb53c), as LabelPool
    std::vector<Particles> particles;
    std::int32_t count=0;
    Particles& next();
    void process(float dt);
};
// A pool of SimpleLabels as the original keeps them: a std::vector<SimpleLabel> and the number in use. Entries are
// reused; the vector only grows, by a new SimpleLabel (SimpleLabel::SimpleLabel 0x22194) when every entry is used.
struct LabelPool {
    std::vector<dungeonraid::SimpleLabelState> labels;
    std::int32_t count=0;
    dungeonraid::SimpleLabelState& next();   // the entry at count
    // Game::Process 0x17526: the active labels are processed; the number in use becomes the last active one + 1.
    void process(float dt);
};
}
