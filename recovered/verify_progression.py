#!/usr/bin/env python3
"""Replay original class save fixtures through the new native pointer layout."""
from pathlib import Path
import ctypes as C
import json
import platform

HERE=Path(__file__).resolve().parent
FIXTURES=HERE.parent/'runtime/liveexec32/original-progression-verification.json'


class Profile(C.Structure):
    _fields_=[('class_type',C.c_int32),('race',C.c_int32),('base_race',C.c_int32),
        ('perks',C.c_int32*4),('flaws',C.c_int32*4),
        ('replacement_skills',C.POINTER(C.c_int32)),('replacement_skill_count',C.c_size_t),
        ('level',C.c_uint8),('games_played',C.c_uint32),('enemies_killed',C.c_uint32),
        ('normal_score',C.c_uint32),('hard_score',C.c_uint32),('harder_score',C.c_uint32)]

MAP={'class_type':'m_class','race':'m_race','base_race':'m_baseRace','perks':'m_perks',
    'flaws':'m_flaws','level':'m_level','games_played':'m_gamesPlayed',
    'enemies_killed':'m_enemiesKilled','normal_score':'m_normalScore',
    'hard_score':'m_hardScore','harder_score':'m_harderScore'}
Achievement=C.CFUNCTYPE(None,C.c_void_p,C.c_int32,C.c_float)
class Hooks(C.Structure):
    _fields_=[('context',C.c_void_p),('achievement',Achievement)]


def make_roster(values):
    roster=(Profile*10)();backings=[]
    for i,row in enumerate(values):
        for native,original in MAP.items():
            value=row[original]
            setattr(roster[i],native,(C.c_int32*4)(*value) if isinstance(value,list) else value)
        backing=(C.c_int32*len(row['m_replacementSkills']))(*row['m_replacementSkills'])
        roster[i].replacement_skills=backing
        roster[i].replacement_skill_count=len(backing)
        backings.append(backing)
    return roster,backings


def view(profile):
    values={old:(list(getattr(profile,native)) if native in ('perks','flaws') else getattr(profile,native))
            for native,old in MAP.items()}
    values['m_replacementSkills']=list(profile.replacement_skills[:profile.replacement_skill_count])
    return values


def expected(row):return {key:row[key] for key in [*MAP.values(),'m_replacementSkills']}


def main():
    fixtures=json.loads(FIXTURES.read_text())
    lib=C.CDLL(str(HERE/'recovered_progression_native.dylib'))
    lib.dr_progression_pointer_size.restype=C.c_uint32
    assert lib.dr_progression_pointer_size()==C.sizeof(C.c_void_p)==8
    for name in ('dr_class_write_game','dr_class_read_game','dr_class_write_full','dr_class_read_full'):
        fn=getattr(lib,name);fn.argtypes=[C.POINTER(Profile),C.POINTER(C.c_uint8),C.c_size_t];fn.restype=C.c_size_t
    for name in ('dr_classes_write','dr_classes_read'):
        fn=getattr(lib,name);fn.argtypes=[C.POINTER(Profile),C.c_size_t,C.POINTER(C.c_uint8),C.c_size_t];fn.restype=C.c_size_t
    lib.dr_class_validate.argtypes=[C.POINTER(Profile)];lib.dr_class_validate.restype=C.c_bool
    lib.dr_replacement_skill_count.argtypes=[C.POINTER(Profile)];lib.dr_replacement_skill_count.restype=C.c_size_t
    lib.dr_class_level_up.argtypes=[C.POINTER(Profile),C.c_size_t,C.c_size_t,C.c_int32,C.POINTER(Hooks)]
    lib.dr_class_level_up.restype=C.c_bool
    checks=0
    for case in fixtures['fixtures']:
        roster,backings=make_roster(case['profiles_before'])
        output=(C.c_uint8*512)(*([0xa5]*512))
        length=lib.dr_classes_write(roster,10,output,len(output))
        blob=bytes.fromhex(case['blob_hex'])
        assert length==len(blob)==472
        assert bytes(output[:472])==blob
        assert bytes(output[472:])==b'\xa5'*40
        assert [view(p) for p in roster]==[expected(p) for p in case['profiles_after_encode']]
        checks+=10
        loaded,load_backings=make_roster(fixtures['defaults'])
        assert lib.dr_classes_read(loaded,10,output,length)==472
        assert [view(p) for p in loaded]==[expected(p) for p in case['profiles']]
        checks+=10
        for index in range(10):
            encoded=(C.c_uint8*64)(*([0xa5]*64))
            assert lib.dr_class_write_full(C.byref(roster[index]),encoded,64)==47
            assert bytes(encoded[:47])==blob[2+47*index:2+47*(index+1)]
            assert bytes(encoded[47:])==b'\xa5'*17
            assert lib.dr_class_write_game(C.byref(roster[index]),encoded,64)==26
            assert bytes(encoded[:26])==blob[2+47*index:2+47*index+26]
            assert lib.dr_replacement_skill_count(C.byref(roster[index]))==sum(s!=255 for s in roster[index].replacement_skills[:20])
            checks+=3
    # Added native bounds guards must reject partial data before changing a
    # profile or its separately allocated skill array.
    loaded,backings=make_roster(fixtures['defaults']);before=[view(p) for p in loaded]
    blob=bytes.fromhex(fixtures['fixtures'][0]['blob_hex'])
    data=(C.c_uint8*len(blob)).from_buffer_copy(blob)
    rejected=0
    for length in range(472):
        assert lib.dr_classes_read(loaded,10,data,length)==0
        assert [view(p) for p in loaded]==before
        rejected+=1
    for length in range(47):
        assert lib.dr_class_read_full(C.byref(loaded[0]),data,length)==0
        assert view(loaded[0])==before[0]
        rejected+=1
    for bad_count in (0,1,9,11,255):
        data[1]=bad_count
        assert lib.dr_classes_read(loaded,10,data,472)==0
        assert [view(p) for p in loaded]==before
        rejected+=1
    level_checks=0
    for case in fixtures['leveling']:
        roster,backings=make_roster(case['before']);events=[]
        callback=Achievement(lambda context,achievement,progress:events.append([achievement,progress]))
        hooks=Hooks(None,callback)
        assert lib.dr_class_level_up(roster,10,case['index'],case['difficulty'],C.byref(hooks))
        assert [view(p) for p in roster]==[expected(p) for p in case['after']]
        assert events==case['achievements'],(case['index'],case['difficulty'],events,case['achievements'])
        level_checks+=1
    result={'status':'passed','native_architecture':platform.machine(),
        'native_pointer_bytes':lib.dr_progression_pointer_size(),'native_profile_bytes':C.sizeof(Profile),
        'original_fixture_profile_roundtrips':fixtures['profile_roundtrips'],
        'differential_checks':checks,'native_partial_or_invalid_inputs_rejected':rejected,
        'level_up_and_achievement_event_scenarios':level_checks,
        'format':'original 26-byte class, 47-byte full class, 472-byte ten-class roster',
        'scope':'class progression codec; Game dirty flags, live gameplay and UI remain outside this module'}
    suffix='_arm64' if platform.machine()=='arm64' else '_x86_64'
    (HERE/('progression_verification'+suffix+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
