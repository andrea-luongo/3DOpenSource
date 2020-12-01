vertex_shader = """
   #version 330
   in vec3 vin_position;
   in vec3 vin_normal;
   uniform vec3 light_direction;
   uniform mat4 camera_matrix;
   uniform mat4 model_matrix;
   uniform mat4 projection_matrix;
   uniform mat3 normal_matrix;
   out vec3 L;
   out vec3 N;
   void main(void)
   {
       vec4 pos = camera_matrix * model_matrix * vec4(vin_position, 1.0);
       L = - (camera_matrix * vec4(normalize(light_direction), 0.0)).xyz;
       N = normalize(normal_matrix * vin_normal);
       gl_Position =  projection_matrix * pos;
   }
   """

fragment_shader = """
   #version 330
   in vec3 L;
   in vec3 N;
   out vec4 fout_color;
   uniform vec3 light_intensity;
   uniform vec3 ambient_color;
   uniform vec3 diffuse_color;
   void main(void)
   {

       vec3 f_N = normalize(N);
       vec3 f_L = normalize(L);
       float K_d = max(dot(f_L , f_N), 0.0);
       vec3 diffuse = K_d * diffuse_color * light_intensity;        

       fout_color = vec4(ambient_color + diffuse, 1.0);
   }
   """

slicer_vertex_shader = """
   #version 330
   in vec3 vin_position;
   uniform vec3 vin_color;
   uniform mat4 camera_matrix;
   uniform mat4 model_matrix;
   uniform mat4 projection_matrix;
   out vec3 vout_color;
   void main(void)
   {
       vout_color = vin_color;
       gl_Position = projection_matrix * camera_matrix * model_matrix * vec4(vin_position, 1.0);
   }
   """

slicer_fragment_shader = """
   #version 330
   in vec3 vout_color;
   in vec4 gl_FragCoord;
   uniform float alpha;
   layout (location = 0) out vec4 fout_color;

   void main(void)
   {
       fout_color = vec4(vout_color, alpha);
   }
   """

show_slices_vertex_shader = """
   #version 330
   in vec3 vin_position;
   uniform vec3 vin_color;
   uniform mat4 camera_matrix;
   uniform mat4 model_matrix;
   uniform mat4 projection_matrix;
   void main(void)
   {
     //  gl_Position =  projection_matrix * camera_matrix * vec4(vin_position, 1.0);
       gl_Position =  vec4(vin_position, 1.0);
   }
   """

