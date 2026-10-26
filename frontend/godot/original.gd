extends Node2D
# Dungeon Raid as the original draws it (T050-A, second stage). The rules run in the native library
# (frontend/gdext); the original game's drawing, recovered there (frontend/gdext/src/ui), turns each frame into a
# draw list, and this script only paints that list with the original textures, passes the mouse on as touches and
# stores the session's bytes under user://. The textures are loaded as the original loads them (ES1Renderer
# loadTexture: premultiplied alpha, linear filtering, clamped) and drawn with its blending (source alpha, one minus
# source alpha); on today's screens they are replaced by HD pictures where assets/hd/ has them (T050-C,
# _texture_path) and sampled sharper where still enlarged more than twice (sharp.gdshader). It starts on the original
# main menu (its buttons are the session's: Continue, New game, Challenge, Tutorial, the sound switch), then the
# original setup screen (name, difficulty, class, the class screen behind Edit, the challenge's mode screen) and the story; after a game's end the original game-over tally and the high scores
# (their Back returns to the main menu, whose High scores button opens them too). The original sounds play as the
# original queues them (each frame's Game::QueueSound calls in order, the recording drawn as GetSoundMapping does).
#
# Checks: "-- --autoplay" plays the rules' own hint paths (and the menus: the first option(s), confirm; the setup
# screen: Random, Begin; the story: Begin; "--challenge": challenge games);
# "--shot=<file.png>" saves the window after 300 frames ("--shot-frame=<n>": after n), "--menu-shot=<file.png>"
# when the first menu has opened, "--over-shot=<file.png>" 20 seconds into the first game-over tally,
# "--scores-shot=<file.png>" 2 seconds into the high scores after it (autoplay waits there 200 frames before Back);
# "--taps=<frame>:<x>:<y>,..." touches the screen (x, y in screen units, 1 wide and 1.5 high) for two frames at those
# frames; "--shots=<folder>:<n>" saves the window every n frames into the folder (frame number named; T050-D's look
# checks); "--lang=<code>" plays in that language (the saved choice untouched).

const SCALE := 640.0   # the original's screen is 1 wide, 1.5 high; the viewport is 640 x 960
const STORE_KEYS := ["classes", "scores0", "scores1", "scores2", "scores3", "scores4", "scores5", "game", "spawn", "settings"]
const TEXTURES := {1: "tiles", 2: "font", 3: "icons", 4: "menus", 5: "fontMenu", 6: "fontScore"}   # GetTextureName
const RAW_FILES := ["tiles.png", "font.png", "icons.png", "menus.png", "fontMenu.png", "fontScore.png", "font.fnt",
		"fontMenu.fnt", "fontScore.fnt", "texts.txt", "sounds.json"]   # see _asset_folder
# T050-D: a language other than English is a folder assets/lang/<code> (frontend/tools/make_cjk_font.py,
# localise_atlas.py): its texts over the original's, the fonts' wide glyphs (textures 7..9) and, where present, the
# pictures with the original's English words redrawn (tiles, menus). The choice is kept in user://frontend.cfg.
const LANGUAGES := ["en", "zh"]
const LANG_FILES := ["texts.txt", "font.fnt", "font.png", "fontMenu.fnt", "fontMenu.png", "fontScore.fnt", "fontScore.png",
		"tiles.png", "menus.png"]
const WIDE_TEXTURES := {7: "font", 8: "fontMenu", 9: "fontScore"}
const LOCALISED := [1, 4]   # tiles, menus
const SETTINGS_FILE := "user://frontend.cfg"
var language := "en"

var session = null
var textures := {}
var batches: Array = []
var error_text := ""
var store_dir := "user://"
# The pointer: queued touch phases for the session's frames (1 down / held, 2 up), whether it is held, where it is.
var queue: Array = []
var held := false
var cursor := Vector2(0.5, 1.45)
var autoplay := false
var challenge := false   # "--challenge": autoplay starts challenge games (the main menu's Challenge, the box's Yes)
var auto_steps: Array = []
var shot := ""
var shot_frame := 300   # "--shot-frame=<n>"
var menu_shot := ""   # "--menu-shot=<file.png>": the window 45 frames after the first menu opened
var menu_frames := 0
var over_shot := ""     # "--over-shot=<file.png>"
var scores_shot := ""   # "--scores-shot=<file.png>"
var shots_dir := ""     # "--shots=<folder>:<n>"
var shots_every := 0
var edge_fill: ColorRect = null   # the strips beside the game on a taller or wider screen (see _layout)
var over_frames := 0    # frames the game-over tally / the high scores after it have been open
var scores_frames := 0
var frames := 0
var ticks := 0
var taps := {}   # "--taps": frame -> touch position
# The original's sounds (assets/original/sounds.json: name, recordings, volume), played as its SoundEngine does: each
# queued sound of a frame, the recording the session drew, several at once.
var sound_table: Array = []
var sound_streams := {}   # "name1" .. -> AudioStream
var players: Array = []
var next_player := 0

