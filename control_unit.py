import dearpygui.dearpygui as dpg
from math import *
import datetime
import pygame
import numpy as nmp

# DATA
dpg.create_context()
dpg.create_viewport(width=1920, height=780)
dpg.setup_dearpygui()

# NE DIRATI - FIKSNE VREDNOSTI ZA PRETVARANJE METARA U PIKSELE
coord_centre = [36*4+5,65*4+15]
reference = [162.8*4-15,64*4+20]

meter = (reference[0]-coord_centre[0])/20

start_x = 300
start_y = 300
start_z = 0

# DIMENZIJE ROVERA
rover_w = 1.13*meter/2
rover_l = 1.19*meter/2

mast_w = 0.3*meter/2
mast_l = 0.2*meter/2

# BITNE PROMENLJIVE (TRENUTNI STATUS)
global x
x = 500
global y
y = 500
z = 0

Dx = 0
Dx = 0

r = 0
mast_r = 0

# TRAŽENE KOORDINATE
w_coords = [
    [13.485, -2.259],
    [6.433, 10.337],
    [10.874, 7.58],
    [9.515, 6.71],
    [25.405, 4.851],
    [9.454, 0.211],
    [19.867, 0.83],
    [23.409, 9.082],
    [16.031, 3.435]
]

w_coords_string = []
for i, w_coord in enumerate(w_coords):
    w_coords_string.append(f"{i+1} - ({w_coord[0]}, {w_coord[1]})")

# KOORDINATE MARKERA
mrk_coords = [
    [5.96, 2.009],
    [-3.632, 7.469],
    [2.484, 5.984],
    [4.163, 12.066],
    [-1.854, 15.088],
    [-1.73, 22.246],
    [3.205, 22.268],
    [6.863, 26.711],
    [7.905, 21.371],
    [3.876, 18.039],
    [6.598, 14.024],
    [11.656, 13.19],
    [6.086, 8.967],
    [13.864, 6.67],
    [13.804, 1.249],
]

path = nmp.load('paths/S4-W3.npy')*4
path += 10
path[:, 0], path[:, 1] = path[:, 1], path[:, 0].copy()
print("PATH:")
print(path)

# FLAGS
autonomy_flag = False
localization_flag = False
pathfinding_flag = False

w, h, channels, data = dpg.load_image(file="depth_map2.png")
w2, h2, channels2, data2 = dpg.load_image(file="terrain_map.png")

#Gamepad implementacija
pygame.init()
pygame.joystick.init()
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Joystick initialized: {joystick.get_name()}")
else:
    joystick=None
    print("No joystick detected")



# BITNE FUNKCIJE
def pixelToMeterCoord(x,y):
    return [(x-coord_centre[0])/meter , (y-coord_centre[1])/meter]

def normalizeCoord(coord = []):
    return (float(coord[0])*meter+coord_centre[0], float(coord[1])*meter+coord_centre[1])

currentWCoord = normalizeCoord(w_coords[0])
goalDistance = sqrt(abs(x - currentWCoord[0])**2 + abs(y - currentWCoord[1])**2)/meter


# KREIRANJE TEKSTURA ZA MAPE
with dpg.texture_registry():
    dpg.add_static_texture(width=w, height=h, default_value=data, tag="texture_depth_tag")
    dpg.add_static_texture(width=w2, height=h2, default_value=data2, tag="texture_map_tag")


# METODE ZA UI DEO KODA
with dpg.theme() as autonomy_btn_theme:
    with dpg.theme_component(dpg.mvInputFloat, enabled_state=False):
        dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 200, 200])
        dpg.add_theme_color(dpg.mvThemeCol_Button, [255, 0, 0])

with dpg.theme() as log_console_theme:
    with dpg.theme_component(dpg.mvChildWindow):
        dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (30, 30, 30, 255))  # Dark gray background

def autonomy_start(sender, app_data, user_data):
    button_label = dpg.get_item_label(sender)
    new_label = "Stop Autonomy" if button_label == "Start Autonomy" else "Start Autonomy"
    dpg.set_item_label(sender, new_label)

    if new_label == "Stop Autonomy":
        dpg.bind_item_theme(sender, autonomy_btn_theme)
    else:
        dpg.bind_item_theme(sender, autonomy_btn_theme) # Default to blue

def showCoords(sender, coordTag):
    if dpg.get_value(sender) == True:
        dpg.configure_item(coordTag, show=True)
    else:
        dpg.configure_item(coordTag, show=False)

