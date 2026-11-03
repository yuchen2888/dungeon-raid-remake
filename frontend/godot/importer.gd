extends Control
# The shell app's first screen (T081): the shell carries none of the original's content, so before the first game the
# player gives it their own copy of the original (Dungeon Raid 1.3.4, an unencrypted IPA). From it this rebuilds, on
# the phone, every original file the game reads, as frontend/tools/import_original_assets.py does on a Mac:
# - user://original/: the pictures (decoded from the IPA's CgBI PNGs by the library, DungeonRaidSession.decode_ios_png),
#   the fonts' .fnt files, the sounds (each .caf's 16-bit samples into a .wav), texts.txt (each English text read from
#   the original program where assets/shell/texts.map says it is) and sounds.json;
# - user://lang/<code>/tiles.png, menus.png: each language's pictures, its patch (assets/shell/patch/) added to the
#   original's.
# Every file taken from the IPA is checked against assets/shell/manifest.json (size and SHA-256; for the program, the
# bytes of its texts) first, so another version of the game is refused instead of misread. frontend/tools/make_shell_data.py makes assets/shell/.
#
# Getting the IPA in: the app's folder shows in the Files app (export option user_data/accessible_from_files_app), and
# an .ipa put there is found by itself; where the platform has a file picker, "Choose file" opens it too.

signal imported

const SHELL := "res://assets/shell/"
const OUT := "user://original/"

var session = null
var status: TextureRect = null
var buttons: Array = []
var lang := "zh" if OS.get_locale_language() == "zh" else "en"
var busy := false

# The screen's words are pictures (shell/text/<key>.<zh|en>.png, frontend/tools/make_shell_art.py): a phone's own
# fonts cannot be counted on, and the game's are the original's, not here yet.
func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	session = ClassDB.instantiate("DungeonRaidSession")
	var bg := ColorRect.new()
	bg.color = Color(0.11, 0.07, 0.19)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var box := VBoxContainer.new()
	box.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	box.offset_left = 48
	box.offset_right = -48
	box.offset_top = 100
	box.offset_bottom = -60
	box.add_theme_constant_override("separation", 30)
	add_child(box)
	var icon := TextureRect.new()
	icon.texture = _picture("res://shell/icon.png")
	icon.custom_minimum_size = Vector2(0, 180)
	icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	box.add_child(icon)
	box.add_child(_words("intro"))
	box.add_child(_button("import", _import_found))
	if DisplayServer.has_feature(DisplayServer.FEATURE_NATIVE_DIALOG_FILE):
		box.add_child(_button("choose", _choose))
	status = _words("none")
	status.modulate = Color(0.75, 0.85, 1.0)
	status.visible = false
	box.add_child(status)
	var legal := _words("legal")
	legal.modulate = Color(0.6, 0.6, 0.72)
	box.add_child(legal)

func _picture(path: String) -> Texture2D:
	var image := Image.new()
	if image.load_png_from_buffer(FileAccess.get_file_as_bytes(path)) != OK:
		return null
	return ImageTexture.create_from_image(image)

# A text picture as wide as the screen's column (its height following).
func _words(key: String) -> TextureRect:
	var r := TextureRect.new()
	r.texture = _picture("res://shell/text/%s.%s.png" % [key, lang])
	r.expand_mode = TextureRect.EXPAND_FIT_HEIGHT_PROPORTIONAL
	r.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT
	r.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return r

func _button(key: String, action: Callable) -> Button:
	var b := Button.new()
	var words := _picture("res://shell/text/%s.%s.png" % [key, lang])
	var label := TextureRect.new()
	label.texture = words
	label.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	label.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	label.offset_top = 22
	label.offset_bottom = -22
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	b.add_child(label)
	b.custom_minimum_size = Vector2(0, 96)
	b.pressed.connect(action)
	buttons.append(b)
	return b

func _say(key: String) -> void:
	status.texture = _picture("res://shell/text/%s.%s.png" % [key, lang])
	status.visible = true

func _import_found() -> void:
	var found := ""
	for f in DirAccess.get_files_at("user://"):
		if f.to_lower().ends_with(".ipa"):
			found = "user://" + f
			break
	if found == "":
		_say("none")
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
	_say("done")
	imported.emit()

