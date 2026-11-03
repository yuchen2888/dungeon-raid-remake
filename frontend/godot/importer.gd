extends Control
# The shell app's first screen (T081): the shell carries none of the original's content, so before the first game the
# player gives it their own copy of the original (Dungeon Raid 1.3.4, an unencrypted IPA). From it this rebuilds, on
# the phone, every original file the game reads, as frontend/tools/import_original_assets.py does on a Mac:
# - user://original/: the pictures (decoded from the IPA's CgBI PNGs by the library, DungeonRaidSession.decode_ios_png),
#   the fonts' .fnt files, the sounds (each .caf's 16-bit samples into a .wav), texts.txt (each English text read from
#   the original program where assets/shell/texts.map says it is) and sounds.json;
# - user://lang/<code>/tiles.png, menus.png: each language's pictures, its patch (assets/shell/patch/) added to the
#   original's.
# Every file taken from the IPA is checked against assets/shell/manifest.json (size and SHA-256) first, so another
# version of the game is refused instead of misread. frontend/tools/make_shell_data.py makes assets/shell/.
#
# Getting the IPA in: the app's folder shows in the Files app (export option user_data/accessible_from_files_app), and
# an .ipa put there is found by itself; where the platform has a file picker, "Choose file" opens it too.

signal imported

const SHELL := "res://assets/shell/"
const OUT := "user://original/"

var session = null
var status: Label = null
var buttons: Array = []
var chinese := OS.get_locale_language() == "zh"
var busy := false

func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	session = ClassDB.instantiate("DungeonRaidSession")
	var font := SystemFont.new()
	font.font_names = PackedStringArray(["PingFang SC", "Hiragino Sans", "Apple SD Gothic Neo", "Helvetica Neue", "sans-serif"])
	var theme_ := Theme.new()
	theme_.default_font = font
	theme_.default_font_size = 30
	theme = theme_
	var bg := ColorRect.new()
	bg.color = Color(0.10, 0.08, 0.19)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var box := VBoxContainer.new()
	box.set_anchors_preset(Control.PRESET_FULL_RECT)
	box.offset_left = 48
	box.offset_right = -48
	box.offset_top = 120
	box.offset_bottom = -80
	box.add_theme_constant_override("separation", 28)
	add_child(box)
	var title := Label.new()
	title.text = "Dungeon Raid"
	title.add_theme_font_size_override("font_size", 56)
	title.add_theme_color_override("font_color", Color(1.0, 0.82, 0.35))
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(title)
	var text := Label.new()
	text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	text.text = _words("intro")
	box.add_child(text)
	var go := _button(_words("import"), _import_found)
	box.add_child(go)
	if DisplayServer.has_feature(DisplayServer.FEATURE_NATIVE_DIALOG_FILE):
		box.add_child(_button(_words("choose"), _choose))
	status = Label.new()
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status.add_theme_color_override("font_color", Color(0.75, 0.85, 1.0))
	box.add_child(status)
	var legal := Label.new()
	legal.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	legal.add_theme_font_size_override("font_size", 20)
	legal.add_theme_color_override("font_color", Color(0.6, 0.6, 0.7))
	legal.text = _words("legal")
	box.add_child(legal)

func _button(label: String, action: Callable) -> Button:
	var b := Button.new()
	b.text = label
	b.custom_minimum_size = Vector2(0, 88)
	b.pressed.connect(action)
	buttons.append(b)
	return b