show_slices_geometry_shader = """
   #version 330
   // layout (triangles ) in;
    layout (lines ) in;
    layout (triangle_strip, max_vertices = 14) out;
    uniform mat4 projection_matrix;
    uniform mat4 camera_matrix;
    uniform float planar_thickness;
    uniform float vertical_thickness;
    uniform float slice_height_offset;
    out vec3 fNormal;
    
    vec3 getNormal()
    {
        vec3 a = vec3(gl_in[0].gl_Position) - vec3(gl_in[1].gl_Position);
        vec3 b = vec3(0.0, 1.0, 0.0);
        return normalize(cross(a, b)); 
    }  
    
    void main()
    {
        vec4 v_0 = gl_in[0].gl_Position;
        vec4 v_1 = gl_in[1].gl_Position;
        vec3 normal = getNormal();
        vec3 up = vec3(0.0, 1.0, 0.0);
        vec4 p_0 = v_0 + planar_thickness * vec4(normal, 0.0);
        vec4 p_1 = v_1 + planar_thickness * vec4(normal, 0.0);
        vec4 p_2 = v_0 - planar_thickness * vec4(normal, 0.0);
        vec4 p_3 = v_1 - planar_thickness * vec4(normal, 0.0);
        vec4 x_0 = p_0 - slice_height_offset * vertical_thickness * vec4(up, 0.0);
        vec4 x_1 = p_1 - slice_height_offset * vertical_thickness * vec4(up, 0.0);
        vec4 x_2 = p_2 - slice_height_offset * vertical_thickness * vec4(up, 0.0);
        vec4 x_3 = p_3 - slice_height_offset * vertical_thickness * vec4(up, 0.0);
        vec4 x_4 = p_0 + (1 - slice_height_offset) * vertical_thickness * vec4(up, 0.0);
        vec4 x_5 = p_1 + (1 - slice_height_offset) * vertical_thickness * vec4(up, 0.0);
        vec4 x_6 = p_3 + (1 - slice_height_offset) * vertical_thickness * vec4(up, 0.0);
        vec4 x_7 = p_2 + (1 - slice_height_offset) * vertical_thickness * vec4(up, 0.0);
        x_0 = projection_matrix * camera_matrix * x_0;
        x_1 = projection_matrix * camera_matrix * x_1;
        x_2 = projection_matrix * camera_matrix * x_2;
        x_3 = projection_matrix * camera_matrix * x_3;
        x_4 = projection_matrix * camera_matrix * x_4;
        x_5 = projection_matrix * camera_matrix * x_5;
        x_6 = projection_matrix * camera_matrix * x_6;
        x_7 = projection_matrix * camera_matrix * x_7;
        
        vec3 side_0 = vec3(x_2-x_3);
        vec3 side_1 = vec3(x_6-x_3);
        fNormal = normalize(cross(side_0, side_1));
        if (dot(fNormal, vec3(0, 0, -1)) > 0){
            fNormal = -fNormal;
        }
        gl_Position = x_3;
        EmitVertex();
        gl_Position = x_2;
        EmitVertex();
        gl_Position = x_6;
        EmitVertex();
        side_0 = vec3(x_7-x_2);
        side_1 = vec3(x_6-x_2);
        fNormal = normalize(cross(side_0, side_1));
        if (dot(fNormal, vec3(0, 0, -1)) > 0){
            fNormal = -fNormal;
        }
        gl_Position =  x_7;
        EmitVertex();
        side_0 = vec3(x_4-x_7);
        side_1 = vec3(x_6-x_7);
        fNormal = normalize(cross(side_0, side_1));
        if (dot(fNormal, vec3(0, 0, -1)) > 0){
            fNormal = -fNormal;
        }
        gl_Position = x_4;
        EmitVertex();
        side_0 = vec3(x_2-x_7);
        side_1 = vec3(x_4-x_7);
        fNormal = normalize(cross(side_0, side_1));
        if (dot(fNormal, vec3(0, 0, -1)) > 0){
            fNormal = -fNormal;
        }
        gl_Position = x_2;
        EmitVertex();
        side_0 = vec3(x_4-x_0);
        side_1 = vec3(x_2-x_0);
        fNormal = normalize(cross(side_0, side_1));
        if (dot(fNormal, vec3(0, 0, -1)) > 0){
            fNormal = -fNormal;
        }
        gl_Position = x_0;
        EmitVertex();
        side_0 = vec3(x_2-x_0);
        side_1 = vec3(x_3-x_0);
        fNormal = normalize(cross(side_0, side_1));
        if (dot(fNormal, vec3(0, 0, -1)) > 0){
            fNormal = -fNormal;
        }
        gl_Position = x_3;
        EmitVertex(); 
        side_0 = vec3(x_3-x_0);
        side_1 = vec3(x_1-x_0);
        fNormal = normalize(cross(side_0, side_1));
        if (dot(fNormal, vec3(0, 0, -1)) > 0){
            fNormal = -fNormal;
        }
        gl_Position = x_1;
        EmitVertex(); 
        side_0 = vec3(x_3-x_1);
        side_1 = vec3(x_6-x_1);
        fNormal = normalize(cross(side_0, side_1));
        if (dot(fNormal, vec3(0, 0, -1)) > 0){
            fNormal = -fNormal;
        }
        gl_Position = x_6;
        EmitVertex(); 
        side_0 = vec3(x_6-x_1);
        side_1 = vec3(x_5-x_1);
        fNormal = normalize(cross(side_0, side_1));
        if (dot(fNormal, vec3(0, 0, -1)) > 0){
            fNormal = -fNormal;
        }
        gl_Position = x_5;
        EmitVertex(); 
        side_0 = vec3(x_5-x_4);
        side_1 = vec3(x_6-x_4);
        fNormal = normalize(cross(side_0, side_1));
        if (dot(fNormal, vec3(0, 0, -1)) > 0){
            fNormal = -fNormal;
        }
        gl_Position = x_4;
        EmitVertex();        
        side_0 = vec3(x_4-x_5);
        side_1 = vec3(x_1-x_5);
        fNormal = normalize(cross(side_0, side_1));
        if (dot(fNormal, vec3(0, 0, -1)) > 0){
            fNormal = -fNormal;
        }
        gl_Position = x_1;
        EmitVertex();        
        side_0 = vec3(x_1-x_0);
        side_1 = vec3(x_4-x_0);
        fNormal = normalize(cross(side_0, side_1));
        if (dot(fNormal, vec3(0, 0, -1)) > 0){
            fNormal = -fNormal;
        }
        gl_Position = x_0;
        EmitVertex();        
        EndPrimitive();
    }
   """

