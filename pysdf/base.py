from typing import Dict, List, Set, Type, Union, Iterable, Any
import lxml.etree as ET

from .sdf_types import *

# TODO: make pose bindings nicer (allow default="0 0 0 0 0 0")


def _make_CamelCase(x):
    return "".join(word.title() for word in x.split("_"))


class SdfElement:
    """The base class for all SDF elements."""

    known_children: Dict[str, Type] = None
    known_attributes: Set[str] = None
    tag: str = None

    def __init__(
        self,
        children: Union[Iterable, "SdfElement", None] = None,
        *args,
        text: str = None,
        tail: str = None,
        **kwargs,
    ) -> None:
        self.children: List["SdfElement"]
        self.attributes: Dict[str, Any] = dict()
        self.known_attributes = self.known_attributes or set()
        self.known_children = self.known_children or dict()
        self.text = text
        self.tail = tail

        for key in kwargs:
            if key in self.known_attributes:
                setattr(self, key, kwargs[key])
            else:
                self.attributes[key] = kwargs[key]

        if children is None:
            self.children = list()
        elif isinstance(children, SdfElement):
            self.children = [children, *args]
        else:
            self.children = [child for child in children]

    @property
    def unknown_elements(self):
        return [x for x in self.children if isinstance(x, UnknownElement)]

    @classmethod
    def from_etree(cls, element: ET.Element, *, instance=None) -> "SdfElement":
        self = instance if instance is not None else cls(**element.attrib)
        self.text = element.text
        self.tail = element.tail

        for child in element:
            if child.tag in self.known_children:
                child_element = self.known_children[child.tag].from_etree(child)
            elif child.tag is ET.Comment:
                child_element = Comment.from_etree(child)
            else:
                child_element = UnknownElement.from_etree(child)

            self.children.append(child_element)

        return self

    def to_etree(
        self, *, out: ET.Element = None, sdf_version: str = None
    ) -> ET.Element:
        out = ET.Element(self.tag or "unknown", self.attributes) if out is None else out
        out.text = self.text
        out.tail = self.tail

        for child in self.children:
            out.append(child.to_etree())

        return out

    @classmethod
    def from_xml(cls, sdf_string: str, *, remove_blank_text=True) -> "SdfElement":
        """Decode XML."""

        parser = ET.XMLParser(remove_blank_text=remove_blank_text)

        try:
            root = ET.fromstring(sdf_string, parser)
        except ET.ParseError as e:
            raise RuntimeError("Invalid XML." + e.text) from None

        return cls.from_etree(root)

    def to_xml(
        self, *, encoding="utf-8", sdf_version: str = None, pretty_print: bool = False
    ) -> str:
        """Encode as XML."""

        return ET.tostring(
            self.to_etree(), encoding=encoding, pretty_print=pretty_print
        ).decode(encoding=encoding)

    def add(self, other: Union["SdfElement", Iterable], *args) -> None:
        if isinstance(other, SdfElement):
            other = [other, *args]

        for item in other:
            self.children.append(item)

    def _iter_impl(
        self, reversed_parts: str, reversed_parents: List["SdfElement"]
    ) -> "SdfElement":
        reversed_parents = [self] + reversed_parents

        for child in self.children:
            reversed_path = [child] + reversed_parents
            for part, element in zip(reversed_parts, reversed_path):
                if element.__class__.__name__ != part:
                    break
            else:
                yield child

        for child in self.children:
            yield from child._iter_impl(reversed_parts, reversed_parents)

    def iter(self, filter: str = None) -> "SdfElement":
        """Iterate over SDF elements

        This function recursively iterates over all elements in the current
        subtree (breadth-first) and yields them. If ``filter`` is not None, only
        those elements matching the filter will be returned. Filters are
        selectors on the tail end of the element's path from the root node to
        the element and are separated by the "/" character. For example,
        ``filter="pose"`` will return all pose elements in the tree and
        ``filter="link/pose"`` will return all pose elements that are children
        of link elements.

        Parameters
        ----------
        filter : str
            If not None, elements are filtered based on this string. The filter
            applies to the tail end of the path to the (recursive) child, and is
            a relative path.

        Yields
        ------

        child : SdfElement
            A recursive child element that matches the given filter (if any) in
            breadth-first order.

        """
        if filter is not None:
            reversed_parts = [x for x in reversed(filter.split("/"))]
        else:
            reversed_parts = list()

        reversed_parts = [x for x in map(_make_CamelCase, reversed_parts)]

        yield from self._iter_impl(reversed_parts, list())


class UnknownElement(SdfElement):
    """A unknown/non-standard Element

    This could be plugin specific configuration or an element that hasn't been
    implemented yet.

    """

    tag = "unknown"

    def __init__(
        self, tag, children: Union[Iterable, "SdfElement", None] = None, *args, **kwargs
    ) -> None:
        self.tag = tag
        super().__init__(children, *args, **kwargs)

    def __getattr__(self, name):
        if name in self.attributes:
            return self.attributes[name]

        raise AttributeError(f"This element has no attribute named `{name}`.")

    @classmethod
    def from_etree(cls, element: ET.Element, *, instance=None) -> "UnknownElement":
        instance = (
            instance
            if instance is not None
            else UnknownElement(element.tag, **element.attrib)
        )
        return super().from_etree(element, instance=instance)


class Comment(SdfElement):
    def to_etree(
        self, *, out: ET.Element = None, sdf_version: str = None
    ) -> ET.Element:
        out = out if out is not None else ET.Comment()
        return super().to_etree(out=out, sdf_version=sdf_version)


class Pose(SdfElement):
    tag = "pose"

    relative_to = Attribute(str, "0")
    rotation_format = Attribute(str, "0", default="euler_rpy")
    degrees = Attribute(bool, "0", default=False)


