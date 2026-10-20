#!/usr/bin/env python3
"""The native session (recovered_session) against the original, frame by frame (T040-G2).

The native side is one C++ session: its objects are loaded with the case (the harness loaders fill ctypes
objects, which are copied into the session's objects and linked), then dr_session_new_game and one
dr_session_frame per frame run every unit with the session's own wiring -- no Python callback takes part in
the play. The harness reads the state from the session's memory. Two phases:
- new games as verify_new_game_play.py (T040-F4): original InitNewGame, then the whole original
  Game::Process every frame; some games weakened (they end early), some strengthened (long games);
- carried mid-game states as verify_game_frames.py (T040-F3): random boards with every enemy type, flags,
  poison and abilities, a few turns each.
The original side is the F4 / F3 harness.

Compared after the start and after every frame: the game state of verify_game_frames.py plus the stroke's
resource counts (Game+0x164b0), without the event
lists (the units' events are compared by the unit tests; the session forwards them unchanged) and without
the flare / quad alpha mirrors (presentation the renderer keeps from those events).
"""
import ctypes as C
import json
import random
import verify_original
from verify_new_game_play import Original as NewGameOriginal, Native as NewGameNative, case
from verify_game_frames import Original as FramesOriginal, Native as FramesNative
from verify_full_turn import case as turn_case
from verify_full_turn import f32
from verify_stroke import HERE, I32, U8, Point, State as Stroke
from verify_motion import Motion, target as motion_target
from verify_abilities import TARGET_POINT
from verify_tokens import Counters
from verify_resources import INTS as RESOURCE_INTS

GAMES,TURNS,LONG_TURNS=9,12,40
CARRIED_GAMES,CARRIED_TURNS=10,5
NAMES=('stroke','preview','match','rune','tokens','resources','path','refill','generation','damage','animation','overlay_alpha',
       'attack_inputs','skills','turn_flags','finish','end','activated','end_of_turn','flights','release_inputs','classes','scroll',
       'player','extra','shatter','touch','screens','input_target','current_label_active','motions')
class Objects(C.Structure):
    _fields_=[(k,C.c_void_p) for k in NAMES]+[('motion_count',C.c_uint32),('falling',C.c_void_p),('falling_count',C.c_uint32)]
EVENT=C.CFUNCTYPE(None,C.c_void_p,I32,C.c_void_p)
TARGET=C.CFUNCTYPE(None,C.c_void_p,I32,I32,C.POINTER(Point))
CHOOSE=C.CFUNCTYPE(I32,C.c_void_p,C.POINTER(Motion))
START=C.CFUNCTYPE(None,C.c_void_p,I32,C.POINTER(Point))
class Host(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT),('target',TARGET),('choose',CHOOSE),('start',START)]
SOURCE_GENERATION,SOURCE_NEW_GAME=8,28

SCREEN_INIT=0x307f8   # GameOverScreen::Initialise
class OriginalMixin:
    def hook(self,u,address,size,context):
        if address==SCREEN_INIT and self.recording:   # recorded and skipped by the harness; its game state is written here
            u.mem_write(self.GAME+0xcac4,b'\x01');self.write(self.GAME+0xcc1c,0)
        return super().hook(u,address,size,context)
    def game_state(self):   # plus the stroke's resource counts (Game+0x164b0, ProcessResourceShadows)
        return dict(super().game_state(),counts=[C.c_int32(self.read(self.GAME+0x164b0+4*i)).value for i in range(6)],
                    game_over_state=C.c_int32(self.read(self.GAME+0xcc1c)).value)
class NewGameSessionOriginal(OriginalMixin,NewGameOriginal):pass
class CarriedSessionOriginal(OriginalMixin,FramesOriginal):pass

