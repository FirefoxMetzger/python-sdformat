from pysdf import SDF, Link, Sensor, Joint, State, Model


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
    model.links[1].add(Link.ParticleEmitter(
        Link.ParticleEmitter.Emitting(text="true"),
        name="my_emitter",
        type="box"
    ))


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
