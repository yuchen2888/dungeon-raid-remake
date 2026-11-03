extends SceneTree
# The shell app's import (T081, importer.gd) checked against the Mac version's files: imports the local IPA into the
# user folder and compares every file it wrote with assets/original/ and assets/lang/ (pictures pixel for pixel,
# sounds sample for sample, texts line for line).
#
#   Godot --headless --path frontend/godot -s res://tests/import_check.gd -- --ipa=<path to the original IPA>
#   ... -- --ipa=<path> --expect=<key>      the import must refuse it with that word (e.g. encrypted, wrong)

func _initialize() -> void:
	var ipa := ""
	var expect := ""   # "--expect=<key>": the import must refuse the IPA with that word (importer.gd's keys)
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--ipa="):
			ipa = a.substr(6)
		elif a.begins_with("--expect="):
			expect = a.substr(9)
	if ipa == "":
		print("import_check: give --ipa=<path>")
		quit(2)
		return
	var importer: Control = load("res://importer.gd").new()
	root.add_child(importer)
	await process_frame
	var t := Time.get_ticks_msec()
	var error: String = await importer.import_ipa(ipa)
	if expect != "":
		print("import_check: refused with \"%s\" (expected \"%s\")" % [error, expect])
		quit(0 if error == expect else 1)
		return
	if error != "":
		print("import_check: the import failed: ", error)
		quit(1)
		return
	print("import_check: imported in %.1f s" % ((Time.get_ticks_msec() - t) / 1000.0))
	var bad := 0
	for name in ["tiles.png", "font.png", "icons.png", "menus.png", "fontMenu.png", "fontScore.png"]:
		bad += _same_picture("user://original/" + name, "res://assets/original/" + name)
	for code in DirAccess.get_directories_at("res://assets/shell/patch"):
		for name in DirAccess.get_files_at("res://assets/shell/patch/" + code):
			if name.ends_with(".png"):
				bad += _same_picture("user://lang/%s/%s" % [code, name], "res://assets/lang/%s/%s" % [code, name])
	for name in ["font.fnt", "fontMenu.fnt", "fontScore.fnt", "sounds.json"]:
		if FileAccess.get_file_as_bytes("user://original/" + name) != FileAccess.get_file_as_bytes("res://assets/original/" + name):
			print("differs: ", name)
			bad += 1
	var mine := FileAccess.get_file_as_string("user://original/texts.txt").split("\n")
	var theirs := FileAccess.get_file_as_string("res://assets/original/texts.txt").split("\n")
	mine.remove_at(0)   # (the first line, a comment, says where it came from)
	theirs.remove_at(0)
	if mine != theirs:
		print("differs: texts.txt")
		bad += 1
	var sounds := 0
	for f in DirAccess.get_files_at("user://original/sounds"):
		var a := AudioStreamWAV.load_from_file("user://original/sounds/" + f)
		var b := AudioStreamWAV.load_from_file(ProjectSettings.globalize_path("res://assets/original/sounds/" + f))
		if a == null or b == null or a.data != b.data or a.mix_rate != b.mix_rate or a.stereo != b.stereo:
			print("differs: sounds/", f)
			bad += 1
		sounds += 1
	print("import_check: %d sounds, %d differences" % [sounds, bad])
	quit(1 if bad else 0)

func _same_picture(mine: String, theirs: String) -> int:
	var a := Image.load_from_file(mine)
	var b := Image.load_from_file(ProjectSettings.globalize_path(theirs))
	if a == null or b == null:
		print("missing: ", mine)
		return 1
	a.convert(Image.FORMAT_RGBA8)
	b.convert(Image.FORMAT_RGBA8)
	if a.get_size() != b.get_size() or a.get_data() != b.get_data():
		print("differs: ", mine)
		return 1
	return 0
