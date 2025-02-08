import dearpygui.dearpygui as dpg
import numpy as np
import cv2
import time

# Initialize Dear PyGui
dpg.create_context()

# Create a theme that removes window padding
with dpg.theme() as no_padding_theme:
    # First create a theme component
    with dpg.theme_component(dpg.mvAll):
        # Then add the style to the component
        dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 0, 0, category=dpg.mvThemeCat_Core)

# Open webcam
vid = cv2.VideoCapture(0)
if not vid.isOpened():
    print("Error: Could not open webcam.")
    exit()

# Get webcam resolution
frame_width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
aspect_ratio = frame_width / frame_height
stretch_mode = False  # Default to keeping aspect ratio

print(f"Camera Resolution: {frame_width}x{frame_height}")

dpg.create_viewport(title="Cam Feed", width=frame_width+16, height=frame_height + 39, resizable=True)


# Function to process frame
def process_frame(frame_bgr):
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB
    return (frame_rgb.astype(np.float32) / 255.0).ravel()


# Read initial frame
ret, frame = vid.read()
if not ret:
    print("Error: Failed to read frame")
    vid.release()
    exit()

texture_data = process_frame(frame)

# Create texture registry
with dpg.texture_registry(show=False):
    dpg.add_raw_texture(frame_width, frame_height, texture_data, format=dpg.mvFormat_Float_rgb, tag="texture_tag")


# Function to update image size and position
def update_image_size():
    viewport_width = dpg.get_viewport_client_width()
    viewport_height = dpg.get_viewport_client_height()

    if stretch_mode:
        new_width, new_height = viewport_width, viewport_height  # Stretch to fill viewport
    else:
        new_width = viewport_width
        new_height = int(viewport_width / aspect_ratio)
        if new_height > viewport_height:
            new_height = viewport_height
            new_width = int(viewport_height * aspect_ratio)

    # Calculate padding to center the image
    pad_x = (viewport_width - new_width) // 2
    pad_y = (viewport_height - new_height) // 2

    dpg.configure_item("image_tag", width=new_width, height=new_height)
    dpg.configure_item("image_container", pos=(pad_x, pad_y))
    dpg.configure_item("button_container", pos=(pad_x, pad_y))
    dpg.configure_item("fit_to_window_button", show=not stretch_mode)


# Button Callbacks
def set_stretch_mode():
    global stretch_mode
    stretch_mode = True
    update_image_size()


def set_aspect_ratio_mode():
    global stretch_mode
    stretch_mode = False
    update_image_size()


def fit_to_window():
    global stretch_mode
    viewport_width = dpg.get_viewport_client_width()
    viewport_height = dpg.get_viewport_client_height()

    # Calculate the aspect ratio of the viewport
    ratio = viewport_width / viewport_height

    if ratio < aspect_ratio:  # Viewport is too tall

        new_height = int(viewport_width / aspect_ratio)
        dpg.set_viewport_height(new_height + dpg.get_viewport_height()-dpg.get_viewport_client_height())

    elif ratio > aspect_ratio:  # Viewport is too wide

        new_width = int(viewport_height * aspect_ratio)
        dpg.set_viewport_width(new_width + dpg.get_viewport_width()-dpg.get_viewport_client_width())

    update_image_size()


# UI Setup
with dpg.window(tag="main_window", no_title_bar=True, no_resize=True, no_move=True, no_scrollbar=True) as main_window:
    dpg.bind_item_theme(main_window, no_padding_theme)

    with dpg.group(tag="image_container"):
        dpg.add_image("texture_tag", tag="image_tag")

    with dpg.group(horizontal=True, tag="button_container"):
        dpg.add_button(label="Stretch", width=80, callback=set_stretch_mode)
        dpg.add_button(label="Keep Aspect Ratio", width=150, callback=set_aspect_ratio_mode)
        dpg.add_button(label="Fit to Window", width=130, callback=fit_to_window, tag="fit_to_window_button", show=False)

# Set it as the main viewport window
dpg.set_primary_window("main_window", True)

# Resize callback with debouncing
last_resize_time = 0
def resize_callback(sender,app_data):
    global last_resize_time
    current_time = time.time()
    if current_time - last_resize_time > 0.1:  # Debounce time of 100ms
        update_image_size()
        last_resize_time = current_time


dpg.set_viewport_resize_callback(resize_callback)

# Start Dear PyGui
dpg.setup_dearpygui()
dpg.show_viewport()

# Main loop
while dpg.is_dearpygui_running():
    ret, frame = vid.read()
    if ret:
        texture_data = process_frame(frame)
        dpg.set_value("texture_tag", texture_data)
    dpg.render_dearpygui_frame()

# Cleanup
vid.release()
dpg.destroy_context()
