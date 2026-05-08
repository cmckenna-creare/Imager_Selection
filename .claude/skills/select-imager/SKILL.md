---
name: select-imager
description: Recommend a camera + lens pairing when the user asks for a camera or imager recommendation. Triggers when the user describes constraints like working distance, field of view (FOV), object-plane resolution (px/mm), depth of field (DOF), frame rate, mount, or cost and asks for a pick. For the final selection, computes metrics from real code execution rather than mental math.
---

# select-imager

## Instructions
The user will ask for an imager recommendation based on desired performance characteristics. These performance characteristics may not fully define the problem. Recommend a camera + lens combination by doing the following. Use `imager_objects.py` for calculations.

1. Ask any needed clarification/correction questions if the user's performance characteristics are not well defined or are unreasonable, such as wanting to image at a distance of 1 nm or 1000 km.
2. Use mental math and industry standards to make a reasonable initial guess for camera and lens parameters. Needed parameters are the inputs to the `Camera` and `Lens` classes in `imager_objects.py`. Avoid unreasonable initial guesses.
3. In a loop, perform the following steps as needed.
  1. Create an `Imager` object with the most recent guess for camera and lens parameters.
  2. Run the calculations inside `Imager` to get the proposed imager performance.
  3. Compare those outputs to the desired performance characteristics.
  4. If the computed performance characteristics do not meet user specifications, select new camera and lens parameters based on what doesn't match and recompute. If the performance characteristics do meet user specifications but you anticipate that actual cameras or lenses with those parameters will be difficult to find or expensive, try more common parameters and recompute to see if a more economical option is available. Use common sense in this step.
4. Check the catalogues inside the `components/` folder. Select a camera and lens that are similar to the camera and lens parameters selected in the last step.
5. Compute the performance characteristics of the components using `imager_objects.py`. See if they meet the user-specified performance characteristics. Also use common sense to make sure other aspects such as frame rate and cost match. If they do (or are close), report the results to the user. If not, use the available components to make a new guess at parameters and go back to step 3. If you have already done this step a few times, ask the user for assistance.
6. Report your recommended components to the user. Report the computed performance characteristics from `imager_objects.py` and compare them to desired in an easy-to-understand table. Highlight any potential issues if they exist. Use common sense to give recommendations on slight configuration alterations that could yield a more versatile system. 
7. Always pass the output of print_imager() to the user verbatum. Do not edit or modify in any way. If it does not have reasonable agreement with the previous step go back and figure out where the error was.

## Example
User: 'Give me recommendations for a camera and lens to find foxes in a field. I want a color camera. The camera is setup about 25 m from the center of the field. The field is about 10 m by 10 m. I want at least 0.1 px/mm resolution across the field, but higher is better.'

Claude:
1. Specification looks reasonable, no clarification needed.
2. Initial guess
  - Minimum required sensor size is 1000 px. 1920x1080 sensors are common. res_x=1920, res_y=1080.
  - 0.007 mm/px pixel pitch is common. pp = 0.007
  - C mount is common. mount = 'C'
  - Foxes do not move very quickly, a framerate of 30 fps should be fine. fps_max = 30.
  - Selecting a reasonable focal length for mid distances of 12mm. focal_length = 12
  - Fairly large DOF may require highish f_num. f_num=5.6. Let's set the lens range to be reasonable. f_num=(1.6, 8)
  - Selecting sensor format to at least match camera. sensor_format_max = 1
  - Closest focus we'll need is 15 m, which is pretty far. Most lenses can focus at 1 m so using that. Setting far distance to a large number. working_distance = (1000, 1000000)
  - Set lens mount to agree with camera. mount = 'C'
3. Start design loop
  1. Create objects
    ```
    uv run python
    from imager_selection.imager_objects import Camera, Lens, Imager
    dist = 25000
    f_num = 5.6
    cam = Camera(res_x= 1920, res_y= 1080, pp= 0.007, mount= 'C', fps_max= 30)
    lens = Lens(focal_length= 12, sensor_format_max= 1, f_num= (1.6,8), working_distance= (1000,1000000), mount= 'C')
    imager = Imager(cam,lens)
    ```
  2. Calculate Performance
    ```
    h_fov, v_fov = imager.calc_FOV(dist)
    res = imager.calc_resolution(dist)
    n_dof, f_dof = imager.get_DOF(dist,f_num)
    print(f'FOV: {h_fov/1000} m, {v_fov/1000} m, Res: {res} px/mm, DOF: {n_dof} m, {f_dof} m')
    ```
  3. This calculation showed that the resolution was not high enough (0.07 px/mm < 0.1 px/mm).
  4. Since the resolution wasn't high enough, increase the lens focal length. Updating lens focal length guess to 25.

  Repeat with updated focal length guess. Now the resolution is good, but the vertical FOV is a little small. Since the user is probably viewing the field at an angle, ask the user if this is OK. They say that it is.
4. Select components.
  - BFS-U3-13Y3C-C has a similar resolution and sufficient framerate. The pixel size is smaller so we may need to switch lenses.
  - The lens with stock # 59-871 has the desired focal length and supports the sensor size of BFS-U3-13Y3C-C.
5. Check imager performance with these components.
  - Repeat the performance calculation using `imager_objects.py`. Now the FOV is too small.
  - Try a lens with a smaller focal length to match this camera. #58-001.
  - This configuration meets desired performance.
6. Report back to the user
  - "Camera BFS-U3-13Y3C-C with Lens #58-001 should work. At 25 m working distance this imager has a FOV of 12.8 by 10.2 m, a resolution of 0.1 px/mm, and more than sufficient depth of field. The total cost is $877. Higher resolution cameras are available at similar prices if you would like more detailed images, since the current resolution is very close to the limit you asked for."

## Reference docs

- `components/c-series-fixed-focal-length-lenses.xlsx`
  - List of lenses to select from.
- `components/flir-blackfly-s-usb3-cameras.xlsx`
  - List of cameras to select from.

## Notes

- **All lengths are mm** in this codebase. Don't mix units.
- **Color vs mono** is encoded in the FLIR model name: the character before the mount suffix is `M` (mono) or `C` (color). E.g. `BFS-U3-13Y3M-C` is mono + C-mount; `BFS-U3-13Y3C-C` is color + C-mount. Match this to the user's request — the catalog spreadsheets do not include a separate color/mono field.
- **Circle of confusion** in `get_DOF` defaults to one pixel pitch (`c = pp`, a conservative 1-pixel blur). For photographic-style DOF, mention or pass `c = 2·pp`.
- **Lens infinity focus**: when a lens's max working distance is unbounded (focuses to infinity), substitute a large value like `1e9` mm so the `Lens` constructor accepts it.
