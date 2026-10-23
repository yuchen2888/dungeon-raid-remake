#include "dungeon_raid_session.hpp"
#include <gdextension_interface.h>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/defs.hpp>
#include <godot_cpp/godot.hpp>
using namespace godot;
// The library's entry (dungeon_raid.gdextension: entry_symbol): registers DungeonRaidSession for scripts.
namespace {
void initialize(ModuleInitializationLevel level) {
    if(level!=MODULE_INITIALIZATION_LEVEL_SCENE)return;
    GDREGISTER_CLASS(DungeonRaidSession);
}
void uninitialize(ModuleInitializationLevel) {}
}
extern "C" GDExtensionBool GDE_EXPORT dungeonraid_library_init(GDExtensionInterfaceGetProcAddress get_proc_address,
        GDExtensionClassLibraryPtr library,GDExtensionInitialization* init) {
    GDExtensionBinding::InitObject object(get_proc_address,library,init);
    object.register_initializer(initialize);
    object.register_terminator(uninitialize);
    object.set_minimum_library_initialization_level(MODULE_INITIALIZATION_LEVEL_SCENE);
    return object.init();
}