func _ready() -> void:
	RenderingServer.set_default_clear_color(Color.BLACK)   # Game::Render clears to black
	edge_fill = ColorRect.new()
	edge_fill.top_level = true
	edge_fill.mouse_filter = Control.MOUSE_FILTER_IGNORE
	edge_fill.material = ShaderMaterial.new()
	edge_fill.material.shader = preload("res://edge_fill.gdshader")
	add_child(edge_fill)
	get_viewport().size_changed.connect(_layout)
	_layout()
	get_window().title = "Dungeon Raid"   # (the project's name keeps the earlier saves' folder)
	var args := OS.get_cmdline_user_args()
	autoplay = args.has("--autoplay")
	challenge = args.has("--challenge")
	for a in args:
		if a.begins_with("--shot="):
			shot = a.substr(7)
			get_window().always_on_top = true   # macOS stops drawing a covered window
		elif a.begins_with("--shot-frame="):
			shot_frame = int(a.substr(13))
		elif a.begins_with("--menu-shot="):
			menu_shot = a.substr(12)
			get_window().always_on_top = true
		elif a.begins_with("--over-shot="):
			over_shot = a.substr(12)
			get_window().always_on_top = true
		elif a.begins_with("--shots="):
			var p := a.substr(8).rsplit(":", true, 1)
			shots_dir = p[0]
			shots_every = int(p[1]) if p.size() > 1 else 300
		elif a.begins_with("--scores-shot="):
			scores_shot = a.substr(14)
			get_window().always_on_top = true
		elif a.begins_with("--taps="):
			for t in a.substr(7).split(","):
				var p := t.split(":")
				if p.size() == 3:
					taps[int(p[0])] = Vector2(float(p[1]), float(p[2]))
	if autoplay or not taps.is_empty():   # its own save folder, so the player's saved game stays untouched
		store_dir = "user://autoplay/"
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(store_dir))
	if not ClassDB.class_exists("DungeonRaidSession"):
		error_text = "The game library did not load (frontend/godot/bin/).\nRun frontend/gdext/build.py extension."
		return
	var assets := _asset_folder()
	language = _language(args)
	var lang_dir := ""
	if language != "en":
		lang_dir = _plain_folder("res://assets/lang/" + language, "user://lang/" + language, LANG_FILES)
		if not FileAccess.file_exists(lang_dir + "/texts.txt"):
			lang_dir = ""   # (its files are not on this machine: English)
	var pictures := lang_dir   # (English has a folder of pictures only: the settings button)
	if language == "en":
		pictures = _plain_folder("res://assets/lang/en", "user://lang/en", ["tiles.png", "menus.png"])
	for id in TEXTURES:
		var name: String = TEXTURES[id]
		var path: String = assets + "/" + name + ".png"
		var hd := name   # (its HD replacement's name, see _texture_path)
		if pictures != "" and id in LOCALISED and FileAccess.file_exists(pictures + "/" + name + ".png"):
			path = pictures + "/" + name + ".png"
			hd = "lang/" + language + "/" + name
		if not _load_texture(id, path, hd):
			error_text = "The original pictures are missing (frontend/godot/assets/original).\nRun frontend/tools/import_original_assets.py."
			return
	if lang_dir != "":
		for id in WIDE_TEXTURES:
			_load_texture(id, lang_dir + "/" + WIDE_TEXTURES[id] + ".png", "lang/" + language + "/" + WIDE_TEXTURES[id])
	var names := _plain_folder("res://assets/lang", "user://lang", ["names.png"])   # (the settings page's)
	_load_texture(10, names + "/names.png", "lang/names")
	texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	if not args.has("--no-hd"):   # (the plain pictures, plainly drawn)
		material = ShaderMaterial.new()
		material.shader = preload("res://sharp.gdshader")
	var table := FileAccess.get_file_as_string(assets + "/sounds.json")
	if table != "":
		sound_table = JSON.parse_string(table)
	for i in 16:
		var player := AudioStreamPlayer.new()
		add_child(player)
		players.append(player)
	session = ClassDB.instantiate("DungeonRaidSession")
	if not session.load_presentation(assets, lang_dir):
		error_text = "The original fonts are missing (frontend/godot/assets/original)."
		return
	for key in STORE_KEYS:
		var file: String = store_dir + key + ".bin"
		if FileAccess.file_exists(file):
			session.restore(key, FileAccess.get_file_as_bytes(file))

