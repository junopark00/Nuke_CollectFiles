# Nuke Script Collector

![cf_main](/resource/cf_main.png)

A Python script for collecting Nuke scripts and preparing them for external delivery. This tool ensures compatibility by converting gizmos into group nodes, making it easy to share and use scripts across different environments.


## ✨ Key Features

- Collects Nuke scripts and all associated assets for seamless external sharing.
- Automatically converts gizmo nodes to group nodes to avoid compatibility issues.
<br>![cf_node](/resource/cf_node.png)
- Simplifies the process of packaging and transferring Nuke projects.
<br>![cf_file_knob](/resource/cf_file_knob.png)


## 🚀 Performance Benefits

- Eliminates manual steps in preparing Nuke scripts for delivery.
- Reduces errors caused by missing or incompatible gizmo nodes.
- Streamlines workflow for artists and technical directors.


## 📋 System Requirements

- Nuke 11 or higher
- Python 3.x
- Windows OS (tested)


## 🚀 Installation

1. **Clone or download this repository.**
    ```bash
    git clone https://github.com/junopark00/NukeCollectFiles.git
    ```
2. **Copy to Nuke directory**
    ```bash
    ~/.nuke/NukeCollectFiles
    ```
3. **Add the line to `init.py`**
    ```python
    import nuke
    nuke.pluginAddPath('./NukeCollectFiles')
    ```


## 📖 Usage

1. Run the script via the Nuke menu `Scripts/Collect Files`.
2. Select the path to the scene you want to collect.
3. The script will package all necessary files and convert gizmos to group nodes automatically.
<br>![cf_done](/resource/cf_done.png)
4. Check the collected directory:
    ```text
    collected
    ├── test.nk
    └── footage
        ├── test.mov
        ├── test.jpg
        └── test
            ├── test.1001.exr
            ├── test.1002.exr
            └── ...
    ```