func _words(key: String) -> String:
	var zh := {
		"intro": "这是 Dungeon Raid 的非官方重制版，不带原版游戏的任何内容。第一次玩之前，需要你自己的原版 Dungeon Raid 1.3.4（未加密的 IPA 文件）。\n\n打开“文件”App →“我的 iPhone”→“Dungeon Raid”，把 IPA 放进去，再点下面的“导入”。",
		"import": "导入", "choose": "选择文件…",
		"none": "没找到 IPA：请把它放进“文件”App 里的“我的 iPhone → Dungeon Raid”文件夹。",
		"reading": "正在读取 %s…", "wrong": "这个 IPA 不是 Dungeon Raid 1.3.4 的未加密原版（%s 不符），没有导入。",
		"done": "导入完成！", "bad_zip": "打不开这个文件：它不是 IPA。",
		"legal": "Dungeon Raid 属于 Firemint / EA。本重制版与其无关，只读取你自己的那份原版，不会上传任何东西。"}
	var en := {
		"intro": "This is an unofficial remake of Dungeon Raid, and it holds none of the original game's content. Before the first game it needs your own copy of the original Dungeon Raid 1.3.4 (an unencrypted IPA file).\n\nOpen the Files app → On My iPhone → Dungeon Raid, put the IPA there, then tap Import.",
		"import": "Import", "choose": "Choose file…",
		"none": "No IPA found: put it in the Files app, On My iPhone → Dungeon Raid.",
		"reading": "Reading %s…", "wrong": "This IPA is not the unencrypted original Dungeon Raid 1.3.4 (%s does not match); nothing was imported.",
		"done": "Imported!", "bad_zip": "This file cannot be opened: it is not an IPA.",
		"legal": "Dungeon Raid belongs to Firemint / EA. This remake has nothing to do with them; it only reads your own copy of the original and uploads nothing."}
	return (zh if chinese else en)[key]

func _say(text: String) -> void:
	status.text = text

func _import_found() -> void:
	var found := ""
	for f in DirAccess.get_files_at("user://"):
		if f.to_lower().ends_with(".ipa"):
			found = "user://" + f
			break
	if found == "":
		_say(_words("none"))
		return
	_run(found)

func _choose() -> void:
	DisplayServer.file_dialog_show("Dungeon Raid", "", "", false, DisplayServer.FILE_DIALOG_MODE_OPEN_FILE,
		PackedStringArray(["*.ipa"]), func(ok: bool, paths: PackedStringArray, _filter: int) -> void:
			if ok and paths.size() > 0:
				_run(paths[0]))

func _run(path: String) -> void:
	if busy:
		return
	busy = true
	for b in buttons:
		b.disabled = true
	var error := await import_ipa(path)
	busy = false
	for b in buttons:
		b.disabled = false
	if error != "":
		_say(error)
		return
	_say(_words("done"))
	imported.emit()

# The import itself; "" when it worked, else what went wrong (in the player's words). Nothing is written to
# user://original/ until every file has been checked.
func import_ipa(path: String) -> String:
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(SHELL + "manifest.json"))
	var files: Dictionary = manifest["files"]
	var zip := ZIPReader.new()
	if zip.open(path) != OK:
		return _words("bad_zip")
	var entries := {}   # name in the app's folder -> its path in the IPA
	for e in zip.get_files():
		var parts := e.split("/")
		if parts.size() == 3 and parts[0] == "Payload" and parts[1].ends_with(".app") and parts[2] != "":
			entries[parts[2]] = e
	var got := {}
	for name: String in files:
		if name == "program":
			continue
		_say(_words("reading") % name)
		await get_tree().process_frame
		if not entries.has(name):
			return _words("wrong") % name
		var bytes := zip.read_file(entries[name])
		if not _matches(bytes, files[name]):
			return _words("wrong") % name
		got[name] = bytes
	_say(_words("reading") % "DungeonRaid")
	await get_tree().process_frame
	var program := PackedByteArray()
	for name: String in entries:   # the program: the file of the app's folder that is it (its name varies)
		if name.get_extension() in ["png", "caf", "nib", "plist", "fnt", "strings", "car", "mobileprovision"]:
			continue
		var bytes := zip.read_file(entries[name])
		if _matches(bytes, files["program"]):
			program = bytes
			break
	zip.close()
	if program.is_empty():
		return _words("wrong") % "DungeonRaid"
	# all there: write the files
	DirAccess.make_dir_recursive_absolute(OUT + "sounds")
	for name: String in got:
		var bytes: PackedByteArray = got[name]
		if name.ends_with(".png"):
			var p: Dictionary = session.decode_ios_png(bytes)
			if p.is_empty():
				return _words("wrong") % name
			Image.create_from_data(p["width"], p["height"], false, Image.FORMAT_RGBA8, p["rgba"]).save_png(OUT + name)
		elif name.ends_with(".caf"):
			_save(OUT + "sounds/" + name.get_basename() + ".wav", _wav(bytes))
		else:
			_save(OUT + name, bytes)
		await get_tree().process_frame
	_save(OUT + "texts.txt", _texts(program).to_utf8_buffer())
	_save(OUT + "sounds.json", FileAccess.get_file_as_bytes(SHELL + "sounds.json"))
	for code in DirAccess.get_directories_at(SHELL + "patch"):
		DirAccess.make_dir_recursive_absolute("user://lang/" + code)
		for name in DirAccess.get_files_at(SHELL + "patch/" + code):
			if not name.ends_with(".png"):
				continue
			var base := Image.load_from_file(OUT + name)
			var patch := Image.new()
			patch.load_png_from_buffer(FileAccess.get_file_as_bytes(SHELL + "patch/" + code + "/" + name))
			base.convert(Image.FORMAT_RGBA8)
			patch.convert(Image.FORMAT_RGBA8)
			var data: PackedByteArray = session.add_patch(base.get_data(), patch.get_data())
			if data.is_empty():
				return _words("wrong") % (code + "/" + name)
			Image.create_from_data(base.get_width(), base.get_height(), false, Image.FORMAT_RGBA8, data).save_png(
				"user://lang/" + code + "/" + name)
			await get_tree().process_frame
	_save(OUT + "imported.txt", ("Dungeon Raid %s, %s\n" % [manifest["version"], Time.get_datetime_string_from_system()]).to_utf8_buffer())
	return ""

