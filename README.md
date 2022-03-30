# PySDF (python-sdformat)

PySDF is a set of python bindings for [SDFormat XML](http://sdformat.org/). The
idea is to provide a method for working with SDF that feels as fast as (or
faster than) XML, but with the added convenience of syntax highlighting,
auto-completion, validation, and some degree of verification.

The current bindings read SDF from _any_ version and will parse it into a
generic representation. Modifications are not validated or verified by default,
allowing for more flexibility, but methods for optional validation and
verification will be added in the future.

## Installation

```
pip install python-sdformat
```

## Usage

The elements of the binding are grouped following the [official SDF
spec](http://sdformat.org/spec) with a few exceptions. This means that you can
find the item you are looking for by following the spec's nesting, e.g., the
`/sensor/imu/angular_velocity/x` element has the corresponding class
`pysdf.Sensor.Imu.AngularVelocity.X` and can - inside an SDF - be accessed as
`parsed_sensor.imu.angular_velocity.x`. The previously mentioned exceptions to
this are:

- The bindings use `snake_case` for variable names and `CamelCase` for class names
- If an element may occur more than once inside its parent, its corresponding attribute
  will be a tuple its name will be plural, e.g. `world.models[idx]`.
- The elements `Pose`, `Frame`, `Plugin`, and `Include` occur frequently across
  several elements and promoted to the top level, i.e., you'd use `pysdf.Pose` not
  `pysdf.Model.Pose`.

## Examples

**Basic Reading and Writing**

```python
from pysdf import SDF

sample_sdf = """<?xml version="1.0" ?>
<sdf version="1.6">
    <model name="empty_axis">
        <link name="link1" />
        <link name="link2" />
        <joint name="joint" type="fixed">
        <parent>link1</parent>
        <child>link2</child>
        <axis/>
        </joint>
    </model>
</sdf>
"""

# string round-trip
parsed = SDF.from_xml(sample_sdf)
sdf_string = SDF.to_xml()

# file round-trip
SDF.to_file("sample.sdf")
parsed = SDF.from_file("sample.sdf")

# prettify/reformat SDF to have nice indentation
SDF.to_file("sample.sdf", remove_blank_text=True)
parsed = SDF.from_file("sample.sdf", pretty_print=True)

```

**Building SDF manually**

```python
from pysdf import SDF; Link, Joint

reference_sdf = """
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

element = SDF(
    Model(
        Link(name="link1"),
        Link(name="link2"),
        Joint(
            Joint.Parent(text="link1"),
            Joint.Child(text="link2"),
            # attributes are set at the end
            # because python only accepts kwargs at the end.
            name="joint",
        ),
        name="empty_axis",
    ),
    version="1.6",
)

element.to_file("sample.sdf", pretty_print=True)
```

**Basic Modifications**

```python
from pysdf import Link, State, Model, Link

# Complex elements (with own children) are added on first read
element = Link()
element.to_xml()  # "<link/>"
element.inertial
element.to_xml()  # "<link><inertial/></link>"

# Simple elements (basic types) are added on first write (__set__):
element.inertial.mass
element.to_xml()  # "<link><inertial/></link>"
element.inertial.mass = 5.0
element.to_xml() 
# "<link><inertial><mass>5.0</mass></inertial></link>"

# default values are populated where applicable
assert element.inertial.inertia.ixx == 1.0

# Where possible types are converted automatically
element = State.Model()
element.scale  # (1.0, 1.0, 1.0), tuple
element.scale = "1 2 3"
assert element.scale == (1.0, 2.0, 3.0)
element.scale = [5, 5, 5]
assert element.scale == (5.0, 5.0, 5.0)

# Inserting children works from sequences of kwargs
element = Model()
element.add(Link(name="test"))
element.add(Link(name="test2"), Link(name="test3"))
element.to_xml() 
# '<model><link name="test"/><link name="test2"/><link name="test3"/><pose/></model>'
```

**Full Modification Example**

```python
from pysdf import SDF, Link

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
```

**Iterating and Filtering**

You can call `element.iter()` to recursively iterate over all child elements of
a subtree (breadth-first). `iter()` also accepts a `filter` kwarg which allows
you to only return children that have a desired path from the caller to the
child. The filter matches the tail of the path, path elements are separated by
the `/` character, and any SDF tag is a valid path element. This allows for easy
selecting and bulk editing of specific children, e.g., use `filter="pose"` to
select all pose elements in a SDF or `filter="model/pose"` to select all pose
elements that are direct children of a model (the model's pose).


Appologies for the long example SDF, but I thought it would be nice to
demonstrate something more real-world.

```python
from pysdf import SDF
import numpy as np

# taken from: 
# https://github.com/ignitionrobotics/sdformat/blob/sdf12/test/sdf/joint_nested_parent_child.sdf
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

# remove_blank_text strips whitespace to allow neat formatting
# later on
element = SDF.from_xml(large_example, remove_blank_text=True)
element.version = "1.9"  # v1.9 supports pose/@degrees

# convert all poses to degrees
for pose in element.iter("pose"):
    pose.degrees = True
    pose_ndarray = np.fromstring(pose.text, count=6, sep=" ")
    rotation_rad = pose_ndarray[3:]
    rotation_deg = rotation_rad / (2*np.pi) * 360
    pose_ndarray[3:] = rotation_deg
    pose.text = " ".join(map(str, pose_ndarray))

# turn on self-collision for all links in the nested model
for link in element.iter("model/model/link"):
    link.self_collide = True

# turn self-collision off (using a different syntax)
for link in element.models[0].iter("link"):
    link.self_collide = False

# offset all links by some vector
for pose in element.iter("link/pose"):
    pose_ndarray = np.fromstring(pose.text, count=6, sep=" ")
    pose_ndarray[:3] += (0, 0, 1)
    pose.text = " ".join(map(str, pose_ndarray))

element.to_file("sample.sdf", pretty_print=True)
```
