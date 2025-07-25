# Poser
Poser is a python based animation toolkit for Maya.  
The toolkit comes equiped with a pose library, plotter, auto-aligner and looper.  
  
<p align="center">
  <img width="417" height="779" alt="image" src="https://github.com/user-attachments/assets/2a8bec80-a1b1-458c-a8e0-aecf07859ecf" />
</p>

## Requirements:
This tool requires the following python packages: [dcc](https://github.com/bhsingleton/dcc) and [mpy](https://github.com/bhsingleton/mpy).  
When downloading these packages from Github make sure to unzip the contents into the Maya scripts folder located inside your user documents folder.  
It is important to remove any prefixes from the unzipped folder name: `dcc-main` > `dcc`, otherwise the tools will fail to run!  

## How to Open:  
Run the following python code from either the script editor or from a shelf button:  

```
from qezposer.ui import qezposer

window = qezposer.QEzPoser()
window.show()
```
