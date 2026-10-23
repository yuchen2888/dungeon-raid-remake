shader_type canvas_item;
// T050-C: the original's pictures drawn sharper on today's screens. Where a picture is enlarged more than twice (a
// texel covers more than two screen pixels: the original 320-point art on a Retina iPhone or Mac, when no HD picture
// replaces it), it is sampled with a Catmull-Rom bicubic filter instead of the bilinear one (GL_LINEAR), which keeps
// edges crisp; elsewhere (the HD replacements in assets/hd, about their own size or smaller), the mipmapped bilinear
// filter as usual, which costs a sixteenth of it. Blending stays the original's (source alpha, one minus source
// alpha, on premultiplied textures), so only the sampling changes, never the layout.

varying vec4 tint;

void vertex() {
	tint = COLOR;
}

vec4 catmull_rom(float t) {
	return vec4(t * (-0.5 + t * (1.0 - 0.5 * t)), 1.0 + t * t * (-2.5 + 1.5 * t),
		t * (0.5 + t * (2.0 - 1.5 * t)), t * t * (-0.5 + 0.5 * t));
}

void fragment() {
	vec2 size = 1.0 / TEXTURE_PIXEL_SIZE;
	vec2 texels = fwidth(UV) * size;   // texels per screen pixel
	vec4 c;
	if (max(texels.x, texels.y) >= 0.5) {
		c = texture(TEXTURE, UV);
	} else {
		vec2 p = UV * size - 0.5;
		vec2 i = floor(p);
		vec4 wx = catmull_rom(p.x - i.x);
		vec4 wy = catmull_rom(p.y - i.y);
		c = vec4(0.0);
		for (int y = 0; y < 4; y++) {
			vec4 row = vec4(0.0);
			for (int x = 0; x < 4; x++) {
				row += wx[x] * textureLod(TEXTURE, (i + vec2(float(x) - 0.5, float(y) - 0.5)) / size, 0.0);
			}
			c += wy[y] * row;
		}
		// (the filter overshoots a little at edges; premultiplied colour stays within its alpha)
		c.a = clamp(c.a, 0.0, 1.0);
		c.rgb = clamp(c.rgb, vec3(0.0), vec3(c.a));
	}
	COLOR = c * tint;
}