class Noise(SdfElement):
    tag = "noise"

    type = Attribute(str, "1", default="none")

    mean = FloatElement("0", 0)
    stddev = FloatElement("0", 0)
    bias_mean = FloatElement("0", 0)
    bias_stddev = FloatElement("0", 0)
    dynamic_bias_stddev = FloatElement("0", 0)
    dynamic_bias_correlation_time = FloatElement("0", 0)
    precision = FloatElement("0", 0)


class NoisyAxis(SdfElement):
    class X(SdfElement):
        tag = "x"
        noise = ChildElement(Noise, 1)

    class Y(SdfElement):
        tag = "y"
        noise = ChildElement(Noise, 1)

    class Z(SdfElement):
        tag = "z"
        noise = ChildElement(Noise, 1)

    x = ChildElement(X, "0")
    y = ChildElement(Y, "0")
    z = ChildElement(Z, "0")


class Frame(SdfElement):
    tag = "frame"

    name = Attribute(str, "1")
    attached_to = Attribute(str, "0")

    pose = ChildElement(Pose, "0")


class Plugin(SdfElement):
    tag = "plugin"

    name = Attribute(str, "1")
    filename = Attribute(str, "1")


class Sensor(SdfElement):
    tag = "sensor"

    class AirPressure(SdfElement):
        tag = "air_pressure"

        class Pressure(SdfElement):
            tag = "pressure"

            noise = ChildElement(Noise, "1")

        reference_altitude = FloatElement("0", 0)
        pressure = ChildElement(Pressure, "0")

    class Altimeter(SdfElement):
        tag = "altimeter"

        class VerticalPosition(SdfElement):
            tag = "vertical_position"

            noise = ChildElement(Noise, "1")

        class HorizontalPosition(SdfElement):
            tag = "horizontal_position"

            noise = ChildElement(Noise, "1")

        vertical_position = ChildElement(VerticalPosition, "0")
        horizontal_position = ChildElement(HorizontalPosition, "0")

    class Camera(SdfElement):
        tag = "camera"

        class Image(SdfElement):
            tag = "image"

            width = IntegerElement("1", 320)
            height = IntegerElement("1", 240)
            format = StringElement("0", "R8G8B8")

        class Clip(SdfElement):
            tag = "clip"

            near = FloatElement("1", 0.1)
            far = FloatElement("1", 100)

        class Save(SdfElement):
            tag = "save"

            enabled = Attribute(bool, "0", default=False)

            path = StringElement("1", "__default__")

        class DepthCamera(SdfElement):
            tag = "depth_camera"

            class Clip(SdfElement):
                tag = "clip"

                near = FloatElement("0", 0.1)
                far = FloatElement("0", 10)

            output = StringElement("1", "depths")
            clip = ChildElement(Clip, "0")

        class Noise(SdfElement):
            tag = "noise"

            type = StringElement("1", "gaussian")
            mean = FloatElement("1", 0)
            stddev = FloatElement("1", 0)

        class Distortion(SdfElement):
            tag = "distortion"

            k1 = FloatElement("0", 0)
            k2 = FloatElement("0", 0)
            k3 = FloatElement("0", 0)
            p1 = FloatElement("0", 0)
            p2 = FloatElement("0", 0)
            center = Vector2("0", "0.5 0.5")

        class Lense(SdfElement):
            tag = "lense"

            class CustomFunction(SdfElement):
                tag = "custom_function"

                c1 = FloatElement("0", 1)
                c2 = FloatElement("0", 1)
                c3 = FloatElement("0", 0)
                f = FloatElement("0", 1)
                fun = StringElement("1", "tan")

            class Intrinsics(SdfElement):
                tag = "intrinsics"

                fx = FloatElement("1", 277)
                fy = FloatElement("1", 277)
                cx = FloatElement("1", 160)
                cy = FloatElement("1", 120)
                s = FloatElement("1", 0)

            type = StringElement("1", "stereographic")
            scale_to_fov = BoolElement("0", True)
            custom_function = ChildElement(CustomFunction, "0")
            cutoff_angle = FloatElement("0", 1.5707)
            env_texture_size = IntegerElement("0", 256)
            intrinsics = ChildElement(Intrinsics, "0")

        name = Attribute(str, "0")
        horizontal_fov = FloatElement("0", 1.047)
        image = ChildElement(Image, "1")
        clip = ChildElement(Clip, "1")
        save = ChildElement(Save, "0")
        depth_camera = ChildElement(DepthCamera, "0")
        segmentation_type = StringElement("0", "semantic")
        box_type = StringElement("0", "2d")
        noise = ChildElement(Noise, "0")
        distortion = ChildElement(Distortion, "0")
        lense = ChildElement(Lense, "0")
        visibility_mask = IntegerElement("0", 4294967295)
        pose = ChildElement(Pose, "0")

    class Contact(SdfElement):
        tag = "contact"

        collision = StringElement("1", "__default__")
        topic = StringElement("1", "__default_topic__")

    class ForceTorque(SdfElement):
        tag = "force_torque"

        class Force(NoisyAxis):
            tag = "force"

        class Torque(NoisyAxis):
            tag = "torque"

        frame = StringElement("0", "child")
        measure_direction = StringElement("0", "child_to_parent")
        force = ChildElement(Force, "0")
        torque = ChildElement(Torque, "0")

    class Gps(SdfElement):
        tag = "gps"

        class Sensing(SdfElement):
            class Horizontal(SdfElement):
                tag = "horizontal"
                noise = ChildElement(Noise, "1")

            class Vertical(SdfElement):
                tag = "vertical"
                noise = ChildElement(Noise, "1")

            horizontal = ChildElement(Horizontal, "0")
            vertical = ChildElement(Vertical, "0")

        class PositionSensing(Sensing):
            tag = "position_sensing"

        class VelocitySensing(Sensing):
            tag = "velocity_sensing"

        position_sensing = ChildElement(PositionSensing, "0")
        velocity_sensing = ChildElement(VelocitySensing, "0")

    class Imu(SdfElement):
        tag = "imu"

        class OrientationReferenceFrame(SdfElement):
            tag = "orientation_reference_frame"

            class GravDirX(SdfElement):
                tag = "grav_dir_x"

                parent_frame = StringElement("0", "__default__")

            localization = StringElement("0", "CUSTOM")
            custom_rpy = Vector3("0", "0 0 0")
            grav_dir_x = ChildElement(GravDirX, "0")

        class AngularVelocity(NoisyAxis):
            tag = "angular_velocity"

        class LinearAcceleration(NoisyAxis):
            tag = "linear_acceleration"

        orientation_reference_frame = ChildElement(OrientationReferenceFrame, "0")
        angular_velocity = ChildElement(AngularVelocity, "0")
        linear_acceleration = ChildElement(LinearAcceleration, "0")
        enable_orientation = BoolElement("0", True)

    class Lidar(SdfElement):
        tag = "lidar"

        class Scan(SdfElement):
            tag = "scan"

            class Horizontal(SdfElement):
                tag = "horizontal"

                samples = IntegerElement("1", 640)
                resolution = FloatElement("1", 1)
                min_angle = FloatElement("1", 0)
                max_angle = FloatElement("1", 0)

            class Vertical(SdfElement):
                tag = "vertical"

                samples = IntegerElement("1", 1)
                resolution = FloatElement("1", 1)
                min_angle = FloatElement("1", 0)
                max_angle = FloatElement("1", 0)

            horizontal = ChildElement(Horizontal, "0")
            vertical = ChildElement(Vertical, "0")

        class Range(SdfElement):
            tag = "range"

            min = FloatElement("1", 0)
            max = FloatElement("1", 1)
            resolution = FloatElement("0", 0)

        class Noise(SdfElement):
            tag = "noise"

            type = StringElement("1", "gaussian")
            mean = FloatElement("0", 0)
            stddev = FloatElement("0", 0)

        scan = ChildElement(Scan, "1")
        range = ChildElement(Range, "1")
        noise = ChildElement(Noise, "0")

    class LogicalCamera(SdfElement):
        tag = "logical_camera"

        near = FloatElement("1", 1)
        far = FloatElement("1", 1)
        aspect_ratio = FloatElement("1", 1)
        horizontal_fov = FloatElement("1", 1)

    class Magnetometer(NoisyAxis):
        tag = "magnetometer"

    class Navsat(Gps):
        tag = "navsat"

    class Ray(SdfElement):
        tag = "ray"

        class Scan(SdfElement):
            tag = "scan"

            class Horizontal(SdfElement):
                tag = "horizontal"

                samples = IntegerElement("1", 640)
                resolution = FloatElement("0", 1)
                min_angle = FloatElement("1", 0)
                max_angle = FloatElement("1", 0)

            class Vertical(SdfElement):
                tag = "vertical"

                samples = IntegerElement("1", 1)
                resolution = FloatElement("0", 1)
                min_angle = FloatElement("1", 0)
                max_angle = FloatElement("1", 0)

            horizontal = ChildElement(Horizontal, "0")
            vertical = ChildElement(Vertical, "0")

        class Range(SdfElement):
            tag = "range"

            min = FloatElement("0", 0)
            max = FloatElement("0", 1)
            resolution = FloatElement("0", 0)

        class Noise(SdfElement):
            tag = "noise"

            type = StringElement("1", "gaussian")
            mean = FloatElement("0", 0)
            stddev = FloatElement("0", 0)

        scan = ChildElement(Scan, "1")
        range = ChildElement(Range, "1")
        noise = ChildElement(Noise, "0")

    class Rfidtag(SdfElement):
        tag = "rfidtag"

    class Rfid(SdfElement):
        tag = "rfid"

    class Sonar(SdfElement):
        tag = "sonar"

        geometry = StringElement("0", "cone")
        min = FloatElement("1", 0)
        max = FloatElement("1", 1)
        radius = FloatElement("0", 0.5)

    class Transceiver(SdfElement):
        tag = "transceiver"

        essid = StringElement("0", "wireless")
        frequency = FloatElement("0", 2442)
        min_frequency = FloatElement("0", 2412)
        max_frequency = FloatElement("0", 2484)
        gain = FloatElement("1", 2.5)
        power = FloatElement("1", 14.5)
        sensitivity = FloatElement("0", -90)

    name = Attribute(str, "1")
    type = Attribute(str, "1")

    always_on = BoolElement("0", False)
    update_rate = FloatElement("0", 0)
    visualize = BoolElement("0", False)
    topic = StringElement("0", "__default__")
    enable_metrics = BoolElement("0", False)
    pose = ChildElement(Pose, "0")
    plugin = ChildElement(Plugin, "*")
    air_pressure = ChildElement(AirPressure, "0")
    altimeter = ChildElement(Altimeter, "0")
    camera = ChildElement(Camera, "0")
    contact = ChildElement(Contact, "0")
    force_torque = ChildElement(ForceTorque, "0")
    gps = ChildElement(Gps, "0")
    imu = ChildElement(Imu, "0")
    lidar = ChildElement(Lidar, "0")
    logical_camera = ChildElement(LogicalCamera, "0")
    magnetometer = ChildElement(Magnetometer, "0")
    navsat = ChildElement(Navsat, "0")
    ray = ChildElement(Ray, "0")
    rfidtag = ChildElement(Rfidtag, "0")
    rfid = ChildElement(Rfid, "0")
    sonar = ChildElement(Sonar, "0")
    transceiver = ChildElement(Transceiver, "0")


