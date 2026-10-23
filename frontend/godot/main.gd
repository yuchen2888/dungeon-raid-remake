extends Node2D
# Dungeon Raid remake, Godot trial prototype (T050-A). Every rule runs in the native session (DungeonRaidSession,
# frontend/gdext); this script draws simple shapes, turns the mouse into the session's touch phases and buttons,
# and stores the session's bytes under user://. Positions are session units (the screen is 1 wide, 1.5 high, the
# board fills y 0.246875 .. 1.246875); S pixels per unit on the 640 x 960 canvas.
# Start with "-- --autoplay" to let the script click through games by itself (used for checks and recordings).

const S := 640.0
const BOARD_TOP := 0.246875
const PITCH := 1.0 / 6.0
enum Screen { TITLE, SETUP, INTRO, GAME, OVER }
const STORE_KEYS := ["classes", "scores0", "scores1", "scores2", "scores3", "scores4", "scores5", "game", "spawn"]
const TILE_COLOURS := [Color(0.86, 0.18, 0.22), Color(0.86, 0.84, 0.78), Color(0.96, 0.78, 0.22), Color(0.32, 0.52, 0.92), Color(0.72, 0.86, 0.92)]
const RESOURCE_NAMES := ["生命", "经验", "金币", "护甲", "升级点"]
const RESOURCE_COLOURS := [Color(0.86, 0.2, 0.24), Color(0.35, 0.8, 0.4), Color(0.96, 0.78, 0.22), Color(0.4, 0.6, 0.95), Color(0.75, 0.65, 0.95)]
const DIFFICULTY_NAMES := ["简单", "普通", "困难", "更难"]
const ITEM_TYPE_NAMES := ["武器", "装备2", "装备3", "装备4", "装备5"]
# Prototype names from each skill's recovered effect (Skill::Activate, docs/T040_SKILLS.md), not the original text.
const SKILL_NAMES := ["攻击得金币", "冻结骷髅", "收集药水", "收集盾牌", "反击", "破除护甲", "剑变金币", "传送",
	"爆炸药水", "药水换经验", "装备升级", "收集一行", "收集金币", "剑变盾牌", "骷髅变剑", "金币变剑",
	"双倍伤害", "双倍金币", "双倍回复", "双倍升级点", "降级强敌", "消灭强敌", "敌人一血", "强化敌人",
	"只出金币", "魔法剑", "地震", "护甲爆炸", "收集一块", "法力药水", "一列变剑", "箭矢",
	"金币变骷髅", "清空棋盘", "技能34", "符文", "骷髅换金币", "保命", "收集边缘", "连锁"]
# Item stats by UpgradeType (what Game::UpdateStats adds them to, recovered_stats.cpp).
const STAT_NAMES := ["剑伤害", "骷髅伤害", "吸血", "毒", "破甲几率", "技能冷却", "经验加成", "金币加成",
	"加成几率A", "加成几率D", "生命上限", "护甲上限", "全体伤害", "升级点加成", "护甲损失减少", "削弱敌人",
	"护盾加成", "每回合回复", "加成几率B", "加成几率C"]

var session = null
var font: Font
var screen := Screen.TITLE
var autoplay := false
var error_text := ""
# The pointer: queued phases for the session's frames, whether it is held, where it is, where it went down.
var queue: Array = []
var held := false
var cursor := Vector2(0.5, 1.45)
var press_at := Vector2(-1, -1)
var auto_steps: Array = []
var show_hint := false
var hint_path := PackedInt32Array()
# The latest read of the session.
var st: Dictionary = {}
var tiles: Array = []
var path := PackedInt32Array()
var skills: Array = []
var menu: Dictionary = {}
var tokens: Array = []
var labels: Array = []
var items: Array = []
var setup: Dictionary = {}
var styles: Dictionary = {}
var store_dir := "user://"
var last_turn := -1
var shots_dir := ""          # autoplay with "--shots=<folder>": screenshots of each screen, for checks
var shots_taken: Dictionary = {}
var frames := 0
var menu_frames := 0         # frames the in-game menu has been open

