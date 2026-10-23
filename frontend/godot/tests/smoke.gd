extends SceneTree
# Headless check that Godot loads the native library and a game runs through it (T050-A):
#   Godot --headless --path frontend/godot -s res://tests/smoke.gd
# Plays turns with the rules' own hint paths (DungeonRaidSession.hint) and exits 1 when nothing happened.

func _init() -> void:
	if not ClassDB.class_exists("DungeonRaidSession"):
		push_error("DungeonRaidSession is missing: the library did not load")
		quit(1)
		return
	var s = ClassDB.instantiate("DungeonRaidSession")
	s.new_game(0, 20261021)
	# the new-game setup screen (T040-M3) and the story screen
	if not s.setup()["open"]:
		push_error("the setup screen did not open")
		quit(1)
		return
	for f in 30:   # its fade-in (0.3 s): no input
		s.frame(1.0 / 60.0, 0, Vector2(0.5, 0.75), -1, -1)
	_press(s)
	s.setup_random_name()
	_press(s)
	if not s.setup_start(20261022):
		push_error("Start was refused")
		quit(1)
		return
	s.intro_done()
	var turns := 0
	for t in range(20):
		var path: PackedInt32Array = s.hint()
		if path.is_empty():
			break
		var board: Array = s.board()
		var steps: Array = []
		for i in path:
			steps.append([1, board[i]["pos"]])
		steps.append([2, board[path[path.size() - 1]]["pos"]])
		for f in range(3000):
			var phase := 0
			var pos := Vector2(0.5, 1.45)
			if f < steps.size():
				phase = steps[f][0]
				pos = steps[f][1]
			var menu: Dictionary = s.menu()
			var button := -1
			if menu["open"] and menu["timer"] < 0.0:
				# choose, then confirm, as bridge_test does
				var choice := 14 if menu["first"] != 14 else 15
				var want_two: bool = menu["type"] == 0
				var ready: bool = menu["first"] != -1 and (not want_two or menu["second"] != -1)
				button = 7 if ready else choice
				phase = [0, 1, 2][f % 3]
			s.frame(1.0 / 60.0, phase, pos, -1, button)
			var st: Dictionary = s.state()
			if st["game_over"]:
				break
			if f > steps.size() and st["input_ready"] and st["attack_phase"] == 0 and st["falling"] == 0 and st["tokens_pending"] == 0 and not st["menu_open"]:
				break
		turns += 1
		if s.state()["game_over"]:
			break
	var st: Dictionary = s.state()
	print("smoke: %d turns, turn %d, level %d, health %d/%d, gold %d, saved %s, blobs %d" % [turns, st["turn"], st["level"], st["health"], st["health_max"], st["gold"], st["has_save"], s.take_changed().size()])
	quit(0 if st["turn"] > 0 else 1)

# A setup call counts only after a frame that began a touch (NameScreen::ProcessInput, T040-M7d): no touch, then one.
func _press(s) -> void:
	s.frame(1.0 / 60.0, 0, Vector2(0.5, 0.75), -1, -1)
	s.frame(1.0 / 60.0, 1, Vector2(0.5, 0.75), -1, -1)