# The game in the middle of the screen (project.godot's stretch aspect "expand": a screen taller than the game's 2:3,
# as an iPhone's, makes the view taller, a wider one wider), and the strips beside it filled from its edges
# (edge_fill.gdshader) instead of black bars. Input follows the node's position (make_input_local).
func _layout() -> void:
	var view := get_viewport().get_visible_rect().size
	var game := Vector2(SCALE, SCALE * 1.5)
	position = ((view - game) * 0.5).max(Vector2.ZERO).floor()
	edge_fill.visible = view.x > game.x + 1.0 or view.y > game.y + 1.0
	edge_fill.position = Vector2.ZERO
	edge_fill.size = view
	var r := Vector4(position.x / view.x, position.y / view.y, (position.x + game.x) / view.x, (position.y + game.y) / view.y)
	(edge_fill.material as ShaderMaterial).set_shader_parameter("game", r)

# A picture's file, or its HD replacement (T050-C) when res://assets/hd/<name>.png exists: the same atlas at a whole
# multiple of the original's size (the drawing's UVs and the fonts' .fnt files are relative to the texture, so nothing
# else changes). <name> is the picture's GetTextureName, or for a language's own pictures lang/<code>/<name> (and
# lang/names). Like the originals the HD pictures stay local only and are exported as plain files.
func _texture_path(original: String, name: String) -> String:
	var hd := "res://assets/hd/" + name + ".png"
	if not FileAccess.file_exists(hd) or OS.get_cmdline_user_args().has("--no-hd"):   # ("--no-hd": quicker in the simulator)
		return original
	var o := _png_size(original)
	var s := _png_size(hd)
	if o.x > 0 and o.y > 0 and s.x % o.x == 0 and s.y % o.y == 0 and s.x / o.x == s.y / o.y:
		return hd
	push_warning("%s is not a whole multiple of the original %dx%d; the original is used" % [hd, o.x, o.y])
	return original

# A PNG's width and height from its header (IHDR), without decoding it; (0, 0) when it cannot be read.
func _png_size(path: String) -> Vector2i:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null or f.get_length() < 24:
		return Vector2i.ZERO
	f.big_endian = true
	f.seek(16)
	return Vector2i(f.get_32(), f.get_32())

# A picture read from its bytes (a res:// file inside the exported package as well as a plain file); null if unreadable.
func _load_picture(path: String) -> Image:
	var image := Image.new()
	return image if image.load_png_from_buffer(FileAccess.get_file_as_bytes(path)) == OK else null

# The original files the game reads as plain files (the pictures, and the fonts and texts the library opens itself):
# the project's own folder when it is one on disk (the editor, the Mac app); in an exported game (iOS) they sit inside
# the package, so they are copied out once into user://original/ (they are exported as is, importer "keep").
func _asset_folder() -> String:
	return _plain_folder("res://assets/original", "user://original", RAW_FILES)

# A folder of plain files: on disk as it is, or (an exported game) copied out of the package into user_dir.
func _plain_folder(res_dir: String, user_dir: String, files: Array) -> String:
	var folder := ProjectSettings.globalize_path(res_dir)
	if FileAccess.file_exists(folder + "/" + files[0]) and not OS.has_feature("template"):
		return folder
	var copy := ProjectSettings.globalize_path(user_dir)
	DirAccess.make_dir_recursive_absolute(copy)
	for file: String in files:
		var bytes := FileAccess.get_file_as_bytes(res_dir + "/" + file)
		if bytes.is_empty():
			continue
		var target := copy + "/" + file
		if FileAccess.file_exists(target) and FileAccess.get_file_as_bytes(target) == bytes:
			continue
		var f := FileAccess.open(target, FileAccess.WRITE)
		if f != null:
			f.store_buffer(bytes)
			f.close()
	return copy

func _load_texture(id: int, path: String, hd := "") -> bool:
	var image := _load_picture(_texture_path(path, hd) if hd != "" else path)
	if image == null:
		return false
	image.convert(Image.FORMAT_RGBA8)
	image.premultiply_alpha()
	image.generate_mipmaps()   # (an HD picture is drawn smaller than its pixels; see sharp.gdshader)
	textures[id] = ImageTexture.create_from_image(image)
	return true