func _ready() -> void:
	# A system font with every Chinese glyph: the default font's fallback misses some (杀, 敌), and on macOS the
	# name "PingFang SC" resolves to PingFang HK, which misses them too.
	var system := SystemFont.new()
	system.font_names = PackedStringArray(["Hiragino Sans GB", "STHeiti", "Noto Sans CJK SC", "Microsoft YaHei", "PingFang SC"])
	font = system
	autoplay = OS.get_cmdline_user_args().has("--autoplay")
	if autoplay:   # its own save folder, so the player's saved game stays untouched
		store_dir = "user://autoplay/"
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(store_dir))
		for arg in OS.get_cmdline_user_args():
			if arg.begins_with("--shots="):
				shots_dir = arg.substr(8)
				get_window().always_on_top = true   # macOS stops drawing a covered window
	if not ClassDB.class_exists("DungeonRaidSession"):
		error_text = "没有加载到游戏规则库（frontend/godot/bin/）。\n请先运行 frontend/gdext/build.py extension。"
		return
	session = ClassDB.instantiate("DungeonRaidSession")
	for key in STORE_KEYS:
		var file: String = store_dir + key + ".bin"
		if FileAccess.file_exists(file):
			session.restore(key, FileAccess.get_file_as_bytes(file))
	_read()

func _seed() -> int:
	return int(Time.get_unix_time_from_system() * 1000.0 + Time.get_ticks_usec()) & 0x7fffffff

# The bytes the session changed (the saved game, class records, high scores, the scroll countdown), written whole
# to a temporary file and renamed so a crash never leaves half a file; an empty saved game is deleted.
func _store() -> void:
	for pair in session.take_changed():
		var key: String = pair[0]
		var bytes: PackedByteArray = pair[1]
		var file := ProjectSettings.globalize_path(store_dir + key + ".bin")
		if key == "game" and bytes.is_empty():
			if FileAccess.file_exists(file):
				DirAccess.remove_absolute(file)
			continue
		var tmp := file + ".tmp"
		var f := FileAccess.open(tmp, FileAccess.WRITE)
		if f == null:
			push_error("cannot write " + tmp)
			continue
		f.store_buffer(bytes)
		f.close()
		DirAccess.rename_absolute(tmp, file)

func _read() -> void:
	st = session.state()
	tiles = session.board()
	path = session.path()
	skills = session.skills()
	menu = session.menu()
	tokens = session.tokens()
	labels = session.labels()
	items = session.items()
	setup = session.setup()

# ---- input -------------------------------------------------------------------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		var p: Vector2 = make_input_local(event).position / S
		if event.pressed:
			_pointer_down(p)
		else:
			_pointer_up(p)
	elif event is InputEventMouseMotion:
		_pointer_move(make_input_local(event).position / S)
	elif event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_ESCAPE and screen != Screen.TITLE:
			_to_title()
		elif event.keycode == KEY_H and screen == Screen.GAME:
			show_hint = not show_hint
			hint_path = session.hint() if show_hint else PackedInt32Array()

func _pointer_down(p: Vector2) -> void:
	cursor = p
	press_at = p
	if screen == Screen.GAME and not _over_back(p):
		queue.append([1, p])
		held = true

func _pointer_move(p: Vector2) -> void:
	cursor = p

func _pointer_up(p: Vector2) -> void:
	cursor = p
	if screen == Screen.GAME and held:
		queue.append([2, p])
		held = false
		return
	var down := _button_at(press_at)
	var up := _button_at(p)
	press_at = Vector2(-1, -1)
	if up != "" and up == down:
		_press(up)

func _over_back(p: Vector2) -> bool:
	return _button_at(p) == "back"

# ---- the screens' own buttons (main menu, setup, story, game over, back) -----------------------------------