class Light(SdfElement):
    tag = "light"

    class Attenuation(SdfElement):
        tag = "attenuation"

        range = FloatElement("1", 10)
        linear = FloatElement("0", 1)
        constant = FloatElement("0", 1)
        quadric = FloatElement("0", 0)

    class Spot(SdfElement):
        tag = "spot"

        inner_angle = FloatElement("1", 0)
        outer_angle = FloatElement("1", 0)
        falloff = FloatElement("1", 0)

    name = Attribute(str, "1")
    type = Attribute(str, "1", default="point")

    cast_shadows = BoolElement("0", False)
    intensity = FloatElement("0", 1)
    diffuse = Color("0", "1 1 1 1")
    specular = Color("0", "1 1 1 1")
    attenuation = ChildElement(Attenuation, "0")
    direction = Vector3("1", "0 0 -1")
    spot = ChildElement(Spot, "0")
    pose = ChildElement(Pose, "0")


class Material(SdfElement):
    tag = "material"

    class Script(SdfElement):
        tag = "script"

        uris = StringElement("+", "__default__", tag="uri")
        name = StringElement("1", "__default__")

    class Shader(SdfElement):
        tag = "shader"

        type = Attribute(str, "1", default="pixel")

        normal_map = StringElement("0", "__default__")

    class Pbr(SdfElement):
        tag = "pbr"

        class Metal(SdfElement):
            tag = "metal"

            class NormalMap(SdfElement):
                tag = "normal_map"

                type = Attribute(str, "0", default="tangent")

            class LightMap(SdfElement):
                tag = "light_map"

                uv_set = Attribute(int, "0", default=0)

            albedo_map = StringElement("0", "")
            roughness_map = StringElement("0", "")
            roughness = FloatElement("0", 0.5)
            metalness_map = StringElement("0", "")
            metalness = FloatElement("0", 0.5)
            environment_map = StringElement("0", "")
            ambient_occlusion_map = StringElement("0", "")
            normal_map = ChildElement(NormalMap, "0")
            emissive_map = StringElement("0", "")
            light_map = ChildElement(LightMap, "0")

        class Specular(SdfElement):
            tag = "specular"

            class NormalMap(SdfElement):
                tag = "normal_map"

                type = Attribute(str, "0", default="tangent")

            class LightMap(SdfElement):
                tag = "light_map"

                uv_set = Attribute(int, "0", default=0)

            albedo_map = StringElement("0", "")
            specular_map = StringElement("0", "")
            glossiness_map = StringElement("0", "")
            glossiness = FloatElement("0", 0)
            environment_map = StringElement("0", "")
            ambient_occlusion_map = StringElement("0", "")
            normal_map = ChildElement(NormalMap, "0")
            emissive_map = StringElement("0", "")
            light_map = ChildElement(LightMap, "0")

        metal = ChildElement(Metal, "0")
        specular = ChildElement(Specular, "0")

    script = ChildElement(Script, "0")
    shader = ChildElement(Shader, "0")
    render_order = FloatElement("0", 0)
    lighting = BoolElement("0", True)
    ambient = Color("0", "0 0 0 1")
    diffuse = Color("0", "0 0 0 1")
    specular = Color("0", "0 0 0 1")
    emissive = Color("0", "0 0 0 1")
    double_sided = BoolElement("0", False)
    pbr = ChildElement(Pbr, "0")


