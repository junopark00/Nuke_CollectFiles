import nuke
import collect_files
nuke.menu("Nuke").addCommand("Scripts/Collect Files", collect_files.main)