show_slices_fragment_shader = """
    #version 330
    in vec4 gl_FragCoord;
    uniform vec3 vin_color;
    layout (location = 0) out vec4 f_color;
    in vec3 fNormal;
    
    void main(void)
    {
       // f_color = vec4(vin_color * fNormal, 1.0);
        vec3 f_N = normalize(fNormal);
        vec3 f_L = vec3(0.0, 0.0, -1.0);
        float K_d = max(dot(f_L , f_N), 0.0);
        vec3 diffuse = K_d * vin_color;        
       // f_color = vec4(0.5* f_N + vec3(0.5), 1.0);
        f_color = vec4(vin_color, 1.0);
    }
    """

initialize_distance_field_vertex_shader = """
   #version 330
   in vec3 vin_position;
   in vec2 vin_texcoords;
   uniform mat4 model_matrix;
   out vec2 vout_texcoords;

   void main(void)
   {
       vout_texcoords = vin_texcoords;
       gl_Position =  model_matrix * vec4(vin_position, 1.0);
   }
   """

initialize_distance_field_fragment_shader = """
   #version 330
   in vec2 vout_texcoords;
   in vec4 gl_FragCoord;
   layout (location = 0) out vec2 fout_color1;
   layout (location = 1) out vec2 fout_color2;
   uniform sampler2D sliced_image_texture;

   void main(void)
   {
       float id = texture(sliced_image_texture, vout_texcoords).r;
       vec2 result = vec2(65535, 65535) * (id) + vec2((gl_FragCoord.x - 0.5), (gl_FragCoord.y - 0.5) ) * (1-id);
       fout_color1 = vec2(result.x, result.y) / 65535 ;
       fout_color2 = vec2(result.x, result.y) / 65535;
   }
   """

distance_field_pass_vertex_shader = """
   #version 330
   in vec3 vin_position;

   void main(void)
   {
        gl_Position =  vec4(vin_position, 1.0);
   }
   """