def changeGoalPoint(sender, appData, userData):
    coordValue = w_coords[int(dpg.get_value(sender)[0]) - 1]
    global currentWCoord
    currentWCoord = normalizeCoord(coordValue)
    dpg.configure_item("goalDistanceLine", p2 = currentWCoord)

def changeMapOpacity(sender, appData, userData):
    opacity = dpg.get_value(sender)
    add_log(f"Opacity: {opacity}")
    dpg.configure_item("depth-map", color=(255,255,255,opacity))




def updateValues():
    point = pixelToMeterCoord(x,y)
    dpg.configure_item("posx-label", default_value=f"X: {point[0]}")
    dpg.configure_item("posy-label", default_value=f"Y: {point[1]}")
    dpg.configure_item("posz-label", default_value=f"Z: {z}")
    goalDistance = sqrt(abs(x - currentWCoord[0])**2 + abs(y - currentWCoord[1])**2)/meter
    #add_log(str(currentWCoord))
    dpg.configure_item("goalDist-label", default_value=f"Distance to current goal: {goalDistance} meters")

log_messages = []
# Function to add a log message
def add_log(message):
    message = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] " + message
    log_messages.append(message)
    dpg.add_text(message, parent="log_console")

    # Scroll to the bottom to show the latest log
    dpg.set_y_scroll("log_console", dpg.get_y_scroll_max("log_console"))

# GRAFIČKI DEO

# UI
def create_control_buttons():
    """Create control buttons for the control unit."""
    dpg.add_button(label="Start Autonomy", callback=autonomy_start)
    dpg.add_button(label="Start Coordinatization")
    dpg.add_button(label="Start Testing Module")

def create_visibility_checkboxes():
    """Create checkboxes for toggling visibility of elements."""
    with dpg.group():
        dpg.add_checkbox(label="Show markers", default_value=True, callback=lambda s, a, u: showCoords(s, "mrk_coords"))
        dpg.add_checkbox(label="Show coordinates", default_value=True, callback=lambda s, a, u: showCoords(s, "w_coords"))
        dpg.add_checkbox(label="Show path")

def create_position_display():
    """Create labels to display the rover's position."""
    with dpg.group():
        dpg.add_text("Position")
        point = pixelToMeterCoord(x, y)
        dpg.add_text(f"X: {point[0]}", tag="posx-label")
        dpg.add_text(f"Y: {point[1]}", tag="posy-label")
        dpg.add_text(f"Z: {z}", tag="posz-label")

def create_goal_selector():
    """Create a dropdown for selecting the current goal."""
    dpg.add_combo(w_coords_string, default_value=w_coords_string[0], tag="wCoordCombo", callback=changeGoalPoint)

def create_depth_opacity_slider():
    """Create a slider to adjust the depth map opacity."""
    dpg.add_slider_float(label="Depth map opacity", min_value=0, max_value=255, default_value=0, callback=changeMapOpacity)

def create_goal_distance_display():
    """Create a label to display the distance to the current goal."""
    dpg.add_text(f"Distance to current goal: {goalDistance} meters", tag="goalDist-label")

def create_log_console():
    """Create the log console for messages."""
    with dpg.child_window(label="Log Console", height=200, width=780, border=True, tag="log_console"):
        dpg.add_text("Log Console Initialized")
    dpg.bind_item_theme("log_console", log_console_theme)

# Main control unit window
with dpg.window(label="Control Unit", width=800, height=735,tag="control_unit_tag"):
    create_control_buttons()
    create_visibility_checkboxes()
    create_position_display()
    create_goal_selector()
    create_depth_opacity_slider()
    create_goal_distance_display()
    create_log_console()

#MAP WINDOW I ISCRTAVANJE #####################################################################################################

# PONOVNO ISCRTAVANJE ROVERA (POZIVA SE KAD GOD SE PROMENI POZICIJA)
def draw_rover(x_val, y_val, rov_w, rov_l):
    return [x_val-rov_w, y_val-rov_l], [x_val-rov_w, y_val+rov_l], [x_val+rov_w, y_val+rov_l], [x_val+rov_w, y_val-rov_l], [x_val-rov_w, y_val-rov_l]


def draw_images():

    dpg.draw_image("texture_map_tag", (0, 0), (1100, 177*4), uv_min=(0, 0), uv_max=(1, 1))
    dpg.draw_image("texture_depth_tag", (0, 0), (1100, 177*4), tag="depth-map",  uv_min=(0, 0), uv_max=(1, 1), color=(255,255,255,0))

