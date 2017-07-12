# tree-gen
Procedural generation of tree models in blender

![Tree Samples](http://chewitt.me/Folio/Trees.jpg)

Read the write up [here](http://chewitt.me/CTH-Dissertation-2017.pdf).

I'd love to develop this into a fully usable blender plugin but don't currently have the time, if anyone would like to I'd very much support this.

If you want to try out the code as is:
* Copy ch_trees into the blender addons folder (`.../blender.app/Contents/Resources/2.78/scripts/addons` on mac)
* Restart blender
* Start a new blend file and in the text editor panel open `.../ch_trees/parametric/gen.py` or `.../ch_trees/lsystems/treegen.py`
* Uncomment the final few lines including `construct(...)`
* Run the script (it will take a few seconds, or more, to generate the tree so don't worry if blender appears to freeze - if you open blender through the command line then you can track the progress)
* You can change the `quaking_aspen` bit inside `construct(...)` to generate different types of trees - see `.../parametric/tree_params` and `.../lsystems/sys_defs` for available presets. You can also edit/create new tree types.

(apologies for such a protracted process, this is why I'd love to incorporate it into an actual plugin - hopefully I or someone else will get around to this soon)

[CC BY-NC-SA 3.0 License](https://creativecommons.org/licenses/by-nc-sa/3.0/)