distance_field_pass_fragment_shader = """
    #version 330
    in vec4 gl_FragCoord;
    uniform ivec2 image_size;
    layout (location = 0) out vec2 fout_color;
    uniform sampler2D read_texture;
    uniform mat3x2 texture_mask;
    
    vec2 evaluate_neighbours(ivec2 t_coords)
    {
        
        vec2 idx1 = texture_mask[0];
        vec2 idx2 = texture_mask[1];
        vec2 idx3 = texture_mask[2];
        ivec2 t_coords0 = t_coords;
        ivec2 t_coords1 = ivec2(min(max(t_coords.x + idx1.x, 0), 65535), min(max(t_coords.y + idx1.y, 0), 65535) );  
        ivec2 t_coords2 = ivec2(min(max(t_coords.x + idx2.x, 0), 65535), min(max(t_coords.y + idx2.y, 0), 65535) );  
        ivec2 t_coords3 = ivec2(min(max(t_coords.x + idx3.x, 0), 65535), min(max(t_coords.y + idx3.y, 0), 65535) );  
    
        vec2 value_0 = texelFetch(read_texture, t_coords0, 0).rg * 65535;
        vec2 value_1 = texelFetch(read_texture, t_coords1, 0).rg * 65535 ;
        vec2 value_2 = texelFetch(read_texture, t_coords2, 0).rg* 65535;
        vec2 value_3 = texelFetch(read_texture, t_coords3, 0).rg * 65535;         
        
        float dist_0 = (value_0.x - t_coords.x) * (value_0.x - t_coords.x) + (value_0.y - t_coords.y) * (value_0.y - t_coords.y);
        ivec2 min_i_j = t_coords;
        float min_dist = dist_0;
        float dist_1 = (value_1.x - t_coords.x) * (value_1.x - t_coords.x) + (value_1.y - t_coords.y) * (value_1.y - t_coords.y);
        float dist_2 = (value_2.x - t_coords.x) * (value_2.x - t_coords.x) + (value_2.y - t_coords.y) * (value_2.y - t_coords.y);
        float dist_3 = (value_3.x - t_coords.x) * (value_3.x - t_coords.x) + (value_3.y - t_coords.y) * (value_3.y - t_coords.y);
        if (dist_1 < min_dist)
        {
            min_i_j = ivec2(t_coords.x + idx1.x, t_coords.y  + idx1.y);
            min_i_j = t_coords1;
            min_dist = dist_1;
        }
        if (dist_2 < min_dist)
        {
            min_i_j = ivec2(t_coords.x + idx2.x, t_coords.y  + idx2.y);
            min_i_j = t_coords2;
            min_dist = dist_2;
        }
        if (dist_3 < min_dist)
        {
            min_i_j = ivec2(t_coords.x + idx3.x, t_coords.y  + idx3.y);
            min_i_j = t_coords3;
            min_dist = dist_3;
        }
        vec2 result = texelFetch(read_texture, min_i_j, 0).rg;
        return result;
    }
    
   void main(void)
   {
        ivec2 t_coords = ivec2(gl_FragCoord.xy);
        vec2 result = evaluate_neighbours(t_coords);
        fout_color = vec2(result.x, result.y); 
   }
   """

copy_texture_vertex_shader = """
   #version 330
   in vec3 vin_position;

   void main(void)
   {
        gl_Position =  vec4(vin_position, 1.0);
   }
   """

copy_texture_fragment_shader = """
    #version 330
    in vec4 gl_FragCoord;
    layout (location = 0) out vec2 fout_color;
    uniform sampler2D read_texture;

   void main(void)
   {
        ivec2 t_coords = ivec2(gl_FragCoord.xy);
        vec2 result =  texelFetch(read_texture, t_coords, 0).rg;
        fout_color = result;
   }
   """

normalize_distance_field_vertex_shader = """
   #version 330
   in vec3 vin_position;
   uniform mat4 model_matrix;

   void main(void)
   {
        gl_Position =  model_matrix * vec4(vin_position, 1.0);
   }
   """

normalize_distance_field_fragment_shader = """
    #version 330
    in vec4 gl_FragCoord;
    layout (location = 0) out vec3 fout_color;
    uniform sampler2D distance_field_texture;
    uniform float diagonal_length;

   void main(void)
   {
        ivec2 t_coords = ivec2(gl_FragCoord.xy);
        ivec2 closest_fragment =  ivec2(texelFetch(distance_field_texture, t_coords, 0).rg * 65535);
        float distance = (t_coords.x - closest_fragment.x) * (t_coords.x - closest_fragment.x) + (t_coords.y - closest_fragment.y) * (t_coords.y - closest_fragment.y);
        float result = sqrt(distance) / diagonal_length;
        float gamma = 3;
        fout_color = pow(vec3(result), vec3(1.0/gamma));
     //   fout_color = vec3(result);
   }
   """

