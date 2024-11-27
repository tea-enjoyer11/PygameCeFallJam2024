#version 330 core

uniform sampler2D tex;
uniform sampler2D noise_tex;

in vec2 uvs;
out vec4 f_color;

const int noise_tex_w = 256;
const int noise_tex_h = 256;



float get_noise() {
    float x = gl_FragCoord.x;
    float y = gl_FragCoord.y;

    x = max(min(x, noise_tex_w), 0);
    y = max(min(y, noise_tex_h), 0);

    return texture(noise_tex, vec2(x, y)).r;
}


void main() {
    float n = get_noise();
    
    f_color = vec4(texture(tex, uvs).rgb * n, 1.0);
    // f_color = vec4(texture(tex, uvs).rgb,1.0);
}