class Geometry(SdfElement):
    tag = "geometry"

    class Empty(SdfElement):
        tag = "empty"

    class Box(SdfElement):
        tag = "box"

        size = Vector3("1", "1 1 1")

    class Capsule(SdfElement):
        tag = "capsule"

        radius = FloatElement("1", 0.5)
        length = FloatElement("1", 1)

    class Cylinder(SdfElement):
        tag = "cylinder"

        radius = FloatElement("1", 1)
        length = FloatElement("1", 1)

    class Ellipsoid(SdfElement):
        tag = "ellipsoid"

        radii = Vector3("0", "1 1 1")

    class Heightmap(SdfElement):
        tag = "heightmap"

        class Texture(SdfElement):
            tag = "texture"

            size = FloatElement("0", 10)
            diffuse = StringElement("1", "__default__")
            normal = StringElement("1", "__default__")

        class Blend(SdfElement):
            tag = "blend"

            min_height = FloatElement("1", 0)
            fade_dist = FloatElement("1", 0)

        uri = StringElement("1", "__default__")
        size = Vector3("0", "1 1 1")
        pos = Vector3("0", "0 0 0")
        textures = ChildElement(Texture, "*")
        blends = ChildElement(Blend, "*")
        use_terrain_paging = BoolElement("0", False)
        sampling = IntegerElement("0", 1)

    class Image(SdfElement):
        tag = "image"

        uri = StringElement("1", "__default__")
        scale = FloatElement("1", 1)
        threshold = IntegerElement("1", 200)
        height = FloatElement("1", 1)
        granularity = IntegerElement("1", 1)

    class Mesh(SdfElement):
        tag = "mesh"

        class Submesh(SdfElement):
            name = StringElement("1", "__default__")
            center = BoolElement("0", False)

        uri = StringElement("1", "__default__")
        submesh = ChildElement(Submesh, "0")
        scale = Vector3("0", "1 1 1")

    class Plane(SdfElement):
        tag = "plane"

        normal = Vector3("1", "1 1 1")
        size = Vector2("1", "1 1")

    class Polyline(SdfElement):
        point = Vector2("+", "0 0")
        height = FloatElement("1", 1)

    class Sphere(SdfElement):
        tag = "sphere"

        radius = FloatElement("1", 1)

    empty = ChildElement(Empty, "0")
    box = ChildElement(Box, "0")
    capsule = ChildElement(Capsule, "0")
    cylinder = ChildElement(Cylinder, "0")
    ellipsoid = ChildElement(Ellipsoid, "0")
    heightmap = ChildElement(Heightmap, "0")
    image = ChildElement(Image, "0")
    mesh = ChildElement(Mesh, "0")
    plane = ChildElement(Plane, "0")
    polyline = ChildElement(Polyline, "0")
    sphere = ChildElement(Sphere, "0")