# The import itself; "" when it worked, else what went wrong (a key of the screen's words). Nothing is written to
# user://original/ until every file has been checked.
func import_ipa(path: String) -> String:
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(SHELL + "manifest.json"))
	var files: Dictionary = manifest["files"]
	var zip := ZIPReader.new()
	if zip.open(path) != OK:
		return "bad_zip"
	var entries := {}   # name in the app's folder -> its path in the IPA
	for e in zip.get_files():
		var parts := e.split("/")
		if parts.size() == 3 and parts[0] == "Payload" and parts[1].ends_with(".app") and parts[2] != "":
			entries[parts[2]] = e
	var got := {}
	for name: String in files:
		_say("reading")
		await _breathe()
		if not entries.has(name):
			return "wrong"
		var bytes := zip.read_file(entries[name])
		if not _matches(bytes, files[name]):
			return "wrong"
		got[name] = bytes
	await _breathe()
	# The program: the file of the app's folder (its name varies) whose armv7 code holds the texts the game reads. Only
	# those bytes are checked (T082): copies decrypted by different tools differ elsewhere, some keep only armv7.
	var program := PackedByteArray()
	var encrypted := false
	for name: String in entries:
		if name.get_extension() in ["png", "caf", "nib", "plist", "fnt", "strings", "car", "mobileprovision"]:
			continue
		var code := _armv7(zip.read_file(entries[name]))
		if code.is_empty():
			continue
		if _sha256(_text_bytes(code)) == manifest["program"]["texts_sha256"]:
			program = code
			break
		encrypted = encrypted or _encrypted(code)
	zip.close()
	if program.is_empty():
		return "encrypted" if encrypted else "wrong"
	# all there: write the files
	DirAccess.make_dir_recursive_absolute(OUT + "sounds")
	for name: String in got:
		var bytes: PackedByteArray = got[name]
		if name.ends_with(".png"):
			var p: Dictionary = session.decode_ios_png(bytes)
			if p.is_empty():
				return "wrong"
			Image.create_from_data(p["width"], p["height"], false, Image.FORMAT_RGBA8, p["rgba"]).save_png(OUT + name)
		elif name.ends_with(".caf"):
			_save(OUT + "sounds/" + name.get_basename() + ".wav", _wav(bytes))
		else:
			_save(OUT + name, bytes)
		await _breathe()
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
				return "wrong"
			Image.create_from_data(base.get_width(), base.get_height(), false, Image.FORMAT_RGBA8, data).save_png(
				"user://lang/" + code + "/" + name)
			await _breathe()
	_save(OUT + "imported.txt", ("Dungeon Raid %s, %s\n" % [manifest["version"], Time.get_datetime_string_from_system()]).to_utf8_buffer())
	return ""

# A frame now and then, so the screen keeps showing it is busy (one after every file would be slow where frames are,
# as in the simulator).
var _last_frame := 0
func _breathe() -> void:
	if Time.get_ticks_msec() - _last_frame > 250:
		await get_tree().process_frame
		_last_frame = Time.get_ticks_msec()

func _matches(bytes: PackedByteArray, want: Dictionary) -> bool:
	return bytes.size() == int(want["size"]) and _sha256(bytes) == want["sha256"]

func _sha256(bytes: PackedByteArray) -> String:
	var h := HashingContext.new()
	h.start(HashingContext.HASH_SHA256)
	h.update(bytes)
	return h.finish().hex_encode()

func _be32(bytes: PackedByteArray, at: int) -> int:
	return (bytes[at] << 24) | (bytes[at + 1] << 16) | (bytes[at + 2] << 8) | bytes[at + 3]

# A Mach-O file's armv7 code (CPU 12, subtype 9): its slice of a universal file, or the file itself when that is all
# it has; empty when it has none.
func _armv7(bytes: PackedByteArray) -> PackedByteArray:
	if bytes.size() < 28:
		return PackedByteArray()
	if _be32(bytes, 0) == 0xcafebabe:
		for i in _be32(bytes, 4):
			var at := 8 + 20 * i
			if at + 20 <= bytes.size() and _be32(bytes, at) == 12 and _be32(bytes, at + 4) == 9:
				var offset := _be32(bytes, at + 8)
				return bytes.slice(offset, offset + _be32(bytes, at + 12))
	elif bytes.decode_u32(0) == 0xfeedface and bytes.decode_u32(4) == 12 and bytes.decode_u32(8) == 9:
		return bytes
	return PackedByteArray()

# Whether App Store encryption is still on (LC_ENCRYPTION_INFO's cryptid): such a copy's texts cannot be read.
func _encrypted(code: PackedByteArray) -> bool:
	var at := 28
	for i in code.decode_u32(16):
		if at + 20 > code.size():
			break
		if code.decode_u32(at) == 0x21:
			return code.decode_u32(at + 16) != 0
		at += code.decode_u32(at + 4)
	return false

# The bytes of every text texts.map gives, each followed by a 0 (make_shell_data.py hashes the same).
func _text_bytes(code: PackedByteArray) -> PackedByteArray:
	var out := PackedByteArray()
	for line in FileAccess.get_file_as_string(SHELL + "texts.map").split("\n", false):
		for piece in line.split("\t")[1].split(","):
			var p := piece.split(":")
			out.append_array(code.slice(int(p[0]), int(p[0]) + int(p[1])))
		out.append(0)
	return out

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