func _buttons() -> Array:
	var b: Array = []
	match screen:
		Screen.TITLE:
			var y := 0.62
			if session != null and session.has_save():
				b.append({"id": "continue", "rect": Rect2(0.2, y, 0.6, 0.1), "text": "继续上一局"})
				y += 0.13
			b.append({"id": "new0", "rect": Rect2(0.2, y, 0.6, 0.1), "text": "新游戏"})
			b.append({"id": "new1", "rect": Rect2(0.2, y + 0.13, 0.6, 0.1), "text": "教程"})
			b.append({"id": "new2", "rect": Rect2(0.2, y + 0.26, 0.6, 0.1), "text": "挑战"})
		Screen.SETUP:
			b.append({"id": "random", "rect": Rect2(0.62, 0.3, 0.32, 0.08), "text": "随机名字"})
			var classes: Array = setup.get("classes", [])
			for i in classes.size():
				var c: Dictionary = classes[i]
				var r := Rect2(0.05 + 0.18 * (i % 5), 0.5 + 0.12 * (i / 5), 0.16, 0.1)
				var text := "职业%d\nLv %d" % [i + 1, c["level"]] if c["unlocked"] else "职业%d\n未解锁" % [i + 1]
				b.append({"id": "class%d" % i, "rect": r, "text": text, "enabled": c["unlocked"], "on": setup["class"] == i})
			if setup.get("challenge", false):
				for m in 2:
					b.append({"id": "mode%d" % m, "rect": Rect2(0.1 + 0.42 * m, 0.86, 0.38, 0.09), "text": "挑战模式 %d" % [m + 1], "on": setup["mode"] == m})
			else:
				for d in 4:
					b.append({"id": "diff%d" % d, "rect": Rect2(0.05 + 0.23 * d, 0.86, 0.21, 0.09), "text": DIFFICULTY_NAMES[d], "on": setup["difficulty"] == d})
			b.append({"id": "start", "rect": Rect2(0.3, 1.08, 0.4, 0.11), "text": "开始", "enabled": setup.get("named", false)})
			b.append({"id": "title", "rect": Rect2(0.3, 1.25, 0.4, 0.08), "text": "返回"})
		Screen.INTRO:
			b.append({"id": "intro", "rect": Rect2(0.3, 1.1, 0.4, 0.11), "text": "继续"})
		Screen.OVER:
			b.append({"id": "leave", "rect": Rect2(0.2, 1.02, 0.6, 0.11), "text": "回到主菜单"})
		Screen.GAME:
			b.append({"id": "back", "rect": Rect2(0.78, 0.0, 0.21, 0.04), "text": "主菜单 Esc", "small": true})
	return b

func _button_at(p: Vector2) -> String:
	for b in _buttons():
		var r: Rect2 = b["rect"]
		if r.has_point(p) and b.get("enabled", true):
			return b["id"]
	return ""

func _press(id: String) -> void:
	if id == "continue":
		if session.continue_game(_seed()):
			_start_playing()
	elif id.begins_with("new"):
		session.new_game(int(id.substr(3)), _seed())
		screen = Screen.SETUP
	elif id == "random":
		session.setup_random_name()
	elif id.begins_with("class"):
		session.setup_select_class(int(id.substr(5)))
	elif id.begins_with("mode"):
		session.setup_mode(int(id.substr(4)))
	elif id.begins_with("diff"):
		session.setup_difficulty(int(id.substr(4)))
	elif id == "start":
		if session.setup_start(_seed()):
			screen = Screen.INTRO
	elif id == "intro":
		session.intro_done()
		_start_playing()
	elif id == "leave":
		session.leave_game_over()
		_to_title()
	elif id == "title" or id == "back":
		_to_title()
	_store()
	_read()

func _start_playing() -> void:
	screen = Screen.GAME
	queue.clear()
	held = false
	show_hint = false
	hint_path = PackedInt32Array()

func _to_title() -> void:
	screen = Screen.TITLE
	queue.clear()
	held = false

# ---- the session's buttons: skills below the board, the level-up / shop / upgrade menu ---------------------

func _skill_rect(i: int) -> Rect2:
	return Rect2(0.01 + 0.25 * i, 1.265, 0.23, 0.215)

func _skill_at(p: Vector2) -> int:
	for i in skills.size():
		if _skill_rect(i).has_point(p):
			return i
	return -1

# FoldoutMenu buttons: 14..17 the options (the shop has three), 7 confirm.
func _menu_rects() -> Dictionary:
	var r := {}
	var n := 3 if menu.get("type", 0) == 1 else 4
	for i in n:
		r[14 + i] = Rect2(0.07, 0.4 + 0.165 * i, 0.86, 0.15)
	r[7] = Rect2(0.3, 1.1, 0.4, 0.09)
	return r

func _menu_button_at(p: Vector2) -> int:
	var rects := _menu_rects()
	for k in rects:
		if rects[k].has_point(p):
			return k
	return -1

func _skill_name(type: int) -> String:
	return SKILL_NAMES[type] if type >= 0 and type < SKILL_NAMES.size() else "技能%d" % type