class Collision(SdfElement):
    tag = "collision"

    class Surface(SdfElement):
        tag = "surface"

        class Bounce(SdfElement):
            tag = "bounce"

            restitution_coefficient = FloatElement("0", 0)
            threshold = FloatElement("0", 100000)

        class Friction(SdfElement):
            tag = "friction"

            class Torsional(SdfElement):
                tag = "torsional"

                class Ode(SdfElement):
                    tag = "ode"

                    slip = FloatElement("0", 0)

                coefficient = FloatElement("0", 0)
                use_patch_radius = BoolElement("0", True)
                patch_radius = FloatElement("0", 0)
                surface_radius = FloatElement("0", 0)
                ode = ChildElement(Ode, "0")

            class Ode(SdfElement):
                tag = "ode"

                mu = FloatElement("0", 1)
                mu2 = FloatElement("0", 1)
                fdir1 = Vector3("0", "0 0 0")
                slip1 = FloatElement("0", 0)
                slip2 = FloatElement("0", 0)

            class Bullet(SdfElement):
                tag = "bullet"

                friction = FloatElement("0", 1)
                friction2 = FloatElement("0", 1)
                fdir1 = Vector3("0", "0 0 0")
                rolling_friction = FloatElement("0", 1)

            torsional = ChildElement(Torsional, "0")
            ode = ChildElement(Ode, "0")
            bullet = ChildElement(Bullet, "0")

        class Contact(SdfElement):
            tag = "contact"

            class Ode(SdfElement):
                tag = "ode"

                soft_cfm = FloatElement("0", 0)
                soft_erp = FloatElement("0", 0.2)
                kp = FloatElement("0", 1e12)
                kd = FloatElement("0", 1)
                max_vel = FloatElement("0", 0.01)
                min_depth = FloatElement("0", 0)

            class Bullet(SdfElement):
                tag = "bullet"

                soft_cfm = FloatElement("0", 0)
                soft_erp = FloatElement("0", 0.2)
                kp = FloatElement("0", 1e12)
                kd = FloatElement("0", 1)
                split_impulse = BoolElement("0", True)
                split_impulse_penetration_threshold = FloatElement("0", -0.01)

            collide_with_contact = BoolElement("0", False)
            collide_without_contact_bitmask = IntegerElement("0", 1)
            collide_bitmask = IntegerElement("0", 65535)
            category_bitmask = IntegerElement("0", 65535)
            poissons_ratio = FloatElement("0", 0.3)
            elastic_modulus = FloatElement("0", -1)
            ode = ChildElement(Ode, "0")
            bullet = ChildElement(Bullet, "0")

        class SoftContact(SdfElement):
            tag = "soft_contact"

            class Dart(SdfElement):
                tag = "dart"

                bone_attachement = FloatElement("1", 100)
                stiffness = FloatElement("1", 100)
                damping = FloatElement("1", 10)
                flesh_mass_fraction = FloatElement("1", 0.5)

            dart = ChildElement(Dart, "0")

        bounce = ChildElement(Bounce, "0")
        friction = ChildElement(Friction, "0")
        contact = ChildElement(Contact, "0")
        soft_contact = ChildElement(SoftContact, "0")

    name = Attribute(str, "1")

    laser_retro = FloatElement("0", 0)
    max_contacts = IntegerElement("0", 10)
    pose = ChildElement(Pose, "0")
    geometry = ChildElement(Geometry, "1")
    surface = ChildElement(Surface, "0")


class Visual(SdfElement):
    tag = "visual"

    class Meta(SdfElement):
        tag = "meta"

        layer = IntegerElement("0", 0)

    name = Attribute(str, "1")
    cast_shadows = BoolElement("0", True)
    laser_retro = FloatElement("0", 0)
    transparency = FloatElement("0", 0)
    visibility_flags = IntegerElement("0", 4294967295)
    meta = ChildElement(Meta, "0")
    pose = ChildElement(Pose, "0")
    material = ChildElement(Material, "0")
    geometry = ChildElement(Geometry, "1")
    plugin = ChildElement(Plugin, "*")


