// The strips beside the game on screens taller (or wider) than its 2:3 (T050-E, the owner's black bars): each point
// outside the game takes the colour of the game's nearest edge, blurred along that edge more the further out it is and
// darkened towards the screen's edge, so the bars continue whatever screen is showing. Inside the game nothing is drawn.
shader_type canvas_item;

uniform sampler2D screen : hint_screen_texture, filter_linear;
uniform vec4 game;   // the game's rectangle in screen UV: left, top, right, bottom

void fragment() {
	vec2 uv = SCREEN_UV;
	if (uv.x >= game.x && uv.x <= game.z && uv.y >= game.y && uv.y <= game.w) {
		discard;
	}
	vec2 px = SCREEN_PIXEL_SIZE;
	vec2 edge = clamp(uv, game.xy + px * 3.0, game.zw - px * 3.0);
	vec2 away = uv - edge;
	bool across = abs(away.y) >= abs(away.x);   // a strip above or below: blur along x
	vec2 along = across ? vec2(px.x, 0.0) : vec2(0.0, px.y);
	vec2 inward = across ? vec2(0.0, -sign(away.y) * px.y) : vec2(-sign(away.x) * px.x, 0.0);
	float far = across ? abs(away.y) / max(game.y, 1.0 - game.w) : abs(away.x) / max(game.x, 1.0 - game.z);
	float spread = 3.0 + far * 140.0;   // pixels between taps
	vec3 sum = vec3(0.0);
	float weight = 0.0;
	for (int k = -8; k <= 8; k++) {
		float w = exp(-float(k * k) / 32.0);
		vec2 p = edge + along * float(k) * spread;
		sum += w * (texture(screen, p).rgb + texture(screen, p + inward * 4.0).rgb) * 0.5;
		weight += w;
	}
	COLOR = vec4(sum / weight * mix(1.0, 0.25, smoothstep(0.0, 1.0, sqrt(far))), 1.0);
}
