#pragma once
#include "dr_bridge.hpp"
#include "ui/presenter.hpp"
// The session calls the drawing layer's screens asked for in a frame (their originals call Game:: from inside
// Game::Process; nothing else runs after them in that frame, so the embedding makes them right after it), and what
// those screens then show of them. Shared by the Godot class and the reference checks' C face.
inline void run_front_requests(drfront::Bridge& bridge,drui::Presenter& ui) {
    using drui::SetupAction;
    const auto requests=std::move(ui.setup.requests);
    ui.setup.requests.clear();
    for(const auto& r:requests) {
        const dungeonraid::SessionObjects o=bridge.objects();
        switch(r.action) {
        case SetupAction::RandomName: bridge.setup_random_name();break;
        case SetupAction::Difficulty: bridge.setup_difficulty(r.value);break;
        case SetupAction::Mode: case SetupAction::ScreenMode: bridge.setup_mode(r.value);break;
        case SetupAction::Class: bridge.setup_select_class(r.value);break;
        case SetupAction::Start:   // the story the session drew (IntroScreen::Initialise: SetupScreen.story)
            if(bridge.setup_start(*o.time))ui.intro.initialise(ui.texts,o.setup->story);
            break;
        case SetupAction::Help: bridge.setup_help();break;
        case SetupAction::Back: bridge.setup_back();break;   // (MainMenu::Show: the session's MainMenuShow event)
        case SetupAction::Edit: bridge.class_open();break;
        default: break;
        }
        ui.setup.after_request(bridge.objects(),r);
    }
    const auto class_requests=std::move(ui.setup.class_requests());
    ui.setup.class_requests().clear();
    for(const auto& r:class_requests) {   // the class screen's (ClassScreen::Process)
        using drui::ClassAction;
        switch(r.action) {
        case ClassAction::Tab: bridge.class_tab();break;
        case ClassAction::Select: bridge.class_select(r.value);break;
        case ClassAction::Race: bridge.class_race(r.value);break;
        case ClassAction::Perk: bridge.class_perk(r.value,r.value2);break;
        case ClassAction::Flaw: bridge.class_flaw(r.value,r.value2);break;
        case ClassAction::Skill: bridge.class_skill(r.value,r.value2);break;
        case ClassAction::Help: bridge.class_help(r.value);break;
        case ClassAction::Done: bridge.class_done();break;
        }
        ui.setup.class_after(bridge.objects(),r);
    }
    if(ui.intro_ended){ui.intro_ended=false;bridge.intro_done();}   // IntroScreen::Process's end: Game::SerialiseState
}