class Joint(SdfElement):
    tag = "joint"

    class Axis(SdfElement):
        tag = "axis"

        class Xyz(SdfElement):
            tag = "xyz"

            expressed_in = Attribute(str, "0")

        class Dynamics(SdfElement):
            tag = "dynamics"

            damping = FloatElement("0", 0)
            friction = FloatElement("0", 0)
            spring_reference = FloatElement("1", 0)
            spring_stiffness = FloatElement("1", 0)

        class Limit(SdfElement):
            tag = "limit"

            lower = FloatElement("1", -1e16)
            upper = FloatElement("1", 1e16)
            effort = FloatElement("0", -1)
            velocity = FloatElement("0", -1)
            stiffness = FloatElement("0", 1e8)
            dissipation = FloatElement("0", 1)

        xyz = ChildElement(Xyz, "0")
        dynamics = ChildElement(Dynamics, "0")
        limit = ChildElement(Limit, "0")

    class Physics(SdfElement):
        tag = "physics"

        class Simbody(SdfElement):
            tag = "simbody"

            must_be_loop_joint = BoolElement("0", False)

        class Ode(SdfElement):
            tag = "ode"

            class Limit(SdfElement):
                tag = "limit"

                cfm = FloatElement("0", 0)
                erp = FloatElement("0", 0.2)

            class Suspension(SdfElement):
                tag = "suspension"

                cfm = FloatElement("1", 0)
                erp = FloatElement("1", 0.2)

            cfm_damping = BoolElement("0", False)
            implicit_spring_damper = BoolElement("0", False)
            fudge_factor = FloatElement("0", 0)
            cfm = FloatElement("0", 0.2)
            erp = FloatElement("0", 0)
            bounce = FloatElement("0", 0)
            max_force = FloatElement("0", 0)
            velocity = FloatElement("0", 0)
            limit = ChildElement(Limit, "0")
            suspension = ChildElement(Suspension, "0")

        simbody = ChildElement(Simbody, "0")
        ode = ChildElement(Ode, "0")
        provide_feedback = BoolElement("0", False)

    name = Attribute(str, "1")
    type = Attribute(str, "1")

    parent = StringElement("1", "__default__")
    child = StringElement("1", "__default__")
    gearbox_ratio = FloatElement("0", 1)
    gearbox_reference_bodx = StringElement("0", "__default__")
    thread_pitch = FloatElement("0", 1)
    axis = ChildElement(Axis, "0")
    axsis2 = ChildElement(Axis, "0")
    physics = ChildElement(Physics, "0")
    pose = ChildElement(Pose, "0")
    sensor = ChildElement(Sensor, "0")


class Link(SdfElement):
    tag = "link"

    class VelocityDecay(SdfElement):
        tag = "velocity_decay"

        linear = FloatElement("0", 0.0)
        angular = FloatElement("0", 0.0)

    class Inertial(SdfElement):
        tag = "inertial"

        class Inertia(SdfElement):
            tag = "inertia"

            ixx = FloatElement("1", 1)
            ixy = FloatElement("1", 0)
            ixz = FloatElement("1", 0)
            iyy = FloatElement("1", 1)
            iyz = FloatElement("1", 0)
            izz = FloatElement("1", 1)

        mass = FloatElement("0", 1)
        pose = ChildElement(Pose, "0")
        inertia = ChildElement(Inertia, "0")

    class Projector(SdfElement):
        tag = "projector"

        name = Attribute(str, "1")

        texture = StringElement("1", "__default__")
        fov = FloatElement("0", 0.785)
        near_clip = FloatElement("0", 0.1)
        far_clip = FloatElement("0", 10)
        pose = ChildElement(Pose, "0")
        plugin = ChildElement(Plugin, "*")

    class AudioSink(SdfElement):
        tag = "audio_sink"

    class AudioSource(SdfElement):
        tag = "audio_source"

        class Contact(SdfElement):
            tag = "contact"

            collisions = StringElement("+", "__default__", tag="collision")

        uri = StringElement("1", "__default__")
        pitch = FloatElement("0", 1)
        gain = FloatElement("0", 1)
        contacts = ChildElement(Contact, "0")
        loop = BoolElement("0", False)
        pose = ChildElement(Pose, "0")

    class Battery(SdfElement):
        tag = "battery"

        name = Attribute(str, "1")
        voltage = FloatElement("1", 0)

    class ParticleEmitter(SdfElement):
        tag = "particle_emitter"

        name = Attribute(str, "1")
        type = Attribute(str, "1", default="point")

        emitting = BoolElement("0", True)
        duration = FloatElement("0", 0)
        size = Vector3("0", "1 1 1")
        particle_size = Vector3("0", "1 1 1")
        lifetime = FloatElement("0", 5)
        rate = FloatElement("0", 10)
        min_velocity = FloatElement("0", 1)
        max_velocity = FloatElement("0", 1)
        scale_rate = FloatElement("0", 0)
        color_start = Color("0", "1 1 1 1")
        color_end = Color("0", "1 1 1 1")
        color_range_image = StringElement("0", "")
        topic = StringElement("0", "")
        particle_scatter_ratio = FloatElement("0", 0.65)
        pose = ChildElement(Pose, "0")
        material = ChildElement(Material, "0")

    name = Attribute(str, "1")

    gravity = BoolElement("0", True)
    enable_wind = BoolElement("0", False)
    self_collide = BoolElement("0", False)
    kinematic = BoolElement("0", False)
    must_be_base_link = BoolElement("0", False)

    velocity_decay = ChildElement(VelocityDecay, "0")

    pose = ChildElement(Pose, "0")
    inertial = ChildElement(Inertial, "0")
    colliders = ChildElement(Collision, "*")
    visuals = ChildElement(Visual, "*")
    sensors = ChildElement(Sensor, "*")
    projectors = ChildElement(Projector, "*")
    audio_sinks = ChildElement(AudioSink, "*")
    audio_sources = ChildElement(AudioSource, "*")
    batteries = ChildElement(Battery, "*")
    lights = ChildElement(Light, "*")
    particle_emitters = ChildElement(ParticleEmitter, "*")


class Include(SdfElement):
    tag = "include"

    merge = Attribute(bool, "0", default=False)
    uri = StringElement("1", "__default__")
    name = StringElement("0", "")
    static = BoolElement("0", False)
    placement_frame = StringElement("0", "")
    pose = ChildElement(Pose, "0")
    plugins = ChildElement(Plugin, "*")


