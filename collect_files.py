import os
import shutil
import re
import concurrent.futures

import nuke

class FileCollector:
    def __init__(self):
        self.video_exts = (
            'mov', 'avi', 'mp4', 'mpeg', 'mpg', 
            'r3d', 'mxf', 'mkv', 'flv', 'webm'
            )
        self.task = nuke.ProgressTask("Collecting Files")
        self.cancelled = False

    def show_panel(self) -> tuple:
        """
        Show a panel to get the output path from the user.

        Returns:
            tuple: A tuple containing the panel result and the output path.
        """
        panel = nuke.Panel("Collect Files v1.0.0")
        panel.setWidth(500)
        panel.addFilenameSearch("Output Path:", "")
        panel.addButton("Cancel")
        panel.addButton("OK")
        return panel.show(), panel.value("Output Path:")

    def has_knob(self, node: nuke.Node, knob: str) -> bool:
        return knob in node.knobs()

    def copy_file(self, src: str, dst: str) -> None:
        """
        Copy a single file from src to dst.

        Args:
            src (str): The source file path.
            dst (str): The destination file path.
        """
        src = os.path.normpath(src)
        dst = os.path.normpath(dst)
        
        try:
            if os.path.exists(src):
                shutil.copy2(src, dst)
                nuke.tprint(f"[COPY] {src} -> {dst}")
            else:
                nuke.tprint(f"[ERROR] Source file does not exist: {src}")
        except Exception as e:
            nuke.tprint(f"[EXCEPTION] Copy failed: {src} -> {dst}\n{e}")

    def copy_sequence_parallel(
        self, 
        file_path: str, 
        output_dir: str, 
        frame_start: int, 
        frame_end: int) -> None:
        """
        Copy an image sequence in parallel using threading.

        Args:
            file_path (str): The path to the image sequence file.
            output_dir (str): The directory where the copied files will be saved.
            frame_start (int): The starting frame number.
            frame_end (int): The ending frame number.
        """
        basename = os.path.basename(file_path)
        dirpath = os.path.dirname(file_path)
        dirname = os.path.basename(dirpath)
        new_dir = os.path.join(output_dir, dirname)
        os.makedirs(new_dir, exist_ok=True)

        nuke.tprint(f"[INFO] Copying sequence: {basename} (Frames {frame_start}~{frame_end})")
        nuke.tprint(f"[INFO] Output folder: {new_dir}")

        # Various padding styles: %04d, %d, ####
        match = re.search(r'(%0?\d*d|#+)', basename)
        if not match:
            nuke.tprint(f"[ERROR] No recognized padding found in: {basename}")
            return

        pad_token = match.group(1)
        if pad_token.startswith('%'):
            pad_search = re.search(r'\d+', pad_token)
            pad_len = int(pad_search.group()) if pad_search else 1
            pattern = r'%0?\d*d'
        else:
            pad_len = len(pad_token)
            pattern = r'#+'

        tasks = []
        for frame in range(frame_start, frame_end + 1):
            frame_str = str(frame).zfill(pad_len)
            file_name = re.sub(pattern, frame_str, basename)
            src = os.path.join(dirpath, file_name)
            dst = os.path.join(new_dir, file_name)
            tasks.append((src, dst, file_name))

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for src, dst, name in tasks:
                if self.task.isCancelled():
                    self.cancelled = True
                    break
                nuke.tprint(f"[FRAME] Copying frame {name}")
                self.task.setMessage(f"Collecting frame: {name}")
                futures.append(executor.submit(self.copy_file, src, dst))
            concurrent.futures.wait(futures)

    def update_node_path(self, node: nuke.Node) -> None:
        """
        Update the file path of a node to the new collected location.

        Args:
            node (nuke.Node): The node whose file path is to be updated.
        """
        file_path = node['file'].value()
        basename = os.path.basename(file_path)
        if self.has_knob(node, 'first') and node['first'].value() != node['last'].value() and os.path.splitext(file_path)[-1][1:].lower() not in self.video_exts:
            subdir = os.path.basename(os.path.dirname(file_path))
            new_path = f'[file dirname [value root.name]]/footage/{subdir}/{basename}'
        else:
            new_path = f'[file dirname [value root.name]]/footage/{basename}'
        nuke.tprint(f"[UPDATE] Node {node.name()} file path updated to: {new_path}")
        node['file'].setValue(new_path)

    def collect(self) -> None:
        """
        Main function to collect files used in the Nuke script.
        """
        result, target_path = self.show_panel()
        if result != 1 or not target_path:
            nuke.tprint("[CANCELLED] Collect cancelled or no output path specified.")
            return

        if os.path.isfile(target_path):
            target_path = os.path.dirname(target_path)
        target_path = target_path.rstrip(os.path.sep) + os.path.sep

        if not os.path.exists(target_path):
            if nuke.ask("Directory does not exist. Create now?"):
                os.makedirs(target_path)
            else:
                nuke.message("Cannot proceed without valid target directory.")
                return

        footage_path = os.path.join(target_path, "footage")
        os.makedirs(footage_path, exist_ok=True)

        script_name = os.path.basename(nuke.root()['name'].value())
        self.convert_gizmo_to_group()
        
        all_nodes = nuke.allNodes()

        for i, node in enumerate(all_nodes):
            if self.task.isCancelled():
                self.cancelled = True
                break

            self.task.setProgress(i * 100 // len(all_nodes))
            self.task.setMessage(f"Processing node: {node.name()}")

            if not self.has_knob(node, 'file') or self.has_knob(node, 'Render'):
                continue

            file_path = node['file'].value()
            if not file_path:
                continue

            ext = os.path.splitext(file_path)[-1][1:].lower()

            if ext in self.video_exts:
                dst = os.path.join(footage_path, os.path.basename(file_path))
                self.copy_file(file_path, dst)
            elif self.has_knob(node, 'first'):
                first = int(node['first'].value())
                last = int(node['last'].value())
                if first == last:
                    dst = os.path.join(footage_path, os.path.basename(file_path))
                    self.copy_file(file_path, dst)
                else:
                    self.copy_sequence_parallel(file_path, footage_path, first, last)
            else:
                dst = os.path.join(footage_path, os.path.basename(file_path))
                self.copy_file(file_path, dst)

        if self.cancelled:
            nuke.message("Collect cancelled.")
            return

        new_script_path = os.path.join(target_path, script_name)
        nuke.scriptSaveAs(new_script_path)

        for node in all_nodes:
            if self.has_knob(node, 'file') and not self.has_knob(node, 'Render'):
                self.update_node_path(node)

        nuke.tprint("Collect done!")
        nuke.message("Collect done!")
        
    def convert_gizmo_to_group(self):
        if not nuke.allNodes():
            return
        no_gizmo_selection = []
        gizmo_selection = []
        for node in nuke.allNodes():
            if 'gizmo_file' in node.knobs():
                gizmo_selection.append(node)
            else:
                no_gizmo_selection.append(node)
        group_selection = []
        error_selection = []

        for node in gizmo_selection:
            # Current Status Variables
            node_name = node.knob('name').value()
            xpos = node['xpos'].value()
            ypos = node['ypos'].value()
            hide_input = node.knob('hide_input').value()
            cached = node.knob('cached').value()
            postage_stamp = node.knob('postage_stamp').value()
            disable = node.knob('disable').value()
            dope_sheet = node.knob('dope_sheet').value()
            tile_color = node.knob('tile_color').value()
            max_inputs = node.maxInputs()
            input_list = []

            # Current Node Isolate Selection
            for n in nuke.allNodes():
                n.knob('selected').setValue(False)
            node.knob('selected').setValue(True)
            
            try:
                nuke.tcl('copy_gizmo_to_group [selected_node]')
            except:
                # Skip ImagePlane gizmos - they often have issues converting
                if "ImagePlane" not in node_name:
                    import traceback
                    nuke.tprint(f"Error converting gizmo '{node_name}': {traceback.format_exc()}")
                    gizmo_selection.remove(node)
                    error_selection.append(node)
                    continue

            # Refresh selections
            group_selection.append(nuke.selectedNode())
            new_group = nuke.selectedNode()

            # Paste Attributes
            new_group.knob('xpos').setValue(xpos)
            new_group.knob('ypos').setValue(ypos)
            new_group.knob('hide_input').setValue(hide_input)
            new_group.knob('cached').setValue(cached)
            new_group.knob('postage_stamp').setValue(postage_stamp)
            new_group.knob('disable').setValue(disable)
            new_group.knob('dope_sheet').setValue(dope_sheet)
            new_group.knob('tile_color').setValue(tile_color)

            # Connect Inputs
            for f in range(0, max_inputs):
                input_list.append(node.input(f))
            for num, r in enumerate(input_list):
                new_group.setInput(num, None)
            for num, s in enumerate(input_list):
                new_group.setInput(num, s)
    
            node.knob('name').setValue(node_name + '_gizmo')
            new_group.knob('name').setValue(node_name)
    
            new_group.knob('selected').setValue(False)

        # Cleanup (remove gizmos, leave groups)
        for y in gizmo_selection:
            y.knob('selected').setValue(True)
            nuke.delete(y)
        for z in group_selection:
            z.knob('selected').setValue(True)
        for w in no_gizmo_selection:
            w.knob('selected').setValue(True) 
        
        if error_selection:
            nuke.alert(f"Failed to convert {len(error_selection)} gizmos to groups.")


def main():
    collector = FileCollector()
    collector.collect()