# The language (T050-D): "--lang=<code>" for the checks, else the saved choice, else the device's (Chinese for a
# Chinese system, English otherwise).
func _language(args: PackedStringArray) -> String:
	for a in args:   # ("--lang=<code>": any language whose files are here, before it is in LANGUAGES)
		if a.begins_with("--lang=") and (a.substr(7) in LANGUAGES or FileAccess.file_exists("res://assets/lang/" + a.substr(7) + "/texts.txt")):
			return a.substr(7)
	var cfg := ConfigFile.new()
	if cfg.load(SETTINGS_FILE) == OK and cfg.get_value("settings", "language", "") in LANGUAGES:
		return cfg.get_value("settings", "language")
	return "zh" if OS.get_locale_language() == "zh" else "en"

func _save_language(code: String) -> void:
	var cfg := ConfigFile.new()
	cfg.load(SETTINGS_FILE)
	cfg.set_value("settings", "language", code)
	cfg.save(SETTINGS_FILE)

# The bytes the session changed, written whole to a temporary file and renamed; an empty saved game is deleted.
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

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		var p: Vector2 = make_input_local(event).position / SCALE
		cursor = p
		if event.pressed:
			queue.append([1, p])
			held = true
		elif held:
			queue.append([2, p])
			held = false
	elif event is InputEventMouseMotion:
		cursor = make_input_local(event).position / SCALE

# The game steps 60 times a second, as the original on the iPhone (EAGLView's display link: Game::Process and
# Game::Render once per screen refresh, dt the time since the last), or 30 with the game menu's high frame rate
# switch off (EAGLView drawView: setAnimationFrameInterval 2); a faster screen only shows each step longer.
func _physics_process(_delta: float) -> void:
	if session == null:
		queue_redraw()
		return
	ticks += 1
	var high: bool = session.state()["high_framerate"]
	if not high and ticks % 2 == 1:
		return
	var delta := 1.0 / 60.0 if high else 1.0 / 30.0
	frames += 1
	if autoplay:
		_autoplay()
	if taps.has(frames):
		cursor = taps[frames]
		queue.append([1, taps[frames]]); queue.append([1, taps[frames]]); queue.append([2, taps[frames]])
	var phase := 0
	var pos := cursor
	if not queue.is_empty():
		var e: Array = queue.pop_front()
		phase = e[0]
		pos = e[1]
	elif held:
		phase = 1
	if session.settings_open():   # (T050-D) the settings page over the main menu takes the touches
		var chosen: int = session.settings_touch(phase, pos)
		if chosen >= 0 and chosen < LANGUAGES.size() and LANGUAGES[chosen] != language:
			_save_language(LANGUAGES[chosen])
			get_tree().call_deferred("reload_current_scene")   # (everything is saved as it changes)
		phase = 0
	var skill_button: int = session.skill_button_at(pos) if phase != 0 else -1
	# (the main menu and the high scores act on the button under the last touch the frame after it ends)
	var menu_button: int = session.menu_button_at(pos) if not session.settings_open() and (phase != 0 or session.main_menu_open() or session.scores_open()) else -1
	session.frame(minf(delta, 0.05), phase, pos, skill_button, menu_button)
	_play_sounds()
	_store()
	batches = session.render(SCALE)
	queue_redraw()
	menu_frames = menu_frames + 1 if session.state()["menu_open"] else 0
	var over: bool = session.state()["game_over"]
	over_frames = over_frames + 1 if over else 0
	scores_frames = scores_frames + 1 if session.scores_open() and not over else 0
	var per_second := 60 if high else 30
	if over_shot != "" and over_frames == 20 * per_second:
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(over_shot)
		print("saved " + over_shot)
		over_shot = ""
	if scores_shot != "" and scores_frames == 2 * per_second:
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(scores_shot)
		print("saved " + scores_shot)
		scores_shot = ""
	if shots_dir != "" and shots_every > 0 and frames % shots_every == 0:
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png("%s/%06d.png" % [shots_dir, frames])
	if autoplay and frames % 600 == 0:
		var st: Dictionary = session.state()
		print("frame %d turn %d health %d gold %d xp %d tokens %d falling %d attack %d ready %s menu %s over %s" % [frames, st["turn"],
			st["health"], st["gold"], st["xp"], st["tokens_pending"], st["falling"], st["attack_phase"], st["input_ready"], st["menu_open"], st["game_over"]])
	if menu_shot != "" and menu_frames == 45:
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(menu_shot)
		print("saved " + menu_shot)
		menu_shot = ""
	if shot != "" and frames == shot_frame:
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(shot)
		print("saved " + shot)

func _exit_tree() -> void:
	for player in players:
		player.stop()
		player.stream = null
	sound_streams.clear()

