# tree-gen
Blender plugin produced as part of my undergraduate dissertation: [Procedural generation of tree models for use in computer graphics](https://chewitt.me/Papers/CTH-Dissertation-2017.pdf).

![Tree Samples](http://chewitt.me/Folio/Trees.jpg)

Thanks to the awesome work of [Luke Pflibsen-Jones](https://github.com/luketimothyjones) you can just drop the `ch_trees` folder into your blender addons folder and enable the plugin in user settings to start generating trees - now with a complete customisation UI! Download the latest version [here](https://github.com/friggog/tree-gen/archive/master.zip).

----

## Documentation

The customizer GUI

[![The customizer interface](https://i.imgur.com/LO0i7SM.jpg)](https://i.imgur.com/AcxtG58.jpg)

&nbsp;

Below is a list of the available parameters and what they do. These can also be found by hovering over the respective input field in the Blender user interface.

--
### Leaf Parameters
--

**Leaf Count** - Number of leaves or blossom on each of the deepest level of branches

**Leaf Shape** - Predefined leaf shapes, rectangle is easiest if wishing to use an image texture
 - Ovate
 - Linear
 - Cordate
 - Maple
 - Palmate
 - Spiky Oak
 - Rounded Oak
 - Elliptic
 - Rectangle
 - Triangle

**Leaf Scale** - Overall leaf scale

**Leaf Width** - Leaf scale in the x-direction (width)

**Leaf Bend** - Fractional amount by which leaves are reoriented to face the light (upwards and outwards)

--

**Blossom Shape** - Predefined blossom shapes
 - Cherry
 - Orange
 - Magnolia

**Blossom Rate** - Fractional rate at which blossom occurs relative to leaves (eg, .4 = 40% of the time a leaf is generated a blossom will be as well)

**Blossom Scale** - Overall blossom scale

&nbsp;

--
### Tree parameters
--

**Tree Shape** - Controls shape of the tree by altering the first level branch length. Custom uses the envelope defined by the pruning parameters to control the tree shape directly rather than through pruning

**Level Count** - Number of levels of branching, typically 3 or 4

--

**Prune Ratio** - Fractional amount by which the effect of pruning is applied

**Prune Width** - Width of the pruning envelope as a fraction of its height (the maximum height of the tree)

**Prune Width Peak** - The fractional distance from the bottom of the pruning up at which the peak width occurs

**Prune Power (low)** - The curvature of the lower section of the pruning envelope. < 1 results in a convex shape, > 1 in concave

**Prune Power (high)** - The curvature of the upper section of the pruning envelope. < 1 results in a convex shape, > 1 in concave

--

**Trunk Splits** - Number of splits at base height on trunk, if negative then the number of splits will be randomly chosen up to a maximum of |base splits|

**Trunk Flare** - How much the radius at the base of the trunk increases

--

**Height** - Scale of the entire tree

**Height variation** - Maximum variation in size of the entire tree

--

**Tropism** - Influence upon the growth direction of the tree in the x, y and z directions, the z element only applies to branches in the second level and above. Useful for simulating the effects of gravity, sunlight and wind

--

**Branch Thickness Ratio** - Ratio of the stem length to radius

**Branch Thickness Ratio Power** - How drastically the branch radius is reduced between branching levels

&nbsp;

--
### Branch Parameters
--

**Number** - The maximum number of child branches at a given level on each parent branch. The first level parameter indicates the number of trunks coming from the floor, positioned in a rough circle facing outwards (see bamboo)

**Length** - The length of branches at a given level as a fraction of their parent branch’s length

**Length Variation** - Maximum variation in branch length

**Base Size** - Proportion of branch on which no child branches/leaves are spawned

**Distribution** - Controls the distribution of branches along their parent stem. 0 indicates fully alternate branching, interpolating to fully opposite branching at 1. Values > 1 indicate whorled branching (as on fir trees) with n + 1 branches in each whorl. Fractional values result in a rounded integer number of branches in each whorl

**Taper** - Controls the tapering of the radius of each branch along its length. If < 1 then the branch tapers to that fraction of its base radius at its end, so a value 1 results in conical tapering. If =2 the radius remains uniform until the end of the stem where the branch is rounded off in a hemisphere, fractional values between 1 and 2 interpolate between conical tapering and this rounded end. Values > 2 result in periodic tapering with a maximum variation in radius equal to the value − 2 of the base radius** - so a value of 3 results in a series of adjacent spheres (see palm trunk)

**Radius Modifier** - (no description)

--

**Curve Resolution** - Number of segments in each branch

**Curve** - Angle by which the direction of the branch will change from start to end, rotating about the branch’s local x-axis

**Curve Variation** - Maximum variation in curve angle of a branch. Applied randomly at each segment

**Curve Back** - Angle in the opposite direction to the curve that the branch will curve back from half way along, creating S shaped branches

**Segment Splits** - Maximum number of dichotomous branches (splits) at each segment of a branch, fractional values are distributed along the branches semi-randomly

**Split Angle** - Angle between dichotomous branches

**Split Angle Variation** - Maximum variation in angle between dichotomous branches

--

**Bend Variation** - Maximum angle by which the direction of the branch may change from start to end, rotating about the branch’s local y-axis. Applied randomly at each segment

--

**Down Angle** - Controls the angle of the direction of a child branch away from that of its parent

**Down Angle Variation** - Maximum variation in down angle, if < 0 then the value of down angle is distributed along the parent stem

--

**Rotation** - Angle around the parent branch between each child branch. If < 0 then child branches are directed this many degrees away from the downward direction in their parent's local basis (see palm leaves). For fanned branches, the fan will spread by this angle and for whorled branches, each whorl will rotate by this angle

**Rotation Variation** - Maximum variation in angle between branches. For fanned and whorled branches, each branch will vary in angle by this much
