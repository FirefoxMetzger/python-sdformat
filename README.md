# PySDF (python-sdformat)

PySDF is a set of python bindings for SDFormat XML. The idea is to provide a
method for working with SDF that feels as fast as (or faster than) XML, but with
the added convenience of syntax highlighting, auto-completion, validation, and
some degree of verification.

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

**Sample Modification**

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


**Manual SDF creation**

```python

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

element.to_file(tmp_path / "sample.sdf", pretty_print=True)
```