marching_squares_vertex_shader = """
   #version 330
   in vec3 vin_position;
  // in vec2 vin_texcoords;
   uniform mat4 model_matrix;
//   out vec2 vout_texcoords;

   void main(void)
   {
   //    vout_texcoords = vin_texcoords;
       gl_Position =  model_matrix * vec4(vin_position, 1.0);
   }
   """

marching_squares_fragment_shader = """
    #version 330
    in vec4 gl_FragCoord;
    uniform sampler2D image_texture;
    uniform float slice_height;
    uniform ivec2 image_size;
    uniform ivec2 viewport_origin;
    uniform vec2 bbox_size;
    uniform vec2 bbox_origin;
    layout (location = 0) out float cell_idx;
    layout (location = 1) out vec3 cell_label;
    layout (location = 2) out vec3 p_0;
    layout (location = 3) out vec3 p_1;
    layout (location = 4) out vec3 p_2;
    layout (location = 5) out vec3 p_3;
    
    void look_up(int idx, inout float l, inout vec2 t0, inout vec2 t1, inout vec2 t2, inout vec2 t3) 
    {
        switch(idx)
        {
            case 0:
                l = 0;
                break;
            case 1:
                l = 1;
                t0 = t0 + vec2(0, -0.5);
                t1 = t1 + vec2(-0.5, 0);
                break;
            case 2:
                l = 1;
                t0 = t0 + vec2(0.5, 0);
                t1 = t1 + vec2(0, -0.5);
                break;
            case 3:
                l = 1;
                t0 = t0 + vec2(0.5, 0);
                t1 = t1 + vec2(-0.5, 0);
                break;
            case 4:
                l = 1;
                t0 = t0 + vec2(0, 0.5);
                t1 = t1 + vec2(0.5, 0);
                break;
            case 5:
                l = 0.5;
                t0 = t0 + vec2(0.5, 0);
                t1 = t1 + vec2(0, -0.5);
                t2 = t2 + vec2(-0.5, 0);
                t3 = t3 + vec2(0, 0.5);
                break;
            case 6:
                l = 1;
                t0 = t0 + vec2(0, 0.5);
                t1 = t1 + vec2(0, -0.5);
                break;
            case 7:
                l = 1;
                t0 = t0 + vec2(-0.5, 0);
                t1 = t1 + vec2(0, 0.5);
                break;
            case 8:
                l = 1;
                t0 = t0 + vec2(-0.5, 0);
                t1 = t1 + vec2(0, 0.5);
                break;
            case 9:
                l = 1;    
                t0 = t0 + vec2(0, 0.5);
                t1 = t1 + vec2(0, -0.5);
                break;
            case 10:                
                l = 0.5;
                t0 = t0 + vec2(0, 0.5);
                t1 = t1 + vec2(0.5, 0);
                t2 = t2 + vec2(0, -0.5);
                t3 = t3 + vec2(-0.5, 0);
                break;;
            case 11:
                l = 1;    
                t0 = t0 + vec2(0, 0.5);
                t1 = t1 + vec2(0.5, 0);
                break;
            case 12:
                l = 1;    
                t0 = t0 + vec2(-0.5, 0);
                t1 = t1 + vec2(0.5, 0);
                break;
            case 13:
                l = 1;    
                t0 = t0 + vec2(0.5, 0);
                t1 = t1 + vec2(0, -0.5);
                break;
            case 14:
                l = 1;    
                t0 = t0 + vec2(0, -0.5);
                t1 = t1 + vec2(-0.5, 0);
                break;
            case 15:
                l = 0;
                break;
        }
    }
    
    void main(void)
    {
        ivec2 t_coords_0 = ivec2(gl_FragCoord.x - 1, gl_FragCoord.y - 0);
        ivec2 t_coords_1 = ivec2(gl_FragCoord.x - 0, gl_FragCoord.y - 0);
        ivec2 t_coords_2 = ivec2(gl_FragCoord.x - 0, gl_FragCoord.y - 1);
        ivec2 t_coords_3 = ivec2(gl_FragCoord.x - 1, gl_FragCoord.y - 1);
        float x_0, x_1, x_2, x_3;
        x_0 =  texelFetch(image_texture, t_coords_0, 0).r; 
        x_1 =  texelFetch(image_texture, t_coords_1, 0).r; 
        x_2 =  texelFetch(image_texture, t_coords_2, 0).r; 
        x_3 =  texelFetch(image_texture, t_coords_3, 0).r; 
        if (gl_FragCoord.x - 1 < 0)
        {
            x_0 = 0;
            x_3 = 0;
        }
        if (gl_FragCoord.y - 1 < 0)
        {
            x_2 = 0;
            x_3 = 0;
        }
        float idx = (x_0 * 8 + x_1 * 4 + x_2 * 2 + x_3);
        float label = 0;
        vec2 tmp_0 = vec2(gl_FragCoord.x - 0.5, gl_FragCoord.y - 0.5); 
        vec2 tmp_1 = vec2(gl_FragCoord.x - 0.5, gl_FragCoord.y - 0.5); 
        vec2 tmp_2 = vec2(gl_FragCoord.x - 0.5, gl_FragCoord.y - 0.5);
        vec2 tmp_3 = vec2(gl_FragCoord.x - 0.5, gl_FragCoord.y - 0.5); 
        look_up(int(idx), label, tmp_0, tmp_1, tmp_2, tmp_3);
        cell_idx = idx/ 256.0;
        cell_label = vec3(label,label,label);
     //   p_0 = vec3(gl_FragCoord.x, slice_height, gl_FragCoord.y);
    //    p_0 = vec3(-tmp_0.x * bbox_size.x / image_size.x - bbox_origin.x, slice_height, tmp_0.y * bbox_size.y / image_size.y + bbox_origin.y);
    //    p_1 = vec3(-tmp_1.x * bbox_size.x / image_size.x - bbox_origin.x, slice_height, tmp_1.y * bbox_size.y / image_size.y + bbox_origin.y);
    //    p_2 = vec3(-tmp_2.x * bbox_size.x / image_size.x - bbox_origin.x, slice_height, tmp_2.y * bbox_size.y / image_size.y + bbox_origin.y);
    //    p_3 = vec3(-tmp_3.x * bbox_size.x / image_size.x - bbox_origin.x, slice_height, tmp_3.y * bbox_size.y / image_size.y + bbox_origin.y);
        p_0 = vec3(-(tmp_0.x - viewport_origin.x) * bbox_size.x / image_size.x + bbox_origin.x, slice_height, (tmp_0.y - viewport_origin.y) * bbox_size.y / image_size.y + bbox_origin.y);
        p_1 = vec3(-(tmp_1.x - viewport_origin.x) * bbox_size.x / image_size.x + bbox_origin.x, slice_height, (tmp_1.y - viewport_origin.y) * bbox_size.y / image_size.y + bbox_origin.y);
        p_2 = vec3(-(tmp_2.x - viewport_origin.x) * bbox_size.x / image_size.x + bbox_origin.x, slice_height, (tmp_2.y - viewport_origin.y) * bbox_size.y / image_size.y + bbox_origin.y);
        p_3 = vec3(-(tmp_3.x - viewport_origin.x) * bbox_size.x / image_size.x + bbox_origin.x, slice_height, (tmp_3.y - viewport_origin.y) * bbox_size.y / image_size.y + bbox_origin.y);
        cell_idx = idx/ 15.0;
    }
   """
