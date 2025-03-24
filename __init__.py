import bpy
from bpy_extras import anim_utils

class RealtimeFCurveUpdater(bpy.types.Operator):
    """Updates F-Curves in real-time when bones are transformed"""
    bl_idname = "pose.realtime_fcurve_update"
    bl_label = "Toggle Realtime F-Curve Update"
    bl_options = {'REGISTER', 'UNDO'}

    _timer = None
    _handler_running = False
    _last_transform_values = {}  # Stores the last transform values to detect changes
    _is_transforming = False  # Tracks whether bones are currently being transformed
    _current_transform_type = None  # Tracks which transform operation is active (translate/rotate/scale)

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'ARMATURE' and context.mode == 'POSE'

    def execute(self, context):
        if not RealtimeFCurveUpdater._handler_running:
            self.start(context)
            return {'RUNNING_MODAL'}
        else:
            self.stop(context)
            return {'FINISHED'}
        
    def get_custom_keybinding(operator_name):
        user_keyconfig = bpy.context.window_manager.keyconfigs.user
        if user_keyconfig:
            pose_keymap = user_keyconfig.keymaps.get("Pose")
            if pose_keymap:
                for keymap_item in pose_keymap.keymap_items:
                    if keymap_item.idname == operator_name and not (keymap_item.map_type == 'TWEAK' or keymap_item.value == 'CLICK_DRAG'):
                        return {
                            "key": keymap_item.type,  # The key (e.g., 'G', 'R', 'S')
                            "shift": keymap_item.shift,  # Shift modifier
                            "ctrl": keymap_item.ctrl,  # Ctrl modifier
                            "alt": keymap_item.alt,  # Alt modifier
                            "oskey": keymap_item.oskey,  # Cmd (OS key) modifier
                        }
        return None
    
    def get_transform_keybindings():
        return [kb for kb in [
            RealtimeFCurveUpdater.get_custom_keybinding("transform.translate"),
            RealtimeFCurveUpdater.get_custom_keybinding("transform.rotate"),
            RealtimeFCurveUpdater.get_custom_keybinding("transform.resize"),
        ] if kb is not None]

    def start(self, context):
        self.stop(context)  # Ensure a clean state before starting
        RealtimeFCurveUpdater._handler_running = True
        RealtimeFCurveUpdater._timer = context.window_manager.event_timer_add(
            context.scene.realtime_fcurve_timer_interval, window=context.window
        )
        context.window_manager.modal_handler_add(self)
        context.scene.realtime_fcurve_active = True  # Set the active state to True
        self._last_transform_values = {}  # Reset stored values
        self._is_transforming = False  # Reset transform state
        self._current_transform_type = None  # Reset transform type
        self.report({'INFO'}, "Realtime F-Curve Updater Enabled")

    def stop(self, context):
        if RealtimeFCurveUpdater._handler_running:
            RealtimeFCurveUpdater._handler_running = False
            if RealtimeFCurveUpdater._timer:
                context.window_manager.event_timer_remove(RealtimeFCurveUpdater._timer)
                RealtimeFCurveUpdater._timer = None
            context.scene.realtime_fcurve_active = False  # Set the active state to False
            self._last_transform_values = {}  # Clear stored values
            self._is_transforming = False  # Reset transform state
            self._current_transform_type = None  # Reset transform type
            self.report({'INFO'}, "Realtime F-Curve Updater Disabled")
            return {'CANCELLED'}
        
    def modal(self, context, event):
        if not RealtimeFCurveUpdater._handler_running:
            return {'CANCELLED'}
        
        transform_keybindings = RealtimeFCurveUpdater.get_transform_keybindings()

        # Check if the mouse is over the 3D Viewport
        mouse_over_view3d = False
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                mouse_x, mouse_y = event.mouse_x, event.mouse_y
                if (area.x <= mouse_x <= area.x + area.width and
                    area.y <= mouse_y <= area.y + area.height):
                    mouse_over_view3d = True
                    break

        # Get the keybindings for each transform operation
        translate_kb = RealtimeFCurveUpdater.get_custom_keybinding("transform.translate")
        rotate_kb = RealtimeFCurveUpdater.get_custom_keybinding("transform.rotate")
        scale_kb = RealtimeFCurveUpdater.get_custom_keybinding("transform.resize")

        # Detect transform start and which operation is being performed
        if mouse_over_view3d and event.value == 'PRESS':
            if (translate_kb and 
                event.type == translate_kb["key"] and
                event.shift == translate_kb["shift"] and
                event.ctrl == translate_kb["ctrl"] and
                event.alt == translate_kb["alt"] and
                event.oskey == translate_kb["oskey"]):
                self._is_transforming = True
                self._current_transform_type = 'TRANSLATE'
                
            elif (rotate_kb and 
                  event.type == rotate_kb["key"] and
                  event.shift == rotate_kb["shift"] and
                  event.ctrl == rotate_kb["ctrl"] and
                  event.alt == rotate_kb["alt"] and
                  event.oskey == rotate_kb["oskey"]):
                self._is_transforming = True
                self._current_transform_type = 'ROTATE'
                
            elif (scale_kb and 
                  event.type == scale_kb["key"] and
                  event.shift == scale_kb["shift"] and
                  event.ctrl == scale_kb["ctrl"] and
                  event.alt == scale_kb["alt"] and
                  event.oskey == scale_kb["oskey"]):
                self._is_transforming = True
                self._current_transform_type = 'SCALE'

        # Detect transform end (Left Mouse Click, Enter, Right Click, Escape, Spacebar)
        if event.type in {'LEFTMOUSE', 'RET', 'RIGHTMOUSE', 'ESC', 'SPACE'} and event.value == 'RELEASE':
            self._is_transforming = False
            self._current_transform_type = None

        # Only update F-curves if bones are being transformed
        if self._is_transforming and event.type == 'TIMER':
            self.update_fcurves(context)

        return {'PASS_THROUGH'}

    def update_fcurves(self, context):
        obj = context.object
        if not obj or not obj.animation_data:
            return
        
        action = obj.animation_data.action
        action_slot = obj.animation_data.action_slot

    # Retrieve the channel bag for the action slot
        channelbag = anim_utils.action_get_channelbag_for_slot(action, action_slot)

        if not action:
            return

        for pb in obj.pose.bones:
            # Only update curves for the current transform type
            if self._current_transform_type == 'TRANSLATE':
                transform_paths = [("location", 3)]
            elif self._current_transform_type == 'ROTATE':
                transform_paths = [("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", 
                                   4 if pb.rotation_mode == 'QUATERNION' else 3)]
            elif self._current_transform_type == 'SCALE':
                transform_paths = [("scale", 3)]
            else:
                return
            
            for curve_path, count in transform_paths:
                for index in range(count):
                    fcurve = channelbag.fcurves.find(f'pose.bones["{pb.name}"].{curve_path}', index=index)
                    if fcurve:
                        current_value = getattr(pb, curve_path)[index]
                        last_value = self._last_transform_values.get((pb.name, curve_path, index), None)

                        # Only update if the value has changed significantly
                        if last_value is None or abs(current_value - last_value) > context.scene.realtime_fcurve_update_threshold:
                            # Insert or update the keyframe
                            keyframe = fcurve.keyframe_points.insert(context.scene.frame_current, current_value, options={'FAST'})
                            self._last_transform_values[(pb.name, curve_path, index)] = current_value

                            # Update handles for the current keyframe and its immediate neighbors
                            current_frame = context.scene.frame_current
                            keyframes_to_update = []

                            # Find the current keyframe and its neighbors
                            for kf in fcurve.keyframe_points:
                                if kf.co.x == current_frame:
                                    keyframes_to_update.append(kf)
                                elif kf.co.x == current_frame - 1:  # Previous keyframe
                                    keyframes_to_update.append(kf)
                                elif kf.co.x == current_frame + 1:  # Next keyframe
                                    keyframes_to_update.append(kf)

                            # Update handles for the selected keyframes
                            for kf in keyframes_to_update:
                                if kf.handle_left_type == 'AUTO_CLAMPED' or kf.handle_right_type == 'AUTO_CLAMPED':
                                    kf.handle_left_type = 'AUTO_CLAMPED'
                                    kf.handle_right_type = 'AUTO_CLAMPED'
                                    fcurve.update()  # Force update the handles

        # Throttle UI updates
        if context.scene.frame_current % 5 == 0:  # Only redraw every 5 frames
            for area in context.screen.areas:
                if area.type in {'GRAPH_EDITOR', 'DOPESHEET_EDITOR'}:
                    area.tag_redraw()
        
        context.view_layer.update()
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

