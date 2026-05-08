from typing import Optional
import numpy as np

# All lengths are in mm.

_VALID_MOUNTS = {'C', 'CS'}


class Camera:
    def __init__(self, res_x: int, res_y: int, pp: float, mount: str, fps_max: Optional[float] = None):
        """Initialize a camera sensor.

        Args:
            res_x: Horizontal resolution in pixels. Must be positive.
            res_y: Vertical resolution in pixels. Must be positive.
            pp: Pixel pitch in mm. Must be positive.
            mount: Lens mount type. Must be 'C' or 'CS'.
            fps_max: Maximum frame rate in frames per second. Must be positive if provided.
        """
        if res_x <= 0 or not isinstance(res_x, int):
            raise ValueError(f"res_x must be a positive integer, got {res_x!r}")
        if res_y <= 0 or not isinstance(res_y, int):
            raise ValueError(f"res_y must be a positive integer, got {res_y!r}")
        if pp <= 0:
            raise ValueError(f"pp (pixel pitch) must be positive, got {pp!r}")
        if mount not in _VALID_MOUNTS:
            raise ValueError(f"mount must be 'C' or 'CS', got {mount!r}")
        if fps_max is not None and fps_max <= 0:
            raise ValueError(f"fps_max must be positive, got {fps_max!r}")

        self.res_x = res_x
        self.res_y = res_y
        self.pp = pp
        self.mount = mount
        self.fps_max = fps_max

        self.calc_sensor_format()

    def get_sensor_wh(self) -> list[float]:
        """Return sensor width and height in mm as [width, height]."""
        return [self.res_x * self.pp, self.res_y * self.pp]

    def calc_sensor_format(self) -> None:
        """Compute and store sensor format as diagonal / 16 in mm."""
        [w, h] = self.get_sensor_wh()
        d = np.sqrt(w**2 + h**2)
        self.sensor_format = d / 16


class Lens:
    def __init__(self, focal_length: float, sensor_format_max: float, f_num: tuple, working_distance: tuple, mount: str):
        """Initialize a lens.

        Args:
            focal_length: Focal length in mm. Must be positive.
            sensor_format_max: Maximum supported sensor format (diagonal / 16) in mm. Must be positive.
            f_num: (min, max) f-number range. Both values must be positive and min <= max.
            working_distance: (min, max) working distance range in mm. Both values must be positive and min <= max.
            mount: Lens mount type. Must be 'C' or 'CS'.
        """
        if focal_length <= 0:
            raise ValueError(f"focal_length must be positive, got {focal_length!r}")
        if sensor_format_max <= 0:
            raise ValueError(f"sensor_format_max must be positive, got {sensor_format_max!r}")
        if len(f_num) != 2 or f_num[0] <= 0 or f_num[1] <= 0 or f_num[0] > f_num[1]:
            raise ValueError(f"f_num must be a (min, max) tuple with positive values and min <= max, got {f_num!r}")
        if len(working_distance) != 2 or working_distance[0] <= 0 or working_distance[1] <= 0 or working_distance[0] > working_distance[1]:
            raise ValueError(f"working_distance must be a (min, max) tuple with positive values and min <= max, got {working_distance!r}")
        if mount not in _VALID_MOUNTS:
            raise ValueError(f"mount must be 'C' or 'CS', got {mount!r}")

        self.focal_length = focal_length
        self.sensor_format_max = sensor_format_max
        self.f_num = f_num
        self.working_distance = working_distance
        self.mount = mount