func _matches(bytes: PackedByteArray, want: Dictionary) -> bool:
	if bytes.size() != int(want["size"]):
		return false
	var h := HashingContext.new()
	h.start(HashingContext.HASH_SHA256)
	h.update(bytes)
	return h.finish().hex_encode() == want["sha256"]

func _save(path: String, bytes: PackedByteArray) -> void:
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f != null:
		f.store_buffer(bytes)
		f.close()

# A .caf's samples (16-bit linear PCM, as all the original's are) as a .wav file.
func _wav(caf: PackedByteArray) -> PackedByteArray:
	var rate := 44100
	var channels := 1
	var little := false
	var samples := PackedByteArray()
	var i := 8
	while i + 12 <= caf.size():
		var type := caf.slice(i, i + 4).get_string_from_ascii()
		var n := 0
		for k in 8:
			n = (n << 8) | caf[i + 4 + k]
		var body := i + 12
		if type == "desc":
			var d := caf.slice(body, body + 32)
			d.reverse()   # (big-endian fields: read them back to front)
			rate = int(d.decode_double(24))
			little = (d.decode_u32(16) & 2) != 0   # kCAFLinearPCMFormatFlagIsLittleEndian
			channels = d.decode_u32(4)
		elif type == "data":
			samples = caf.slice(body + 4, caf.size() if n < 0 else body + n)   # (after the edit count)
		i = body + n
		if n < 0:
			break
	if not little:   # (WAV is little-endian)
		for k in range(0, samples.size() - 1, 2):
			var t := samples[k]
			samples[k] = samples[k + 1]
			samples[k + 1] = t
	var out := PackedByteArray()
	out.resize(44)
	out.encode_u32(0, 0x46464952)   # "RIFF"
	out.encode_u32(4, 36 + samples.size())
	out.encode_u32(8, 0x45564157)   # "WAVE"
	out.encode_u32(12, 0x20746d66)  # "fmt "
	out.encode_u32(16, 16)
	out.encode_u16(20, 1)
	out.encode_u16(22, channels)
	out.encode_u32(24, rate)
	out.encode_u32(28, rate * channels * 2)
	out.encode_u16(32, channels * 2)
	out.encode_u16(34, 16)
	out.encode_u32(36, 0x61746164)  # "data"
	out.encode_u32(40, samples.size())
	out.append_array(samples)
	return out

# texts.txt as import_original_assets.py writes it, each text from the program's bytes at texts.map's pieces.
func _texts(program: PackedByteArray) -> String:
	var out := "# The original game's texts (rebuilt on this device from your copy; frontend/godot/importer.gd)\n"
	for line in FileAccess.get_file_as_string(SHELL + "texts.map").split("\n", false):
		var parts := line.split("\t")
		var value := PackedByteArray()
		for piece in parts[1].split(","):
			var p := piece.split(":")
			value.append_array(program.slice(int(p[0]), int(p[0]) + int(p[1])))
		var text := ""
		for b in value:   # (Latin-1, a character a byte)
			text += char(b)
		out += parts[0] + "\t" + text.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t") + "\n"
	return out
