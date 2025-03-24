# Realtime F-curves.

A blender addon/extension that updates f-curves in the graph editor in realtime as the bone is transformed.


# Settings

It has one setting.

Interval - is how often the addon checks for changes. You can set it between 1 and 0.01 seconds.

# Purpose of this addon?

I like using quaternions when animating, because the interpolation makes sense, and there's no gimbal lock, but generaly using euler makes more sense in the graph editor, where animators spend 90% of their time. Quaternions get extremely confusing there, the curves don't exactly correspond to the actual axis of movement, and there's the 4th dimension thing; the W axis, and I always just rotated the bone in the viewport, because that calculated all the quaternions properly, but I couldn't see the changes reflected in the graph editor while transforming, which made tiny tweaks tedious. So I made this addon.