class RealtimeFCurvePanel(bpy.types.Panel):
    """Creates a Panel in the Animation tab of the 3D Viewport"""
    bl_label = "Realtime F-Curve Updater"
    bl_idname = "VIEW3D_PT_realtime_fcurve_updater"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Toggle button
        if not RealtimeFCurveUpdater._handler_running:
            layout.operator("pose.realtime_fcurve_update", text="Enable", icon='PLAY')
        else:
            layout.operator("pose.realtime_fcurve_update", text="Disable", icon='PAUSE')

        # Timer interval setting
        layout.prop(scene, "realtime_fcurve_timer_interval", text="Interval (s)") 

        # Update threshold setting
        layout.prop(scene, "realtime_fcurve_update_threshold", text="Threshold (m)")

def register():
    bpy.utils.register_class(RealtimeFCurveUpdater)
    bpy.utils.register_class(RealtimeFCurvePanel)
    bpy.types.Scene.realtime_fcurve_active = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.realtime_fcurve_timer_interval = bpy.props.FloatProperty(
        name="Timer Interval",
        description="Interval (in seconds) between updates",
        default=0.1,
        min=0.01,
        max=1.0
    )
    bpy.types.Scene.realtime_fcurve_update_threshold = bpy.props.FloatProperty(
        name="Update Threshold",
        description="Minimum change required to update keyframes",
        default=0.0001,
        min=0.000001,
        max=1.0
    )

def unregister():
    bpy.utils.unregister_class(RealtimeFCurveUpdater)
    bpy.utils.unregister_class(RealtimeFCurvePanel)
    del bpy.types.Scene.realtime_fcurve_active
    del bpy.types.Scene.realtime_fcurve_timer_interval
    del bpy.types.Scene.realtime_fcurve_update_threshold

if __name__ == "__main__":
    register()