func _option_lines(i: int) -> Array:
	var type: int = menu["type"]
	if type == 0:
		var o: Dictionary = menu["options"][i]
		if o["type"] < 40:
			return [_skill_name(o["type"]), "技能 · 冷却 %d 回合" % o["max"] if o["max"] >= 0 else "技能 · 只能用一次"]
		var parts: Array = []
		for pair in [["health", "生命上限"], ["healing", "药水回复"], ["shield", "盾牌护甲"], ["damage", "基础伤害"]]:
			if o[pair[0]] != 0:
				parts.append("%s +%d" % [pair[1], o[pair[0]]])
		var chance: PackedInt32Array = o["chance"]
		for k in 4:
			if chance[k] != 0:
				parts.append("加成几率%s +%d%%" % ["ABCD"[k], chance[k]])
		return ["属性提升", "，".join(parts) if not parts.is_empty() else "（无）"]
	if type == 1:
		var it: Dictionary = menu["items"][i]
		var lines: Array = ["%s" % ITEM_TYPE_NAMES[clampi(it["type"], 0, 4)], _stats_text(it["stats"])]
		if menu["scroll_slot"] == i:
			lines.append("附赠卷轴：" + _skill_name(menu["scroll"]["type"]))
		return lines
	var slot: int = menu["upgrade_items"][i]
	var item_type: int = items[slot]["type"] if slot >= 0 and slot < items.size() else -1
	var stat: int = menu["upgrade_type"][i]
	var item_name: String = ITEM_TYPE_NAMES[item_type] if item_type >= 0 and item_type < 5 else "装备"
	var stat_name: String = STAT_NAMES[stat] if stat >= 0 and stat < 20 else "属性%d" % stat
	return [item_name, "%s +%d" % [stat_name, menu["upgrade_amount"][i]]]

func _stats_text(stats: PackedInt32Array) -> String:
	var parts: Array = []
	for k in stats.size():
		if stats[k] != 0:
			parts.append("%s %+d" % [STAT_NAMES[k], stats[k]])
	return "，".join(parts) if not parts.is_empty() else "（无属性）"

# ---- frames -----------------------------------------------------------------------------------------------

func _process(delta: float) -> void:
	if session == null:
		queue_redraw()
		return
	frames += 1
	if shots_dir != "":
		_shots()
	if autoplay and frames > 20:
		_autoplay()
	if screen == Screen.GAME:
		var phase := 0
		var pos := cursor
		if not queue.is_empty():
			var e: Array = queue.pop_front()
			phase = e[0]
			pos = e[1]
		elif held:
			phase = 1
		var skill_button := -1
		var menu_button := -1
		if phase != 0:
			if st.get("menu_open", false):
				menu_button = _menu_button_at(pos)
			else:
				skill_button = _skill_at(pos)
		session.frame(minf(delta, 0.05), phase, pos, skill_button, menu_button)
		_store()
		_read()
		if phase == 2 and show_hint:
			show_hint = false
			hint_path = PackedInt32Array()
		menu_frames = menu_frames + 1 if st["menu_open"] else 0
		if st["game_over"]:
			screen = Screen.OVER
		if autoplay and st["turn"] != last_turn:
			last_turn = st["turn"]
			if last_turn % 10 == 0:
				print("autoplay: turn %d, level %d, health %d/%d, gold %d, skills %d" % [st["turn"], st["level"], st["health"], st["health_max"], st["gold"], skills.size()])
	if autoplay and screen == Screen.OVER and (shots_dir == "" or shots_taken.has("over")):
		print("autoplay: game over at turn %d, level %d, kills %d" % [st["turn"], st["level"], st["kills"]])
		get_tree().quit(0)
	queue_redraw()

# The script plays by itself: the main menu's new game, a random name and Start, then the rules' own hint paths,
# options then confirm in the menus, a ready skill now and then; it stops at the game-over screen.
func _autoplay() -> void:
	if not auto_steps.is_empty():
		var s: Array = auto_steps.pop_front()
		match s[0]:
			"down": _pointer_down(s[1])
			"move": _pointer_move(s[1])
			"up": _pointer_up(s[1])
		return
	match screen:
		Screen.TITLE:
			_auto_click(Rect2(0.2, 0.62, 0.6, 0.1).get_center() if not session.has_save() else _rect_of("new0").get_center())
		Screen.SETUP:
			_auto_click(_rect_of("random" if not setup["named"] else "start").get_center())
		Screen.INTRO:
			_auto_click(_rect_of("intro").get_center())
		Screen.GAME:
			if st["menu_open"]:
				if menu["timer"] < 0.0 and menu_frames > 30:
					var need_two: bool = menu["type"] == 0
					if menu["first"] == -1:
						_auto_click(_menu_rects()[14].get_center())
					elif need_two and menu["second"] == -1:
						_auto_click(_menu_rects()[15 if menu["first"] != 15 else 16].get_center())
					else:
						_auto_click(_menu_rects()[7].get_center())
				return
			if not (st["input_ready"] and st["attack_phase"] == 0 and st["falling"] == 0 and st["tokens_pending"] == 0) or held or not queue.is_empty():
				return
			for i in skills.size():
				if skills[i]["ready"] and randi() % 4 == 0:
					_auto_click(_skill_rect(i).get_center())
					return
			var hint: PackedInt32Array = session.hint()
			if hint.is_empty():
				return
			auto_steps.append(["down", tiles[hint[0]]["pos"]])
			for i in hint:
				auto_steps.append(["move", tiles[i]["pos"]])
				auto_steps.append(["wait", null])
			auto_steps.append(["up", tiles[hint[hint.size() - 1]]["pos"]])