class Imager:
    def __init__(self, camera: Camera, lens: Lens):
        """Initialize an imager pairing a camera sensor with a lens.

        Args:
            camera: Camera instance.
            lens: Lens instance.
        """
        if not isinstance(camera, Camera):
            raise TypeError(f"camera must be a Camera instance, got {type(camera).__name__!r}")
        if not isinstance(lens, Lens):
            raise TypeError(f"lens must be a Lens instance, got {type(lens).__name__!r}")
        if camera.mount != lens.mount:
            raise NotImplementedError(
                f"Mismatched mounts (camera: {camera.mount!r}, lens: {lens.mount!r}) are not supported"
            )

        self.camera = camera
        self.lens = lens

    def calc_FOV(self, distance: float) -> list[float]:
        """Calculate the field of view at a given object-plane distance.

        Uses the thin-lens equation. If the camera sensor format exceeds the
        lens's maximum sensor format, the effective sensor is scaled down to
        fit within the lens image circle before computing FOV.

        Args:
            distance: Distance from the lens to the object plane in mm.
                Must be greater than the lens focal length.

        Returns:
            [fov_width, fov_height] in mm at the object plane.

        Raises:
            ValueError: If distance <= focal_length (no real image formed).
        """
        if distance <= self.lens.focal_length:
            raise ValueError(
                f"distance ({distance} mm) must be greater than focal_length "
                f"({self.lens.focal_length} mm) to form a real image"
            )

        [w, h] = self.camera.get_sensor_wh()

        # Scale effective sensor area down if sensor exceeds lens image circle.
        if self.camera.sensor_format > self.lens.sensor_format_max:
            scale = self.lens.sensor_format_max / self.camera.sensor_format
            w *= scale
            h *= scale

        # Thin-lens FOV: FOV = sensor_size * (do - f) / f
        fov_width = w * (distance - self.lens.focal_length) / self.lens.focal_length
        fov_height = h * (distance - self.lens.focal_length) / self.lens.focal_length

        return [fov_width, fov_height]

    def calc_resolution(self, distance: float) -> float:
        """Calculate the object-plane resolution at a given distance.

        Uses thin-lens magnification m = f / (d - f). One pixel of pitch `pp`
        on the sensor maps to `pp / m` at the object plane, so the resolution
        is `m / pp = f / (pp * (d - f))`. Independent of sensor / image-circle
        match because pixel pitch sets the sampling rate.

        Args:
            distance: Distance from the lens to the object plane in mm.
                Must be greater than the lens focal length.

        Returns:
            Resolution at the object plane in px/mm.

        Raises:
            ValueError: If distance <= focal_length (no real image formed).
        """
        f = self.lens.focal_length
        if distance <= f:
            raise ValueError(
                f"distance ({distance} mm) must be greater than focal_length "
                f"({f} mm) to form a real image"
            )

        return f / (self.camera.pp * (distance - f))

    def get_DOF(self, distance: float, f_num: float, c: Optional[float] = None) -> list[float]:
        """Compute the near and far distances that will be in focus.

        Uses the exact thin-lens blur-circle derivation. The circle of confusion
        defines the largest acceptable blur spot on the sensor.

        Args:
            distance: Nominal distance to subject in mm. Must be greater than
                the lens focal length.
            f_num: F-number (aperture setting). Must be within the lens f-number
                range [f_num_min, f_num_max].
            c: Circle of confusion diameter in mm on the image plane. Defaults to camera pixel pitch
                if not provided.

        Returns:
            [near, far] in-focus distances in mm. Far is float('inf') when the
            subject is at or beyond the hyperfocal distance.

        Raises:
            ValueError: If distance <= focal_length.
            ValueError: If f_num is outside the lens f-number range.
            ValueError: If c is provided but not positive.
        """
        f = self.lens.focal_length

        if distance <= f:
            raise ValueError(
                f"distance ({distance} mm) must be greater than focal_length ({f} mm)"
            )
        if not (self.lens.f_num[0] <= f_num <= self.lens.f_num[1]):
            raise ValueError(
                f"f_num ({f_num}) is outside the lens range {self.lens.f_num}"
            )
        if c is not None and c <= 0:
            raise ValueError(f"c (circle of confusion) must be positive, got {c!r}")

        if c is None:
            c = self.camera.pp

        s = distance

        # Exact thin-lens DOF formulas derived from blur-circle geometry:
        #   b = (f/N) * |v - v'| / v'   where v = f*s/(s-f), v' = f*D/(D-f)
        # Solving b = c for D near and far gives:
        #   D_near = f²·s / (f² + N·c·(s−f))
        #   D_far  = f²·s / (f² − N·c·(s−f))  [∞ when s ≥ hyperfocal]
        common = f_num * c * (s - f)
        d_near = (f**2 * s) / (f**2 + common)

        if common >= f**2:
            # Subject is at or beyond the hyperfocal distance.
            d_far = float('inf')
        else:
            d_far = (f**2 * s) / (f**2 - common)

        return [d_near, d_far]

    def print_imager(self, distance: float, f_num: float, c: Optional[float] = None) -> None:
        """Print camera + lens parameters and FOV, resolution, and DOF results.

        Values are formatted to 4 significant figures. Lengths are shown in
        mm when the magnitude is < 1000 mm and in m otherwise. Arguments
        match get_DOF; FOV and resolution use only `distance`.
        """
        [fov_w, fov_h] = self.calc_FOV(distance)
        res = self.calc_resolution(distance)
        [d_near, d_far] = self.get_DOF(distance, f_num, c)
        [sensor_w, sensor_h] = self.camera.get_sensor_wh()
        wd_min, wd_max = self.lens.working_distance

        def fmt_length(x: float) -> str:
            if x == float('inf'):
                return 'inf'
            if abs(x) >= 1000:
                return f'{x / 1000:.4g} m'
            return f'{x:.4g} mm'

        fps = f'{self.camera.fps_max:.4g} fps' if self.camera.fps_max is not None else 'n/a'

        print('Camera:')
        print(f'  Resolution:     {self.camera.res_x} x {self.camera.res_y} px')
        print(f'  Pixel pitch:    {fmt_length(self.camera.pp)}')
        print(f'  Sensor size:    {fmt_length(sensor_w)} x {fmt_length(sensor_h)}')
        print(f'  Sensor format:  {self.camera.sensor_format:.4g}')
        print(f'  Mount:          {self.camera.mount}')
        print(f'  Max frame rate: {fps}')
        print('Lens:')
        print(f'  Focal length:   {fmt_length(self.lens.focal_length)}')
        print(f'  Max sensor fmt: {self.lens.sensor_format_max:.4g}')
        print(f'  F-number range: {self.lens.f_num[0]:.4g} to {self.lens.f_num[1]:.4g}')
        print(f'  Working dist:   {fmt_length(wd_min)} to {fmt_length(wd_max)}')
        print(f'  Mount:          {self.lens.mount}')
        print('Results:')
        print(f'  FOV:        {fmt_length(fov_w)} x {fmt_length(fov_h)}')
        print(f'  Resolution: {res:.4g} px/mm')
        print(f'  DOF:        {fmt_length(d_near)} to {fmt_length(d_far)}')

    def plot_imager(self, distance: float, f_num: float, save_path: str, c: Optional[float] = None) -> None:
        """Plot DOF, resolution, and FOV vs working distance and save to file.

        Sweeps working distance across the lens's allowed range and plots the
        three metrics in stacked subplots. Each axis auto-switches between mm
        and m depending on the magnitude of the data. The supplied `distance`
        is marked on each subplot as a vertical reference line.

        Args:
            distance: Reference working distance in mm (marked on each subplot).
            f_num: F-number used for the DOF curves. Must be within the lens range.
            save_path: Path to write the figure to (extension determines format).
            c: Circle of confusion in mm. Defaults to camera pixel pitch.
        """
        import matplotlib.pyplot as plt

        f = self.lens.focal_length
        wd_min, wd_max = self.lens.working_distance
        # Sweep ±a few-x around the prescribed distance, clamped to the lens range
        # and to wd > f (real-image requirement).
        lo = max(wd_min, f * 1.001, 0.3 * distance)
        hi = min(wd_max, 3.0 * distance)
        distances = np.linspace(lo, hi, 500)

        fovs = np.array([self.calc_FOV(d) for d in distances])
        fov_w = fovs[:, 0]
        fov_h = fovs[:, 1]
        res = np.array([self.calc_resolution(d) for d in distances])
        dofs = np.array([self.get_DOF(d, f_num, c) for d in distances])
        d_near = dofs[:, 0]
        d_far = dofs[:, 1]

        def pick_unit(values: np.ndarray) -> tuple[float, str]:
            """Return (divisor, label) — m if median magnitude >= 1000 mm, else mm."""
            finite = values[np.isfinite(values)]
            if finite.size == 0 or np.median(np.abs(finite)) < 1000:
                return 1.0, 'mm'
            return 1000.0, 'm'

        x_div, x_unit = pick_unit(distances)
        fov_div, fov_unit = pick_unit(np.concatenate([fov_w, fov_h]))
        dof_div, dof_unit = pick_unit(np.concatenate([d_near, d_far]))

        fig, (ax_fov, ax_res, ax_dof) = plt.subplots(3, 1, figsize=(8, 10), sharex=True)

        x = distances / x_div
        ax_fov.plot(x, fov_w / fov_div, label='Width')
        ax_fov.plot(x, fov_h / fov_div, label='Height')
        ax_fov.set_ylabel(f'FOV ({fov_unit})')
        ax_fov.legend()
        ax_fov.grid(True, which='both', alpha=0.3)

        ax_res.plot(x, res)
        ax_res.set_ylabel('Resolution (px/mm)')
        ax_res.grid(True, which='both', alpha=0.3)

        # Mask infinities (subject beyond hyperfocal) so they don't blow up the y-axis.
        d_far_plot = np.where(np.isfinite(d_far), d_far / dof_div, np.nan)
        ax_dof.plot(x, d_near / dof_div, label='Near')
        ax_dof.plot(x, d_far_plot, label='Far')
        ax_dof.set_ylabel(f'DOF bounds ({dof_unit})')
        ax_dof.set_xlabel(f'Working distance ({x_unit})')
        # Cap DOF y-axis at 5x the prescribed working distance — Far diverges
        # near hyperfocal and would otherwise dominate the plot.
        ax_dof.set_ylim(0, 5 * distance / dof_div)
        ax_dof.legend()
        ax_dof.grid(True, which='both', alpha=0.3)

        for ax in (ax_fov, ax_res, ax_dof):
            ax.axvline(
                distance / x_div, color='red', linestyle='--', linewidth=1.5,
                alpha=0.8, label=f'Prescribed WD ({distance / x_div:.4g} {x_unit})',
            )
        # Re-draw legends so the prescribed-WD line shows up on every subplot.
        ax_fov.legend()
        ax_res.legend()
        ax_dof.legend()

        fig.suptitle(f'Imager metrics vs working distance (f/{f_num:.4g})')
        fig.tight_layout()
        fig.savefig(save_path)
        plt.close(fig)


# Ignore
from imager_selection.imager_objects import Camera, Lens, Imager
dist = 2591
f_num = 2.8
cam = Camera(res_x= 5320, res_y= 4600, pp= 0.00274, mount= 'C', fps_max= 15)
lens = Lens(focal_length= 100, sensor_format_max= 4/3, f_num= (2.8,22), working_distance= (750,1000000), mount= 'C')
imager = Imager(cam,lens)
h_fov, v_fov = imager.calc_FOV(dist)
res = imager.calc_resolution(dist)
n_dof, f_dof = imager.get_DOF(dist,f_num)
imager.print_imager(dist,f_num)