import pytest

from pysdf import SDF, Model, Joint, Link


def test_basic_iter():
    sample_sdf = """<?xml version="1.0" ?>
    <sdf version="1.6">
        <model name="empty_axis">
            <link name="link1" />
            <joint name="joint" type="fixed">
                <parent>link1</parent>
                <child>link2</child>
            </joint>
            <link name="link2" />
        </model>
    </sdf>
    """

    element = SDF.from_xml(sample_sdf)

    gen = element.iter()
    assert isinstance(next(gen), Model)
    assert isinstance(next(gen), Link)
    assert isinstance(next(gen), Joint)
    assert isinstance(next(gen), Link)
    assert isinstance(next(gen), Joint.Parent)
    assert isinstance(next(gen), Joint.Child)
    with pytest.raises(StopIteration):
        next(gen)


def test_element_filter():
    sample_sdf = """<?xml version="1.0" ?>
    <sdf version="1.6">
        <model name="empty_axis">
            <link name="link1" />
            <joint name="joint" type="fixed">
                <parent>link1</parent>
                <child>link2</child>
            </joint>
            <link name="link2" />
        </model>
    </sdf>
    """

    element = SDF.from_xml(sample_sdf)

    gen = element.iter("Link")
    assert isinstance(next(gen), Link)
    assert isinstance(next(gen), Link)
    with pytest.raises(StopIteration):
        next(gen)


def test_tail_filter():
    sample_sdf = """<?xml version="1.0" ?>
    <sdf version="1.6">
        <model name="empty_axis">
            <link name="link1" />
            <joint name="joint" type="fixed">
                <parent>link1</parent>
                <child>link2</child>
            </joint>
            <link name="link2" />
            <model name="nested_model">
                <link name="link1" />
                <joint name="inner_joint" type="fixed">
                    <parent>link1</parent>
                    <child>link2</child>
                </joint>
                <link name="link2" />
            </model>
        </model>
    </sdf>
    """

    element = SDF.from_xml(sample_sdf)

    gen = element.iter("model/model/joint")
    item: Joint = next(gen)
    assert isinstance(item, Joint)
    assert item.name == "inner_joint"
    with pytest.raises(StopIteration):
        next(gen)

    gen = element.iter("model/joint")

    item: Joint = next(gen)
    assert isinstance(item, Joint)
    assert item.name == "joint"

    item: Joint = next(gen)
    assert isinstance(item, Joint)
    assert item.name == "inner_joint"

    with pytest.raises(StopIteration):
        next(gen)


def test_declared_frames():
    sample_sdf = """<?xml version="1.0" ?>
    <sdf version="1.6">
        <model name="empty_axis">
            <link name="link1" />
            <joint name="joint" type="fixed">
                <parent>link1</parent>
                <child>link2</child>
            </joint>
            <link name="link2" />
            <model name="nested_model">
                <link name="link1" />
                <joint name="inner_joint" type="fixed">
                    <parent>link1</parent>
                    <child>link2</child>
                </joint>
                <link name="link2" />
            </model>
        </model>
    </sdf>
    """
    
    element = SDF.from_xml(sample_sdf)
    frames = element.declared_frames()
    assert frames == [
        "__model__",
        "empty_axis",
        "link1",
        "joint",
        "link2",
        "nested_model",
        "nested_model::link1",
        "nested_model::inner_joint",
        "nested_model::link2"
    ]