# The frame shown last (one frame old), saved once per moment.
func _shots() -> void:
	var name := ""
	match screen:
		Screen.TITLE: name = "title" if frames > 10 else ""
		Screen.SETUP: name = "setup"
		Screen.INTRO: name = "intro"
		Screen.OVER: name = "over"
		Screen.GAME:
			if st["menu_open"] and menu_frames > 20:
				name = "menu%d" % menu["type"]
			elif path.size() >= 4:
				name = "stroke"
			elif st["attack_phase"] != 0 and st["incoming_damage"] > 0:
				name = "attack"
			elif st["turn"] == 20 and st["input_ready"]:
				name = "turn20"
	if name == "" or shots_taken.has(name):
		return
	shots_taken[name] = frames
	if frames - shots_taken.get("_last", -100) < 3 and name != "over":
		shots_taken.erase(name)
		return
	shots_taken["_last"] = frames
	get_viewport().get_texture().get_image().save_png(shots_dir.path_join(name + ".png"))

func _auto_click(p: Vector2) -> void:
	auto_steps.append_array([["wait", null], ["wait", null], ["down", p], ["wait", null], ["up", p], ["wait", null]])

func _rect_of(id: String) -> Rect2:
	for b in _buttons():
		if b["id"] == id:
			return b["rect"]
	return Rect2()

# ---- drawing ----------------------------------------------------------------------------------------------

func _style(fill: Color, border: Color, width: int, radius: int) -> StyleBoxFlat:
	var key := "%s|%s|%d|%d" % [fill.to_html(), border.to_html(), width, radius]
	if not styles.has(key):
		var sb := StyleBoxFlat.new()
		sb.bg_color = fill
		sb.border_color = border
		sb.set_border_width_all(width)
		sb.set_corner_radius_all(radius)
		sb.anti_aliasing = true
		styles[key] = sb
	return styles[key]

func _box(r: Rect2, fill: Color, border := Color(0, 0, 0, 0), width := 0, radius := 12) -> void:
	draw_style_box(_style(fill, border, width, radius), Rect2(r.position * S, r.size * S))

