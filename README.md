# Poser
Poser is a python based animation toolkit for Maya.  
The toolkit comes equiped with a pose library, plotter, auto-aligner and looper.  
  
<p align="center">
  <img width="417" height="779" alt="Poser" src="https://github.com/user-attachments/assets/83791fea-ef90-431b-943c-b6690d53ceb8" />
</p>

## Requirements:
This tool requires the following python packages: [dcc](https://github.com/bhsingleton/dcc) and [mpy](https://github.com/bhsingleton/mpy).  
When downloading these packages from Github make sure to unzip the contents into the Maya scripts folder located inside your user documents folder.  

> [!IMPORTANT]
> Make sure to remove any prefixes from the unzipped folder name!  
> For example: dcc-main > dcc, otherwise the tools will fail to run.

## How to Open:  
Run the following python code from either the script editor or from a shelf button:  

```
from poser.ui import qposer

window = qposer.QPoser()
window.show()
```