class SessionMixin:
    def __init__(self):
        super().__init__();lib=self.session_lib=C.CDLL(str(HERE/'recovered_session_native.dylib'));self.session=None
        lib.dr_session_create.argtypes=[C.POINTER(Host),I32];lib.dr_session_create.restype=C.c_void_p
        lib.dr_session_destroy.argtypes=[C.c_void_p];lib.dr_session_destroy.restype=None
        lib.dr_session_objects.argtypes=[C.c_void_p];lib.dr_session_objects.restype=Objects
        lib.dr_session_link.argtypes=[C.c_void_p];lib.dr_session_link.restype=None
        lib.dr_session_set_falling.argtypes=[C.c_void_p,C.POINTER(I32),C.c_uint32];lib.dr_session_set_falling.restype=None
        lib.dr_session_set_motions.argtypes=[C.c_void_p,C.POINTER(Motion),C.c_uint32];lib.dr_session_set_motions.restype=None
        lib.dr_session_new_game.argtypes=[C.c_void_p,C.c_uint32];lib.dr_session_new_game.restype=None
        lib.dr_session_frame.argtypes=[C.c_void_p,C.c_float,I32,Point];lib.dr_session_frame.restype=I32
        self.sources={}
        def event(_,source,p):
            k=(source,C.cast(p,C.POINTER(I32))[1 if source==6 else 0]);self.sources[k]=self.sources.get(k,0)+1   # (unit, event kind) seen in play (RoundEvent: kind second)
            if source==SOURCE_NEW_GAME:
                e=C.cast(p,C.POINTER(I32*4)).contents;self.new_events.append(list(e))
            elif source==SOURCE_GENERATION:
                e=C.cast(p,C.POINTER(I32*6)).contents;self.gen_events.append(list(e))
        def get_target(_,kind,index,out):out[0]=Point(*motion_target(kind,index))
        def choose(_,p):p.contents.linked=self.case['special_link'];return self.case['special_choice']
        def start(_,kind,out):out[0]=Point(*TARGET_POINT)
        self.host_cb=(EVENT(event),TARGET(get_target),CHOOSE(choose),START(start));self.host=Host(None,*self.host_cb)
    def load(self,c):
        if self.session:self.q=self.own_queue   # the loaders replace the harness's own token queue, not the session's
        super().load(c);lib=self.session_lib;self.own_queue=self.q
        if self.session:lib.dr_session_destroy(self.session)
        self.session=lib.dr_session_create(C.byref(self.host),1);o=lib.dr_session_objects(self.session)
        # the case, as the harness loaders built it, becomes the session's state
        pairs=dict(stroke=self.state,preview=self.p,match=self.m,rune=self.rune,resources=self.r,path=self.path_state,refill=self.refill,
                   generation=self.gen,damage=self.damage,animation=self.anim,overlay_alpha=self.overlay,attack_inputs=self.inputs,
                   skills=self.skills,turn_flags=self.turn_flags,finish=self.fin_flags,end=self.flags,activated=self.flags_254,
                   end_of_turn=self.eot_state,flights=self.flights,release_inputs=self.release_inputs,classes=self.classes,
                   scroll=self.scroll_state,player=getattr(self,'player',None),extra=self.extra,shatter=self.shatter,touch=self.touch,
                   screens=self.screens)
        pairs={k:v for k,v in pairs.items() if v is not None}   # the carried harness has no PlayerStats (zero)
        for name,obj in pairs.items():C.memmove(getattr(o,name),C.addressof(obj),C.sizeof(obj))
        lib.dr_session_link(self.session)
        moving=(I32*max(1,len(self.moving_list)))(*self.moving_list);lib.dr_session_set_falling(self.session,moving,len(self.moving_list))
        motions=[t for _,t in sorted(self.motions.items())];array=(Motion*max(1,len(motions)))(*motions)
        lib.dr_session_set_motions(self.session,array,len(motions))
        counters=self.token_counters();q=C.c_void_p(o.tokens)
        fn=self.tokens_lib.dr_token_queue_restore;fn.argtypes=[C.c_void_p,C.POINTER(Counters)];fn.restype=None;fn(q,C.byref(counters))
        # from here on the harness reads the session's memory
        o=lib.dr_session_objects(self.session)
        for name,obj in pairs.items():setattr(self,{v:k for k,v in self.attribute_names().items()}.get(name,name),type(obj).from_address(getattr(o,name)))
        self.fin_flags=self.finish;self.counter=U8.from_address(o.animation+type(self.anim).counterattack.offset)
        self.label_active=(U8*4).from_address(o.extra+type(self.extra).label_active.offset)
        self.q=o.tokens;self.sync()
    def attribute_names(self):
        return dict(state='stroke',p='preview',m='match',rune='rune',r='resources',path_state='path',refill='refill',gen='generation',
                    damage='damage',anim='animation',overlay='overlay_alpha',inputs='attack_inputs',skills='skills',turn_flags='turn_flags',
                    finish='finish',flags='end',flags_254='activated',eot_state='end_of_turn',flights='flights',release_inputs='release_inputs',
                    classes='classes',scroll_state='scroll',player='player',extra='extra',shatter='shatter',touch='touch',screens='screens')
    def sync(self):
        o=self.session_lib.dr_session_objects(self.session)
        self.moving_list=list((I32*o.falling_count).from_address(o.falling)) if o.falling_count else []
        self.motions={i:Motion.from_address(o.motions+i*C.sizeof(Motion)) for i in range(o.motion_count)}
    def game_state(self):
        return dict(super().game_state(),counts=list(self.state.counts),game_over_state=self.screens.game_over_state_cc1c)
    def new_game(self,time):
        self.new_events=[];self.gen_events=[];self.session_lib.dr_session_new_game(self.session,time);self.sync()
    def play_frame(self,phase,touch,dt):
        self.frame_route=self.session_lib.dr_session_frame(self.session,dt,phase,Point(*touch));self.sync()
        return dict(self.game_state(),reached_attack=self.frame_route==0)

class NewGameSession(SessionMixin,NewGameNative):pass
class CarriedSession(SessionMixin,FramesNative):pass