class Model(SdfElement):
    tag = "model"

    class Gripper(SdfElement):
        tag = "gripper"

        class GraspCheck(SdfElement):
            tag = "grasp_check"

            detach_steps = IntegerElement("0", 40)
            attach_steps = IntegerElement("0", 40)
            min_contact_count = IntegerElement("0", 2)

        name = Attribute(str, "1")
        grasp_check = ChildElement(GraspCheck, "0")
        gripper_links = StringElement("+", "__default__", tag="gripper_link")
        palm_link = StringElement("1", "__default__")

    name = Attribute(str, "1")
    canonical_link = Attribute(str, "0")
    placement_frame = Attribute(str, "0")
    static = BoolElement("0", False)
    self_collide = BoolElement("0", False)
    allow_auto_disable = BoolElement("0", True)

    include = ChildElement(Include, "*")
    models = ChildElement(None, "*")  # None is a sentinel for self/cls
    enable_wind = BoolElement("0", False)
    frames = ChildElement(Frame, "*")
    pose = ChildElement(Pose, "0")
    links = ChildElement(Link, "*")
    joints = ChildElement(Joint, "*")
    plugin = ChildElement(Plugin, "*")
    gripper = ChildElement(Gripper, "*")


class Actor(SdfElement):
    tag = "actor"

    name = Attribute(str, "1")

    class Skin(SdfElement):
        tag = "skin"

        filename = StringElement("1", "__default__")
        scale = FloatElement("0", 1)

    class Animation(SdfElement):
        tag = "animation"

        name = Attribute(str, "1")

        filename = StringElement("1", "__default__")
        scale = FloatElement("0", 1)
        interpolate_x = BoolElement("0", False)

    class Script(SdfElement):
        tag = "script"

        class Trajectory(SdfElement):
            tag = "trajectory"

            class Waypoint(SdfElement):
                tag = "waypoint"

                time = FloatElement("0", 0)
                pose = ChildElement(Pose, "1")

            id = Attribute(int, "1", default=0)
            type = Attribute(str, "1")
            tension = Attribute(float, "0", default=0)
            waypoints = ChildElement(Waypoint, "*")

        loop = BoolElement("0", True)
        delay_start = FloatElement("0", 0)
        auto_start = BoolElement("0", True)
        trajectories = ChildElement(Trajectory, "*")

    skin = ChildElement(Skin, "0")
    animations = ChildElement(Animation, "*")
    script = ChildElement(Script, "1")
    pose = ChildElement(Pose, "0")
    links = ChildElement(Link, "*")
    joints = ChildElement(Joint, "*")
    plugins = ChildElement(Plugin, "*")


class Physics(SdfElement):
    tag = "physics"

    class Dart(SdfElement):
        tag = "dart"

        class Solver(SdfElement):
            tag = "solver"

            solver_type = StringElement("1", "dantzig")

        solver = ChildElement(Solver, "1")
        collision_detector = StringElement("0", "fcl")

    class Simbody(SdfElement):
        tag = "simbody"

        class Contact(SdfElement):
            stiffness = FloatElement("0", 1e8)
            dissipation = FloatElement("0", 100)
            plastic_coef_resolution = FloatElement("0", 0.5)
            plastic_impact_velocity = FloatElement("0", 0.5)
            state_friction = FloatElement("0", 0.9)
            dynamic_friction = FloatElement("0", 0.9)
            viscous_friction = FloatElement("0", 0)
            override_impact_capture_velocity = FloatElement("0", 0.001)
            override_stiction_transition_velocity = FloatElement("0", 0.001)

        min_step_size = FloatElement("0", 0.0001)
        accuracy = FloatElement("0", 0.001)
        max_transient_velocity = FloatElement("0", 0.01)
        contact = ChildElement(Contact, "0")

    class Bullet(SdfElement):
        tag = "bullet"

        class Solver(SdfElement):
            tag = "solver"

            type = StringElement("1", "quick")
            min_step_size = FloatElement("0", 0.0001)
            iters = IntegerElement("1", 50)
            sor = FloatElement("1", 1.3)

        class Constraints(SdfElement):
            tag = "constraint"

            cfm = FloatElement("1", 0)
            erp = FloatElement("1", 0.2)
            contact_surface_layer = FloatElement("1", 0.001)
            split_impulse = BoolElement("1", True)
            split_impulse_penetration_threshold = FloatElement("1", -0.01)

        solver = ChildElement(Solver, "1")
        constraints = ChildElement(Constraints, "1")

    class Ode(SdfElement):
        tag = "ode"

        class Solver(SdfElement):
            tag = "solver"

            type = StringElement("1", "quick")
            min_step_size = FloatElement("0", 0.0001)
            island_threads = IntegerElement("0", 0)
            iters = IntegerElement("1", 50)
            precon_iters = IntegerElement("0", 0)
            sor = FloatElement("1", 1.3)
            thread_position_correction = BoolElement("0", False)
            use_dynamic_moi_rescaling = BoolElement("1", False)
            friction_model = StringElement("0", "pyramid_model")

        class Constraints(SdfElement):
            tag = "constraint"

            cfm = FloatElement("1", 0)
            erp = FloatElement("1", 0.2)
            contact_max_correcting_vel = FloatElement("1", 100)
            contact_surface_layer = FloatElement("1", 0.001)

        solver = ChildElement(Solver, "1")
        constraints = ChildElement(Constraints, "1")

    name = Attribute(str, "0", default="default_physics")
    default = Attribute(bool, "0", default=False)
    type = Attribute(str, "0", default="ode")

    max_step_size = FloatElement("1", 0.001)
    real_time_factor = FloatElement("1", 0.001)
    real_time_update_rate = FloatElement("1", 1000)
    max_contacts = IntegerElement("0", 20)
    dart = ChildElement(Dart, "0")
    simbody = ChildElement(Simbody, "0")
    bullet = ChildElement(Bullet, "0")
    ode = ChildElement(Ode, "0")


