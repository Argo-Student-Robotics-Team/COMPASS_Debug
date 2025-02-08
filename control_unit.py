import subprocess
import time
import dearpygui.dearpygui as dpg
from math import *
import datetime
import pygame
import numpy as nmp
import threading

# DATA
dpg.create_context()
dpg.create_viewport(width=1920, height=780)
dpg.setup_dearpygui()

# NE DIRATI - FIKSNE VREDNOSTI ZA PRETVARANJE METARA U PIKSELE
coord_centre = [36 * 4 + 5, 65 * 4 + 15]
reference = [162.8 * 4 - 15, 64 * 4 + 20]

meter = (reference[0] - coord_centre[0]) / 20

start_x = 300
start_y = 300
start_z = 0

# DIMENZIJE ROVERA
rover_w = 1.13 * meter / 2
rover_l = 1.19 * meter / 2

mast_w = 0.3 * meter / 2
mast_l = 0.2 * meter / 2

# BITNE PROMENLJIVE (TRENUTNI STATUS)
global x
x = 500
global y
y = 500
z = 0

Dx = 0
Dy = 0  # ranije je ovde pisalo Dx?

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
    w_coords_string.append(f"{i + 1} - ({w_coord[0]}, {w_coord[1]})")

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
path = nmp.load('paths/S4-W3.npy') * 4
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

# LOGOVANJE
# Global log storage
log_messages = []


# Clear the log file at program start
def initialize_log_file():
    try:
        with open("log_messages.txt", "w") as file:  # Open in write mode to truncate the file
            file.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Log file initialized.\n")
    except Exception as e:
        print(f"Error initializing log file: {e}")


# Initialize the log file
initialize_log_file()


# Save log message to a file immediately
def save_log_to_file(message):
    try:
        with open("log_messages.txt", "a") as file:  # Append mode to keep existing logs
            file.write(message + "\n")
    except Exception as e:
        print(f"Error saving log to file: {e}")


# Add a log message to the log console
# This function also stores the log message in the global log_messages list for later use
def add_log(message):
    global log_messages
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_message = f"[{timestamp}] {message}"
    log_messages.append(full_message)

    # Save the log to file immediately
    save_log_to_file(full_message)

    # Izbegavamo prepunjavanje console_log i log_messages tako sto cemo da smanjimo broj poruka u listi za 1900 i
    # icrtacemo novi console_log tako da sadrzi samo poslednjih 100 poruka.
    if (len(log_messages) > 2000):
        log_messages = log_messages[1900:]
        # Update the log console dynamically
        if dpg.does_item_exist("log_console"):
            # Clear the console and re-add messages after truncating
            dpg.delete_item("log_console", children_only=True)  # Remove existing log messages
            for log in log_messages:
                dpg.add_text(log, parent="log_console")  # Add the new truncated messages

            # Scroll to the bottom of the console
            dpg.set_y_scroll("log_console", dpg.get_y_scroll_max("log_console"))
    else:
        # Update the log console dynamically
        if dpg.does_item_exist("log_console"):
            dpg.add_text(full_message, parent="log_console")
            dpg.set_y_scroll("log_console", dpg.get_y_scroll_max("log_console"))


# Clear the log console and the global log_messages list of all messages
def clear_logs():
    global log_messages  # This needs to be implemented the other way because its better not to use global variables in functions

    # Add a "Logs Cleared" message to both file and console
    add_log("Log Console Cleared")

    # Clear the log_messages list
    log_messages = []

    # Clear the log console visually
    if dpg.does_item_exist("log_console"):
        dpg.delete_item("log_console", children_only=True)
        dpg.add_text("Log Console Cleared", parent="log_console")


# BITNE FUNKCIJE
def pixelToMeterCoord(x, y):
    return [(x - coord_centre[0]) / meter, (y - coord_centre[1]) / meter]


def normalizeCoord(coord=[]):
    return (float(coord[0]) * meter + coord_centre[0], float(coord[1]) * meter + coord_centre[1])


currentWCoord = normalizeCoord(w_coords[0])
goalDistance = sqrt(abs(x - currentWCoord[0]) ** 2 + abs(y - currentWCoord[1]) ** 2) / meter

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


stop_event = threading.Event()
camera_running = False
thread = None


def open_camera():
    global camera_running, stop_event, thread

    if camera_running:
        add_log("Camera closed")
        camera_running = False
        stop_event.set()
        if thread is not None:
            thread.join()
            thread = None
        dpg.set_item_label("open_camera_button", "Open camera")
    else:
        stop_event.clear()
        camera_running = True
        dpg.set_item_label("open_camera_button", "Close camera")
        # Start the camera worker in a new thread
        thread = threading.Thread(target=camera_worker)
        thread.start()