# Text centred on p (or starting at p with left = true), in pixels of the 640-wide canvas; "\n" breaks lines.
func _text(p: Vector2, text: String, size := 24, colour := Color.WHITE, left := false) -> void:
	var lines := text.split("\n")
	var y := p.y * S - (lines.size() - 1) * size * 0.6
	for line in lines:
		var w := font.get_string_size(line, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
		var x := p.x * S if left else p.x * S - w / 2.0
		draw_string(font, Vector2(x, y + size * 0.36), line, HORIZONTAL_ALIGNMENT_LEFT, -1, size, colour)
		y += size * 1.2

func _draw() -> void:
	draw_rect(Rect2(0, 0, S, S * 1.5), Color(0.08, 0.07, 0.1))
	if session == null:
		_text(Vector2(0.5, 0.7), error_text, 24, Color(1, 0.6, 0.6))
		return
	match screen:
		Screen.TITLE: _draw_title()
		Screen.SETUP: _draw_setup()
		Screen.INTRO: _draw_intro()
		Screen.GAME, Screen.OVER: _draw_game()
	for b in _buttons():
		_draw_button(b)

func _draw_button(b: Dictionary) -> void:
	var enabled: bool = b.get("enabled", true)
	var on: bool = b.get("on", false)
	var fill := Color(0.3, 0.26, 0.42) if enabled else Color(0.18, 0.17, 0.2)
	if on:
		fill = Color(0.55, 0.42, 0.18)
	var r: Rect2 = b["rect"]
	_box(r, fill, Color(0.9, 0.8, 0.5) if on else Color(0, 0, 0, 0), 3 if on else 0, 10)
	_text(r.get_center(), b["text"], 18 if b.get("small", false) else 24, Color.WHITE if enabled else Color(0.5, 0.5, 0.5))

func _draw_title() -> void:
	_text(Vector2(0.5, 0.26), "Dungeon Raid", 64, Color(0.96, 0.8, 0.35))
	_text(Vector2(0.5, 0.36), "重制版 · Godot 试玩原型", 28, Color(0.8, 0.8, 0.85))
	_text(Vector2(0.5, 1.3), "玩法：在棋盘上按住鼠标，拖过 3 个以上相连的同类格子再松开。\n剑和骷髅可以连在一起，剑越多伤害越高。\nEsc 回主菜单，H 显示一条可连的线。", 20, Color(0.7, 0.7, 0.75))

func _draw_setup() -> void:
	_text(Vector2(0.5, 0.15), "开局设置", 40, Color(0.96, 0.8, 0.35))
	_text(Vector2(0.06, 0.34), "名字：" + setup.get("name", ""), 26, Color.WHITE, true)
	_text(Vector2(0.06, 0.45), "职业（只有已解锁的可选）", 22, Color(0.8, 0.8, 0.85), true)
	_text(Vector2(0.06, 0.8), "挑战模式" if setup.get("challenge", false) else "难度", 22, Color(0.8, 0.8, 0.85), true)

func _draw_intro() -> void:
	_text(Vector2(0.5, 0.45), "故事", 44, Color(0.96, 0.8, 0.35))
	_text(Vector2(0.5, 0.7), "（原版的故事文字还没接进来，\n点「继续」进入地下城）", 24, Color(0.8, 0.8, 0.85))

func _draw_game() -> void:
	_box(Rect2(0, BOARD_TOP, 1, 1), Color(0.12, 0.11, 0.15), Color(0, 0, 0, 0), 0, 0)
	var selecting := path.size() > 0
	for t in tiles:
		_draw_tile(t, selecting and t["dimmed"] and not t["selected"])
	if path.size() > 1:
		var pts := PackedVector2Array()
		for i in path:
			pts.append(tiles[i]["pos"] * S)
		draw_polyline(pts, Color(1, 1, 0.8, 0.6), 10.0, true)
	if hint_path.size() > 1:
		var pts := PackedVector2Array()
		for i in hint_path:
			pts.append(tiles[i]["pos"] * S)
		draw_polyline(pts, Color(0.4, 1, 0.5, 0.5), 6.0, true)
	# New tiles fall in from above the board: the top area is drawn over them, as the original's bars are.
	draw_rect(Rect2(0, 0, S, BOARD_TOP * S), Color(0.08, 0.07, 0.1))
	_draw_top()
	if selecting and st["current_damage"] > 0:
		var last: Vector2 = tiles[path[path.size() - 1]]["pos"]
		var at := Vector2(clampf(last.x, 0.12, 0.88), maxf(last.y - 0.11, BOARD_TOP + 0.04))
		_box(Rect2(at - Vector2(0.1, 0.03), Vector2(0.2, 0.06)), Color(0.6, 0.1, 0.12, 0.9))
		_text(at, "伤害 %d" % st["current_damage"], 22)
	for k in tokens:
		var tc: Color = RESOURCE_COLOURS[clampi(k["reward_type"], 0, 4)]
		draw_circle(k["pos"] * S, 12.0, tc, true, -1.0, true)
	for l in labels:
		var lc: Color = [Color(0.4, 1, 0.4), Color(1, 0.6, 0.2), Color(0.8, 0.5, 1)][l["kind"]]
		lc.a = l["alpha"] / 255.0
		_text(l["pos"], "%d" % l["number"], int(28 * maxf(l["scale"], 0.5)), lc)
	if st["attack_phase"] != 0 and st["incoming_damage"] > 0:
		_box(Rect2(0.25, BOARD_TOP + 0.44, 0.5, 0.12), Color(0.5, 0.05, 0.08, 0.85))
		_text(Vector2(0.5, BOARD_TOP + 0.5), "敌人攻击 %d" % st["incoming_damage"], 30)
	_draw_skills()
	if st["menu_open"]:
		_draw_menu()
	if screen == Screen.OVER:
		_draw_over()

func _draw_top() -> void:
	_text(Vector2(0.02, 0.02), "第 %d 回合 · 等级 %d · 击杀 %d · 剑伤 %d · 骷髅伤 %d" % [st["turn"], st["level"], st["kills"], st["weapon_damage"], st["base_damage"]], 18, Color(0.8, 0.8, 0.85), true)
	var values := [[st["health"], st["health_max"]], [st["xp"], 100], [st["gold"], 100], [st["armour"], st["armour_max"]], [st["up"], 100]]
	for i in 5:
		var r := Rect2(0.1 + 0.2 * i - 0.09, 0.05, 0.18, 0.17)
		_box(r, Color(0.16, 0.15, 0.2))
		_text(Vector2(r.get_center().x, 0.075), RESOURCE_NAMES[i], 18, Color(0.8, 0.8, 0.85))
		_text(Vector2(r.get_center().x, 0.125), "%d/%d" % values[i], 24)
		var frac := clampf(float(values[i][0]) / maxf(float(values[i][1]), 1.0), 0.0, 1.0)
		_box(Rect2(r.position.x + 0.01, 0.175, r.size.x - 0.02, 0.025), Color(0.08, 0.07, 0.1), Color(0, 0, 0, 0), 0, 4)
		if frac > 0.0:
			_box(Rect2(r.position.x + 0.01, 0.175, (r.size.x - 0.02) * frac, 0.025), RESOURCE_COLOURS[i], Color(0, 0, 0, 0), 0, 4)

func _draw_tile(t: Dictionary, dim: bool) -> void:
	var c: Vector2 = t["pos"] * S
	var h := S * PITCH * 0.45
	var a := 0.28 if dim else 1.0
	var type: int = t["type"]
	var bg := Color(0.2, 0.19, 0.25, a)
	draw_style_box(_style(bg, Color(1, 0.95, 0.6) if t["selected"] else Color(0, 0, 0, 0), 4 if t["selected"] else 0, 12), Rect2(c - Vector2(h, h), Vector2(2 * h, 2 * h)))
	var col: Color = TILE_COLOURS[type] if type >= 0 and type < 5 else Color(0.4, 0.8, 0.4)
	col.a = a
	match type:
		0:
			if t["mana"]:
				col = Color(0.3, 0.4, 1.0, a)
			elif t["explosive"]:
				col = Color(1.0, 0.55, 0.1, a)
			draw_circle(c + Vector2(0, h * 0.18), h * 0.55, col, true, -1.0, true)
			draw_rect(Rect2(c.x - h * 0.16, c.y - h * 0.72, h * 0.32, h * 0.4), col)
		1:
			if t["enemy_type"] != 0:
				col = Color(0.72, 0.45, 0.9, a)
			draw_circle(c + Vector2(0, -h * 0.12), h * 0.52, col, true, -1.0, true)
			draw_rect(Rect2(c.x - h * 0.3, c.y + h * 0.2, h * 0.6, h * 0.3), col)
			var eye := Color(0.1, 0.08, 0.12, a)
			draw_circle(c + Vector2(-h * 0.2, -h * 0.15), h * 0.13, eye, true, -1.0, true)
			draw_circle(c + Vector2(h * 0.2, -h * 0.15), h * 0.13, eye, true, -1.0, true)
			_tile_number(c + Vector2(-h * 0.62, -h * 0.62), "%d" % t["attack"], Color(1, 0.35, 0.35, a))
			_tile_number(c + Vector2(h * 0.62, h * 0.66), "%d" % t["health"], Color(1, 1, 1, a))
			if t["defence"] > 0:
				_tile_number(c + Vector2(-h * 0.62, h * 0.66), "%d" % t["defence"], Color(0.5, 0.75, 1, a))
			if t["enemy_type"] != 0:
				_tile_number(c + Vector2(h * 0.62, -h * 0.62), "★", Color(1, 0.9, 0.4, a))
		2:
			draw_circle(c, h * 0.6, col, true, -1.0, true)
			draw_circle(c, h * 0.4, Color(0.75, 0.55, 0.1, a), false, 4.0, true)
		3:
			var pts := PackedVector2Array([c + Vector2(-h * 0.6, -h * 0.6), c + Vector2(h * 0.6, -h * 0.6), c + Vector2(h * 0.55, h * 0.05), c + Vector2(0, h * 0.7), c + Vector2(-h * 0.55, h * 0.05)])
			draw_colored_polygon(pts, col)
			if t["broken"]:
				draw_line(c + Vector2(-h * 0.1, -h * 0.6), c + Vector2(h * 0.1, h * 0.5), Color(0.1, 0.1, 0.1, a), 4.0, true)
		4:
			if t["magic_sword"]:
				col = Color(0.65, 0.6, 1.0, a)
			elif t["arrow"]:
				col = Color(0.55, 0.95, 0.55, a)
			if t["broken"]:
				col = col.darkened(0.4)
			draw_line(c + Vector2(-h * 0.55, h * 0.55), c + Vector2(h * 0.6, -h * 0.6), col, h * 0.2, true)
			draw_line(c + Vector2(-h * 0.5, h * 0.05), c + Vector2(-h * 0.05, h * 0.5), Color(0.6, 0.45, 0.25, a), h * 0.14, true)
		_:
			_text(t["pos"], "?", 36, col)
	if t["frozen"]:
		draw_style_box(_style(Color(0.6, 0.85, 1, 0.35 * a), Color(0, 0, 0, 0), 0, 12), Rect2(c - Vector2(h, h), Vector2(2 * h, 2 * h)))
	if t["flaming"]:
		draw_style_box(_style(Color(0, 0, 0, 0), Color(1, 0.5, 0.1, a), 4, 12), Rect2(c - Vector2(h, h), Vector2(2 * h, 2 * h)))

func _tile_number(p: Vector2, text: String, colour: Color) -> void:
	var w := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, 20).x
	draw_string(font, p + Vector2(-w / 2.0, 7), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, colour)

