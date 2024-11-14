#version 330 core

in vec3 vert;
in vec2 texcoord;
out vec2 uvs;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;


void main() {
    uvs = texcoord;
    gl_Position = projection * view * model * vec4(vert, 1.0);
}