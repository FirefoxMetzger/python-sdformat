from pysdf import SDF, Link, Sensor, Joint, State, Model
import numpy as np


def test_read_write_roundtrips(tmp_path):
    # This basically just checks for crashes

    sample_sdf = """<?xml version="1.0" ?>
    <sdf version="1.6">
        <model name="empty_axis">
            <link name="link1" />
            <link name="link2" />
            <joint name="joint" type="fixed">
                <parent>link1</parent>
                <child>link2</child>
            </joint>
        </model>
    </sdf>
    """

    # string round-trip
    parsed = SDF.from_xml(sample_sdf)
    sdf_string = parsed.to_xml()

    # file round-trip
    parsed.to_file(tmp_path / "sample.sdf")
    parsed = SDF.from_file(tmp_path / "sample.sdf")


def test_modification_basics():
    element = Link()
    assert element.to_xml() == "<link/>"

    element.inertial
    assert element.to_xml() == "<link><inertial/></link>"

    element.inertial.mass
    assert element.to_xml() == "<link><inertial/></link>"

    element.inertial.mass = 5.0
    assert element.to_xml() == "<link><inertial><mass>5.0</mass></inertial></link>"

    assert element.inertial.inertia.ixx == 1.0

    element = State.Model()
    element.scale = "1 2 3"
    assert element.scale == (1.0, 2.0, 3.0)
    element.scale = [5, 5, 5]
    assert element.scale == (5.0, 5.0, 5.0)

    element = Model()
    element.add(Link(name="test"))
    element.add(Link(name="test2"), Link(name="test3"))
    assert len(element.links) == 3


def test_sample_modification():
    sample_sdf = """<?xml version="1.0" ?>
    <sdf version="1.6">
        <model name="empty_axis">
            <link name="link1" />
            <link name="link2" />
            <joint name="joint" type="fixed">
                <parent>link1</parent>
                <child>link2</child>
            </joint>
        </model>
    </sdf>
    """

    parsed = SDF.from_xml(sample_sdf)
    model = parsed.model

    model.name = "modified_model"
    model.links[1].add(
        Link.ParticleEmitter(
            Link.ParticleEmitter.Emitting(text="true"), name="my_emitter", type="box"
        )
    )


def test_creation(tmp_path):
    element = SDF(
        Model(
            Link(name="link1"),
            Link(name="link2"),
            Joint(
                Joint.Parent(text="link1"),
                Joint.Child(text="link2"),
                name="joint",
            ),
            name="empty_axis",
        ),
        version="1.6",
    )

    element.to_file(tmp_path / "sample.sdf", pretty_print=True)


def test_iter_and_filter(tmp_path):
    # taken from: https://github.com/ignitionrobotics/sdformat/blob/4b83e96562eb6e28696a608bc70c2c03cc299773/test/sdf/joint_nested_parent_child.sdf
    large_example = """
    <sdf version="1.8">
    <model name="joint_nested_parent_child">
        <model name="M1">
        <link name="L1">
            <pose>0 0 1 0 0 0</pose>
        </link>
        <link name="L2">
            <pose>1 1 0 0 0 0</pose>
        </link>
        <frame name="F1">
            <pose>1 0 0 0 0 0</pose>
        </frame>
        <model name="M2">
            <pose>0 0 1 1.570796326790 0 0</pose>
            <link name="L1"/>
        </model>
        </model>

        <link name="L1">
        <pose>0 0 10 0 1.57079632679 0</pose>
        </link>

        <frame name="F1" attached_to="M1::L1">
        <pose>1 0 0 0 0 0</pose>
        </frame>

        <!-- Joint with a parent link in a nested model -->
        <joint name="J1" type="fixed">
        <pose>1 0 0 0 0 0</pose>
        <parent>M1::L1</parent>
        <child>L1</child>
        </joint>
        <!-- Joint with a sibling parent frame which is attached to a link in a nested model -->
        <joint name="J2" type="fixed">
        <pose>0 1 0 0 0 0</pose>
        <parent>F1</parent>
        <child>L1</child>
        </joint>
        <!-- Joint with a child link in a nested model -->
        <joint name="J3" type="fixed">
        <pose>0 0 1 0 0 0</pose>
        <parent>L1</parent>
        <child>M1::L2</child>
        </joint>

        <!-- Joint with a child frame in a nested model -->
        <joint name="J4" type="fixed">
        <pose>0 0 1 0 0 0</pose>
        <parent>L1</parent>
        <child>M1::F1</child>
        </joint>

        <!-- Joint with a child model in a nested model -->
        <joint name="J5" type="fixed">
        <pose>0 0 1 0 0 0</pose>
        <parent>L1</parent>
        <child>M1::M2</child>
        </joint>

        <!-- Joint with a nested model frame as a parent  -->
        <joint name="J6" type="fixed">
        <pose>0 0 1 0 0 0</pose>
        <parent>M1::__model__</parent>
        <child>L1</child>
        </joint>

        <!-- Joint with a nested model frame as a child  -->
        <joint name="J7" type="fixed">
        <pose>0 0 1 0 0 0</pose>
        <parent>L1</parent>
        <child>M1::__model__</child>
        </joint>
    </model>
    </sdf>
    """

    element = SDF.from_xml(large_example, remove_blank_text=True)
    element.version = "1.9"

    for pose in element.iter("pose"):
        pose.degrees = True
        pose_ndarray = np.fromstring(pose.text, count=6, sep=" ")
        rotation_rad = pose_ndarray[3:]
        rotation_deg = rotation_rad / (2 * np.pi) * 360
        pose_ndarray[3:] = rotation_deg
        pose.text = " ".join(map(str, pose_ndarray))

    for link in element.iter("model/model/link"):
        link.self_collide = True

    for link in element.models[0].iter("link"):
        link.self_collide = False

    element.to_file(tmp_path / "sample.sdf", pretty_print=True)