func _draw_skills() -> void:
	for i in 4:
		var r := _skill_rect(i)
		if i >= skills.size():
			_box(r, Color(0.13, 0.12, 0.16))
			_text(r.get_center(), "空技能栏", 18, Color(0.4, 0.4, 0.45))
			continue
		var s: Dictionary = skills[i]
		var ready: bool = s["ready"]
		var pressed: bool = st["skill_pressed"] == i
		_box(r, Color(0.45, 0.35, 0.15) if pressed else Color(0.2, 0.19, 0.27), Color(0.5, 1, 0.5) if ready else Color(0, 0, 0, 0), 3 if ready else 0)
		_text(Vector2(r.get_center().x, r.position.y + 0.05), _skill_name(s["type"]), 20)
		_text(Vector2(r.get_center().x, r.position.y + 0.11), "可以用" if ready else "冷却 %d/%d" % [s["current"], s["max"]], 18, Color(0.6, 1, 0.6) if ready else Color(0.75, 0.75, 0.8))
		var frac := clampf(float(s["current"]) / maxf(float(s["max"]), 1.0), 0.0, 1.0)
		_box(Rect2(r.position.x + 0.015, r.position.y + 0.16, (r.size.x - 0.03) * frac, 0.02), Color(0.5, 1, 0.5) if ready else Color(0.5, 0.5, 0.7), Color(0, 0, 0, 0), 0, 4)