def draw_rover_on_canvas():

    with dpg.draw_node(tag="rover_node"):
        #dpg.draw_rectangle(pmin=(x-rover_w/2,y-rover_l/2), pmax=(x+rover_w/2, y+rover_l/2), color=(255,0,0), thickness=2)
        dpg.draw_polygon(draw_rover(x,y,rover_w, rover_l), tag="rover_poly", color=(255,0,0), fill=(255,0,0,70),thickness=2)
        dpg.draw_arrow(tag="rover_arrow", p2=(x,y), p1=(x, y-40), color=(255,0,0,180), thickness=3)

        with dpg.draw_node(tag="mast_node"):
            dpg.draw_polygon(draw_rover(x,y,mast_w,mast_l), tag="mast_poly", color=(0,255,0), thickness=2)
            dpg.draw_line([x-mast_w-150, y-mast_l-240], [x-mast_w, y-mast_l], tag="cam_angle_left", color=(255,255,255,130))
            dpg.draw_line([x+mast_w+150, y-mast_l-240], [x+mast_w, y-mast_l], tag="cam_angle_right", color=(255,255,255,130))

            #dpg.draw_bezier_cubic([x-mast_w-50, y-mast_l-80], [x-20, y-120], [x+20,y-120], [x-mast_w+65, y-mast_l-80], color=(255,255,255,130))'''
            dpg.draw_line([x, y-300], [x, y-mast_l], tag = "mast_line", color=(0,255,0))

def draw_points():

    dpg.draw_circle(radius=5, color=(255,220,0), center=(coord_centre[0],coord_centre[1]), thickness=3, fill=(255,220,0))
    dpg.draw_circle(radius=5, color=(255,220,0), center=(reference[0],reference[1]), thickness=3, fill=(255,220,0))

    with dpg.draw_node(tag="w_coords"):
        for i, w_coord in enumerate(w_coords):
            coord = normalizeCoord(w_coord)

            dpg.draw_circle(radius=5, color=(60,60,255), center=(coord[0],coord[1]), thickness=3, fill=(60,60,255))
            dpg.draw_text([coord[0] + 10, coord[1] - 30], f"{i+1}", size=20, color=(60,60,255))

    with dpg.draw_node(tag="mrk_coords"):
        for i, mrk_coord in enumerate(mrk_coords):
            coord = normalizeCoord([mrk_coord[1],mrk_coord[0]])

            dpg.draw_circle(radius=5, color=(0,255,0), center=(coord[0],coord[1]), thickness=3, fill=(0,255,0))
            dpg.draw_text([coord[0] + 10, coord[1] - 30], f"{i+1}", size=20, color=(0,255,0))


with dpg.window(label="Map", pos=(800,0),tag="map_tag"):

    with dpg.drawlist(width=1090, height=700,tag="drawlist_tag"):

        draw_images()
        draw_rover_on_canvas()
        draw_points()

        dpg.draw_line([x,y], currentWCoord, color=(60,60,255,150), tag="goalDistanceLine", thickness=2)

        dpg.draw_polyline(path.tolist(), color=(0,20,255), thickness=2)

############################################################################################################################

main_viewport_width=1920
main_viewport_heigth=780

conrol_unit_width=800
control_unit_heigth=735
control_unit_width_precentage=800/1920
control_unit_ratio=800/735

map_width=1090
map_height=700
map_width_precentage=1090/1920
map_ratio=1090/700

map_image_width=1100
map_image_heigth=177*4
map_image_precetage=1100/1920
map_image_ratio=1100/(177*4)


# Promena velicine glavnog prozora i skaliranje njegove dece
def resize_content(sender, app_data):
    viewport_width = dpg.get_viewport_client_width()
    viewport_height= dpg.get_viewport_client_height()

    new_control_unit_width=int(viewport_width*control_unit_width_precentage)
    new_map_width=int(viewport_width*map_width_precentage)

    dpg.set_item_width("control_unit_tag",int(new_control_unit_width))
    dpg.set_item_height("control_unit_tag",int(viewport_height))
    dpg.set_item_pos("map_tag", (int(new_control_unit_width),0))
    dpg.set_item_width("drawlist_tag",int(new_map_width))
    dpg.set_item_height("drawlist_tag",int(viewport_height))

    new_map_image_width=int(viewport_width*map_image_precetage)

    #dpg.draw_image("texture_map_tag", (0, 0), (1100, 177*4), uv_min=(0, 0), uv_max=(1, 1))
    #dpg.draw_image("texture_depth_tag", (0, 0), (1100, 177*4), tag="depth-map",  uv_min=(0, 0), uv_max=(1, 1), color=(255,255,255,0))

    dpg.set_item_size("texture_map_tag", (new_map_image_width, int(new_map_image_width/map_image_ratio)))
    dpg.set_item_size("texture_depth_tag", (new_map_image_width, int(new_map_image_width/map_image_ratio)))