class Scene(SdfElement):
    tag = "scene"

    class Sky(SdfElement):
        tag = "sky"

        class Clouds(SdfElement):
            tag = "clouds"

            speed = FloatElement("0", 0.6)
            direction = FloatElement("0", 0)
            humidity = FloatElement("0", 0.5)
            mean_size = FloatElement("0", 0.5)
            ambient = Color("0", "0.8 0.8 0.8 1")

        time = FloatElement("0", 10)
        sunrise = FloatElement("0", 6)
        sunset = FloatElement("0", 20)
        clouds = ChildElement(Clouds, "0")

    class Fog(SdfElement):
        tag = "fog"

        color = Color("0", "1 1 1 1")
        type = StringElement("0", "none")
        start = FloatElement("0", 1)
        end = FloatElement("0", 100)
        density = FloatElement("0", 1)

    ambient = Color("1", "0.4 0.4 0.4 1")
    background = Color("1", "0.7 0.7 0.7 1")
    sky = ChildElement(Sky, "0")
    shadows = BoolElement("0", True)
    fog = ChildElement(Fog, "0")
    grid = BoolElement("0", True)
    origin_visual = BoolElement("0", True)


class State(SdfElement):
    tag = "state"

    class Insertations(SdfElement):
        tag = "insertations"

        models = ChildElement(Model, "*")
        lights = ChildElement(Light, "*")

    class Deletions(SdfElement):
        tag = "deletions"

        names = StringElement("+", "__default__")

    class Model(SdfElement):
        tag = "model"

        class Joint(SdfElement):
            tag = "joint"

            class Angle(SdfElement):
                tag = "angle"

                axis = Attribute(int, "0", default=0)

            name = Attribute(str, "1")
            angles = ChildElement(Angle, "+")

        class Link(SdfElement):
            tag = "link"

            class Collision(SdfElement):
                tag = "collision"

                name = Attribute(str, "1")

            name = Attribute(str, "1")

            velocity = ChildElement(Pose, "0")
            acceleration = ChildElement(Pose, "0")
            wrench = ChildElement(Pose, "0")
            collisions = ChildElement(Collision, "*")
            pose = ChildElement(Pose, "0")

        name = Attribute(str, "1")
        joints = ChildElement(Joint, "*")
        models = ChildElement(None, "*")  # None means self
        scale = Vector3("0", "1 1 1")
        frames = ChildElement(Frame, "*")
        pose = ChildElement(Pose, "0")
        links = ChildElement(Link, "*")

    class Light(SdfElement):
        tag = "light"

        name = Attribute(str, "1")

        pose = ChildElement(Pose, "0")

    world_name = Attribute(str, "1")

    sim_time = Vector2("0", "0 0")
    wall_time = Vector2("0", "0 0")
    real_time = Vector2("0", "0 0")
    iterations = IntegerElement("1", 0)
    insertations = ChildElement(Insertations, "0")
    deletions = ChildElement(Deletions, "0")
    model = ChildElement(Model, "*")
    light = ChildElement(Light, "*")


class World(SdfElement):
    class Audio(SdfElement):
        tag = "audio"

        device = StringElement("1", default="default")

    class Wind(SdfElement):
        tag = "wind"

        linear_velocity = Vector3("0", "0 0 0")

    class Atmosphere(SdfElement):
        tag = "atmosphere"

        type = Attribute(str, "1", default="adiabatic")
        temperature = FloatElement("0", 288.15)
        pressure = FloatElement("0", 101325)
        temperature_gradient = FloatElement("0", -6.5e-3)

    class Gui(SdfElement):
        tag = "gui"

    class Road(SdfElement):
        tag = "road"

    class SphericalCoordinates(SdfElement):
        tag = "spherical_coordinates"

    class Population(SdfElement):
        tag = "population"

    tag = "world"
    name = Attribute(str, "1")

    audio = ChildElement(Audio, "0")
    wind = ChildElement(Wind, "0")
    includes = ChildElement(Include, "*")
    gravity = Vector3("1", "0 0 -9.8")
    magnetic_field = Vector3("1", "6e-06 2.3e-05, -4.2e-05")
    atmosphere = ChildElement(Atmosphere, "1")
    gui = ChildElement(Gui, "0")
    physics_engine = ChildElement(
        Physics, "1", removed_in="1.6", alternative="World.physics_engines"
    )
    physics_engines = ChildElement(Physics, "+")
    scene = ChildElement(Scene, "1")
    lights = ChildElement(Light, "*")
    frame = ChildElement(Frame, "*")
    models = ChildElement(Model, "*")
    actors = ChildElement(Actor, "*")
    plugins = ChildElement(Plugin, "*")
    joints = ChildElement(Joint, "*", removed_in="1.7")
    roads = ChildElement(Road, "*")
    spherical_coordinates = ChildElement(SphericalCoordinates, "0")
    states = ChildElement(State, "*")
    populations = ChildElement(Population, "*")


class SDF(SdfElement):
    """SDFormat Root Element

    This element is a container for one or more simulation worlds or
    for a single fragment of a world (Model, Actor, Light).

    Parameters
    ----------
    version : str
        The SDFormat version.

    """

    tag = "sdf"

    version = Attribute(str, "1", default="1.9")

    worlds = ChildElement(World, "*")
    actor = ChildElement(Actor, "0")
    model = ChildElement(Model, "0")
    light = ChildElement(Light, "0")

    actors = ChildElement(Actor, "*", removed_in="1.8", alternative="self.actor")
    models = ChildElement(Model, "*", removed_in="1.8", alternative="self.model")
    lights = ChildElement(Light, "*", removed_in="1.8", alternative="self.light")

    @classmethod
    def from_file(cls, path: str, *, remove_blank_text: bool = False) -> "SDF":
        parser = ET.XMLParser(remove_blank_text=remove_blank_text)
        return SDF.from_etree(ET.parse(str(path), parser).getroot())

    def to_file(self, path: str, *, pretty_print: bool = False) -> None:
        ET.ElementTree(self.to_etree()).write(
            path, xml_declaration=True, pretty_print=pretty_print
        )