func _draw_menu() -> void:
	_box(Rect2(0.03, 0.27, 0.94, 0.97), Color(0.1, 0.09, 0.14, 0.96), Color(0.9, 0.8, 0.5), 3, 16)
	var type: int = menu["type"]
	_text(Vector2(0.5, 0.33), ["升级！选两项", "商店：选一件装备", "装备升级：选一项"][clampi(type, 0, 2)], 32, Color(0.96, 0.8, 0.35))
	var rects := _menu_rects()
	for k in rects:
		if k == 7:
			continue
		var i: int = k - 14
		var chosen: bool = menu["first"] == k or menu["second"] == k
		var r: Rect2 = rects[k]
		_box(r, Color(0.35, 0.28, 0.15) if chosen else Color(0.2, 0.19, 0.27), Color(1, 0.85, 0.4) if chosen else Color(0, 0, 0, 0), 3 if chosen else 0)
		var lines := _option_lines(i)
		_text(Vector2(r.position.x + 0.03, r.position.y + 0.045), lines[0], 24, Color.WHITE, true)
		for j in range(1, lines.size()):
			_text(Vector2(r.position.x + 0.03, r.position.y + 0.045 + 0.045 * j), lines[j], 18, Color(0.8, 0.8, 0.85), true)
	var ready: bool = menu["confirm_ready"]
	_box(rects[7], Color(0.3, 0.55, 0.3) if ready else Color(0.2, 0.2, 0.22))
	_text(rects[7].get_center(), "确定", 26, Color.WHITE if ready else Color(0.5, 0.5, 0.5))

func _draw_over() -> void:
	_box(Rect2(0.08, 0.45, 0.84, 0.72), Color(0.1, 0.09, 0.14, 0.95), Color(0.9, 0.8, 0.5), 3, 16)
	_text(Vector2(0.5, 0.55), "胜利！" if st["victory"] else "游戏结束", 44, Color(0.96, 0.8, 0.35))
	_text(Vector2(0.5, 0.7), "等级 %d · 坚持到第 %d 回合 · 击杀 %d" % [st["level"], st["turn"], st["kills"]], 24)
	_text(Vector2(0.5, 0.78), "累计经验 %d · 累计金币 %d" % [st["total_xp"] + st["xp"], st["total_gold"] + st["gold"]], 22, Color(0.8, 0.8, 0.85))
	_text(Vector2(0.5, 0.88), "（原版的计分画面还在恢复中，这里先简化）", 18, Color(0.6, 0.6, 0.65))