dpg.set_viewport_resize_callback(resize_content)

# METODA ZA PONOVNO ISCRTAVANJE NA MAPI
def moveRover(sender, app_data, user_data,intensity):
    global x, y, r

    if intensity==None:
        intensity=0.4

    #print(f"{x}, {y}, {r} - before")
    Dx = cos(radians(r-90))*intensity
    x -= Dx
    Dy = sin(radians(r-90))*intensity
    y += Dy
    dpg.configure_item("rover_poly", points=draw_rover(x,y,rover_w, rover_l))
    dpg.configure_item("rover_arrow", p2=(x,y), p1=(x, y-40))
    dpg.configure_item("mast_poly", points=draw_rover(x,y,mast_w, mast_l))
    dpg.configure_item("mast_line", p2 = [x, y-300], p1 = [x, y-mast_l])
    dpg.configure_item("cam_angle_left", p1 = [x-mast_w-150, y-mast_l-240], p2 = [x-mast_w, y-mast_l])
    dpg.configure_item("cam_angle_right", p1 = [x+mast_w+150, y-mast_l-240], p2 = [x+mast_w, y-mast_l])

    dpg.configure_item("goalDistanceLine", p1 = (x,y))
    add_log(f"Current position: ({x},{y},{z})")





# [ DEBUGING FUNKCIJE ]
def steerRoverL(sender, app_data, user_data,intensity):
    if intensity==None:
        intensity=0.4
    global r
    r += intensity

def steerRoverR(sender, app_data, user_data,intensity):
    if intensity==None:
        intensity=0.4
    global r
    r -= intensity

def steerMastL(sender, app_data, user_data):
    global mast_r
    mast_r += 0.4

def steerMastR(sender, app_data, user_data):
    global mast_r
    mast_r -= 0.4

with dpg.handler_registry():
    dpg.add_key_down_handler(key=dpg.mvKey_W, callback=moveRover)
    dpg.add_key_down_handler(key=dpg.mvKey_A, callback=steerRoverL)
    dpg.add_key_down_handler(key=dpg.mvKey_D, callback=steerRoverR)
    dpg.add_key_down_handler(key=dpg.mvKey_Q, callback=steerMastL)
    dpg.add_key_down_handler(key=dpg.mvKey_E, callback=steerMastR)

def gamepad_input():
    if joystick:
        pygame.event.pump()  # Process events so joystick input is updated
        axis0 = joystick.get_axis(0)  #leva pecurka (left-right)
        axis1 = joystick.get_axis(1)  # (up-down)
        axis2 = joystick.get_axis(2)  #desna pecurka
        axis3 = joystick.get_axis(3)
        DpadLR,DpadUD = joystick.get_hat(0)  # tapl,prvi je levo(-) desno(+) drugi je gore dole,


        if axis2>0:
            steerRoverR(None,None,None,axis2*0.4)

        else:
            steerRoverL(None,None,None,abs(axis2)*0.4)

        if axis1<-0.01:
            moveRover(None,None,None,abs(axis1*0.4))

        if DpadLR != 0:
            if DpadLR>0:
                steerMastR(None,None,None)
            else:
                steerMastL(None,None,None)


# POKRETANJE GLAVNOG PROGRAMA
dpg.show_viewport()
while dpg.is_dearpygui_running():
    gamepad_input()
    updateValues()


    #r = dpg.get_value("rotation_knob")
    #mast_r = dpg.get_value("mast_rotation_knob")
    #print(f"{x}, {y}, {r} - DURING")

    dpg.apply_transform("rover_node", dpg.create_translation_matrix([x,y]) * dpg.create_rotation_matrix(pi*r/180, [0,0,-1]) * dpg.create_translation_matrix([-x,-y]))
    dpg.apply_transform("mast_node", dpg.create_translation_matrix([x,y]) * dpg.create_rotation_matrix(pi*mast_r/180, [0,0,-1]) * dpg.create_translation_matrix([-x,-y]))
    dpg.render_dearpygui_frame()
dpg.destroy_context()
pygame.quit()