def camera_worker():
    global camera_running
    add_log("Camera opened")
    # Start the camera subprocess in a non-blocking way so that we can later terminate it.
    proc = subprocess.Popen(["python", "camera.py"])
    try:
        # Wait until the stop_event is set.
        while (not stop_event.is_set()) and (proc.poll() is None):
            time.sleep(0.1)  # Sleep a short time to avoid busy waiting
    finally:
        # When stop_event is set, terminate the subprocess.
        if proc.poll() is not None:
            add_log("Camera closed")
            camera_running = False
            dpg.set_item_label("open_camera_button", "Open camera")
        else:
            proc.terminate()    # Terminate the camera process
            proc.wait()         # Wait for the process to fully terminate



def autonomy_start(sender, app_data, user_data):
    button_label = dpg.get_item_label(sender)
    new_label = "Stop Autonomy" if button_label == "Start Autonomy" else "Start Autonomy"
    dpg.set_item_label(sender, new_label)

    if new_label == "Stop Autonomy":
        add_log(f"Autonomy started. Initial position: ({pixelToMeterCoord(x, y)})")
        dpg.bind_item_theme(sender, autonomy_btn_theme)

    else:
        actual_position = pixelToMeterCoord(x, y)
        target_position = pixelToMeterCoord(currentWCoord[0], currentWCoord[1])
        compare_positions(target_position, actual_position)
        add_log(f"Autonomy stopped. Final position: ({actual_position[0]:.2f}, {actual_position[1]:.2f})")
        dpg.bind_item_theme(sender, autonomy_btn_theme)  # Default to blue


def showCoords(sender, coordTag):
    if dpg.get_value(sender):
        dpg.configure_item(coordTag, show=True)
    else:
        dpg.configure_item(coordTag, show=False)


def changeGoalPoint(sender, appData, userData):
    coordValue = w_coords[int(dpg.get_value(sender)[0]) - 1]
    global currentWCoord
    currentWCoord = normalizeCoord(coordValue)
    dpg.configure_item("goalDistanceLine", p2=currentWCoord)
    add_log(f"New Target Position: {coordValue}")


def changeMapOpacity(sender, appData, userData):
    opacity = dpg.get_value(sender)
    add_log(f"Opacity: {opacity}")
    dpg.configure_item("depth-map", color=(255, 255, 255, opacity))


def updateValues():
    point = pixelToMeterCoord(x, y)
    dpg.configure_item("posx-label", default_value=f"X: {point[0]}")
    dpg.configure_item("posy-label", default_value=f"Y: {point[1]}")
    dpg.configure_item("posz-label", default_value=f"Z: {z}")
    goalDistance = sqrt(abs(x - currentWCoord[0]) ** 2 + abs(y - currentWCoord[1]) ** 2) / meter
    #add_log(str(currentWCoord))
    dpg.configure_item("goalDist-label", default_value=f"Distance to current goal: {goalDistance} meters")


# GRAFIČKI DEO

# UI
def create_control_buttons():
    """Create control buttons for the control unit."""
    dpg.add_button(label="Open camera", callback=open_camera, tag="open_camera_button")
    dpg.add_button(label="Start Autonomy", callback=autonomy_start)
    dpg.add_button(label="Start Coordinatization")
    dpg.add_button(label="Start Testing Module")


def create_visibility_checkboxes():
    """Create checkboxes for toggling visibility of elements."""
    with dpg.group():
        dpg.add_checkbox(label="Show markers", default_value=True, callback=lambda s, a, u: showCoords(s, "mrk_coords"))
        dpg.add_checkbox(label="Show coordinates", default_value=True,
                         callback=lambda s, a, u: showCoords(s, "w_coords"))
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
    dpg.add_slider_float(label="Depth map opacity", min_value=0, max_value=255, default_value=0,
                         callback=changeMapOpacity)


def create_goal_distance_display():
    """Create a label to display the distance to the current goal."""
    dpg.add_text(f"Distance to current goal: {goalDistance} meters", tag="goalDist-label")


def create_log_console():
    """Create the log console for messages."""
    with dpg.child_window(label="Log Console", height=200, width=780, border=True, tag="log_console"):
        dpg.add_text("Log Console Initialized")
    dpg.bind_item_theme("log_console", log_console_theme)


# Main control unit window
with dpg.window(label="Control Unit", width=800, height=735, tag="control_unit_tag"):
    create_control_buttons()
    create_visibility_checkboxes()
    create_position_display()
    create_goal_selector()
    create_depth_opacity_slider()
    create_goal_distance_display()
    create_log_console()


# MAP WINDOW I ISCRTAVANJE

# PONOVNO ISCRTAVANJE ROVERA (POZIVA SE KAD GOD SE PROMENI POZICIJA)
def draw_rover(x_val, y_val, rov_w, rov_l):
    return [x_val - rov_w, y_val - rov_l], [x_val - rov_w, y_val + rov_l], [x_val + rov_w, y_val + rov_l], [
        x_val + rov_w, y_val - rov_l], [x_val - rov_w, y_val - rov_l]