def state_only(x):
    """The game state without event lists and presentation mirrors."""
    if isinstance(x,dict):
        return {k:state_only(v) for k,v in x.items() if k not in ('events','encounters','end_events','flares','quads')}
    if isinstance(x,list):return [state_only(v) for v in x]
    return x

def set_health(old,new,health,maximum=None):
    old.write(old.GAME+RESOURCE_INTS['health'],health);new.r.health=health
    if maximum is not None:old.write(old.GAME+RESOURCE_INTS['health_max'],maximum);new.r.health_max=maximum

def main():
    rng=random.Random(0x5e55);frames=turns=moves=ended=0;routes={};sources={};phases={}
    def signed_states(x):
        if isinstance(x,dict):return {k:(C.c_int32(v).value if k=='enemy_state' and isinstance(v,int) else signed_states(v)) for k,v in x.items()}
        if isinstance(x,list):return [signed_states(v) for v in x]
        return x
    def compare(stage,a,b,**info):
        a,b=state_only(signed_states(a)),state_only(signed_states(b))
        if a!=b:
            (HERE/'session_failure.json').write_text(json.dumps(dict(stage=stage,info=info,original=a,native=b),indent=2,default=str))
            raise AssertionError(f'session_failure.json ({stage})')
    def play(old,new,game,count):
        nonlocal frames,turns,moves,ended
        for turn in range(count):
            path=new.pick_path(rng);moves+=len(path)>=3
            script=[(1,i) for i in path]+[(2,path[-1])] if len(path)>=3 else []
            for frame in range(3000):
                dt=f32(rng.choice([1/60,1/30]))
                if frame<len(script):
                    phase,i=script[frame];centre=new.state.selection.tiles[i].geometry.center;touch=[centre.x,centre.y]
                else:phase,touch=0,[0.5,0.5]
                if not script and frame==0:old.set_ready(0);new.set_ready(0)
                info=dict(game=game,turn=turn,frame=frame,phase=phase)
                a,b=old.play_frame(phase,touch,dt),new.play_frame(phase,touch,dt);compare('frame',a,b,**info);frames+=1
                routes[new.frame_route]=routes.get(new.frame_route,0)+1
                if new.frame_route==11 or new.flags.game_over_screen:ended+=1;return
                if frame>=len(script) and a['common']['input_ready'] and a['common']['phase']==0 and not new.moving_list and not a['common']['pending']:break
            else:raise AssertionError('turn did not finish')
            turns+=1
    old,new=NewGameSessionOriginal(),NewGameSession()
    for game in range(GAMES):
        c=case(rng);old.load(c);new.load(c)
        a=NewGameOriginal.run(old);new.new_game(c['new_game']['time'])
        compare('init events',[a['new_events'],a['events']],[new.new_events,new.gen_events],game=game)
        old.moving_list=[old.index(v) for v in old.list_values(old.GAME+0xb3f8)]
        if game%3==1:set_health(old,new,rng.choice([2,4,6]))   # weakened after the start: enemies end the game early
        elif game%3==2:set_health(old,new,1000,1000)            # strengthened: long games, later enemies
        compare('after init',old.game_state(),new.game_state(),game=game)
        play(old,new,game,LONG_TURNS if game%3==2 else TURNS)
    phases['new_games']=dict(games=GAMES,turns=turns,frames=frames,ended=ended);sources.update(new.sources)
    old,new=CarriedSessionOriginal(),CarriedSession()
    for game in range(CARRIED_GAMES):
        c=turn_case(rng);old.load(c);new.load(c)
        if game%2==0:set_health(old,new,5000,5000)   # most carried boards end the game within a turn
        compare('load',old.game_state(),new.game_state(),game=game)
        play(old,new,GAMES+game,CARRIED_TURNS)
    phases['carried']=dict(games=CARRIED_GAMES,turns=turns-phases['new_games']['turns'],frames=frames-phases['new_games']['frames'],
                           ended=ended-phases['new_games']['ended'])
    for k,v in new.sources.items():sources[k]=sources.get(k,0)+v
    assert phases['new_games']['ended'] and phases['carried']['ended'],phases
    report=dict(status='passed',phases=phases,turns=turns,moves=moves,frames=frames,games_ended=ended,frame_routes=routes,
                events_by_unit_kind={f'{k[0]}:{k[1]}':v for k,v in sorted(sources.items())},
                original='Original InitNewGame (new games) or a loaded state (carried), then the whole original Game::Process every frame',
                native='One recovered_session: dr_session_new_game (new games), then dr_session_frame (the session wires every unit itself)',
                boundaries=['time() returns the case seed; item construction and UpdateStats recorded (zero item stats)',
                            'the harness picks the paths; screens closed; interface targets from the harness',
                            'events and presentation mirrors not compared here (unit tests)'],
                scope='games from their start through many turns up to the end of the game, and carried mid-game states')
    (HERE/'session_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
