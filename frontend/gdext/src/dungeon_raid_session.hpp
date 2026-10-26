#pragma once
#include "dr_bridge.hpp"
#include "ui/presenter.hpp"
#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/variant/array.hpp>
#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/packed_byte_array.hpp>
#include <godot_cpp/variant/packed_int32_array.hpp>
#include <godot_cpp/variant/vector2.hpp>
#include <memory>
// The Godot face of drfront::Bridge (T050-A): one object per app run, read and driven by the scene script. All
// positions are session units (screen 1 wide, 1.5 high); the script scales them to the window.
class DungeonRaidSession : public godot::RefCounted {
    GDCLASS(DungeonRaidSession,godot::RefCounted);
public:
    DungeonRaidSession();
    void restore(const godot::String& key,const godot::PackedByteArray& bytes);
    void new_game(int kind,int seed);
    bool continue_game(int seed);
    bool has_save();
    void leave_game_over();        // the trial prototype's (main.gd) way out of the game-over screen
    bool main_menu_open();         // the main menu takes the touches
    bool scores_open();            // the high scores are open (they too act on the last touch after it ends)
    godot::Dictionary setup();     // the setup screen: open, challenge, name, named, class, difficulty, mode, classes
    void setup_random_name();
    bool setup_select_class(int type);
    bool setup_difficulty(int difficulty);
    bool setup_mode(int mode);
    bool setup_start(int seed);
    void intro_done();
    int frame(double dt,int phase,godot::Vector2 touch,int skill_button,int menu_button);
    godot::Array take_changed();   // [[key, bytes], ...]
    godot::Array sounds();         // the last frame's sounds to play, in order: [[sound, recording], ...] (sounds.json)
    godot::Array board();          // 36 Dictionaries in board order (index = y * 6 + x of the slot)
    godot::PackedInt32Array path();
    godot::Dictionary state();
    godot::Array skills();
    godot::Dictionary menu();
    godot::Array items();          // the five equipped items
    godot::Array tokens();         // the flying tokens
    godot::Array labels();         // the leech, flame and spike labels that are showing
    godot::PackedInt32Array hint();
    // The original game's drawing (frontend/gdext/src/ui): load_presentation(assets folder, language folder or "")
    // reads the original fonts (and a language's texts and wide glyphs, T050-D) and attaches the presenter to the
    // session's events (before any game); render(scale) draws a frame and returns it as batches [texture
    // (GetTextureName: 0 none, 1 tiles .. 6 fontScore; 7..9 the wide glyphs), points (screen units x scale),
    // colours, texture coordinates, triangle indices], consecutive draws of one texture merged.
    bool load_presentation(const godot::String& assets,const godot::String& language);
    godot::Array render(double scale);
    int skill_button_at(godot::Vector2 touch);   // the skill button (0..3), menu button (4) or stats button (5); -1
    int menu_button_at(godot::Vector2 touch);    // the open menu's button under a touch (-1 none)
    // The settings page (T050-D, T050-J): open over the main menu (the touches are its own then: the game gets none).
    // settings_configure: the languages offered (each its row in the names picture) and the embedding's values;
    // settings_touch gives SettingsView::Result (1 a value changed, 2 the language changed, 3 the volume slides, 4 an
    // original switch flipped, 5 another page, 100 closed, -1 nothing); settings_values reads the values back
    // (language: an index into the configured ones, volume, vibration, hd, fast).
    void settings_configure(const godot::PackedInt32Array& name_rows,int language,double volume,bool vibration,bool hd,
                            bool fast);
    godot::Dictionary settings_values();
    bool settings_open();
    int settings_touch(int phase,godot::Vector2 touch);
protected:
    static void _bind_methods();
private:
    godot::Array sounds_;
    std::unique_ptr<drfront::Bridge> bridge_;
    std::unique_ptr<drui::Presenter> ui_;
    std::unique_ptr<std::pair<drfront::Bridge*,drui::Presenter*>> link_;
    std::uint32_t hint_seed_=1;
};