func _play_sounds() -> void:
	for s in session.sounds():
		var sound: int = s[0]
		if sound < 0 or sound >= sound_table.size():
			continue
		var entry: Dictionary = sound_table[sound]
		var file: String = "%s%d" % [entry["name"], int(s[1]) + 1]
		if not sound_streams.has(file):
			var path := "res://assets/original/sounds/" + file + ".wav"
			sound_streams[file] = load(path) if ResourceLoader.exists(path) else null
		var stream: AudioStream = sound_streams[file]
		if stream == null:
			continue
		var player: AudioStreamPlayer = players[next_player]
		next_player = (next_player + 1) % players.size()
		player.stream = stream
		player.volume_db = linear_to_db(float(entry["volume"]))
		player.play()

func _draw() -> void:
	if error_text != "":
		draw_string(ThemeDB.fallback_font, Vector2(20, 60), error_text, HORIZONTAL_ALIGNMENT_LEFT, 600, 22)
		return
	var item := get_canvas_item()
	for b in batches:
		var texture: Texture2D = textures.get(b[0])
		RenderingServer.canvas_item_add_triangle_array(item, b[4], b[1], b[2], b[3], PackedInt32Array(), PackedFloat32Array(),
			texture.get_rid() if texture != null else RID())

# The rules' hint path, stroked tile by tile (three frames each), whenever the board waits for a stroke.
func _autoplay() -> void:
	if not auto_steps.is_empty():
		var s: Array = auto_steps.pop_front()
		cursor = s[1]   # (the main menu reads the button under the last touch after it ends)
		if s[0] == "down":
			queue.append([1, s[1]]); held = true
		elif s[0] == "up":
			queue.append([2, s[1]]); held = false
		return
	if frames % 30 != 0 or held:
		return
	if session.state()["game_over"]:   # the game-over tally counts on its own
		return
	if session.scores_open():   # the high scores after a game: Back (after a look)
		if scores_frames < 200:
			return
		var b := Vector2(0.85, 1.45)
		auto_steps.append(["down", b]); auto_steps.append(["wait", b]); auto_steps.append(["up", b])
		return
	if session.main_menu_open():   # Continue, or New game without a saved game (Challenge: over a saved game, Yes)
		var t := Vector2(0.2078125, 0.353125) if session.has_save() else Vector2(0.228125, 0.525)
		if challenge:
			t = Vector2(0.225, 0.61875)
		auto_steps.append(["down", t]); auto_steps.append(["wait", t]); auto_steps.append(["up", t])
		if challenge and session.has_save():
			var yes := Vector2(0.742, 0.647)
			for i in 20:
				auto_steps.append(["wait", yes])
			auto_steps.append(["down", yes]); auto_steps.append(["wait", yes]); auto_steps.append(["up", yes])
		return
	var setup: Dictionary = session.setup()
	if setup["open"] or setup["intro"]:   # Random, then Begin (the story's Begin at the same place)
		var t := Vector2(0.86, 0.145) if setup["open"] and not setup["named"] else Vector2(0.5, 1.41)
		auto_steps.append(["down", t]); auto_steps.append(["wait", t]); auto_steps.append(["up", t])
		return
	var st: Dictionary = session.state()
	if st.get("menu_open", false):   # the first option (and the second in the level-up menu), then confirm
		var m: Dictionary = session.menu()
		if m.get("timer", 0.0) >= 0.0 or menu_frames < 60:   # still sliding in (and a moment to look at it)
			return
		var y := func(k: int) -> float: return 0.28125 + (33 + 57 * k + 26) / 320.0
		var taps := [Vector2(0.5, y.call(0))]
		if m.get("type", 0) == 0:
			taps.append(Vector2(0.5, y.call(1)))
		taps.append(Vector2(0.071875 + 44 / 320.0, 0.28125 + 278 / 320.0))
		for t in taps:
			auto_steps.append(["down", t])
			auto_steps.append(["wait", t])
			auto_steps.append(["up", t])
			for i in 3:
				auto_steps.append(["wait", t])
		return
	if not (st["input_ready"] and st["attack_phase"] == 0 and st["falling"] == 0 and st["tokens_pending"] == 0):
		return
	var path: PackedInt32Array = session.hint()
	if path.is_empty():
		return
	var board: Array = session.board()
	for n in path.size():
		var p: Vector2 = board[path[n]]["pos"]
		auto_steps.append(["down" if n == 0 else "move", p])
		auto_steps.append(["wait", p])
		auto_steps.append(["wait", p])
	auto_steps.append(["up", board[path[path.size() - 1]]["pos"]])