def draw_images():
    dpg.draw_image("texture_map_tag", (0, 0), (1100, 177 * 4), uv_min=(0, 0), uv_max=(1, 1))
    dpg.draw_image("texture_depth_tag", (0, 0), (1100, 177 * 4), tag="depth-map", uv_min=(0, 0), uv_max=(1, 1),
                   color=(255, 255, 255, 0))


def draw_rover_on_canvas():
    with dpg.draw_node(tag="rover_node"):
        #dpg.draw_rectangle(pmin=(x-rover_w/2,y-rover_l/2), pmax=(x+rover_w/2, y+rover_l/2), color=(255,0,0), thickness=2)
        dpg.draw_polygon(draw_rover(x, y, rover_w, rover_l), tag="rover_poly", color=(255, 0, 0), fill=(255, 0, 0, 70),
                         thickness=2)
        dpg.draw_arrow(tag="rover_arrow", p2=(x, y), p1=(x, y - 40), color=(255, 0, 0, 180), thickness=3)

        with dpg.draw_node(tag="mast_node"):
            dpg.draw_polygon(draw_rover(x, y, mast_w, mast_l), tag="mast_poly", color=(0, 255, 0), thickness=2)
            dpg.draw_line([x - mast_w - 150, y - mast_l - 240], [x - mast_w, y - mast_l], tag="cam_angle_left",
                          color=(255, 255, 255, 130))
            dpg.draw_line([x + mast_w + 150, y - mast_l - 240], [x + mast_w, y - mast_l], tag="cam_angle_right",
                          color=(255, 255, 255, 130))

            #dpg.draw_bezier_cubic([x-mast_w-50, y-mast_l-80], [x-20, y-120], [x+20,y-120], [x-mast_w+65, y-mast_l-80], color=(255,255,255,130))'''
            dpg.draw_line([x, y - 300], [x, y - mast_l], tag="mast_line", color=(0, 255, 0))


def draw_points():
    dpg.draw_circle(radius=5, color=(255, 220, 0), center=(coord_centre[0], coord_centre[1]), thickness=3,
                    fill=(255, 220, 0))
    dpg.draw_circle(radius=5, color=(255, 220, 0), center=(reference[0], reference[1]), thickness=3, fill=(255, 220, 0))

    with dpg.draw_node(tag="w_coords"):
        for i, w_coord in enumerate(w_coords):
            coord = normalizeCoord(w_coord)

            dpg.draw_circle(radius=5, color=(60, 60, 255), center=(coord[0], coord[1]), thickness=3, fill=(60, 60, 255))
            dpg.draw_text([coord[0] + 10, coord[1] - 30], f"{i + 1}", size=20, color=(60, 60, 255))

    with dpg.draw_node(tag="mrk_coords"):
        for i, mrk_coord in enumerate(mrk_coords):
            coord = normalizeCoord([mrk_coord[1], mrk_coord[0]])

            dpg.draw_circle(radius=5, color=(0, 255, 0), center=(coord[0], coord[1]), thickness=3, fill=(0, 255, 0))
            dpg.draw_text([coord[0] + 10, coord[1] - 30], f"{i + 1}", size=20, color=(0, 255, 0))


with dpg.window(label="Map", pos=(800, 0), tag="map_tag"):
    with dpg.drawlist(width=1090, height=700, tag="drawlist_tag"):
        draw_images()
        draw_rover_on_canvas()
        draw_points()

        dpg.draw_line([x, y], currentWCoord, color=(60, 60, 255, 150), tag="goalDistanceLine", thickness=2)

        dpg.draw_polyline(path.tolist(), color=(0, 20, 255), thickness=2)


# POREDJENJE SA REFERENTNOM TACKOM
def compare_positions(target_position, actual_position):
    add_log(f"Comparing positions...")  # Debug log

    # Calculate the Euclidean distance error
    error = sqrt((target_position[0] - actual_position[0]) ** 2 +
                 (target_position[1] - actual_position[1]) ** 2)

    # Log the comparison
    add_log(f"Actual position: ({actual_position[0]:.2f}, {actual_position[1]:.2f})")
    add_log(f"Target position: ({target_position[0]:.2f}, {target_position[1]:.2f})")
    add_log(f"Distance error: {error:.2f} meters")

    return error


# METODA ZA PONOVNO ISCRTAVANJE NA MAPI
def moveRover(sender, app_data, user_data):
    global x, y, r

    #print(f"{x}, {y}, {r} - before")
    Dx = cos(radians(r - 90)) * user_data
    x -= Dx
    Dy = sin(radians(r - 90)) * user_data
    y += Dy
    dpg.configure_item("rover_poly", points=draw_rover(x, y, rover_w, rover_l))
    dpg.configure_item("rover_arrow", p2=(x, y), p1=(x, y - 40))
    dpg.configure_item("mast_poly", points=draw_rover(x, y, mast_w, mast_l))
    dpg.configure_item("mast_line", p2=[x, y - 300], p1=[x, y - mast_l])
    dpg.configure_item("cam_angle_left", p1=[x - mast_w - 150, y - mast_l - 240], p2=[x - mast_w, y - mast_l])
    dpg.configure_item("cam_angle_right", p1=[x + mast_w + 150, y - mast_l - 240], p2=[x + mast_w, y - mast_l])

    dpg.configure_item("goalDistanceLine", p1=(x, y))
    add_log(f"Current position: ({x},{y},{z})")

    # Compare with target position (example: currentWCoord is the target)
    actual_position = pixelToMeterCoord(x, y)
    target_position = pixelToMeterCoord(currentWCoord[0], currentWCoord[1])
    compare_positions(target_position, actual_position)
    add_log(f"Rover moved to position: ({pixelToMeterCoord(x, y)})")


# [ DEBUGING FUNKCIJE ]
def steerRover(sender, app_data, user_data):
    global r
    r += user_data
    if (user_data > 0):
        add_log(f"Rover steered left. Current angle: {r}")
    else:
        add_log(f"Rover steered right. Current angle: {r}")


def steerMast(sender, app_data, user_data):
    global mast_r
    mast_r += user_data
    if (user_data > 0):
        add_log(f"Mast steered left. Current angle: {mast_r}")
    else:
        add_log(f"Mast steered right. Current angle: {mast_r}")


with dpg.handler_registry():
    dpg.add_key_down_handler(key=dpg.mvKey_W, callback=moveRover, user_data=0.4)
    dpg.add_key_down_handler(key=dpg.mvKey_A, callback=steerRover, user_data=0.4)
    dpg.add_key_down_handler(key=dpg.mvKey_D, callback=steerRover, user_data=-0.4)
    dpg.add_key_down_handler(key=dpg.mvKey_Q, callback=steerMast, user_data=0.4)
    dpg.add_key_down_handler(key=dpg.mvKey_E, callback=steerMast, user_data=-0.4)

# GAMEPAD IMPLEMENTATION
pygame.init()
pygame.joystick.init()
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Joystick initialized: {joystick.get_name()}")
    add_log(f"Joystick initialized: {joystick.get_name()}")
else:
    joystick = None
    print("No joystick detected")
    add_log(f"No joystick detected")


def gamepad_input():
    if joystick:
        pygame.event.pump()  # Process events so joystick input is updated
        axis0 = joystick.get_axis(0)  # leva pecurka (left-right)
        axis1 = joystick.get_axis(1)  # (up-down)
        axis2 = joystick.get_axis(2)  # desna pecurka
        axis3 = joystick.get_axis(3)
        DpadLR, DpadUD = joystick.get_hat(0)  # tapl,prvi je levo(-) desno(+) drugi je gore dole,

        if axis1 < -0.01:
            moveRover(None, None, abs(axis1 * 0.4))

        # izgleda zbunjujuce, axis2 ima vrednosti[-1,1], kada je na -1 tada treba da skrene u levo pa dobijemo
        # -(-1*0.4) i time dobije 0.4 sto znaci skrecemo levo jer je rezultat u plusu
        # a kada je axis2=1 onda -(1*0.4) i time dobijemo -0.4 sto znaci da skrecemo desno
        if axis2 > 0.01:
            steerRover(None, None, -(axis2 * 0.4))
        if axis2 < -0.01:
            steerRover(None, None, -(axis2 * 0.4))

        if DpadLR != 0:
            if DpadLR > 0:
                steerMast(None, None, -0.4)
            else:
                steerMast(None, None, 0.4)


# POKRETANJE GLAVNOG PROGRAMA
dpg.show_viewport()
while dpg.is_dearpygui_running():
    gamepad_input()
    updateValues()

    """
    r = dpg.get_value("rotation_knob")
    mast_r = dpg.get_value("mast_rotation_knob")
    print(f"{x}, {y}, {r} - DURING")
    """

    dpg.apply_transform("rover_node", dpg.create_translation_matrix([x, y]) * dpg.create_rotation_matrix(pi * r / 180,
                                                                                                         [0, 0,
                                                                                                          -1]) * dpg.create_translation_matrix(
        [-x, -y]))
    dpg.apply_transform("mast_node",
                        dpg.create_translation_matrix([x, y]) * dpg.create_rotation_matrix(pi * mast_r / 180, [0, 0,
                                                                                                               -1]) * dpg.create_translation_matrix(
                            [-x, -y]))
    dpg.render_dearpygui_frame()

dpg.destroy_context()
pygame.quit()
if thread is not None:
    stop_event.set()
    thread.join()

